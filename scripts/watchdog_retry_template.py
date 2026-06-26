#!/usr/bin/env python3
"""看门狗重试标准流程模板 — 检查文件 → token 预检 → 数据采集 → JSON 构建 → 上报。

用法：
    1. 复制此文件到 /tmp/watchdog_review.py
    2. 修改 DATE / TITLE 变量
    3. 在 collect_data() 中填入实际的数据采集逻辑
    4. 运行 python3 /tmp/watchdog_review.py

本模板适用于 cron 模式（无用户在场），依赖：
- /usr/local/files/docs/stock/YYYY-MM-DD-A股复盘.{md,json} 检查与生成
- 复盘 API 上报到 https://xiaoniu.tech/api/stock/reviews
- Tencent 行情 API + Sina /tob/ 收评文章 + 东财 push2 API
"""
import json
import os
import sys
import urllib.request
import urllib.error
import re

# ============ 配置区 ============
DATE = "2026-06-25"  # 复盘日期
TITLE_PATTERN = "{year}年{month}月{day}日（周三）A股复盘"
LOCAL_DIR = "/usr/local/files/docs/stock"
LOCAL_MD = f"{LOCAL_DIR}/{DATE}-A股复盘.md"
LOCAL_JSON = f"{LOCAL_DIR}/{DATE}-A股复盘.json"
API_URL = "https://xiaoniu.tech/api/stock/reviews"
MIN_FILE_SIZE = 5 * 1024  # 5KB 阈值


# ============ Step 1: 检查文件 ============
def check_existing_files():
    """如果主任务已生成文件（>5KB），不执行重试，返回 True。"""
    if os.path.exists(LOCAL_JSON) and os.path.getsize(LOCAL_JSON) > MIN_FILE_SIZE:
        print(f"[SILENT] 主任务已成功: {LOCAL_JSON} ({os.path.getsize(LOCAL_JSON)} bytes)")
        return True
    print(f"[WARN] 文件不存在或太小: {LOCAL_JSON}")
    return False


# ============ Step 2: token 预检 ============
def get_api_key():
    """从 ~/.profile 读取 STOCK_REVIEW_API_KEY（cron 模式不继承 shell 环境变量）。"""
    api_key = os.environ.get('STOCK_REVIEW_API_KEY', '')
    if not api_key:
        profile_path = os.path.expanduser('~/.profile')
        try:
            with open(profile_path, 'r') as f:
                for line in f:
                    if 'STOCK_REVIEW_API_KEY' in line and 'export' in line:
                        line = line.strip()
                        if line.startswith('export '):
                            line = line[7:]
                        _, _, val = line.partition('=')
                        val = val.strip()
                        if val.startswith('"') and val.endswith('"'):
                            val = val[1:-1]
                        elif val.startswith("'") and val.endswith("'"):
                            val = val[1:-1]
                        api_key = val
                        break
        except Exception as e:
            print(f"[ERROR] 读取 ~/.profile 失败: {e}", file=sys.stderr)
            return None
    return api_key


def precheck_token(api_key):
    """用最小 payload 测试 token 有效性。返回 True 表示可继续。"""
    if not api_key:
        print("[ERROR] API key 未配置", file=sys.stderr)
        return False
    print(f"[INFO] API key length: {len(api_key)}, prefix: {api_key[:10]}")

    data = json.dumps({"date": DATE, "content": "ping"}).encode('utf-8')
    req = urllib.request.Request(
        API_URL, data=data,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode('utf-8', errors='replace')
        try:
            result = json.loads(body)
        except json.JSONDecodeError:
            print(f"[ERROR] 非 JSON 响应: {body}", file=sys.stderr)
            return False
        code = result.get('code', -1)
        msg = result.get('msg', '')
        if code == 200:
            print(f"[INFO] Token 完全有效（code 200）")
            return True
        elif code == 400:
            # 鉴权通过但 payload 格式问题 — 这是好信号
            print(f"[INFO] Token 有效（code 400 鉴权通过: {msg}）")
            return True
        elif code == 401:
            print(f"[ERROR] Token 已过期: {msg}", file=sys.stderr)
            return False
        else:
            print(f"[WARN] 未知 code: {code} {msg}", file=sys.stderr)
            return False
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')
        print(f"[ERROR] HTTP {e.code}: {body}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return False


# ============ Step 3: 数据采集 ============
def fetch_tencent_indices():
    """通过腾讯 API 拉取主要 A 股指数。"""
    indices_codes = [
        ("sh000001", "上证指数"),
        ("sz399001", "深证成指"),
        ("sz399006", "创业板指"),
        ("sh000016", "上证50"),
        ("sh000300", "沪深300"),
        ("sh000905", "中证500"),
        ("sh000688", "科创50"),
    ]
    codes_str = ",".join([c for c, _ in indices_codes])
    url = f"https://qt.gtimg.cn/q={codes_str}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = resp.read().decode('gbk', errors='replace')

    results = []
    for code, name in indices_codes:
        m = re.search(rf'v_{code}="([^"]+)"', data)
        if not m:
            continue
        fields = m.group(1).split('~')
        if len(fields) < 35:
            continue
        results.append({
            'code': code.replace('sh', '').replace('sz', ''),
            'name': fields[1],
            'close': float(fields[3]),
            'changePercent': float(fields[32]),
            'reason': "通过腾讯 API 拉取",
        })
    return results


def fetch_sina_tob_article():
    """从 Sina 财经首页找到 /tob/ 综合收评文章并提取正文。"""
    # Step 1: 找到 URL
    url = "https://finance.sina.com.cn/stock/"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        html = resp.read().decode('utf-8', errors='replace')

    tob_url = None
    for href in re.findall(r'href="(https://finance\.sina\.com\.cn/tob/[^"]+)"', html):
        if DATE in href:
            tob_url = href
            break
    if not tob_url:
        return None

    # Step 2: 抓取文章
    req = urllib.request.Request(tob_url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        raw_html = resp.read().decode('utf-8', errors='replace')

    # Step 3: 提取标题
    title_m = re.search(r'<title>([^<]+)</title>', raw_html)
    title = title_m.group(1) if title_m else "收评"

    # Step 4: 提取正文（用 <p> fallback）
    paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', raw_html, re.DOTALL)
    body = '\n'.join(paragraphs)
    body = re.sub(r'<[^>]+>', '', body)
    body = re.sub(r'&nbsp;', ' ', body)
    body = re.sub(r'\s+', ' ', body).strip()

    return {
        'url': tob_url,
        'title': title,
        'body': body,
    }


def fetch_tencent_stocks(codes):
    """通过腾讯 API 批量查询个股。codes 是 [(code, name), ...]。"""
    codes_str = ",".join([c for c, _ in codes])
    url = f"https://qt.gtimg.cn/q={codes_str}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = resp.read().decode('gbk', errors='replace')

    results = {}
    for code, name in codes:
        m = re.search(rf'v_{code}="([^"]+)"', data)
        if not m:
            continue
        fields = m.group(1).split('~')
        if len(fields) < 35:
            continue
        results[code] = {
            'code': code,
            'name': fields[1],
            'current': float(fields[3]),
            'changePercent': float(fields[32]),
        }
    return results


# ============ Step 4: 组装 JSON ============
def build_review(indices, article, stocks):
    """组装复盘 JSON。注意：当且仅当早盘快报时才有 focusSectors/focusStocks。"""
    if article is None:
        article_summary = f"复盘 {DATE} 数据。"
    else:
        # 提取开篇段（核心盘面）作为 summary
        article_summary = article['body'][:500] if article else ""

    return {
        "date": DATE,
        "title": TITLE_PATTERN.format(year=DATE[0:4], month=int(DATE[5:7]), day=int(DATE[8:10])),
        "markets": {
            "summary": article_summary,
            "indices": indices,
            "volume": "数据见正文",
        },
        "todayHot": {
            "topSectors": [],  # 由实际分析填入
            "concepts": [],
            "fallingSectors": [],
            "summary": "数据见正文",
        },
        "news": [],
        "content": "",  # 完整 markdown body 在最后填入
    }


# ============ Step 5: 上报 API ============
def upload_review(api_key, data):
    """上报复盘 JSON 到 xiaoniu.tech API。"""
    payload = json.dumps(data, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(
        API_URL, data=payload,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read().decode('utf-8', errors='replace')
        result = json.loads(body)
        if result.get('code') == 200:
            data_obj = result.get('data', {})
            record_id = data_obj.get('_id', 'unknown')
            print(f"[SUCCESS] 上报成功: _id={record_id}")
            return True
        else:
            print(f"[ERROR] 上报失败: {result}", file=sys.stderr)
            return False
    except Exception as e:
        print(f"[ERROR] 上报异常: {e}", file=sys.stderr)
        return False


# ============ 主流程 ============
def main():
    # Step 1: 检查文件
    if check_existing_files():
        return 0  # 不执行重试

    # Step 2: token 预检
    api_key = get_api_key()
    if not api_key:
        return 1
    if not precheck_token(api_key):
        return 1

    # Step 3: 数据采集
    print("[INFO] 拉取指数...")
    indices = fetch_tencent_indices()
    print(f"[INFO] 拉取到 {len(indices)} 个指数")

    print("[INFO] 拉取 Sina /tob/ 文章...")
    article = fetch_sina_tob_article()
    if article:
        print(f"[INFO] 文章标题: {article['title']}")
        print(f"[INFO] 正文长度: {len(article['body'])} 字符")
    else:
        print("[WARN] 未找到 Sina /tob/ 文章")

    # Step 4: 组装 JSON（需根据实际文章内容填充）
    data = build_review(indices, article, {})

    # Step 5: 上报
    if upload_review(api_key, data):
        return 0
    return 1


if __name__ == '__main__':
    sys.exit(main())
