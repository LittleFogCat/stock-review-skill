---
name: stock-review-skill
description: '生成中国 A 股市场复盘报告。Use when users ask for 股市复盘、A股复盘、盘后总结、明日关注板块、热点梳理、复盘 JSON、复盘结果上报。'
argument-hint: '[复盘日期，可选 YYYY-MM-DD；不传则按当日复盘规则处理]'
user-invocable: true
---

# 股市复盘

根据复盘对象日期的盘面表现、盘中及盘后消息，生成标准化的复盘 markdown 文档、结构化 JSON 结果，并通过 Python 脚本上报至复盘 API。apiKey 是整个流程的硬性前置条件，上报成功是流程完成条件。

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
- 执行完整复盘流程前，必须先向用户索取 apiKey，用于复盘上报鉴权。
- 若本地尚未持久化 `STOCK_REVIEW_API_KEY`，或用户要求更新凭证，必须先运行 `python ./scripts/stock_review_cli.py set-api-key`，由脚本在终端中安全读取 apiKey 并持久化到本地环境变量 `STOCK_REVIEW_API_KEY`。
- 不要把 apiKey 直接写入自然语言回复、日志、markdown、JSON 或命令行历史；优先让用户在脚本提示中输入。
- `apiKey`、`token` 与 `STOCK_REVIEW_API_KEY` 指代同一份接口凭证。
- 若用户拒绝提供 apiKey，必须立即停止整个复盘流程，不得继续生成 markdown、JSON，亦不得提供任何“仅本地生成、不上报”的替代执行路径。

## 输出要求

1. 今日热点：总结今日大盘盘面与领涨、热点、龙头板块。
2. 消息面：收集今日盘中影响股票的突发新闻与重点消息。
3. 明日关注板块：根据今日盘面表现、盘中及盘后的政经新闻，预判明日重点关注的板块。
4. 明日关注个股：根据重点关注板块，综合情绪、盘面、业绩等，挑选明日关注个股，数量在15只以内。需要给出明确的个股代码和名称，以及推荐理由。
5. JSON 结果：字段结构必须符合 [股市复盘 JSON 模型](./references/review_model.md)。
6. JSON 中的 `content` 字段应与 markdown 正文一致，不得留空。
7. 上报结果：必须执行真实 API 上报，并向用户返回脚本的实际执行结果；若上报失败，则本次复盘流程视为未完成。

## 执行流程

1. 确定复盘对象日期，并据此判断是当日复盘还是历史复盘。
2. 在开始收集盘面信息前，先确认用户是否已提供 apiKey；若未提供或本地环境变量 `STOCK_REVIEW_API_KEY` 缺失，则先运行 `python ./scripts/stock_review_cli.py set-api-key` 完成持久化。若用户不提供 apiKey，则立即终止流程。
3. 收集复盘对象日期对应的盘面数据、板块表现、个股异动和政经新闻。
4. 优先从以下来源收集信息：东方财富、同花顺、澎湃财经、新华社、财联社，以及其他相关政经网站。
5. 基于收集结果生成复盘 markdown 文档，格式参考 [文档模板](./assets/review_doc_template.md)。
6. 生成结构化 JSON，字段与示例参考 [JSON 模型](./references/review_model.md) 和 [JSON 示例](./assets/review_sample.json)，并将 JSON 落盘为本地文件，例如 `stock_review_<date>.json`。
7. 生成 JSON 后，必须立即运行 `python ./scripts/stock_review_cli.py report --json-file <json文件路径>` 执行真实 `POST` 请求，不得仅以自然语言描述接口调用步骤代替实际执行。
8. 只有在第 7 步上报成功后，完整复盘流程才算完成；若上报失败，必须向用户明确返回失败信息，而不是将流程描述为已完成。
9. 汇总返回给用户时，应包含 markdown 正文、JSON 结果，以及脚本上报成功或失败的实际结果。

## 资源

- [复盘 API](./references/review_api.md)
- [上报 Python CLI](./scripts/stock_review_cli.py)
- [股市复盘 JSON 模型](./references/review_model.md)
- [复盘 markdown 模板](./assets/review_doc_template.md)
- [复盘 markdown 示例](./assets/review_doc_sample.md)
- [复盘 JSON 示例](./assets/review_sample.json)

## 备注

- 本 skill 适合重复执行的复盘工作流，不适合作为实时交易建议工具。
- 若用户只需要单个字段说明或接口细节，可直接读取相应资源文件，而不必执行完整流程。
- 本 skill 中的 `token` 与 `apiKey` 指代同一份接口凭证。
- 该 skill 的标准输出默认包含真实上报，不存在“只生成不报送”的完成态。
- 只要用户请求复盘，agent 就必须先满足 apiKey 前置条件，再走脚本上报路径，不得只输出 curl、伪代码或接口描述。

## 常见陷阱

### JSON 中直接包含中文引号导致解析失败
当 JSON 的 `reason` 或 `content` 字段中出现中文左引号（"）或右引号（"）时，Python 的 `json.dumps` 可能将其视为字符串结束符，导致 `JSONDecodeError`。**解决办法**：使用 Python 的 `json.dump(data, f, ensure_ascii=False, indent=2)` 从代码输出 JSON，避免手写时引入未转义的特殊引号。`"喝酒吃药"` 等短语应写为 `'喝酒吃药'` 或使用「」替代。

### 网络数据源阻截
腾讯行情 API（`qt.gtimg.cn`）通常稳定可用且无需 cookie/user-agent 处理。东方财富 API 可能对无浏览器头的 curl 请求返回空响应。东财网页版嵌入了大量 iframe，浏览器 snapshot 可能超时。详见 [数据源参考](./references/data_source.md)。

### 交易日判断
周末或节假日复盘时，对象日期回退到最近一个交易日。非交易日时段没有盘面数据更新，获取的指数为上一交易日收盘值。