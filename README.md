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

## 使用前配置

在使用本 skill 前，需要先定义 `apiKey`。

- `apiKey` 即复盘上报接口使用的 Bearer Token。
- `token` 与 `apiKey` 指代同一份接口凭证。
- 若未定义 `apiKey`，本 skill 仍可生成复盘 markdown 和 JSON，但不应执行 API 上报。
- 若宿主支持 secret 或环境变量，建议通过安全配置注入真实凭证，再在运行时作为 `apiKey` 使用。

## 主要资源

- [SKILL.md](./SKILL.md)
- [复盘 markdown 模板](./assets/review_doc_template.md)
- [复盘 markdown 示例](./assets/review_doc_sample.md)
- [复盘 JSON 示例](./assets/review_sample.json)
- [复盘 JSON 模型](./references/review_model.md)
- [复盘 API](./references/review_api.md)

## 注意事项

- `SKILL.md` 中的 `name` 为 `stock-review-skill`，安装后的目录名应与之保持一致。
- 本 skill 面向复盘工作流，不应作为实时交易建议工具使用。
- 若只需要字段说明或接口细节，可直接阅读 `references/` 下的文档。