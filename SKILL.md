---
name: stock-review-skill
description: '生成中国 A 股市场复盘报告。Use when users ask for 股市复盘、A股复盘、盘后总结、明日关注板块、热点梳理、复盘 JSON、复盘结果上报。'
argument-hint: '[复盘日期，可选 YYYY-MM-DD；不传则按当日复盘规则处理]'
user-invocable: true
---

# 股市复盘

根据复盘对象日期的盘面表现、盘中及盘后消息，生成标准化的复盘 markdown 文档与结构化 JSON 结果；若配置启用了上传，则再通过 Python 脚本上报至复盘 API。apiKey 仅在启用上传时才是前置条件。

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
- **跨周末复盘**：若复盘对象日期为周五，且当前时间在周六/周日/周一，则「消息面」应扩展收集周六至周一的周末新闻（不限于周五 9:00→次日 9:00 窗口）。将周末重大事件单独列为「周末要闻」板块，补充到消息面中。关注的重点包括：周五晚间美股的映射表现、周末政策/产业事件（如 IPO 上会）、中东地缘局势变化、以及下周一可能影响开盘的情绪催化。
- 若 `config.yml` 中的 `review.upload.enabled=true`，或用户通过命令行/环境变量显式启用了上传，则执行上报前必须先向用户索取 apiKey，用于复盘上报鉴权。
- 若已启用上传且本地尚未持久化 `STOCK_REVIEW_API_KEY`，或用户要求更新凭证，必须先运行 `python ./scripts/stock_review_cli.py set-api-key`，由脚本在终端中安全读取 apiKey 并持久化到本地环境变量 `STOCK_REVIEW_API_KEY`。
- 不要把 apiKey 直接写入自然语言回复、日志、markdown、JSON 或命令行历史；优先让用户在脚本提示中输入。
- `apiKey`、`token` 与 `STOCK_REVIEW_API_KEY` 指代同一份接口凭证。
- 若已启用上传但用户拒绝提供 apiKey，必须立即停止上报流程；若未启用上传，则不得因缺少 apiKey 阻塞 markdown 与 JSON 的本地生成。

## 输出要求

1. 今日热点：总结今日大盘盘面与领涨、热点、龙头板块。
2. 消息面：收集今日盘中影响股票的突发新闻与重点消息。
3. 明日关注板块：根据今日盘面表现、盘中及盘后的政经新闻，预判明日重点关注的板块。
4. 明日关注个股：根据重点关注板块，综合情绪、盘面、业绩等，挑选明日关注个股，数量在15只以内。需要给出明确的个股代码和名称，以及推荐理由。
5. 事实约束：所有指数点位、涨跌幅、成交额、板块表现、个股代码/名称、新闻、政策、公告、业绩和事件原因，必须来自本次实际收集到的数据或原始报道；无法核实的内容宁可省略，也不得猜测、脑补、按常识补全，或为了凑结构而编造。
6. 模板与示例约束：[复盘 markdown 模板](./assets/review_doc_template.md)、[复盘 markdown 示例](./assets/review_doc_sample.md) 与 [复盘 JSON 示例](./assets/review_sample.json) 仅用于格式和字段说明，不是事实来源；不得把示例中的板块、个股、新闻、涨跌幅、理由等内容改写后当作本次复盘事实。
7. JSON 结果：字段结构必须符合 [股市复盘 JSON 模型](./references/review_model.md)。
8. JSON 中的 `content` 字段应与 markdown 正文一致，不得留空。
9. 输出前复查：必须对 markdown 与 JSON 中的关键事实做一轮复查，至少核对交易日期、指数数据、热点板块、新闻标题与结论、关注个股代码/名称/理由是否都能在已收集来源中找到依据；发现无依据、互相矛盾或来源不清的内容时，必须删除或改写为明确的不确定表述。
10. 上报结果：若已启用上传，必须执行真实 API 上报，并向用户返回脚本的实际执行结果；若上报失败，则本次复盘流程视为未完成。若未启用上传，则可跳过上报，本地 markdown 与 JSON 生成完成即可视为流程完成。

## 执行流程

1. 确定复盘对象日期，并据此判断是当日复盘还是历史复盘。
2. 先读取 `config.yml` 中的 `review.upload.enabled`；若其为 `true`，或用户通过命令行/环境变量显式启用了上传，再确认用户是否已提供 apiKey。若未提供或本地环境变量 `STOCK_REVIEW_API_KEY` 缺失，则先运行 `python ./scripts/stock_review_cli.py set-api-key` 完成持久化。若此时用户仍不提供 apiKey，则立即终止上报流程；若未启用上传，则跳过此步骤。
3. 收集复盘对象日期对应的盘面数据、板块表现、个股异动和政经新闻。
4. 优先从以下来源收集信息：财联社电报（cls.cn/telegraph，首推，SSR 渲染浏览器可直接读取）、金融界股票首页（stock.jrj.com.cn，聚合 A 股头条/公告速递/7x24 小时电报，周末新闻也覆盖）、腾讯行情 API（qt.gtimg.cn，指数数据最轻量）、澎湃财经、新华社。
5. 在写入 markdown 和 JSON 前，先逐项核对将要输出的关键事实是否在本次收集结果中有明确依据；若某条事实只来自示例、模板记忆、模糊印象，或无法追溯到已收集来源，则不得写入结果。
6. 基于经过核对的结果生成复盘 markdown 文档，格式参考 [文档模板](./assets/review_doc_template.md)。
7. 生成结构化 JSON，字段与示例参考 [JSON 模型](./references/review_model.md) 和 [JSON 示例](./assets/review_sample.json)，并将 JSON 落盘为本地文件，例如 `stock_review_<date>.json`。
8. 在上报前，复查 markdown 与 JSON 的事实一致性，确认两者没有互相矛盾、没有把示例内容误写成真实事实、没有出现无法证实的结论。
9. 若已启用上传，生成 JSON 后必须立即运行 `python ./scripts/stock_review_cli.py report --json-file <json文件路径>` 执行真实 `POST` 请求，不得仅以自然语言描述接口调用步骤代替实际执行；若未启用上传，则跳过该步骤。注意：命令中可能需要用 `python3` 代替 `python`。
10. 若已启用上传，只有在第 9 步上报成功后，完整复盘流程才算完成；若上报失败，必须向用户明确返回失败信息，而不是将流程描述为已完成。若未启用上传，则 markdown 与 JSON 生成完成即可视为流程完成。
11. 汇总返回给用户时，应包含 markdown 正文、JSON 结果，以及脚本上报成功、失败或已按配置跳过上报的实际结果。

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
- 是否执行真实上报由 `config.yml` 中的 `review.upload.enabled` 控制；当其为 `false` 时，允许以“生成 markdown 与 JSON、跳过上报”作为完成态。
- 只有在启用上传时，agent 才必须先满足 apiKey 前置条件，再走脚本上报路径；未启用上传时，不得凭空要求用户提供 apiKey。
- 如果事实依据不足，允许输出“未确认”或直接省略该条，不允许为了完整性伪造事实。

## 常见陷阱

### 把模板或示例误当成事实来源
模板、示例和历史输出只用于说明结构，不用于提供当日事实。若模型直接复用示例中的板块、个股、新闻、涨跌幅或理由，就会产生事实性错误。**解决办法**：所有将写入结果的事实都必须能回溯到本次实际收集的数据或原始报道；凡是无法指出来源的内容，一律删除，不要保留。

### JSON 中直接包含中文引号导致解析失败
当 JSON 的 `reason` 或 `content` 字段中出现中文左引号（"）或右引号（"）时，Python 的 `json.dumps` 可能将其视为字符串结束符，导致 `JSONDecodeError`。**解决办法**：使用 Python 的 `json.dump(data, f, ensure_ascii=False, indent=2)` 从代码输出 JSON，避免手写时引入未转义的特殊引号。`"喝酒吃药"` 等短语应写为 `'喝酒吃药'` 或使用「」替代。

### 网络数据源阻截
腾讯行情 API（`qt.gtimg.cn`）通常稳定可用且无需 cookie/user-agent 处理。东方财富 API 可能对无浏览器头的 curl 请求返回空响应。东财网页版嵌入了大量 iframe，浏览器 snapshot 可能超时。详见 [数据源参考](./references/data_source.md)。

### 交易日判断
周末或节假日复盘时，对象日期回退到最近一个交易日。非交易日时段没有盘面数据更新，获取的指数为上一交易日收盘值。

### Shell profile 非交互 guard 导致 env var 不生效
`stock_review_cli.py set-api-key` 将 `STOCK_REVIEW_API_KEY` 写入 shell profile。各 shell 的默认 profile 文件有不同行为：
- `.bashrc` 通常顶部有 `[ -z "$PS1" ] && return`，非交互 shell 中 `source ~/.bashrc` 会直接返回，export 语句不会执行
- `.profile` / `.bash_profile` 无此 guard，非交互 shell 也能正常加载

**解决办法：** 如果 `report` 命令报 `STOCK_REVIEW_API_KEY is not configured` 但 key 确实已写入 `.bashrc`，需改用 `source ~/.profile` 或在命令中直接 export 该变量。长期 fix 是将 `resolve_shell_profile()` 中 bash 的目标改为 `.profile`。

### Python CLI 执行失败：python 命令不存在
部分现代 Linux 发行版（如 Ubuntu 20.04+）默认不安装 `python` 符号链接，仅提供 `python3`。直接运行 `python ./scripts/stock_review_cli.py` 会报 `command not found`。
**解决办法：** 如果 `python` 未找到，尝试 `python3`。CLI 脚本头部可以不依赖 shebang，用 `python3 ./scripts/stock_review_cli.py` 显式调用即可。也可在流程开始时检查 `which python || which python3` 确定可用解释器。