# 当日复盘 Markdown 模板（2026-06-29 实战验证版）

此模板基于 2026-06-29 cron 复盘实战生成，所有章节顺序、字段命名、表格列数已通过 `validate_json.py` 验证 + xiaoniu.tech API 上报验证（code 200）。

## 完整结构

```markdown
# YYYY年M月D日（周X）A股复盘

> 复盘日期：YYYY年M月D日（周X）| 复盘时段：9:30-15:00

---

## 🚨 风险提示

[风险等级] + 边角风险点（未触发阈值时也用 R0 标注）

---

## 一、今日大盘

[markets.summary]

| 指数 | 收盘价 | 涨跌幅 | 评价 |
| --- | --- | :---: | --- |
| 上证指数 | 4073.9 | +1.16% | 评价 |
[...9 个主要指数]

[markets.volume]

[结构分化分析]

---

## 二、今日热点

### 行业板块涨幅 TOP5

1. **板块名：+X.XX%** — 原因
   龙头：**个股 +X.XX%**、**个股 +X.XX%**

[5 个行业板块]

### 概念板块涨幅 TOP5

1. **概念名：+X.XX%** — 原因

[5-8 个概念板块]

### 领跌板块 TOP5

| 板块 | 跌幅 | 逻辑 |
| --- | :---: | --- |
| 板块 | -X.XX% | 原因 |

[5 个领跌板块]

### 龙头板块梳理

[整体热点总结 + 涨停/跌停家数 + 涨停股分布描述]

**今日涨停股清单**：
- **个股名（代码）：+X.XX%**

[17 只涨停股]

**今日跌停股清单**：
- **个股名（代码）：-X.XX%**

[2 只跌停股]

---

## 三、消息面

### 宏观政策
+ [消息1]
+ [消息2]
[5 条]

### 产业/行业
+ [消息1]
[7 条，含"反截取式漏报"自检]

### 公司公告
+ [消息1]
[10 条]

### 环球市场
+ [消息1]
[6 条]

### 盘后市场观点
+ [观点1]
[3 条]

---

## 四、明日观察点

> **说明**：当日复盘不包含「明日关注板块」和「明日关注个股」章节——这两章节仅出现在早盘快报中。本节列出明日可观察的关键变量。

1. [观察点 1]
[5 条]

---

*数据来源：[4 个数据源]*
```

## 关键约束（不可修改）

1. **标题严格匹配正则**：`^\d{4}年\d{1,2}月\d{1,2}日（周[一二三四五六日]）A股复盘$`
2. **章节顺序固定**：今日大盘 → 今日热点（行业→概念→领跌→龙头）→ 消息面（宏观→产业→公司→环球→盘后）→ 明日观察点
3. **不包含 `focusSectors`/`focusStocks` 字段**（这两个仅属于早盘快报）
4. **`明日关注板块` 和 `明日关注个股` 章节仅出现在早盘快报中**——当用户要求"明日关注"时，**当日复盘改为 `四、明日观察点` 章节，列出可观察变量而非推荐标的**
5. **消息面"反截取式漏报"自检**：政策原文含并列方向（"AA、BB、CC"）时，每个并列项单独列一条

## 用户偏好处理（2026-06-29 实测）

**场景**：用户 cron prompt 明确要求"明日关注板块 + 明日关注个股（15只以内）"

**正确处理**：
- ❌ 不得为了"满足用户要求"而违反核心约束 1.6.1，在当日复盘中加入 `focusSectors`/`focusStocks` 字段
- ❌ 不得用"用户偏好"覆盖"skill 核心约束"
- ✅ 当日复盘改为"明日观察点"章节（不带具体推荐），并明确说明限制
- ✅ 在 final response 中解释"明日关注板块/个股仅在早盘快报出现"

## Python 构造脚本骨架

```python
import json

date_str = "2026-06-29"
title = "2026年6月29日（周一）A股复盘"  # 严格匹配正则

# 1. 构造数据
indices = [...]  # 9 个指数
top_sectors = [...]  # 5 个行业板块
concepts = [...]  # 5-8 个概念板块
falling_sectors = [...]  # 5 个领跌板块
news = [
    {"title": "宏观政策", "content": [...]},
    {"title": "产业/行业", "content": [...]},
    {"title": "公司公告", "content": [...]},
    {"title": "环球市场", "content": [...]},
    {"title": "盘后市场观点", "content": [...]},
]

# 2. 构造 markets 和 todayHot
markets = {
    "summary": "...",
    "indices": indices,
    "volume": "...",
}
today_hot = {
    "topSectors": top_sectors,
    "concepts": concepts,
    "fallingSectors": falling_sectors,
    "summary": "...",
}

# 3. 构造 report_json（含 type=2）
report_json = {
    "date": date_str,
    "title": title,
    "type": 2,  # ⚠️ 必填
    "markets": markets,
    "todayHot": today_hot,
    "news": news,
    "content": "",  # 后面填充 markdown
}

# 4. 构造 markdown 正文（参考上方结构）
md = f"""# {title}
..."""

# 5. 填充 content 字段
report_json["content"] = md

# 6. 写盘
with open(f"/usr/local/files/docs/stock/{date_str}-A股复盘.md", "w") as f:
    f.write(md)
with open(f"/usr/local/files/docs/stock/{date_str}-A股复盘.json", "w") as f:
    json.dump(report_json, f, ensure_ascii=False, indent=2)
```

## 验证流程（必走）

1. **JSON 类型验证**：用 `validate_json.py` 逐字段检查类型（markets 是对象、todayHot 是对象、changePercent 是 number）
2. **标题正则匹配**：`re.match(r"^\d{4}年\d{1,2}月\d{1,2}日（周[一二三四五六日]）A股复盘$", title)`
3. **不含当日复盘禁止字段**：检查 JSON 中无 `focusSectors`/`focusStocks`
4. **Token 预检**：先用 `{"date": date, "content": "ping"}` 测试 API 鉴权
5. **完整上报**：返回 `code: 200` 才算成功
6. **final response 原样回读**：用 `read_file` 读 .md 文件，原样输出全部正文——禁止只写摘要

## 关联模板

- [早盘快报模板](./morning-brief-template.md)（占位 — 后续补充）
- [复盘 markdown 官方模板](../assets/review_doc_template.md)（skill 内置）
