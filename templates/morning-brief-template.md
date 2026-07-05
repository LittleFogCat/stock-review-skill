# 早盘快报 Markdown 模板（2026-06-29 实战验证版）

此模板基于 2026-06-29 cron 早盘快报实战生成，所有章节顺序、字段命名、表格列数已通过 `validate_json.py` 验证 + xiaoniu.tech API 上报验证（code 200）。

## 与当日复盘的关键区别

| 维度 | 当日复盘 | 早盘快报 |
|------|---------|---------|
| 复盘时段 | 当日 9:30-15:00 | 前一交易日收盘 ~ 当日 8:00 |
| 触发时间 | 15:15 | 8:00 |
| JSON `type` | `2` | `1` |
| 关注板块字段 | ❌ 不包含 | ✅ `focusSectors`（必填非空） |
| 关注个股字段 | ❌ 不包含 | ✅ `focusStocks`（必填非空） |
| `todayHot` | 完整填入 | 空数组 + summary 字符串 |
| 美股数据 | 不需要 | ✅ 隔夜美股表格（必填） |
| 收盘价数据 | ✅ 当日收盘 | ⚠️ 仅"昨日 A 股回顾" |

## 完整结构

```markdown
# YYYY年M月D日早盘快报

> 早盘日期：YYYY年M月D日（周X）| 消息截止：当日 08:00

---

## 🚨 风险提示

[风险等级 R0/R1/R2/R3 + 触发条目，未触发阈值时也用 R0 标注]

---

## 一、隔夜美股

| 指数 | 收盘 | 涨跌幅 | 评价 |
| --- | --- | :---: | --- |
| 道琼斯 | 51999.67 | +0.64% | 评价 |
| 纳斯达克 | 26376.34 | -1.15% | 评价 |
| 标普 500 | 7511.35 | -0.57% | 评价 |

[markets.summary 隔夜美股一句话总结]

[结构特征描述：科技 vs 价值、涨跌幅排行、关键个股异动]

> **跨周末标注**：周一早盘的「隔夜美股」= 上周五收盘（美股周六周日休市），不是周日晚上→周一凌晨的数据。报告需明确标注「上周五收盘（因周末美股休市）」。

---

## 二、昨日 A 股回顾

[昨日复盘文件提取的指数、板块涨跌、涨停/跌停家数、龙头个股走势]

| 指数 | 收盘 | 涨跌幅 | 评价 |
| --- | --- | :---: | --- |
| 上证指数 | XXXX | ±X.XX% | 评价 |
[...9 个主要指数]

**昨日热点板块**（延续强势 / 回调 / 轮动）：
- 板块名：±X.XX% — 走势特征

[3-5 个关键板块]

**昨日涨停股清单**：
- 个股名（代码）：+X.XX%

[5-10 只代表性涨停股]

---

## 三、盘前重大消息

### 宏观与政策
+ [消息 1]（来源：XXX）
+ [消息 2]（来源：XXX）
[3-5 条]

### 产业与行业
+ [消息 1]（来源：XXX）
[3-5 条，含「反截取式漏报」自检]

### 公司公告
+ [消息 1]（来源：XXX）
[2-3 条]

### 环球市场
+ [消息 1]（来源：XXX）
[2-3 条]

---

## 四、今日关注线索

[解禁 / 财报 / 政策事件 / 海外映射 / 事件驱动]

- [线索 1]
- [线索 2]
- [线索 3]
[3-5 条]

---

## 五、今日关注板块（≤8 个）

| 板块 | 关注理由 | 催化方向 |
| --- | --- | --- |
| 板块名 | 短线关注理由 | 政策 / 财报 / 海外映射 / 事件 |
[8 个以内]

---

## 六、今日关注个股（≤10 只）

按板块分组（**非扁平数组**）：

- **板块 A**
  - 个股名（代码）：关注理由
  - 个股名（代码）：关注理由
- **板块 B**
  - 个股名（代码）：关注理由
  - 个股名（代码）：关注理由

[10 只以内，代码 + 名称 + 短线关注理由]

---

*数据来源：[4-5 个数据源]*
```

## 关键约束（不可修改）

1. **标题严格匹配正则**：`^\d{4}年\d{1,2}月\d{1,2}日早盘快报$`
2. **`type` 字段必填且为 `1`**：API 拒收缺失或错误值
3. **`focusSectors` 字段名是 `name`**（不是 `sector`！）—— 易错点
4. **`focusStocks` 字段名是 `sector`**（与 `focusSectors.name` 不同）—— 易错点
5. **`focusStocks` 必须是按板块分组的嵌套数组**，不是扁平数组
6. **`todayHot` 即使无盘中数据也要填含空数组的对象**：
   ```python
   {"topSectors": [], "concepts": [], "fallingSectors": [], "summary": "早盘快报模式，不包含当日盘中数据。"}
   ```
7. **`news[].content` 必须是数组**（即使只有一条）：`"content": [markdown_str]`
8. **「今日关注板块」和「今日关注个股」必须基于双依据**：(a) 昨日盘面表现 + (b) 隔夜/盘前消息面，**不得仅凭单方面信息做判断**
9. **早盘快报不包含当日盘中数据**（尚未开盘）

## Python 构造脚本骨架

```python
import json

date_str = "2026-06-30"
title = "2026年6月30日早盘快报"  # 严格匹配正则

# 1. 隔夜美股数据
us_indices = [
    {"code": "DJI", "name": "道琼斯", "close": 51999.67, "changePercent": 0.64, "reason": "..."},
    {"code": "IXIC", "name": "纳斯达克", "close": 26376.34, "changePercent": -1.15, "reason": "..."},
    {"code": "SPX", "name": "标普500", "close": 7511.35, "changePercent": -0.57, "reason": "..."},
]

# 2. 昨日 A 股回顾（从昨日复盘 JSON 读取）
yesterday_summary = "..."
yesterday_top_sectors = [...]  # 仅作 markdown 正文填充，JSON 字段不重复

# 3. 消息面
news = [
    {"title": "宏观与政策", "content": ["..."], "source": "新浪财经操盘必读"},
    {"title": "产业与行业", "content": ["..."], "source": "新浪财经"},
    {"title": "公司公告", "content": ["..."], "source": "东方财富"},
    {"title": "环球市场", "content": ["..."], "source": "新浪 7x24"},
]

# 4. 今日关注板块（重点字段）
focus_sectors = [
    {
        "name": "板块名",  # ⚠️ 字段名是 name，不是 sector
        "reason": "短线关注理由",
        "stocks": [
            {"code": "000001", "name": "个股名", "reason": "..."},
        ],
    },
    # ...最多 8 个
]

# 5. 今日关注个股（按板块分组的嵌套数组）
focus_stocks = [
    {
        "sector": "板块名",  # ⚠️ 字段名是 sector，与 focusSectors.name 不同
        "stocks": [
            {"code": "000001", "name": "个股名", "reason": "..."},
        ],
    },
    # ...最多 10 只，按板块分组
]

# 6. 构造 markets 和 todayHot
markets = {
    "summary": "隔夜美股三大指数分化：道指+0.64%...",
    "indices": us_indices,
    "volume": "未获取（隔夜美股）",
}
today_hot = {
    "topSectors": [],  # 早盘快报无盘中数据
    "concepts": [],
    "fallingSectors": [],
    "summary": "早盘快报模式，不包含当日盘中数据。",
}

# 7. 构造 report_json（含 type=1）
report_json = {
    "date": date_str,
    "title": title,
    "type": 1,  # ⚠️ 必填且为 1（早盘快报）
    "markets": markets,
    "todayHot": today_hot,
    "news": news,
    "focusSectors": focus_sectors,
    "focusStocks": focus_stocks,
    "content": "",  # 后面填充 markdown
}

# 8. 构造 markdown 正文（参考上方结构）
md = f"""# {title}
..."""

# 9. 填充 content 字段
report_json["content"] = md

# 10. 写盘
with open(f"/usr/local/files/docs/stock/{date_str}-早盘快报.md", "w") as f:
    f.write(md)
with open(f"/usr/local/files/docs/stock/{date_str}-早盘快报.json", "w") as f:
    json.dump(report_json, f, ensure_ascii=False, indent=2)
```

## 验证流程（必走）

1. **JSON 类型验证**：用 `validate_json.py` 逐字段检查类型
   - `markets` 是对象（summary/indices/volume）
   - `todayHot` 是对象（含空数组也合法）
   - 所有 `changePercent` 是 number
   - `news[].content` 是 array
   - `focusSectors[].name` 字段名正确（不是 sector！）
   - `focusStocks[].sector` 字段名正确
   - `focusStocks[].stocks` 是数组
2. **标题正则匹配**：`re.match(r"^\d{4}年\d{1,2}月\d{1,2}日早盘快报$", title)`
3. **必填字段非空**：`focusSectors` 和 `focusStocks` 都必须存在且非空
4. **Token 预检**：先用 `{"date": date, "content": "ping"}` 测试 API 鉴权
5. **完整上报**：返回 `code: 200` 才算成功
6. **final response 原样回读**：用 `read_file` 读 .md 文件，原样输出全部正文——禁止只写摘要

## 常见错误码（API 拒收原因）

| 错误码 msg | 根因 | 修复 |
|-----------|------|------|
| `今日热点格式错误` | `todayHot` 设为 `null` | 改为含空数组的对象 |
| `关注板块第 N 项板块名称不能为空` | `focusSectors` 用 `sector` 字段名 | 改为 `name` |
| `明日关注个股第 N 项所属板块不能为空` | `focusStocks` 是扁平数组 | 改为按板块分组的嵌套数组 |
| `市场总览格式错误` | `markets` 设为数组 | 改为对象（含 summary/indices/volume） |
| `消息面第 N 项内容必须为数组` | `news[].content` 是字符串 | 改为单元素数组 `["..."]` |
| `市场指数第 N 项评价不能为空` | `markets.indices[].reason` 缺失 | 补填 reason |
| `type 字段必须为 0、1 或 2` | `type` 字段缺失 | 添加 `"type": 1` |

## 关联模板

- [当日复盘模板](./daily-review-template.md)（2026-06-29 实战验证版）
- [复盘 markdown 官方模板](../assets/review_doc_template.md)（skill 内置）