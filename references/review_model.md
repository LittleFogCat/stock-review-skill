# 股市复盘JSON模型

股市复盘JSON模型如下：

| 参数名 | 类型 | 说明 |
|--------|------|------|
| date | string | 复盘日期，格式为 YYYY-MM-DD |
| markets | object | 市场总览对象 |
| markets.summary | string | 市场摘要，概括当日整体表现 |
| markets.indices | array | 指数数据数组 |
| markets.indices[].code | string | 指数代码（如 000001） |
| markets.indices[].close | number | 收盘价（如 24.24） |
| markets.indices[].changePercent | number | 涨跌幅百分比（如 0.24 表示 +0.24%） |
| markets.indices[].name | string | 指数名称（如“上证指数”） |
| markets.indices[].reason | string | 涨跌原因说明 |
| markets.volume | string | 量能数据，成交额描述 |
| todayHot | object | 今日热点对象 |
| todayHot.topSectors | array | 热点行业板块数组 |
| todayHot.topSectors[].name | string | 板块名称 |
| todayHot.topSectors[].changePercent | number | 板块涨跌幅百分比 |
| todayHot.topSectors[].reason | string | 板块上涨原因 |
| todayHot.topSectors[].stocks | array | 该板块内龙头个股数组 |
| todayHot.topSectors[].stocks[].code | string | 股票代码 |
| todayHot.topSectors[].stocks[].name | string | 股票名称 |
| todayHot.topSectors[].stocks[].changePercent | number | 个股涨跌幅百分比 |
| todayHot.concepts | array | 热点概念板块数组，结构与 topSectors 相同 |
| todayHot.fallingSectors | array | 领跌板块数组，结构与 topSectors 相同 |
| todayHot.summary | string | 热点总结，概括最强主线、龙头及资金动向 |
| news | array | 消息面新闻数组，按分类组织 |
| news[].title | string | 新闻分类副标题（如“人事与监管”） |
| news[].content | array | 该分类下的新闻条目数组，每个元素为 markdown 格式的字符串 |
| focusSectors | array | 明日关注板块数组 |
| focusSectors[].name | string | 板块名称（可包含子板块，如“电力（火电/水电）”） |
| focusSectors[].reason | string | 关注理由，说明持续性逻辑 |
| focusStocks | array | 明日关注个股数组，按板块分类 |
| focusStocks[].sector | string | 所属板块名称 |
| focusStocks[].stocks | array | 该板块下关注个股数组 |
| focusStocks[].stocks[].code | string | 股票代码 |
| focusStocks[].stocks[].name | string | 股票名称 |
| focusStocks[].stocks[].reason | string | 个股关注理由（如封板表现、放量突破等） |
| title | string | **强制格式**：当日复盘 → `YYYY年M月D日（周X）A股复盘`；早盘快报 → `YYYY年M月D日早盘快报`。不得自由发挥。 |
| content | string | 文章详情内容，以 markdown 格式存储，可为空 |
| type | number | 类型：`1` 早盘快报、`2` 今日复盘。可为空，服务器将根据时间自行判断。 |

JSON 示例见：[JSON 示例](../assets/review_sample.json)

