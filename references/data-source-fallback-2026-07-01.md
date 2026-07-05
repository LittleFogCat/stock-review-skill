# 数据源回退矩阵（2026-07-01 实测快照）

**触发场景**：东财 push2 API 完全不可用时，复盘板块/涨停数据如何采集。

**环境**：本服务器（Linux，外部 IP 经云厂商 NAT）。其他服务器可能 push2 仍可用，先 ping 测试。

---

## 1. 状态快照（2026-07-01 15:15 实测）

| 数据源 | 状态 | 失败模式 | 备注 |
|--------|------|----------|------|
| 腾讯 API `qt.gtimg.cn` 指数 | ✅ 稳定 | - | 9 个主要指数 100% 可用 |
| 腾讯 API `qt.gtimg.cn` 个股 | ✅ 稳定 | - | 50+ 只批量查询正常 |
| 腾讯 API pt 板块代码 | ✅ 稳定 | - | 17 个申万二级板块，覆盖度有限 |
| **东财 push2 API** | ❌ **完全不可用** | `Remote end closed` / `Empty reply` | 5+ Referer 全部失败 |
| akshare `_em` 系列 | ❌ 不可用 | - | 早就被封 |
| akshare THS 行业/概念 | ❌ 不可用 | - | 同花顺改页面结构 |
| JRJ 首页 | ❌ 死页面 | - | 仅 12-13KB 导航 |
| **Sina `/cpbd/` 操盘必读** | ✅ **15:15 后稳定** | - | 11KB 全文，含消息分类 |
| Sina `/cpbd/` 8:00 前 | ❌ 403 Forbidden | - | 编辑团队未更新 |
| **Sina `/tob/` 综合收评** | ⚠️ 部分 | SSR 仅有专题语（< 100 字符），需用 title+meta desc 提取 | description 字段可能 stale |
| **Sina 首页标题** | ✅ 稳定 | - | 含板块/涨停/异动/收评等关键词的标题 |
| **Sina snipe 实时异动** | ✅ 稳定 | - | 14:05/14:35/14:50 多时段更新 |
| Sina `/roll/` 滚动 | ✅ 稳定 | - | 8:00 前唯一可用新闻源 |

---

## 2. 板块数据采集回退流程

### Step 1：尝试东财 push2（1 次，立即失败回退）

```python
import urllib.request, json

def try_em_push2(fs, po, pz=20, timeout=10):
    """尝试 push2 API，失败立即返回 None"""
    url = f"https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz={pz}&po={po}&np=1&fltt=2&invt=2&fid=f3&fs={fs}&fields=f1,f2,f3,f4,f12,f14"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://quote.eastmoney.com/"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8", errors="replace"))
        return data.get("data", {}).get("diff", [])
    except Exception as e:
        print(f"  push2 失败 ({fs}): {e}")
        return None

# 快速测试
result = try_em_push2("m:90+t:2", 1)
if result is None:
    # Step 2: 走回退路径
    pass
```

### Step 2：腾讯 pt 板块代码（17 个，覆盖主要热点）

```python
import urllib.request, re

pt_codes = {
    "pt01801110": "家用电器", "pt01801083": "元件(PCB/覆铜板)",
    "pt01801084": "光学光电子", "pt01801085": "消费电子",
    "pt01801086": "电子化学品", "pt01801039": "非金属材料",
    "pt01801082": "其他电子Ⅱ", "pt01801055": "工业金属",
    "pt01801053": "贵金属", "pt01801104": "软件开发",
    "pt01801103": "IT服务", "pt01801017": "养殖业",
    "pt01801015": "渔业", "pt01801081": "半导体",
    "pt01801080": "电子", "pt01801054": "小金属",
    "pt01801036": "塑料",
}

def fetch_pt_sectors():
    codes = ",".join(pt_codes.keys())
    url = f"http://qt.gtimg.cn/q={codes}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://finance.qq.com/"})
    with urllib.request.urlopen(req, timeout=15) as r:
        raw = r.read().decode("gbk", errors="replace")

    results = []
    for line in raw.strip().split("\n"):
        m = re.match(r'v_(\w+)="([^"]+)"', line)
        if not m: continue
        code, payload = m.group(1), m.group(2)
        parts = payload.split("~")
        if len(parts) < 35: continue
        try:
            results.append({
                "code": code,
                "name": parts[1] if len(parts) > 1 else code,
                "changePercent": float(parts[32]) if parts[32] else 0,
                "changeAmount": float(parts[31]) if parts[31] else 0,
            })
        except (ValueError, IndexError):
            pass
    results.sort(key=lambda x: -x["changePercent"])
    return results
```

**限制**：仅 17 个板块。复盘需要写「行业板块 TOP5」时，从结果中取前 5；不够时用 Sina 头条补充。

### Step 3：Sina 首页标题提取板块线索

```python
import urllib.request, re

def fetch_sina_titles():
    """从 Sina 财经首页提取板块异动标题"""
    url = "https://finance.sina.com.cn/stock/"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://www.baidu.com/"})
    with urllib.request.urlopen(req, timeout=15) as r:
        html = r.read().decode("utf-8", errors="replace")

    titles = re.findall(r'<a[^>]+>([^<]{10,80})</a>', html)
    keywords = ["板块", "涨停", "跌停", "异动", "飙升", "爆发", "走强", "走弱", "涨", "跌", "收评", "复盘", "大涨", "大跌", "集体", "分化", "震荡", "突破"]
    interesting = []
    seen = set()
    for t in titles:
        t = t.strip()
        if t in seen: continue
        seen.add(t)
        for kw in keywords:
            if kw in t:
                interesting.append(t)
                break
    return interesting

# 使用：t = fetch_sina_titles()，从返回的标题中识别当日热点板块
# 示例输出：'养殖板块掀涨停潮，益生股份上半年净利最多预'、'保险板块午后'、'快讯：科创50跌超2% 午后算力芯片概念'
```

### Step 4：Sina snipe 实时异动文章（板块龙头股清单）

```python
import urllib.request, re

def fetch_sina_home_links(date_str):
    """从 Sina 首页列出当日所有文章链接"""
    url = "https://finance.sina.com.cn/stock/"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        html = r.read().decode("utf-8", errors="replace")

    candidates = []
    for pattern, label in [
        (rf'href="(https://finance\.sina\.com\.cn/stock/bxjj/{date_str}/doc-[^"]+\.shtml)"', 'bxjj'),
        (rf'href="(https://finance\.sina\.com\.cn/stock/snipe/{date_str}/doc-[^"]+\.shtml)"', 'snipe'),
        (rf'href="(https://finance\.sina\.com\.cn/tob/{date_str}/doc-[^"]+\.shtml)"', 'tob'),
        (rf'href="(https://finance\.sina\.com\.cn/stock/cpbd/{date_str}/doc-[^"]+\.shtml)"', 'cpbd'),
    ]:
        for href in re.findall(pattern, html):
            candidates.append((label, href))
    # 去重保序
    seen = set()
    out = []
    for c in candidates:
        if c[1] not in seen:
            seen.add(c[1])
            out.append(c)
    return out
```

**snipe 文章正文模式**（固定格式，提取前 14:50 异动数据）：
```
07月01日消息，截止14:50，创新药板块活跃，珍宝岛、润都股份、海南海药（维权）、威尔药业、昂利康涨停，
石药创新、普蕊斯、海思科、千红制药、立方制药等个股涨幅居前。

声明：市场有风险，投资需谨慎。...
```

用正则提取：
- 板块名（"创新药板块"）
- 涨停股（"珍宝岛、润都股份..."）
- 涨幅居前股（"石药创新、普蕊斯..."）

### Step 5：Sina `/cpbd/` 操盘必读全文（消息面分类）

**URL**：`https://finance.sina.com.cn/stock/cpbd/YYYY-MM-DD/doc-*.shtml`（从首页找当日唯一一篇）

**正文标记**：`<-- 正文开始 -->...<-- 正文结束 -->`，**始终可用**（15:15 收盘后）。

**结构**（2026-07-01 实战验证）：
```
登录新浪财经APP 搜索【信披】查看更多考评等级

影响股市利好与利空消息

宏观新闻
1、...
2、...

行业新闻
1、...
...

公司新闻
1、...
...

环球市场
美股三大指数集体收涨...

投资机会参考
1、...

【停复牌】
...
【增减持】
...
```

**提取策略**：用 `<!-- 正文开始 -->` 到 `<!-- 正文结束 -->` 切片，去 HTML 标签，按"宏观/行业/公司/环球"四节分类填入 `news[]`。

---

## 3. 涨停股统计替代方案

东财 push2 不可用时，涨停家数无法精确统计。**替代做法**：

1. **从 Sina snipe 实时异动文章聚合**（按板块去重）
2. **从 Sina 首页"收评"标题提取**——多数收评文章会写"上涨个股超 XXXX 只"
3. **腾讯 API 批量查询候选股后过滤**（拉涨幅 > 9.8/19.5/29.5 的）

```python
# 从 snipe 文章聚合的简化版
def aggregate_limit_up_from_snipe(snipe_articles):
    """从多个 snipe 文章中提取涨停股"""
    limit_up = []
    for url in snipe_articles:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            html = r.read().decode("utf-8", errors="replace")
        # 提取涨停股
        text = re.sub(r'<[^>]+>', '\n', html)
        m = re.search(r'截止\d+:\d+，([^板块]+)板块.*?涨停', text)
        if m:
            sector = m.group(1).strip()
            # 找涨停股名（"、"分隔）
            body = text[text.find("涨停"):text.find("声明") if "声明" in text else len(text)]
            stocks = re.findall(r'([\u4e00-\u9fa5]{2,5})', body[:500])
            for s in stocks:
                if s not in limit_up:
                    limit_up.append({"name": s, "sector": sector})
    return limit_up
```

**标注规范**：报告必须明确写"涨停家数未精确统计，依据 Sina 实时异动文章 + 个股 API 交叉验证推算 ≥N 只"。

---

## 4. 7/1 实战完整复盘命令链（仅供参考）

```bash
# Step 1: 互斥锁
LOCK_FILE=~/.hermes/cron/locks/复盘_$(date +%Y-%m-%d).lock
[ -f "$LOCK_FILE" ] && echo "[SILENT]" && exit 0
date +%s > "$LOCK_FILE"

# Step 2: 数据采集
python3 /tmp/collect_review_2026-07-01_v2.py > /tmp/data.json  # 指数 + 板块（含 push2 失败回退）

# Step 3: 抓 Sina 头条/snipe
python3 /tmp/fetch_sina_titles.py > /tmp/sina_titles.txt
python3 /tmp/fetch_sina_articles.py > /tmp/sina_articles.txt

# Step 4: 拉个股
python3 /tmp/fetch_stocks.py > /tmp/stocks.txt

# Step 5: 生成报告
python3 /tmp/generate_report.py  # 写 .md + .json

# Step 6: token 预检（ping payload）
python3 /tmp/token_ping2.py  # 必须看到 code 200 或 code 400（不是 401）

# Step 7: 上报
python3 /tmp/upload_review.py  # POST 完整 JSON

# Step 8: 释放锁（在 cron 模式下不需要，文件本身标记完成）
```

---

## 5. 何时重新尝试 push2

每 5-7 天可以 ping 一次 push2 看是否恢复：

```bash
timeout 10 curl -s -o /dev/null -w "%{http_code}\n" \
  -H "User-Agent: Mozilla/5.0" \
  -H "Referer: https://quote.eastmoney.com/" \
  "https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=5&po=1&fid=f3&fs=m:90+t:2&fields=f1,f2,f3,f4,f12,f14"
```

- 返回 200 + JSON → push2 复活
- 返回 000 / curl error → 仍被封，继续走回退

把测试结果记在 data-source-availability-YYYY-MM-DD.md，下次复盘时优先用当前可用渠道。
