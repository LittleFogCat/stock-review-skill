# 互斥锁文件管理（生命周期 + 误删坑 + 规范速查）

> 📌 本文件是 **cron 互斥锁** 的唯一权威记录。看门狗相关的「陈旧锁」处理见 [watchdog-stale-lock.md](watchdog-stale-lock.md)。

## 🔴 核心 pitfall：成功上报后严禁删除锁文件（2026-08-25 实测踩坑）

当日复盘/早盘主任务完整跑完后（**互斥锁已获取 → 写盘 markdown+JSON → API code=200**），
**不要 `rm -f ~/.hermes/cron/locks/{早盘,复盘}_$(date +%Y-%m-%d).lock`**。

### 为什么不能删

- 互斥锁的语义是「**今日是否已推送**」的持久标记，**不是**「本次运行是否进行中」的临时锁。
- 看门狗/主任务次日（同一天）再次触发时，第一步是 `[ -f "$LOCK_FILE" ]` 检查——
  **锁文件存在 → [SILENT] 退出，不重复推**。
- 删除锁文件 = 把这个「已推送」标记清掉，同一天后续任何 job（看门狗重试、手动补跑、fallback 模型）
  都会再次竞争、再次推送 → **重新打开事故 C（同一天收到多条重复推送）的窗口**。

## ⚠️ 锁文件误删坑：不要把 `rm -f $LOCK_FILE` 与生成命令绑在同一条 terminal 里（2026-09-10 实测补记）

**症状**：为「清理上次占位」而写
`rm -f ~/.hermes/cron/locks/复盘_$(date +%Y-%m-%d).lock; cd /tmp && python3 gen_review.py`
—— rm 和生成脚本放同一终端命令，`;`/`&&` 前段把刚抢到的锁删掉，任务结尾才发现锁「丢了」，需重新 `date +%s > "$LOCK_FILE"` 补抢。

**根因**：锁应该在**任务开头的互斥检查**里抢（`if [ ! -f ]; then date +%s > "$LOCK_FILE"; fi`），之后的流程**绝不该再碰锁文件**。把 rm 塞进生成命令等于主动破坏互斥。

**正确处理**：
- ❌ 不要在任务的任何后续命令里 `rm -f $LOCK_FILE`（即使带 `|| true` 也危险）
- ❌ 不要为了「清理占位」在脚本开头删锁
- ✅ 一个 job 内锁文件只写一次（开头检查时），其余阶段只读不删
- ✅ 若中途误删锁：末尾重新 `date +%s > "$LOCK_FILE"` 补回，再执行 final response 推送（推送完成后锁应保留在盘上，看门狗靠它判断「已推送过」）

## 正确姿势与完整流程速查

1. **抢到锁后全程保留锁文件直到本轮 cron 结束**，不做任何手动清理。
2. 锁文件由系统按日期自动轮转（`早盘_YYYY-MM-DD.lock` / `复盘_YYYY-MM-DD.lock` 各自独立命名），
   次日新日期自然不会命中旧锁，无需 agent 删旧锁。
3. 只做「抢不到锁 → [SILENT] 退出」「抢到锁 → 继续执行」，不碰锁文件的删除。

| 步骤 | 命令 | 约定 |
|------|------|------|
| 抢锁 | `date +%s > "$LOCK_FILE"` | 成功后继续 |
| 检查已推送 | `[ -f "$LOCK_FILE" ]` | 存在 → [SILENT] |
| 锁文件内容 | Unix 时间戳 `date +%s` | 诊断谁先抢到 |
| **释放锁** | **⚠️ 无——成功上报后不删锁** | 锁即「已推送」标记 |

**正例（✅）**：
```bash
LOCK_FILE=~/.hermes/cron/locks/复盘_$(date +%Y-%m-%d).lock
if [ -f "$LOCK_FILE" ]; then echo "LOCKED..."; echo "[SILENT]"; exit 0; fi
date +%s > "$LOCK_FILE"   # 抢锁
echo "LOCK_ACQUIRED"
# ... 完整流程（写盘 + 上报）...
# ✅ 结束：不删锁，直接退出
```

**反例（❌ 2026-08-25 实际发生）**：
```bash
# 成功上报 code=200 后错误地执行了：
rm -f ~/.hermes/cron/locks/复盘_$(date +%Y-%m-%d).lock
echo "lock cleared"
```
→ 这会移除当日「已推送」标记，若同日再有 job 触发会重复推送，违背互斥设计初衷。

## 锁文件规范速览

- 路径：`~/.hermes/cron/locks/{早盘,复盘}_$(date +%Y-%m-%d).lock`
- 抢锁（开头第一步）：`if [ -f "$LOCK_FILE" ]; then echo "LOCKED"; exit 0; fi; date +%s > "$LOCK_FILE"; echo "LOCK_ACQUIRED"`
- 抢到锁 → 继续执行；看到 `LOCKED` → 立即 `[SILENT]` 退出
- 内容：抢锁时的 Unix 时间戳，便于诊断谁先抢到
- 两层互斥：lockfile 防重复推送 + 文件大小阈值（早盘 JSON >3KB / 复盘 JSON >5KB）防「生成了但内容不全」

**事后确认**：`ls -la ~/.hermes/cron/locks/` 应能看到当日锁文件且内容为抢锁时间戳。锁存在 = 该日报已推送过，防止看门狗/retry job 重复推送。

## 背景：SKILL.md 已达 100,000 字符上限（2026-08-25 发现）

`stock-review-skill/SKILL.md` 已触及 100K 单文件上限（100,233 字符），**任何 patch 都会因超限被拒绝**。
后续新增内容必须放进 `references/` 支持文件，SKILL.md 只加一行指针（若指针本身也超限，暂时只更新本文件）。
