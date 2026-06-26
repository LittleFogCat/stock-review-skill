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