# 股市复盘文档模板

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