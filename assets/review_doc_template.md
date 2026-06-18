# 股市复盘文档模板

本模板中的占位符、示例字段和 `// etc..` 说明仅用于展示文档结构，不构成任何可直接引用的事实。生成复盘时，所有指数、板块、个股、新闻和结论都必须替换为本次实际收集并已核实的数据；如果没有核实到对应事实，不要为了套模板而补写。

## 格式

```markdown
# 今日盘面
**复盘日期：${date}（周X）**

---

## 今日大盘
${markets.summary}

| 指数 | 收盘价 | 涨跌幅 | 评价 |
| --- | --- | :---: | --- |
| ${markets.indices[0].name} | ${markets.indices[0].close} | ${markets.indices[0].changePercent}% | ${markets.indices[0].reason} |
| ${markets.indices[1].name} | ${markets.indices[1].close} | ${markets.indices[1].changePercent}% | ${markets.indices[1].reason} |
// etc..

${markets.volume}

---

## 今日热点
### 行业板块涨幅 TOP5

1. **${todayHot.topSectors[0].name}：** ${todayHot.topSectors[0].changePercent}% — ${todayHot.topSectors[0].reason}  
龙头：**${todayHot.topSectors[0].stocks[0].name} ${todayHot.topSectors[0].stocks[0].changePercent}%、${todayHot.topSectors[0].stocks[1].name} ${todayHot.topSectors[0].stocks[1].changePercent}% ** // etc..

2. **${todayHot.topSectors[1].name}：** ${todayHot.topSectors[1].changePercent}% — ${todayHot.topSectors[1].reason}  
龙头：**${todayHot.topSectors[1].stocks[0].name} ${todayHot.topSectors[1].stocks[0].changePercent}%**  // etc..

// etc..

### 概念板块涨幅 TOP5
1. **${todayHot.concepts[0].name}：** ${todayHot.concepts[0].changePercent}%
2. **${todayHot.concepts[1].name}：** ${todayHot.concepts[1].changePercent}%
// etc..

### 领跌板块 TOP5
| 板块 | 跌幅 | 逻辑 |
| --- | :---: | --- |
| ${todayHot.fallingSectors[0].name} | ${todayHot.fallingSectors[0].changePercent}% | ${todayHot.fallingSectors[0].reason} |
| ${todayHot.fallingSectors[1].name} | ${todayHot.fallingSectors[1].changePercent}% | ${todayHot.fallingSectors[1].reason} |
// etc..

### 龙头板块梳理
${todayHot.summary}

---

## 消息面
### ${news[0].title}
+ ${news[0].content[0]}
+ ${news[0].content[1]}
+ ${news[0].content[2]}
// etc..

### ${news[1].title}
+ ${news[1].content[0]}
+ ${news[1].content[1]}
+ ${news[1].content[2]}
// etc..

// etc..

---

## 明日关注板块
+ **${focusSectors[0].name}：** ${focusSectors[0].reason}
+ **${focusSectors[1].name}：** ${focusSectors[1].reason}
// etc..

---

## 明日关注个股
**${focusStocks[0].sector}：**

+ ${focusStocks[0].stocks[0].name}（${focusStocks[0].stocks[0].code}）：${focusStocks[0].stocks[0].reason}
+ ${focusStocks[0].stocks[1].name}（${focusStocks[0].stocks[1].code}）：${focusStocks[0].stocks[1].reason}
+ ${focusStocks[0].stocks[2].name}（${focusStocks[0].stocks[2].code}）：${focusStocks[0].stocks[2].reason}
// etc..

**${focusStocks[1].sector}：**

+ ${focusStocks[1].stocks[0].name}（${focusStocks[1].stocks[0].code}）：${focusStocks[1].stocks[0].reason}

// etc..

// etc..
```

其中，标注了 `// etc..` 部分的内容为可变长度数组元素，具体数量根据数组真实数据确定，而非模板中的固定内容。

---

## 早盘快报格式

早盘快报不包含当日盘中数据（尚未开盘），结构比当日复盘精简。昨日盘面数据从昨日复盘 JSON 提取，不重新拉取 API。

```markdown
# YYYY年M月D日早盘快报

## 一、隔夜美股

| 指数 | 收盘点位 | 涨跌幅 | 解读 |
|------|---------|:------:|------|
| 道琼斯 | ${dji_close} | ${dji_change}% | ${dji_reason} |
| 标普500 | ${spx_close} | ${spx_change}% | ${spx_reason} |
| 纳斯达克 | ${ixic_close} | ${ixic_change}% | ${ixic_reason} |

> **影响因素**：${us_market_summary}

## 二、昨日A股回顾
// 数据来源：昨日复盘 JSON（/usr/local/files/docs/stock/YYYY-MM-DD-A股复盘.json）

| 指数 | 收盘价 | 涨跌幅 | 评价 |
| --- | --- | :---: | --- |
| ${markets.indices[0].name} | ${markets.indices[0].close} | ${markets.indices[0].changePercent}% | ${markets.indices[0].reason} |
// etc..

昨日领涨板块：${yesterday_top_sectors_summary}
昨日涨停/跌停家数：${yesterday_limit_summary}

## 三、盘前重大消息

### 📌 宏观政策
- ${macro_news[0]}
- ${macro_news[1]}
// etc..

### 📌 产业/行业
- ${industry_news[0]}
- ${industry_news[1]}
// etc..

### 📌 资金面
- ${fund_news[0]}
// etc..

## 四、今日关注线索

### 市场焦点
1. ${focus_clue[0]}
2. ${focus_clue[1]}
// etc..（≤8条）

### 风险提示
- ⚠️ ${risk[0]}
// etc..

---

## 五、今日关注板块
// 综合昨日复盘板块表现 + 盘前催化方向，≤8个

+ **${focusSectors[0].name}：** ${focusSectors[0].reason}
+ **${focusSectors[1].name}：** ${focusSectors[1].reason}
// etc..

## 六、今日关注个股
// 综合昨日复盘个股走势 + 盘前催化线索，≤10只

**${sector_name}：**

+ ${stock_name}（${stock_code}）：${stock_reason}
+ ${stock_name}（${stock_code}）：${stock_reason}
// etc..

// etc..（可按板块分组）
```