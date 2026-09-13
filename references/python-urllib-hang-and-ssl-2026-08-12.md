# cron 数据采集：urllib 间歇性 hang 用 curl 回退 + 互斥锁成功推送后必须保留（2026-08-12 实测）

## 背景
2026-08-12 早盘快报 cron 实测。browser_navigate 启动即超时（120s）。
Python `urllib.request` 对 `qt.gtimg.cn` 与 `finance.sina.com.cn` 均间歇性 hang（无响应直到超时），
但 `curl -sS --max-time N` 稳定可用。当日靠 curl 完成全部采集。
（SSL 证书过期上报的 Python ctx 修复见 `api-upload-ssl-cert-pitfall.md`。）

## 1. urllib hang 时的可靠回退：curl --max-time（而非 browser）
- 症状：`urllib.request.urlopen` 对 qt.gtimg.cn / sina 首页 / sina 文章页 hang 到超时（25s+ 无响应）。
  同一进程内先跑 curl 成功、再跑 urllib 仍 hang——不是一次性网络故障，是 urllib 在本环境对某些 host 不可靠。
- 已记录的「browser_navigate + browser_console 双步法」本日不可用（browser daemon 启动超时）。
- **可靠路径**：`curl -sS --max-time 15 "<url>" -H "User-Agent: Mozilla/5.0" -H "Referer: https://finance.sina.com.cn/"`。
  - `--max-time` 必须有，否则 curl 也可能 hang 到默认超时。
  - 美股指数 `http://qt.gtimg.cn/q=usDJI,usIXIC,usINX` 用 curl 一次取全，`iconv -f gbk -t utf-8` 解码。
  - 批量个股行情 `http://qt.gtimg.cn/q=sz002585,sz002859,...` 同样 curl。
  - 从 Python 脚本里调 curl：`subprocess.run(["curl","-sS","--max-time","15",url,"-H",...], capture_output=True, timeout=20)`，
    返回 stdout 再 `decode("utf-8", errors="replace")`。这比在 Python 里裸 urllib 稳。
- 正文提取：Sina 文章正文容器随栏目变，正则依次尝试
  `id="artibody"...</div>\s*</div>`、`id="artibody"...<!--`、`<!-- 正文开始 -->...<!-- 正文结束 -->`；
  取第一个 `len>100` 的文本块。`/marketresearch/`、`/hyyj/`、`/roll/`、`/money/bond/` 等栏目无固定的
  `<!-- 正文开始 -->` 标记，必须靠 artibody 正则兜底。

## 2. 互斥锁成功推送后必须保留（禁止删除）
- 早盘/复盘 cron 第一步抢到 `~/.hermes/cron/locks/{早盘,复盘}_YYYY-MM-DD.lock` 后，**整个任务结束都不要删锁**。
- 锁文件的作用是「本日已推送」标记——看门狗/其他 job 看到锁存在就直接 [SILENT]，避免同日重复推送。
- 若成功推送后删除锁，另一 job 会误判「今日未推送」而再次推送，造成事故 C（重复推送）。
- 2026-08-12 实测踩坑：任务末尾想 `rm -f` 锁文件，被安全策略拦截（mass_file_deletion）——幸好被拦，锁得以保留。
  正确做法：锁文件留到次日，由次日任务的 `date +%s >` 覆盖。