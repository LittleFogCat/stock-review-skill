# stock-review-skill

一个可分发的通用 Agent Skill 包，用于生成中国 A 股市场复盘报告。

## 功能

- 生成复盘 markdown 文档
- 生成结构化复盘 JSON
- 汇总今日热点、消息面、明日关注板块与个股
- 支持历史日期复盘
- 支持按既定 API 上报复盘结果

## 仓库结构

本仓库根目录就是 skill 包内容。

```text
stock-review-skill/
├── SKILL.md
├── README.md
├── scripts/
│   └── stock_review_cli.py
├── assets/
│   ├── review_doc_sample.md
│   ├── review_doc_template.md
│   └── review_sample.json
└── references/
    ├── review_api.md
    └── review_model.md
```

## 安装方式

在目标工作区中，将本仓库内容放入以下任一标准 skill 目录，并确保目标目录名为 `stock-review-skill`：

- `.github/skills/stock-review-skill/`
- `.agents/skills/stock-review-skill/`
- `.claude/skills/stock-review-skill/`

例如，可将当前仓库根目录整体复制到：

```text
<workspace>/.github/skills/stock-review-skill/
```

复制后，目标目录中应直接包含 `SKILL.md`、`assets/`、`references/`，不要再额外嵌套一层仓库目录。

## 使用场景

适用于以下请求：

- 股市复盘
- A股复盘
- 盘后总结
- 明日关注板块
- 热点梳理
- 复盘 JSON
- 复盘结果上报

## 首次使用与鉴权

从现在开始，apiKey 是整个复盘流程的前置要求，且复盘结果上报必须通过仓库内的 Python 脚本执行，不能只用自然语言描述接口调用。

执行任何完整复盘流程前，agent 都应先确认用户已提供 apiKey，并在本地持久化为环境变量 `STOCK_REVIEW_API_KEY`。

推荐命令：

```text
python ./scripts/stock_review_cli.py set-api-key
```

- 脚本会在终端中安全提示用户输入 apiKey，并将其持久化到本地环境变量 `STOCK_REVIEW_API_KEY`。
- `apiKey`、`token` 与 `STOCK_REVIEW_API_KEY` 指代同一份接口凭证。
- 若用户拒绝提供 apiKey，则必须停止整个复盘流程，不得继续生成 markdown、JSON 或任何未上报结果。

生成 JSON 文件后，必须使用以下命令执行真实上报；未完成上报不算流程完成：

```text
python ./scripts/stock_review_cli.py report --json-file <path-to-review-json>
```

## 主要资源

- [SKILL.md](./SKILL.md)
- [Python CLI](./scripts/stock_review_cli.py)
- [复盘 markdown 模板](./assets/review_doc_template.md)
- [复盘 markdown 示例](./assets/review_doc_sample.md)
- [复盘 JSON 示例](./assets/review_sample.json)
- [复盘 JSON 模型](./references/review_model.md)
- [复盘 API](./references/review_api.md)

## 注意事项

- `SKILL.md` 中的 `name` 为 `stock-review-skill`，安装后的目录名应与之保持一致。
- 本 skill 面向复盘工作流，不应作为实时交易建议工具使用。
- 若只需要字段说明或接口细节，可直接阅读 `references/` 下的文档。
- 若需要更新凭证，可再次运行 `python ./scripts/stock_review_cli.py set-api-key` 覆盖本地 `STOCK_REVIEW_API_KEY`。