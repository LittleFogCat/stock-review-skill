# 定时复盘 Cron 配置参考

## 推荐调度

```
30 7 * * 1-5
```

每周一到周五早上 7:30（CST / GMT+8）触发，在执行当日复盘时不违反「交易时段 9:00-16:00 内不执行」的限制。

## 为什么 7:30

| 时间点 | 是否可行 | 说明 |
|--------|:---:|------|
| 6:00-7:00 | ⚠️ | 太早，周末新闻和周一早间消息可能尚未充分发布 |
| **7:30** | ✅ | 早间新闻已基本到位，且距 9:00 开盘尚有缓冲 |
| 8:00-8:30 | ✅ | 也可行，但离开盘更近，若流程耗时较长可能挤压 |
| 9:00-16:00 | ❌ | 交易时段，skill 规则明确禁止执行当日复盘 |
| 16:00-17:00 | ⚠️ | 盘后数据可能尚未完全结算，部分 API 数据可能滞后 |
| 17:00+ | ✅ | 盘后复盘可用，但非交易日的盘后时段会回退到前一交易日 |

## 跨周末行为

周一 7:30 触发时，复盘对象日期为上周五。skill 的跨周末规则自动生效：
- 消息面扩展收集周六~周一早间的周末新闻
- 新增「周末要闻」板块
- 关注美股周五晚间映射、周末政策事件、地缘变化

## Cron 创建命令参考

### 单用户模式（发送到触发来源）

```text
cronjob action=create \
  name="早盘复盘（工作日7:30）" \
  schedule="30 7 * * 1-5" \
  skills=["stock-review-skill"] \
  prompt="执行当日股市复盘流程..." \
  deliver="origin"
```

### 多用户群发模式（发送到所有已配对 QQbot 用户）

`deliver` 参数支持逗号分隔的 `platform:user_id` 列表，可将复盘结果同时发给多个用户：

```text
cronjob action=create \
  name="早盘复盘（工作日7:30）" \
  schedule="30 7 * * 1-5" \
  skills=["stock-review-skill"] \
  prompt="执行当日股市复盘流程..." \
  deliver="qqbot:FE4752B5B674A7ACF1352E122671A089,qqbot:9731C372BF998A9B0CF8A42603BE20F3,qqbot:A8AFD91CF51B0D37E378CA38FEEDFC72"
```

对于已存在的 cron job，用 `cronjob action=update` 修改 `deliver` 字段即可添加/移除接收用户。

## 注意事项

- `deliver="origin"` 让结果只回送到触发来源；若需群发，改用逗号分隔的用户列表
- 新配对用户需先给 bot 发一条消息（激活 DM 通道），否则 cron 执行时发给该用户可能失败
- Cron 运行在独立 session 中，无当前对话上下文，prompt 需自包含
- 若上报 API 挂了，cron 仍会生成本地 markdown + JSON，不会静默失败
- **`no_agent=true` 脚本的静默规则**：使用 `no_agent=true` + `script` 的 cron job（如看门狗），脚本的 stdout 会被直接投递给用户。健康状态下必须保持 **空 stdout**，否则每 tick 都会发一条消息骚扰用户。仅在需要用户关注时才输出（详见 system-monitor 技能中的同名陷阱）。
- **模型选择建议**：复盘 cron job 建议使用轻量模型（如 `deepseek-v4-flash`）而非旗舰模型（如 `deepseek-v4-pro`）——复盘是数据采集+格式化任务，不需要最强推理能力，用 flash 模型可显著降低 token 成本且减少 API 排队延迟。通过 `cronjob action=update job_id=<id> model='{"model":"deepseek-v4-flash","provider":"deepseek"}'` 切换。

## Gateway 健康看门狗（推荐配套部署）

复盘 cron job 与 Hermes Gateway 运行在同一进程中。当 Gateway 的 QQ Bot WebSocket 长时间断连时，进程可能进入 degraded 状态，间接导致同进程内的 cron scheduler 无法正常初始化 agent（即使 DeepSeek API 本身正常）。

**推荐**：在复盘 cron 之外单独部署一个 Gateway 健康看门狗：

```
cronjob action=create \
  name="Gateway健康看门狗" \
  schedule="*/5 * * * *" \
  script="hermes-watchdog.py" \
  no_agent=true \
  deliver="origin"
```

看门狗脚本逻辑（参考 `~/.hermes/scripts/hermes-watchdog.py`）：
1. 用 `tac` 快速扫描 gateway log 最近的 WebSocket 事件
2. WebSocket 断连超过 5 分钟 → 自动 `systemctl --user restart hermes-gateway`
3. 重启成功 → 静默（空 stdout，不骚扰用户）
4. 重启失败 → 输出错误信息通知用户

此看门狗不能解决 DeepSeek API 无响应的问题（那是上游依赖），但能确保 Gateway 进程本身不会成为瓶颈。
