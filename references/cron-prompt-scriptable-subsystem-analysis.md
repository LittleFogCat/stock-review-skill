# 可脚本化子系统分析：cron prompt 冗余样板代码清单

> 创建时间：2026-07-05
> 创建者：小奶茉
> 场景：主人要求"检查 stock-review-skill 里可脚本化、应从 cron prompt 省略的部分"
> 状态：**分析完成，尚未实现**——本文档是设计蓝图，等待主人批准后开工

## 核心结论

skill 当前 1836 行的 SKILL.md 中，**cron 必跑的样板代码累计 ~240 行**，可脚本化后 prompt 缩短至 ~8 行调用。

## 可脚本化的 8 大子系统

| # | 子系统 | 当前 prompt 行数 | 脚本化后 | 对应 SKILL.md 章节 |
|---|---|---|---|---|
| A | 互斥锁 + 文件检查 | ~30 行 | 1 行 | "🔴 Cron Pipeline 架构约束" 事故 A/C |
| B | JSON 字段类型验证 | ~25 行 | 1 行 | 1.4 JSON 类型约束（markets/todayHot/changePercent/content） |
| C | Token 读取 | ~15 行 | 1 行 | "Token 预检流程" + 1.8 上报约束 |
| D | API 上报 | ~30 行 | 1 行 | "API 上报方式" + "Python 写入陷阱" |
| E | 行情数据采集 | ~50 行 | 1 行 | "执行流程·当日复盘" + 美股字段索引陷阱 |
| F | final response 构造 | ~20 行 | 1 行 | "事故 A/B/D 修复" + read_file 行号剥离 |
| G | 节假日检测 | ~10 行 | 1 行 | "节假日复盘" + 3 步验证链 |
| H | 风险信号扫描 | ~60 行 | 1 行 | "🔴 风险信号触发机制" R1/R2/R3 |

## 重要脚本清单与对应章节映射

### A. cron_preflight.py
**对应 SKILL.md 章节**：
- "🔴 Cron Pipeline 架构约束 → 事故 A（final response 摘要截断）"（事故 A 修复）
- "🔴 Cron Pipeline 架构约束 → 事故 C（重复推送）"（互斥锁机制）
- "🔴 Cron Pipeline 架构约束 → 事故 D（看门狗跨职责）"（权限检查）

**输入**：`python3 cron_preflight.py <mode> <date>`（mode = `daily_review` 或 `early_brief`）

**输出状态码**：
- `0 LOCKED` → 看门狗/重试模式：主任务已推送，立即 `[SILENT]` 退出
- `0 LOCK_ACQUIRED` → 主任务：抢锁成功，继续
- `0 READY` → 文件已生成 + token 有效 + 大小达标
- `2 TOKEN_EXPIRED` → 上报前 token 预检失败（最小 payload POST 返回 401）
- `3 SERVER_DOWN` → 服务器不可达（xiaoniu.tech ping 通但 443 拒连接）

**事故根治理由**：
事故 A：cron prompt 第一步调用预检，强制 LLM 看到明确状态码才能继续，杜绝"摘要截断"
事故 C：lockfile 在文件系统层隔离主任务和看门狗（`~/.hermes/cron/locks/{早盘,复盘}_YYYY-MM-DD.lock`）
事故 D：脚本输出 [SILENT]/[ALERT]/[RETRY] 状态字符串，喂给 LLM 当 prompt 输入，自然阻止"跨职责塞股市内容"

---

### B. validate_review_json.py
**对应 SKILL.md 章节**：
- "输出要求" 字段类型对照表（17 行）
- 1.4 JSON 类型约束（markets 是对象、todayHot 是对象、changePercent 是 number、content 必填）

**输入**：`python3 validate_review_json.py <json_file> [model_file]`

**验证项**（按 review_model.md 实际定义）：
- `markets` 是 object（非数组、非 null）
- `markets.indices[].reason` 非空（事故 "评价不能为空"）
- `todayHot` 是 object（含空数组也合法）
- `todayHot.topSectors[].reason` 非空
- `todayHot.fallingSectors[].reason` 非空
- 所有 `changePercent` 是 number（非字符串 "N/A"、非 null）
- `news[].content` 是 array（非字符串——事故"内容必须为数组"）
- `focusSectors[].name` 字段名（不是 `sector`！）
- `focusStocks[].sector` 字段名
- `focusSectors[].stocks[]`、`focusStocks[].stocks[]` 内部 code/name/reason 非空
- `type` 字段必填：早盘快报=1、复盘=2（事故"type 字段必须为 0、1 或 2"）
- 当日复盘不得包含 `focusSectors`/`focusStocks`（仅早盘快报专属）

**输出**：`[OK]` 或 `[ERROR] <字段路径>: <期望类型> 实际 <实际类型>`

---

### C. resolve_api_key.py
**对应 SKILL.md 章节**：
- "Token 更新需要同步两处 + 预检"
- "API 上报方式：Python 脚本"
- "execute_code 沙箱不继承 shell 环境变量"

**输入**：`python3 resolve_api_key.py`

**读取优先级**：
1. `~/.hermes/skills/stock-review-skill/config.yml` 中 `review.upload.apiKey`
2. `~/.profile` 中 `export STOCK_REVIEW_API_KEY='...'` 或 `"..."`（自动兼容单/双引号）
3. `~/.bashrc` 同上（仅当 ~/.profile 无值，作为 fallback）

**验证**：key 必须以 `xntk_` 开头且长度合理（>20 字符）

**输出**：`有效 key 到 stdout` 或 `exit 1`

**事故根治理由**：
- 单/双引号自动识别：`~/.profile` 常见 `xntk_xxxx='...'`（单引号），旧正则只匹配双引号导致 key 为空 → 401
- 3 处优先级避免「token 已更新但调用方读旧值」的 race condition

---

### D. upload_review.py
**对应 SKILL.md 章节**：
- 1.8 上报约束第 1 条（token 预检）
- 1.8 上报约束第 2 条（type 字段）
- 1.8 上报约束第 3 条（上报方式：Python 脚本）
- "curl 上报时 Authorization header 触发 shell 'Bad substitution' 错误"（2026-06-25 事故）
- "Python 写入 shell 脚本时 $VAR 字面量被吞掉的陷阱"

**输入**：`python3 upload_review.py <json_file>`

**内部步骤**：
1. 调 `resolve_api_key.py` 获取 key
2. 先 POST 最小 payload `{"date":"...","content":"ping"}` 做 token 预检
3. code 200 → 继续完整 payload
4. code 401 → 输出 `TOKEN_EXPIRED`，exit 2
5. code 400 → token 有效但格式不对（已通过鉴权），exit 4
6. ConnectionError → 输出 `SERVER_DOWN`，exit 3

**事故根治理由**：
- 内置 token 预检（先 ping 最小 payload），避免完整复盘生成后才发