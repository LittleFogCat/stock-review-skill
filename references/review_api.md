# 股市复盘API

## 上报复盘结果

**前置条件**：

- 调用该接口前，必须先定义 `apiKey`。
- 本文中的 `apiKey` 即 Bearer Token；`token` 与 `apiKey` 表示同一份接口凭证。
- 若未定义 `apiKey`，则不得执行上报请求。

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