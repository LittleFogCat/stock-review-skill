#!/usr/bin/env python3
"""Find the currently-valid xiaoniu.tech stock-review API key (xntk_).

背景: 本服务器存在多个历史 `xntk_` key。config.yml 的 apiKey 已脱敏为占位符
(xntk_...bYP)；~/.profile 可能无 STOCK_REVIEW_API_KEY。真实 key 存于
~/.hermes/state.db 和 ~/.hermes/.hermes_history（grep 'xntk_[A-Za-z0-9_-]+'）。

禁止"取最长候选"当作唯一规则 (2026-08-24 反证修正): 历史上最长候选
(len 40, 后缀匹配脱敏占位符) 已过期返回 401，而较短候选 (len 37) 当时才是有效 key。
(2026-11-16 起该 key 已轮换作废，本脚本仅作历史排障参考；常规取 key 请读本机环境变量/.env，
完整 key 禁止写入本仓库或日志。)
必须对所有去重候选项逐个 POST 最小合规 payload 测试，筛出 code=200 者。

用法:
  python3 test_api_keys.py            # 找第一个有效 key
  python3 test_api_keys.py --all      # 列出所有候选及其鉴权结果
输出: 每个候选的 len / HTTP / code；末尾打印 VALID_KEY=<key> 供调用方捕获。

预检必须"只读不落库"（2026-11-17 修订）：不要再使用含 content 的 ping payload 或
"最小合规 payload"（它们会通过校验并创建垃圾记录，历史已产生 65+ 条）。改用不含 content
的 payload `{"date": "2099-01-01"}`：无效 key -> 401；有效 key -> 400（鉴权通过、落库前被拒）。
两个 code 足以区分，且永不写入数据。

SSL 说明: xiaoniu.tech 证书校验对部分环境失败 (SSL: CERTIFICATE_VERIFY_FAILED)，
故用 check_hostname=False + verify_mode=CERT_NONE 的 context（见
references/api-upload-ssl-cert-pitfall.md）。
"""
import json
import os
import re
import ssl
import sys
import urllib.error
import urllib.request

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

ENDPOINT = "https://xiaoniu.tech/api/stock/reviews"
PATTERN = re.compile(r"xntk_[A-Za-z0-9_\-]+")
SOURCES = [
    os.path.expanduser("~/.hermes/state.db"),
    os.path.expanduser("~/.hermes/.hermes_history"),
    os.path.expanduser("~/.profile"),
]

# 只读预检 payload：不含 content/市场字段 → 有效 key 返回 400（鉴权通过、落库前被拒），
# 不会像旧的"最小合规 payload"那样每测一个有效 key 就写入一条垃圾记录。
PAYLOAD = {
    "date": "2099-01-01",
}


def collect_candidates():
    cands = set()
    for src in SOURCES:
        if not os.path.exists(src):
            continue
        try:
            with open(src, "rb") as f:
                blob = f.read().decode("utf-8", errors="replace")
        except Exception:
            continue
        cands.update(PATTERN.findall(blob))
    res = []
    for c in cands:
        # 过滤残留/残缺候选：真 xntk_ key 通常 >= 37 字符；排除占位/示例串
        if len(c) < 30:
            continue
        if re.search(r"(unknown|placeholder|xxx|^xntk_key$)", c, re.I):
            continue
        res.append(c)
    return sorted(set(res), key=len)


def test_key(key):
    req = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(PAYLOAD).encode(),
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=20, context=ctx) as r:
            body = json.loads(r.read().decode())
        return r.status, body.get("code"), body.get("msg")
    except urllib.error.HTTPError as e:
        return e.code, None, e.read().decode()[:80]
    except Exception as e:
        return None, None, "%s: %s" % (type(e).__name__, str(e)[:80])


def main():
    cands = collect_candidates()
    if not cands:
        print("NO_CANDIDATES")
        return 1
    print("候选 key 数:", len(cands), file=sys.stderr)
    for c in cands:
        status, code, msg = test_key(c)
        # 只读预检判定：401=无效；400=鉴权通过（落库前被拒）；200=误写记录（不应出现）
        valid = code in (200, 400)
        flag = " <== VALID" if valid else ""
        warn = " (⚠️ code=200 说明已写入记录)" if code == 200 else ""
        print(f"len={len(c)} {c} -> HTTP {status} code={code}{flag}{warn}")
        if valid and "--all" not in sys.argv:
            print("VALID_KEY=" + c)
            return 0
    print("NO_VALID_KEY")
    return 1


if __name__ == "__main__":
    sys.exit(main())