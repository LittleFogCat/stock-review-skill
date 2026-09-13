# 停用/移除一个功能机制（端到端清除流程）

**触发**：主人说「去除所有 X 相关内容」「停用 X」「把 X 拿掉」「不再保留 X」。
本文件是 2026-09-14 移除「模型评分 / 回测」机制时固化下来的流程。

## 核心认知：机制不在一个地方，至少散落在 5 层

只改仓库文件 = 只清了 1/5。剩下的会让 cron 去调用一个已删除的脚本，任务静默失败。
**逐层核对，缺一层就是没清干净**：

| 层 | 位置 | 检查方式 |
|---|---|---|
| 1. 技能仓库文件 | `~/.hermes/skills/stock-review-skill/`（git 仓库） | `grep -rn` 内容关键词 |
| 2. 仓库内被引用的脚本 | `scripts/*.py`、`references/*.md` | 按文件名 + 内容双重搜 |
| 3. **cron job 的 prompt** | `~/.hermes/cron/jobs.json` 各 job 的 `prompt` 字段 | 搜机制关键词，**最容易漏** |
| 4. **专职 cron job** | jobs.json 里整个 job 就是为该机制存在的 | `cronjob action='list'` 看 job 名单 |
| 5. **运行时数据目录** | 仓库外，如 `/root/stock_model/` | 不在 git 里，需单独确认 |

## 执行步骤

### Step 1 — 先拉远程，保持基线干净

```bash
cd ~/.hermes/skills/stock-review-skill
git status -sb && git pull --ff-only origin master
```
远程可能在你上次提交后又进了新提交（本次就遇到 2 个）。在旧基线上改，随后 rebase 会平白多出冲突。

### Step 2 — 全仓库扫描（文件名 + 内容双路）

```bash
# 文件名路：脚本名/机制名/同义词
find . -path ./.git -prune -o -type f \( \
  -iname "*scor*" -o -iname "*backtest*" -o -iname "*model*" \
  -o -iname "*回测*" -o -iname "*评分*" \) -print

# 内容路：机制关键词 + 脚本路径引用（路径引用最容易被忘）
grep -rn -E "评分|回测|scorer|PyTorch|MAE|超额收益|stock_model|/root/stock_model" \
  --include="*.md" --include="*.py" --include="*.yml" --include="*.json" . \
  | grep -v "^./.git"
```

**仓库自带的 `AGENTS.md` / `CLAUDE.md` 也要扫** —— 它们是项目说明双入口，会列 references 清单。

### Step 3 — ⚠️ 同名/近名文件：先读内容再删（本次差点误删）

`grep -i model` 命中了 `references/review_model.md`。**它叫 model 但完全不是 ML 模型** —— 内容是「股市复盘 JSON 的字段表」（`date` / `markets` / `todayHot` …）。

**规则：任何命中文件名搜索的文件，删除前必须 `head -20` 读一遍确认语义。**
「复盘数据模型」和「机器学习模型」在中文里都叫「模型」，按名字删必出事。

### Step 4 — 删内容而非删整份文件（优先）

若机制只是某文件里的**一节**，删那一节，保留文件其余内容。用 `patch` 精确替换，别整份删。

本次 4 处都是节级/句级删除：
- `premarket-run-2026-09-10.md`：删整个 `## scorer.py 评分` 章节
- `us-market-holiday-trap.md`：流程链里去掉 `→ scorer.py 评分（…）→`
- `risk-signal-cases.md`：「全部标注**模型评分均为负值**」→「全部标注**偏谨慎**」
- `stock-code-and-gbk-pitfalls.md`：`（2026-07-24 早盘快报/回测）` → `（2026-07-24 早盘快报）`

改写句子时保留原意、只摘掉机制指涉，不要顺手重写整段 —— 那会引入未授权的内容变更。

### Step 5 — 清 cron job prompt（本次的核心增量）

**这是最容易漏、后果最重的一层**：仓库文件删了，但 job prompt 里还写着「执行 `python3 scorer.py …`」→ 每次跑都调用不存在的脚本。

```python
import json, shutil
p = '/root/.hermes/cron/jobs.json'
shutil.copy(p, p + '.bak.before_<feature>_removal')   # 先备份

d = json.load(open(p))
jobs = d if isinstance(d, list) else d.get('jobs', [])
for j in jobs:
    if (j.get('job_id') or j.get('id')) == '<job_id>':
        pr = j['prompt']
        i = pr.find('## 🤖 模型评分步骤')      # 段落起始锚点
        if i > 0:
            j['prompt'] = pr[:i].rstrip() + '\n'   # 截断式删除整段
json.dump(d, open(p, 'w'), ensure_ascii=False, indent=2)
```

- 段落一般在 prompt 末尾 → 用 `find(锚点)` + 截断最稳。
- 改完**必须复读 jobs.json** 验证关键词已消失（`cronjob action='list'` 只是 preview，不是证据）：
  ```python
  print('评分' in pr, 'scorer' in pr)   # 期望 False False
  ```

### Step 6 — 删专职 job（独立授权，先问）

若某 job 整个就是为该机制而存在（如「模型增量更新」），应 `cronjob action='remove'`。
**但这是删除操作，先 `clarify` 确认**——本次给了三个选项（彻底删 / 先暂停保留 / 只动仓库），主人选了彻底删。
不要因为「指令说清除所有相关」就自行删 job：job 删除不可逆，且可能牵连他人依赖。

### Step 7 — 复查全 cron

```python
kws = ['评分','回测','scorer','stock_model','PyTorch','模型增量']
for j in jobs:
    pr = j.get('prompt','') or ''
    hit = [k for k in kws if k in pr]
    if hit: print((j.get('job_id') or j.get('id')), hit)
print('剩余 job 数:', len(jobs))
```

### Step 8 — 提交推送（走常规 git 流程）

仓库改动用一份 `refactor(<范围>): 移除全部 X 相关内容` 提交，正文列出每个文件的改动点。
提交后 `git push`，并 `git fetch` + `git rev-parse master origin/master` 双向核对 SHA。

### Step 9 — 报告残留（不要静默）

仓库外的运行时目录（本次 `/root/stock_model/`，含模型权重 + score JSON + 脚本）**不在 git 里**，
不会随提交消失。**主动报告它还在，并问是否清理** —— 主人可能想留档，也可能想一并清掉。

## 陷阱清单

- ❌ 只改仓库、忘了 cron prompt → job 调用已删除的脚本，静默失败
- ❌ 按文件名删 `review_model.md` 这类同名文件 → 误删「复盘 JSON 字段表」
- ❌ 把整个文件删掉，而机制只是其中一节 → 顺带丢掉了同文件里的有效内容
- ❌ 直接 `rm` 丢弃的文件 → 违反主人铁律，一律 `mv` 到 `/tmp/discarded_<topic>/`
- ❌ 自行删除专职 cron job → 先 `clarify`，删除不可逆
- ❌ 改完不复查 jobs.json → `list` 的 preview 会骗人
- ❌ 忘了运行时数据目录 → 磁盘上还留着一整套旧机制，且不报错
- ❌ 在旧基线上改 → 先 `pull --ff-only` 对齐远程

## 实测记录（2026-09-14 移除模型评分/回测）

- 仓库 4 处（3 处节/句级 + 1 处整章节）
- cron 2 处：早盘快报 prompt 删段（2091 → 1618 字符）+ 删除「模型增量更新」job（`fa831c23c89b`）
- 提交 `f9d0f19`，推送 `5461d5e..f9d0f19`
- 运行时残留：`/root/stock_model/`（已报告主人，等指示）
