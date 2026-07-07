# stock-review-skill

一个可分发的通用 Agent Skill 包，用于生成中国 A 股市场复盘报告。

## 功能

- 生成复盘 markdown 文档
- 生成结构化复盘 JSON
- 汇总今日热点、消息面、明日关注板块与个股
- 支持历史日期复盘
- 支持按配置决定是否上报复盘结果

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

## 本地配置

仓库提交的是示例配置文件 `config.example.yml`，本地实际使用的 `config.yml` 不纳入 Git 版本控制。

推荐做法：

```text
Copy-Item config.example.yml config.yml
```

随后只修改本地 `config.yml`。由于 `.gitignore` 已忽略该文件，正常 `git pull` 不会覆盖你的个人配置。

如果以后误把 `config.yml` 提交进 Git，需要先把它从索引中移除，再保留本地文件：

```text
git rm --cached config.yml
```

这个模式适合存放本地地址、开关项、个人凭证占位等易变配置；真实密钥仍优先建议通过环境变量或安全输入方式注入。

当前推荐的配置结构如下：

```yaml
review:
    upload:
        enabled: false
        apiUrl: "https://xiaoniu.tech/api/stock/reviews"
        apiKey: ""
        timeoutSeconds: 30
    local:
        doc:
            enabled: true
            path: "/usr/local/files/docs/stock"
        json:
            enabled: true
            path: "/usr/local/files/docs/stock"
```

其中，CLI 当前真正会读取的是 `review.upload.enabled`、`review.upload.apiUrl`、`review.upload.apiKey` 和 `review.upload.timeoutSeconds`；`review.local.*` 目前只保留为本地落盘配置预留字段，当前脚本不会消费它们。只有当 `review.upload.enabled=true`，或被命令行/环境变量显式开启上传时，才需要配置 apiKey。

如果没有检测到 `config.yml`，CLI 会直接使用与 `config.example.yml` 对齐的默认参数；也就是说，`config.example.yml` 既是示例，也是默认配置基线。

`report` 子命令的配置优先级为：命令行参数 > 环境变量 > `config.yml` > 默认参数（与 `config.example.yml` 一致）。

可覆盖的运行时参数包括：

- `--config-file` > `STOCK_REVIEW_CONFIG_FILE` > `./config.yml`
- `--api-url` > `STOCK_REVIEW_API_URL` > `review.upload.apiUrl` > 内置默认 API 地址
- `--api-key` > `STOCK_REVIEW_API_KEY` > `review.upload.apiKey` > 无默认值
- `--timeout-seconds` > `STOCK_REVIEW_API_TIMEOUT_SECONDS` > `review.upload.timeoutSeconds` > `30`
- `--upload-enabled` / `--upload-disabled` > `STOCK_REVIEW_UPLOAD_ENABLED` > `review.upload.enabled` > `false`

为了兼容旧配置，CLI 仍会接受历史字段 `upload-review`、`baseUrl` 和 `doc-path`，但建议后续统一迁移到上面的新结构。

### Webhook 配置（可选）

如需将复盘结果同步推送到自有后端 / Discord / Slack 等 Webhook 接收端，可在 `config.yml` 中启用 `review.upload.webhook` 子节点。**已知约束**：v1 仅完成「字段 + CLI 持久化」，实际推送触发逻辑留待 v2 落地（详细说明见 [`references/review_api.md`](./references/review_api.md) 的「Webhook 推送」章节）。

```text
python scripts/stock_review_cli.py set-webhook-url https://your-host/api/hook
python scripts/stock_review_cli.py set-webhook-secret
python scripts/stock_review_cli.py show-webhook
```

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

只有当配置启用了上传时，apiKey 才是上报流程的前置要求；若未启用上传，则可以只生成本地 markdown 和 JSON，而不必配置 apiKey。

当 `review.upload.enabled=true`，或通过命令行/环境变量显式启用上传时，agent 才需要确认用户已提供 apiKey，并在本地持久化为环境变量 `STOCK_REVIEW_API_KEY`。

推荐命令：

```text
python ./scripts/stock_review_cli.py set-api-key
```

- 脚本会在终端中安全提示用户输入 apiKey，并将其持久化到本地环境变量 `STOCK_REVIEW_API_KEY`。
- `apiKey`、`token` 与 `STOCK_REVIEW_API_KEY` 指代同一份接口凭证。
- 若已启用上传但用户拒绝提供 apiKey，则必须停止上报流程；若未启用上传，则不应因缺少 apiKey 阻塞本地 markdown 和 JSON 生成。

若启用了上传，生成 JSON 文件后必须使用以下命令执行真实上报；若未启用上传，则不需要执行该命令：

```text
python ./scripts/stock_review_cli.py report --json-file <path-to-review-json>
```

如需临时覆盖配置，可直接通过命令行传参，例如：

```text
python ./scripts/stock_review_cli.py report --json-file <path-to-review-json> --api-url https://xiaoniu.tech/api/stock/reviews --timeout-seconds 60 --upload-enabled
```

如果未启用上传而误执行 `report`，CLI 会直接返回“Upload is disabled by configuration”的错误，提示先开启上传配置。

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