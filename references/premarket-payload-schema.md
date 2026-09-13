# 早盘快报（type=1）JSON 必填字段速查

**用途**：避免再次踩到 `code=400 "明日关注个股第 N 项所属板块不能为空"` / `今日热点格式错误` / `消息面第 N 项内容必须为数组` 等坑。

**触发场景**：早盘快报 cron 完成后，用 `stock_review_cli.py report` 上报时返回 `HTTP 200 + code=400` 错误。

---

## 最小完整 payload 模板（type=1）

```python
import json

payload = {
    "date": "YYYY-MM-DD",
    "title": "YYYY年M月D日早盘快报",   # ⚠️ 不带「（周X）」后缀
    "type": 1,                          # ⚠️ 必填，1=早盘快报
    "content": "<完整 markdown 正文>",   # ⚠️ 必填，非空字符串

    # markets 必填对象（即使无当日盘后数据也要写）
    "markets": {
        "summary": "前一交易日 A 股一句话总结",
        "indices": [
            {
                "name": "上证指数",
                "code": "sh000001",
                "close": 3996.16,
                "change": -40.43,
                "changePercent": -1.00,
                "reason": "失守 4000 点"   # ⚠️ 必填字符串
            },
            # ... 其他 8 个主指数
        ],
        "volume": "两市全天成交约 3.39 万亿元"   # ⚠️ 必填字符串
    },

    # todayHot 必填对象（早盘无盘中数据，用空数组）
    "todayHot": {                       # ⚠️ 必填对象，不是 null
        "topSectors": [],
        "concepts": [],
        "fallingSectors": [],
        "summary": "早盘快报：今日尚未开盘，盘前催化：xxx、yyy、zzz"
    },

    # news 必填数组
    "news": [
        {
            "title": "宏观与政策",
            "content": [                 # ⚠️ 必填数组，不是字符串
                "R1·美伊冲突升级：...",
                "霍尔木兹海峡关闭：...",
                "本周中国央行公开市场..."
            ]
        },
        {"title": "产业与行业", "content": ["..."]},
        {"title": "环球市场", "content": ["..."]},
        {"title": "事件与会议", "content": ["..."]},
        {"title": "公司公告", "content": ["..."]}
    ],

    # focusSectors 必填非空数组
    "focusSectors": [
        # ⚠️ stocks 字段可以为空数组 []（2026-07-30 实测 API 接受）
        # 当板块有关注理由但未选出具体个股时，用 stocks: []
        {"name": "石油石化/油运", "reason": "...", "stocks": []},
        {"name": "券商/大金融", "reason": "...", "stocks": [
            {"code": "300308", "name": "中际旭创", "reason": "..."}
        ]},
        # ... ≤8 个
    ],

    # focusStocks 必填非空数组（按板块分组）
    "focusStocks": [
        {
            "sector": "AI算力/光模块",              # ⚠️ 字段名是 sector，必填
            "stocks": [
                {"code": "300308", "name": "中际旭创", "reason": "..."}
            ]
        }
        # ... ≤10 个总股票
    ]
}
```

---

## 字段名速查表（最容易混淆的）

| 数据 | 字段 | 错误样例 | 正确样例 |
|------|------|----------|----------|
| 关注板块名称 | **`focusSectors[].name`** | `{"sector": "...", "reason": "..."}` ❌ | `{"name": "...", "reason": "..."}` ✅ |
| 关注个股所属板块 | **`focusStocks[].sector`** | `{"group": "...", "stocks": [...]}` ❌ | `{"sector": "...", "stocks": [...]}` ✅ |
| 板块个股涨跌幅 | **`topSectors[].changePercent`** | `"5.32"`（字符串）❌ | `5.32`（数字）✅ |
| 板块逻辑理由 | **`focusSectors[].reason`** | 缺失 ❌ | 非空字符串 ✅ |
| 市场指数评价 | **`markets.indices[].reason`** | 缺失 ❌ | 非空字符串 ✅ |
| 消息面每条内容 | **`news[].content`** | `"..."`（字符串）❌ | `["..."]`（数组）✅ |
| 复盘类型 | **`type`** | 缺失 ❌ | `1`（早盘）或 `2`（复盘）✅ |
| 早盘热点结构 | **`todayHot`** | `null` ❌ | `{"topSectors":[], "concepts":[], "fallingSectors":[], "summary":"..."}` ✅ |

---

## code=400 错误信息速查（2026-07-13 实测整理）

| msg | 修复 |
|------|------|
| `"市场指数第 N 项评价不能为空"` | 给 `markets.indices[N].reason` 填非空字符串 |
| `"今日热点格式错误"` | `todayHot` 设为对象（含空数组），不要 null |
| `"消息面第 N 项内容必须为数组"` | `news[N].content` 改为数组 `["..."]` |
| `"明日关注个股第 N 项所属板块不能为空"` | `focusStocks[N].sector` 填非空字符串 |
| `"关注板块第 N 项板块名称不能为空"` | `focusSectors[N].name`（不是 sector）填非空字符串 |
| `"type 字段必须为 0、1 或 2"` | 加 `type: 1`（早盘）或 `type: 2`（复盘） |
| `"标题格式错误"` | 标题严格匹配 `YYYY年M月D日早盘快报`（不带周X） |

---

## 上报前自检 checklist

```python
def validate_payload_for_api(data):
    """返回 (ok: bool, errors: list[str])"""
    errors = []
    if data.get("type") not in (1, 2):
        errors.append("type 字段必须为 1 或 2")
    if not isinstance(data.get("markets"), dict):
        errors.append("markets 必须是对象")
    elif not data["markets"].get("summary") or not data["markets"].get("volume"):
        errors.append("markets.summary 和 markets.volume 必填")
    for i, idx in enumerate(data.get("markets", {}).get("indices", [])):
        if not idx.get("reason"):
            errors.append(f"markets.indices[{i}].reason 必填")
    if not isinstance(data.get("todayHot"), dict):
        errors.append("todayHot 必须是对象（早盘用空数组对象）")
    for i, n in enumerate(data.get("news", [])):
        if not isinstance(n.get("content"), list):
            errors.append(f"news[{i}].content 必须是数组")
    for i, s in enumerate(data.get("focusSectors", [])):
        if not s.get("name") or not s.get("reason"):
            errors.append(f"focusSectors[{i}].name 和 reason 必填")
    for i, s in enumerate(data.get("focusStocks", [])):
        if not s.get("sector"):
            errors.append(f"focusStocks[{i}].sector 必填")
        for j, st in enumerate(s.get("stocks", [])):
            if not st.get("code") or not st.get("name") or not st.get("reason"):
                errors.append(f"focusStocks[{i}].stocks[{j}] 三字段必填")
    if not data.get("content"):
        errors.append("content 必填非空字符串")
    return (len(errors) == 0, errors)
```

---

## 上报脚本 fallback chain（cron 模式）

```python
# 1. 优先：环境变量
api_key = os.environ.get("STOCK_REVIEW_API_KEY", "")

# 2. fallback：~/.profile 单/双引号提取
if not api_key:
    profile_path = os.path.expanduser("~/.profile")
    with open(profile_path) as f:
        for line in f:
            if "STOCK_REVIEW_API_KEY" in line and "export" in line:
                m = re.search(r"'([^']+)'", line) or re.search(r'"([^"]+)"', line)
                if m:
                    api_key = m.group(1)
                    break

# 3. fallback：config.yml apiKey 字段（实测可用）
if not api_key:
    config_path = "/root/.hermes/skills/stock-review-skill/config.yml"
    try:
        with open(config_path) as f:
            content = f.read()
        m = re.search(r'apiKey:\s*"?([^"\s]+)"?', content)
        if m:
            api_key = m.group(1)
    except FileNotFoundError:
        pass

# 4. fallback：agent.log 反查
# 见主 SKILL.md「STOCK_REVIEW_API_KEY 完全缺失的应急方案」章节
```

---

## 上报方式

**首选**：`stock_review_cli.py report --json-file <path>`（避免 shell 变量替换问题）
**备选**：Python 脚本 `urllib.request` POST 到 `https://xiaoniu.tech/api/stock/reviews`，header `Authorization: Bearer <key>`

**重要**：HTTP 200 + code=200 = 成功；HTTP 200 + code=4xx = 字段问题，**token 是有效的**。
