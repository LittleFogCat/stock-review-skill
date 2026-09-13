# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 这是什么

`stock-review-skill` 是一个可分发的通用 Agent Skill 包,根目录就是 skill 内容本身。`SKILL.md` 是宿主加载的入口,定义核心约束、工作模式、执行流程。

**三种工作模式**:当日复盘(15:15)、早盘快报(8:00)、快速股价查询。详细触发判断见 `SKILL.md` 第 2-3 节。

**关键事实**:仓库中的一切约束/清单/事故复盘都是历史事故累积的结果,不是抽象规则。修改前先读 `references/incidents/` 理解约束背后的真实失败案例(尤其 taotao-auto、copper-tariff、risk-scanner-overreach)。

## 命令

### JSON 校验与反编造

```bash
# 上报前必跑:JSON 字段类型预校验(对应 SKILL.md 1.4 常见错误码)
python scripts/validate_review_json.py path/to/review.json

# 反编造自检清单 + 模糊措辞黑名单朗读(对应 SKILL.md 1.2.3)
python scripts/anti_fabrication.py checklist

# 校验量化声明清单(每条 claim 必须带 source/scope/timestamp)
python scripts/anti_fabrication.py check-claims claims.json
```

### 日期与跨日历工具

```bash
# 交易日判断(K 线方案,API 不可用时保守返回 True)
python scripts/is_trading_day.py 2026-07-06  # exit 0=交易日 1=非交易日 2=无法判断

# 早盘「隔夜美股」真实日期(A 股日历 + 美股节假日双层回退)
python scripts/resolve_overnight_us.py 2026-06-29
# 输出 JSON 含 us_data_date(剔除美股节假日后的真实日期)+ warning + label
```

### 上报 CLI

```bash
# 写入 token 到 review.upload.webhook.token(config.yml)
python scripts/stock_review_cli.py set-webhook-token <token>
python scripts/stock_review_cli.py set-webhook-url <url>

# 上报复盘 JSON(优先级:CLI > 环境变量 > config.yml > 默认)
python scripts/stock_review_cli.py report --json-file review.json \
    [--config-file path] [--api-url URL] [--api-key KEY] \
    [--timeout-seconds 30] [--upload-enabled|--upload-disabled]
```

兼容别名(set-api-key 已 deprecation,会同时写 STOCK_REVIEW_API_KEY + webhook.token):

```bash
python scripts/stock_review_cli.py set-api-key
# stderr: WARNING: 'set-api-key' is deprecated; prefer 'set-webhook-token' ...
```

参数优先级见 `README.md` 和 `stock_review_cli.py` 的 `resolve_report_settings` 函数。

### Cron 看门狗重试模板

`scripts/watchdog_retry_template.py` 是 cron 模式复盘重试的 Python 骨架,包含检查文件(>5KB)→ token 预检 → 数据采集 → JSON 构建 → 上报的标准流程。**复制到 `/tmp/` 修改 DATE/TITLE/采集函数再运行**,不要就地编辑模板。

## 仓库结构

```
SKILL.md                    宿主加载入口:核心约束(§1)+ 三模式定义(§2)+ 输入(§4)+ 输出(§5)+ 执行步骤(§6)
README.md                   安装方式 + 配置优先级 + 使用场景
config.example.yml          CLI 真实消费的字段(仅 review.upload.*)
config.yml                  本地实际配置(.gitignored,不能误提交)

scripts/
  stock_review_cli.py       上报 CLI + set-webhook-{url,token,secret} + 配置加载(无 PyYAML 依赖,自带 YAML 解析 + serializer)；set-api-key 为 deprecation alias
  validate_review_json.py   上报前必跑:JSON 字段类型/title 正则/focusSectors 字段名等
  anti_fabrication.py       反编造:assert_data_provenance + enforce_no_fabrication 装饰器
  is_trading_day.py         K 线判定交易日
  resolve_overnight_us.py    跨周末美股日期解析(含美股 9 大节假日表)
  watchdog_retry_template.py cron 看门狗重试模板

references/                  SKILL.md 涉及的详细子文档(数据源/陷阱/API/事故)
  review_model.md           JSON 模型字段表(注意 focusSectors[].name vs focusStocks[].sector 字段名差异)
  review_api.md             上报/查询 API + 常见错误码
  data_source.md            pyTDX/akshare 状态总览(akshare THS/东财被封,东财 push2 自 2026-07-01 不可用)
  cron_setup.md             cron 调度 + 看门狗 + idle timeout(部署层,Skill 职责外但常被引用)
  holiday_detection.md      节假日检测三种方案(K 线/Sina 新闻/Tencent API)
  tencent-api-field-map.md  腾讯 API 字段索引,含美股 [3]/[4] 互换的踩坑记录
  data-source-fallback-2026-07-01.md  push2 失效后的完整回退流程
  incidents/                事故复盘(taotao-auto 编造 / copper-tariff 漏扫 / risk-scanner-overreach)

assets/                      模板/示例(不修改,只是结构参考)
templates/                   实战验证过的 markdown 模板(morning-brief/daily-review)
```

## 工作流起点

接到任何「股市复盘/A股复盘/盘后总结/早盘/快报/股价查询」请求,流程是:

1. **判断模式** — `SKILL.md` §2(当日复盘/早盘快报/快速股价查询),§3 触发词对应。
2. **必读约束** — `SKILL.md` §1(1.1 事实约束 / 1.2 反编造红线 / 1.4 JSON 类型 / 1.5 数据源 / 1.7 查询约束 / 1.8 上报约束 / 1.9 风险信号)。
3. **场景具体步骤** — `SKILL.md` §6.1(通用)+ §6.2/6.3/6.4(各模式步骤)。
4. **跑校验脚本** — `validate_review_json.py` 上报前必跑;`anti_fabrication.py checklist` 输出前必跑。
5. **上报(若 enabled)** — 先 token 预检(`SKILL.md` 1.8),再 `stock_review_cli.py report`。

## 编辑纪律(必读)

SKILL.md 是宿主加载的入口,**任何修改都会影响所有调用者**。项目采用「每节一句话结论 + 子文档引用」的精简模式(见 `.claude/projects/D--Repositories-stock-review-skill/memory/skill_cleanup_pattern.md`):

- **重复内容** → 保留一句在 SKILL.md,详细内容确认后移到 `references/` 子文档
- **覆盖范围已被其他约束吸收** → 直接删除
- **历史误诊/已推翻的判断** → 移到子文档「历史」章节,不要散落在 SKILL.md

修改 SKILL.md 前先看 `.ai/todo/` 目录下的 review 笔记(理解当前待办背景)。

## 数据源警示(2026-07 实时状态)

- **东财 push2 API**:自 2026-07-01 起完全不可用(5+ 次重试均 `Remote end closed`,疑似 IP 段屏蔽)。**视为「可尝试」而非可靠**,失败立即回退到 `references/data-source-fallback-2026-07-01.md` 的 Sina `/cpbd/` + 首页 + snipe + 腾讯 pt 组合。
- **akshare 东财/THS**:服务端识别封禁
- **JRJ 首页**:死页面 + 404 + CAPTCHA 已弃用
- **腾讯 API `qt.gtimg.cn`**:稳定主用;美股 `[3]/[4]` 是当前价/昨收(与 A 股 `[2]/[3]` 互换),涨跌幅在 `[31]/[32]`;**所有代码族成交额字段 `[7]` 都返回 `0`**
- **腾讯 API pt 板块代码**(`pt01801xxx`):33 个仅 13 个有数据,覆盖不全
- **pyTDX** 服务器 `60.12.136.250:7709` 稳定

## 提交与配置纪律

- **修改提交默认 = commit + push**(推 `https://github.com/LittleFogCat/stock-review-skill.git`)。仅当主人明确说「提交到本地」时只 commit 不 push。
- `config.yml` 是本地个人凭证/路径,**绝不提交**,`.gitignore` 已忽略。若误提交先 `git rm --cached config.yml` 保留本地副本。
- `~/.claude/projects/D--Repositories-stock-review-skill/memory/MEMORY.md` 是主人跨会话记忆索引,SKILL.md 精简方法论已持久化,本项目相关偏好会先写入这里再行动。

## 模式选择速查

| 用户说法 | 模式 | 参考 |
|---------|------|------|
| 股市复盘 / 盘后总结 / A股复盘 | 当日复盘 | SKILL.md §2.1 / §6.2 |
| 早盘快报 / 盘前消息 / 快报 | 早盘快报 | SKILL.md §2.2 / §6.3 |
| 查一下茅台 / 宁德时代多少钱 / 查行情 | 快速股价查询 | SKILL.md §2.3 / §6.4 |
| 复盘 2026-06-15(历史日期) | 当日复盘(历史日期) | SKILL.md §4.2 |

历史复盘不受交易时段限制;当日复盘 9:00-15:15 交易时段内禁止执行(用 `is_trading_day.py` 判断)。
