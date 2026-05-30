---
name: stock-review-skill
description: '生成中国 A 股市场复盘报告。Use when users ask for 股市复盘、A股复盘、盘后总结、明日关注板块、热点梳理、复盘 JSON、复盘结果上报。'
argument-hint: '[复盘日期，可选 YYYY-MM-DD；不传则按当日复盘规则处理]'
user-invocable: true
---

# 股市复盘

根据复盘对象日期的盘面表现、盘中及盘后消息，生成标准化的复盘 markdown 文档、结构化 JSON 结果，并上报至复盘 API。

## 何时使用

- 用户要求生成中国 A 股或沪深市场的复盘报告。
- 用户要求总结今日热点、消息面、明日关注板块、明日关注个股。
- 用户要求输出复盘 markdown、复盘 JSON，或把结果上报到既定 API。
- 用户给出历史日期，希望复盘指定交易日。

## 输入约定

- 默认执行当日复盘；若用户明确指定日期，则执行历史复盘。
- 当日复盘以 9:00 至次日 9:00 为一个复盘周期；例如 7 月 12 日上午 7:00 复盘，对象日期为 7 月 11 日。
- 历史复盘以用户指定日期的 9:00 至次日 9:00 为消息与盘面收集范围。
- 每日 9:00 至 16:00 交易时段内不执行当日复盘；该限制不适用于历史复盘。
- 使用本 skill 前，需先在宿主环境或调用上下文中定义 `apiKey`。
- `apiKey` 即复盘上报接口使用的 Bearer Token；若未定义 `apiKey`，则只生成 markdown 和 JSON，不执行 API 上报。

## 输出要求

1. 今日热点：总结今日大盘盘面与领涨、热点、龙头板块。
2. 消息面：收集今日盘中影响股票的突发新闻与重点消息。
3. 明日关注板块：根据今日盘面表现、盘中及盘后的政经新闻，预判明日重点关注的板块。
4. 明日关注个股：根据重点关注板块，综合情绪、盘面、业绩等，挑选明日关注个股，数量在15只以内。需要给出明确的个股代码和名称，以及推荐理由。
5. JSON 结果：字段结构必须符合 [股市复盘 JSON 模型](./references/review_model.md)。
6. 若生成 JSON，则 `content` 字段应与 markdown 正文一致；若仅需结构示例，可留空。

## 执行流程

1. 确定复盘对象日期，并据此判断是当日复盘还是历史复盘。
2. 收集复盘对象日期对应的盘面数据、板块表现、个股异动和政经新闻。
3. 优先从以下来源收集信息：东方财富、同花顺、澎湃财经、新华社、财联社，以及其他相关政经网站。
4. 基于收集结果生成复盘 markdown 文档，格式参考 [文档模板](./assets/review_doc_template.md)。
5. 生成结构化 JSON，字段与示例参考 [JSON 模型](./references/review_model.md) 和 [JSON 示例](./assets/review_sample.json)。
6. 需要上报且已定义 `apiKey` 时，按 [复盘 API 说明](./references/review_api.md) 发送 `POST` 请求。

## 资源

- [复盘 API](./references/review_api.md)
- [股市复盘 JSON 模型](./references/review_model.md)
- [复盘 markdown 模板](./assets/review_doc_template.md)
- [复盘 markdown 示例](./assets/review_doc_sample.md)
- [复盘 JSON 示例](./assets/review_sample.json)

## 备注

- 本 skill 适合重复执行的复盘工作流，不适合作为实时交易建议工具。
- 若用户只需要单个字段说明或接口细节，可直接读取相应资源文件，而不必执行完整流程。
- 本 skill 中的 `token` 与 `apiKey` 指代同一份接口凭证。
