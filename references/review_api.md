# 股市复盘API

## 上报复盘结果

**前置条件**：

- 调用该接口前，必须先向用户索取 apiKey。
- 收到 apiKey 后，应先运行 `python ./scripts/stock_review_cli.py set-api-key`，将其持久化为本地环境变量 `STOCK_REVIEW_API_KEY`。
- 本文中的 `apiKey` 即 Bearer Token；`token` 与 `STOCK_REVIEW_API_KEY` 表示同一份接口凭证。
- 若未配置 `STOCK_REVIEW_API_KEY`，则整个复盘流程不得继续，且不得生成未上报的最终结果。
- 上报请求应通过 `python ./scripts/stock_review_cli.py report --json-file <path-to-review-json>` 实际执行，而不是只输出接口描述。
- 对本 skill 而言，上报是完成条件，不是可选环节；JSON 生成后必须立即调用上报脚本。

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