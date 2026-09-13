# API 上报 code=400 字段错误速查（实测补充）

> ⚠️ SKILL.md 已到 100k 上限，新增陷阱记录在此文件。SKILL.md 中的「API 上报 code=400 优先排查」对照表仍是主索引，本文件收纳后续实测新增的错误码。

## 例 8（2026-08-11 当日复盘实测）：龙头个股涨跌幅必须为数字

**错误返回**：`HTTP 200 + {"code":400, "msg":"热点行业第 1 项龙头个股第 1 项涨跌幅必须为数字"}`

**根因**：`todayHot.topSectors[].stocks[]`（及 `todayHot.fallingSectors[].stocks[]`）内每个元素的涨跌幅字段名写错，被 server 判定为「不是数字」。
- 本会话实际踩坑：在 Python 采集脚本里用内部简写字段名 `chg` 存涨跌幅（`{"code":..., "name":..., "chg": 10.04}`），构建 JSON 时**直接复用**了这个 dict，未把 `chg` 重命名为 API 要求的 `changePercent`。
- server 读到 `stocks[0]` 没有 `changePercent` 字段（只有 `chg`），报「涨跌幅必须为数字」——但实际是**字段名不符**，不是数字类型问题。

**修复**：构建 JSON 时对 stocks 内每个元素显式映射字段名：
```python
"stocks": [
    {"code": x["code"], "name": x["name"],
     "changePercent": x["chg"],   # 必须显式重命名为 changePercent，不能复用 chg
     "reason": x["reason"]}
    for x in sector["stocks"]
]
```
同样处理 `fallingSectors[].stocks[]`。

**自检**：上报前用 python 打印 `data["todayHot"]["topSectors"][0]["stocks"][0]`，确认键为 `code/name/changePercent/reason` 而非 `chg`。

**诊断要点**：HTTP 200 + code=400 = payload 字段问题（token 有效），读 `msg` 定位字段，不要误判 token 过期去重置 key。