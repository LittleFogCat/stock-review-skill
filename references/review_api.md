# 股市复盘API

## 上报复盘结果

**前置条件**：

- 本节仅在 `config.yml` 中的 `review.upload.enabled=true`，或用户通过命令行/环境变量显式启用了上传时适用；若未启用上传，可跳过本 API。
- 调用该接口前，必须先向用户索取 apiKey。
- 收到 apiKey 后，应先运行 `python ./scripts/stock_review_cli.py set-api-key`，将其持久化为本地环境变量 `STOCK_REVIEW_API_KEY`。
- 本文中的 `apiKey` 即 Bearer Token；`token` 与 `STOCK_REVIEW_API_KEY` 表示同一份接口凭证。
- 若已启用上传但未配置 `STOCK_REVIEW_API_KEY`，则上报流程不得继续。
- 上报请求应通过 `python ./scripts/stock_review_cli.py report --json-file <path-to-review-json>` 实际执行，而不是只输出接口描述。
- 对本 skill 而言，只有在启用上传时，上报才是完成条件；若未启用上传，可仅生成本地 markdown 与 JSON。

**路径**：`https://xiaoniu.tech/api/stock/reviews`

**方法**：`POST`

**请求体类型**：`application/json`

**认证/鉴权**：

- `Authorization` 头，值为 Bearer 令牌，格式：`Bearer ${apiKey}`。
- 若宿主环境支持密钥配置，建议将真实凭证保存在安全的 secret 或环境变量中，再映射为运行时的 `apiKey`。

**请求体**：

按照 [股市复盘JSON模型](./review_model.md) 格式填写。

**返回值**：

```json
{
    "code": 200,
    "message": null
}
```
- `code`：状态码，200 表示成功，401 表示未授权，403 表示权限拒绝。
- `message`：错误信息，成功时为 null。

---

## Webhook 推送（v1：配置预留）

> **状态**：v1 已支持 `config.yml` 字段 + `set-webhook-url` / `set-webhook-secret` / `show-webhook` 三个 CLI 子命令。**实际推送触发逻辑在 `report` 完成后尚未实现**——目前 `webhook.enabled` 与 `webhook.url` 字段仅作为配置预留，xiaoniu.tech 主上报流程不受影响。等 v2 落地后，本节会增补接收方签名校验、重试退避、幂等键等内容。

如果你打算把 stock-review-skill 接入**自有后端 / Discord / Slack 等 Webhook 接收端**，先按本节配好字段，等 v2 上线即自动生效。

### 1. 字段说明

`config.yml` 中 `review.upload.webhook` 子节点：

| 字段 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `enabled` | bool | `false` | 是否启用 webhook 推送。v1 仅作配置预留；v2 启用后会真正在 `report` 完成后触发 POST |
| `url` | string | `""` | 接收端 URL（建议 HTTPS）。空 = 不推送 |
| `secret` | string | `""` | HMAC-SHA256 签名密钥。空 = 不签名（v2 启用后会发出"无签名"警告） |
| `maxRetries` | int | `3` | 失败重试次数（v2 触发实现后生效）。仅 5xx / 网络错误触发重试，4xx 不重试 |

### 2. CLI 配置流程

```bash
# 一次性写入 URL（推荐保留 TTY 提示，避免 URL 进 shell history）
python scripts/stock_review_cli.py set-webhook-url https://your-host/api/hook

# 写入 secret（getpass 安全输入，不回显）
python scripts/stock_review_cli.py set-webhook-secret

# 启用 webhook（如不写则保持 enabled=false）
# 注：CLI 没有 enable/disable 子命令，直接手编 config.yml 把 enabled 改 true 即可，
#     或用 python -c "..." + update_runtime_config_setting 调脚本。

# 验证当前生效的配置
python scripts/stock_review_cli.py show-webhook
```

覆盖链：`--url`（命令行参数） > `$STOCK_REVIEW_WEBHOOK_URL`（环境变量） > `config.yml` > DEFAULT_RUNTIME_CONFIG。`--config-file` 可指向任意路径。

### 3. 接收方接入预览（v2 推送启用后）

v2 启用后，每次 `report` 成功后，stock_review_skill 会异步向 `webhook.url` POST 一份**完整的复盘 JSON**，请求头如下：

| 头字段 | 值 | 说明 |
|--------|----|------|
| `Content-Type` | `application/json` | JSON 载荷 |
| `Authorization` | `Bearer <STOCK_REVIEW_API_KEY>` | 复用主 API 的 API Key（v2 阶段） |
| `X-Stock-Review-Signature` | `sha256=<hex>` | HMAC-SHA256(secret, raw_body) |
| `X-Stock-Review-Event-Id` | `<uuid>` | 同一份复盘的重发拥有同一 event_id，接收方据此幂等去重 |
| `X-Stock-Review-Timestamp` | `<unix epoch>` | 防重放窗口由接收方决定（建议 ±5 分钟） |

接收方应答约定：

- 2xx = 接收成功，客户端不再重试
- 4xx = 永久失败（载荷不合法等），客户端不重试
- 5xx / 网络错误 = 临时失败，客户端按 `webhook.maxRetries` 触发指数退避重试

### 4. 第三方接入参考实现

```python
import hashlib
import hmac

def verify_signature(secret: str, body: bytes, signature_header: str) -> bool:
    if not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header[len("sha256="):])
```

注：v2 上线后才能真实收到 POST 请求；v1 阶段该方法只是模板化的占位实现。

---

## 核对已推送的复盘记录（GET · 诊断用途）

**使用场景**：用户问"复盘都推送到服务器了吗？"或"最近几天复盘推送是否成功？"时，用来无损地列出服务器上所有已上报的复盘记录，与本地 `/usr/local/files/docs/stock/` 目录对比，找出推送缺失的日期。这是排查"本地有文件但服务器没收到"的快速诊断手段。

**路径**：`https://xiaoniu.tech/api/stock/reviews`

**方法**：`GET`

**认证**：同上，`Authorization: Bearer ${STOC...KEY` 是 xiaoniu.tech 复盘 API 的凭证（`xntk_` 前缀），**不是** QQ Bot 的 App ID/Secret。两套体系独立。

**重要语义提示**：用户说"复盘推送/上报/服务器"默认指本 API；"QQ 推送/QQ 消息/QQ 收没收到"指 QQ Bot 网关。两者不要混淆。诊断推送问题时优先用本 GET 端点核对服务器记录。

**返回值结构**：
```json
{
    "code": 200,
    "success": true,
    "msg": null,
    "data": {
        "reviews": [
            {
                "_id": "6a3a33262430a85bccd4ac7c",
                "date": "2026-06-23",
                "markets": { ... },
                "title": "...",
                "content": "..."
            }
        ]
    }
}
```
- `data.reviews`：服务器上所有复盘记录的数组，按 date 升序排列。
- 每个记录包含 `date`（复盘日期 YYYY-MM-DD）、`_id`（MongoDB ObjectId）、`title`、`markets`、`content` 等完整字段。
- 同一日期可能有多条记录（如 2026-06-22 有 4 条），通常是同一交易日被多次提交（手工补传、cron 重试、不同模式等）。

**调用示例（execute_code 沙箱模式）**：
```python
import os, json, urllib.request

# execute_code 沙箱不继承 shell 环境变量，必须从 ~/.profile 读取
key = None
for line in open(os.path.expanduser("~/.profile")):
    if "STOCK_REVIEW_API_KEY" in line and "export" in line:
        key = line.split("=", 1)[1].strip().strip("'").strip('"')
        break

req = urllib.request.Request(
    "https://xiaoniu.tech/api/stock/reviews",
    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
)
data = json.loads(urllib.request.urlopen(req, timeout=15).read().decode())
reviews = data["data"]["reviews"]

# 服务器上的全部日期（去重）
server_dates = sorted(set(r.get("date") for r in reviews))
print(f"服务器共 {len(reviews)} 条记录，{len(server_dates)} 个不同日期")
print(f"最新: {server_dates[-1] if server_dates else '（空）'}")
```

**与本地文件对比的标准做法**：
```python
import os
local_dates = set()
for f in os.listdir("/usr/local/files/docs/stock/"):
    parts = f.replace("stock_review_", "").split(".")
    if parts and len(parts[0]) == 10:
        local_dates.add(parts[0])

print("本地有、服务器无:", sorted(local_dates - server_dates) or "（无）")
print("服务器有、本地无:", sorted(server_dates - local_dates) or "（无）")
```

**重要陷阱**：
- 沙箱中的 Python 字符串**不能直接使用包含 `*` 的正则分组**（脱敏工具会吞掉星号）。读取 key 用 `split("=", 1)[1].strip().strip("'")` 即可，避免正则。
- GET 返回的复盘记录可能重复（同一日期多条），对比前先去重 `set(r.get("date") for r in reviews)`。
- 同一日期的多条记录可能时间戳不同、内容不同（cron 多次补跑或手工修正导致），需要时再按 `_id` 单独核对。
- `STOC... 变量的来源仍是 xiaoniu.tech 复盘 API 凭证。

---

## 常见错误码与排错

xiaoniu.tech 复盘 API 在字段类型不符或必填字段缺失时，会返回 HTTP 200 + `{"code": 400, "msg": "..."}`。以下是已实测验证的常见错误码、根因和解决办法。

### `todayHot` 字段必须是对象而非 null（"今日热点格式错误"）

早盘快报 JSON 中若将 `todayHot` 设为 `null` 或不包含该字段，API 返回 HTTP 200 + `code: 400, msg: "今日热点格式错误"`。review_model.md 中 `todayHot` 的类型为 `object`，不是 optional/nullable。

**解决办法**：对于早盘快报（无盘中数据），`todayHot` 必须设为包含空数组的对象：

```json
"todayHot": {
  "topSectors": [],
  "concepts": [],
  "fallingSectors": [],
  "summary": "早盘快报模式，不包含当日盘中数据。"
}
```

`summary` 可简要描述前一日盘面或留空字符串，但字段本身不能省略。构建 JSON 时用 Python 代码保证所有字段类型匹配 review_model.md。

### `focusSectors` 字段名错误（"关注板块第 N 项板块名称不能为空"）

**现象**：早盘快报上报时 API 返回 HTTP 200 + `{"code":400,"msg":"关注板块第 1 项板块名称不能为空"}`。明明已填入 `"sector": "存储芯片"`，但 API 仍报名称不能为空。

**根因**：`focusSectors` 和 `focusStocks` 使用了不同的字段命名约定，极易混淆：

| 字段 | 字段名 | 类型 | 示例 |
|------|--------|------|------|
| `focusSectors[].name` | **`name`** | string | `"存储芯片"` |
| `focusSectors[].reason` | **`reason`** | string | `"美光暴涨+15%催化"` |
| `focusStocks[].sector` | **`sector`** | string | `"存储芯片"` |

直觉上容易认为 `focusSectors` 也用 `sector` 字段，但根据 review_model.md，`focusSectors` 的板块名称字段是 `name`（附有 `reason` 字段），而 `focusStocks` 的分组字段才是 `sector`。

**解决办法**：
1. 构建 JSON 前务必对照 `review_model.md` 确认 `focusSectors[].name` 和 `focusSectors[].reason` 两个字段
2. `focusSectors` 的结构为：`{"name": "板块名", "reason": "短线关注理由", "stocks": [...]}`
3. `focusStocks` 的结构为：`{"sector": "板块名", "stocks": [...]}`
4. 2026-06-26 早盘快报实测验证：使用 `name` 后上报成功返回 code 200

### `focusStocks` 格式错误（"所属板块不能为空"）

**现象**：早盘快报上报时 API 返回 HTTP 200 + `{"code":400,"msg":"明日关注个股第 N 项所属板块不能为空"}`。这是因为 `focusStocks` 的结构是**按板块分组的嵌套格式**，而非扁平数组。

**错误格式（扁平数组，会被 API 拒绝）**：

```json
"focusStocks": [
  {"code": "603986", "name": "兆易创新", "reason": "..."},
  {"code": "600584", "name": "长电科技", "reason": "..."}
]
```

**正确格式（按板块分组）**：

```json
"focusStocks": [
  {
    "sector": "存储芯片",
    "stocks": [
      {"code": "603986", "name": "兆易创新", "reason": "..."}
    ]
  },
  {
    "sector": "先进封装/封测",
    "stocks": [
      {"code": "600584", "name": "长电科技", "reason": "..."}
    ]
  }
]
```

**解决办法**：
1. 构建 JSON 前必须对照 `review_model.md` 中的 `focusStocks` 字段定义确认结构
2. `focusStocks[].sector` 是必填字符串，不能为空
3. `focusStocks[].stocks` 是必填数组，每个元素包含 `code`、`name`、`reason` 三个字段
4. 使用 Python 代码从结构化数据生成（如 `for sector in sectors: entry = {"sector": sector["name"], "stocks": [...]}`），而不是手动拼接

**排查**：收到此错误时优先检查 focusStocks 的结构是扁平数组还是按板块分组的嵌套数组。2026-06-25 早盘快报中实测验证：扁平数组上报 → code 400，分组嵌套 → code 200。

### `markets` 字段必须是对象而非数组（"市场总览格式错误"）

根据 `review_model.md`，`markets` 是一个**对象**，包含 `summary`（string）、`indices`（array）、`volume`（string）三个字段。若错误地将 `markets` 设为指数数组（如 `[{"name":"道琼斯",...}]`），API 返回 HTTP 200 + `code: 400, msg: "市场总览格式错误"`。

**正确格式**：

```json
"markets": {
  "summary": "隔夜美股三大指数分化：道指+0.64%...",
  "indices": [
    {"code": "DJI", "name": "道琼斯", "close": 51999.67, "changePercent": 0.64, "reason": "..."},
    {"code": "IXIC", "name": "纳斯达克", "close": 26376.34, "changePercent": -1.15, "reason": "..."},
    {"code": "SPX", "name": "标普500", "close": 7511.35, "changePercent": -0.57, "reason": "..."}
  ],
  "volume": "未获取（隔夜美股）"
}
```

**解决办法**：构建 JSON 时始终对照 `review_model.md` 的字段定义，确认 `markets` 是对象。对于早盘快报，`markets.summary` 和 `markets.volume` 必须存在（可填描述性字符串或「未获取」），不能省略。

### `news[].content` 必须是数组而非字符串（"消息面第 N 项内容必须为数组"）

**现象**：完整复盘 JSON 上报时 API 返回 HTTP 200 + `{"code":400,"msg":"消息面第 1 项内容必须为数组"}`。

**根因**：`review_model.md` 中 `news[].content` 字段类型为 `array`（该分类下所有新闻条目的 markdown 字符串数组），但容易误以为是单个长字符串。LLM 直觉上把 `news[].content` 当作 `string` 填充（如 `"国务院李强主持国务院常务会议..."`），导致 API 拒绝接收。

**正确格式**：

```json
"news": [
  {
    "category": "宏观与政策",
    "title": "国务院总理李强主持国务院常务会议：加力推进人工智能创新突破",
    "content": [
      "国务院总理李强 6 月 29 日主持召开国务院常务会议，会议指出，要加力推进人工智能创新突破，加快关键技术攻关和超大规模智算集群建设。"
    ],
    "source": "新浪财经操盘必读"
  },
  {
    "category": "产业与行业",
    "title": "寒武纪成科创板首只万亿市值股票",
    "content": [
      "AI 算力龙头寒武纪（688256）今日盘中突破万亿市值，盘中最高 +8.91% 报 1614.09 元/股。"
    ],
    "source": "新浪财经"
  }
]
```

**注意**：每条新闻的 `content` 是一个**数组**（即使只有一条 markdown 字符串，也要包成单元素数组 `["..."]`）。多条相关新闻可放在同一 `content` 数组的不同元素里：`["第一条新闻全文 markdown", "第二条新闻全文 markdown"]`。

**解决办法**：
1. Python 脚本构建 news 时务必用列表包装：`"content": [n["content"]]`（即使只有一条）
2. 上报前对照 `review_model.md` 验证 `news[].content` 是 `list[str]` 而非 `str`
3. 收到"内容必须为数组"错误时，**只改 content 字段为数组后重新 POST**，不要重新跑整个采集流程

**2026-06-30 实测**：当日复盘首次上报 `news[].content = "国务院李强..."`（字符串）→ code 400；修复为 `"content": ["国务院李强..."]`（单元素数组）→ code 200 上报成功（_id `6a436ec3d8fb6366079046cc`）。

### `markets.indices[].reason` 缺失（"市场指数第 N 项评价不能为空"）

**现象**：完整 JSON 上报时 API 返回 HTTP 200 + `{"code":400,"msg":"市场指数第 1 项评价不能为空"}`。

**根因**：JSON 中 `markets.indices[]` 数组的每一项**必须有 `reason` 字段**（string 类型），不能为空。这与 `sectors[].reason` 字段类似。

**解决办法**：

```python
# 为每个 index 条目补填 reason
for idx in data["markets"]["indices"]:
    pct = idx.get("changePercent", 0)
    if pct <= -5: idx["reason"] = "大幅杀跌"
    elif pct <= -3: idx["reason"] = "收跌"
    elif pct <= 0: idx["reason"] = "小幅下跌"
    elif pct <= 3: idx["reason"] = "小幅上涨"
    else: idx["reason"] = "大涨"
```

同样，`todayHot.topSectors[].reason` 和 `todayHot.fallingSectors[].reason` 也需要有值。

**2026-07-02 实测**：首次上报缺失 reason → code 400 "市场指数第 1 项评价不能为空"；补上 reason 后 → code 200 上报成功。

### `type` 字段缺失（"type 字段必须为 0、1 或 2"）

**现象**：完整 JSON 上报时 API 返回 HTTP 200 + `{"code":400,"msg":"type 字段必须为 0（自动）、1（早盘快报）或 2（今日复盘）"}`。

**根因**：`review_model.md` 中 `type` 字段描述为"可为空"，但 2026-06-29 实测 API 实际**要求必填**，缺失时拒绝接收。

**解决办法**：
- 上报 JSON 中**必须包含** `type` 字段
- 早盘快报：`"type": 1`
- 当日复盘：`"type": 2`
- 在 Python 脚本生成 JSON 时添加该字段：`data["type"] = 1`（或 2），然后再 `json.dump`
- 该字段不影响本地 markdown 文件内容，仅用于 API 路由识别

**2026-06-29 早盘快报实测**：第一次上报无 `type` 字段 → code 400；补上 `"type": 1` → code 200，上报成功。

### 服务器自动补全 `focusSectors: []` / `focusStocks: []` 字段

**现象**：当日复盘 JSON 中**故意不包含** `focusSectors` 和 `focusStocks` 字段（这两个字段仅属于早盘快报）。API 上报时返回的响应中却显示：

```json
"focusSectors": [],
"focusStocks": []
```

**结论**：xiaoniu.tech API 后端在接收到缺失字段时，会**自动补全为空数组**（默认零值）。这与 review_model.md 中规定的「当日复盘不应包含 `focusSectors` / `focusStocks` 字段」**不冲突**——这是 server-side 的容错处理。

**实测影响**：
- 客户端不需要手动塞 `focusSectors: []` 来通过 server 校验
- 即使完全省略这两个字段，API 仍返回 code 200
- 报告内容（content / markdown body）依然不包含「明日关注板块」「明日关注个股」章节

**反推结论**：该 API server 对当日复盘和早盘快报使用同一个 endpoint，依赖**客户端提交时是否带 focus 数据**来区分模式。当日复盘省略 → server 自动补空数组；早盘快报正常填 → server 正常存储。无需客户端特殊处理。

### Token 预检 ping payload 模式（2026-06-25 验证）

上报前用最小 payload 做 token 鉴权预检，避免完整复盘生成后才发现 token 过期浪费 LLM 调用：

```bash
# 上报到 xiaoniu.tech
curl -X POST "https://xiaoniu.tech/api/stock/reviews" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${STOCK_REVIEW_API_KEY}" \
  -d '{"date":"2026-06-25","content":"ping"}'
```

- 返回 `HTTP 200 + code 200` → token 完全有效
- 返回 `HTTP 200 + code 401` → token 过期，立即告知用户
- 返回 `HTTP 200 + code 400 + msg: "市场总览格式错误"`（或类似）→ **token 有效但 payload 格式不对**（这是好信号——鉴权已通过，只是 ping 缺字段）
- 返回 `Connection refused` → 服务器不可达

**经验**：本次复盘实际收到 `code 400 "市场总览格式错误"`，证明鉴权通过，继续生成完整 JSON 上报最终成功。**不要因为 code 400 就放弃——必须看 msg 内容判断是格式问题还是鉴权问题。**