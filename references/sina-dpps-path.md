# Sina 大盘分析路径（/dpps/，手机端）— 收评单路径双文章

**实测日期**：2026-08-19 早盘快报（首发）；2026-09-04 当日复盘（再验证）

## 发现

Sina 财经新增稳定的**手机端大盘分析路径 `/dpps/`**（域名 `finance.sina.cn`，注意是 `.cn` 不是 `.com.cn`），**一个路径同时提供「收评」和「涨停分析」两篇文章**，是当前单路径最高效的昨日盘面数据源之一。

## URL 模式

```
收评：   finance.sina.cn/stock/dpps/YYYY-MM-DD/detail-<id>.d.html
涨停分析：finance.sina.cn/stock/dpps/YYYY-MM-DD/detail-<id>.d.html
```

两者同目录（`/dpps/YYYY-MM-DD/`），仅 `detail-<id>` 不同。从 Sina 股票首页 `finance.sina.com.cn/stock/` 的 `<a>` 链接中筛选 `href` 含 `/stock/dpps/` 即可同时找到：

- 「收评：沪指探底回升涨0.19% 农业板块爆发」 → 填充当日复盘/早盘的指数+板块+领涨领跌
- 「8月18日沪深两市涨停分析：神奇制药4连板」 → 连板高度、市场情绪、涨停结构

## 浏览器提取

用 `browser_navigate` 访问后 `browser_snapshot`（或 `browser_console` 提取 `<article>` 段落）。注意：
- 收评正文在 `<article>` 的多个 `<p>` 中，第一段给指数+涨跌家数，后续分段给领涨/领跌板块+个股+消息面
- 涨停分析正文很短（一段引语+一张涨停图），实际价值在**标题给出连板高度**（如"神奇制药4连板"）+ 页面底部滚动新闻条（常含亚太/外围数据如「韩国综合股价指数KOSPI下跌5%」）
- 手机站（.cn）页面还带大量无关推荐/评论，提取时需过滤

## 与既有路径的优先级

该路径与 `/tob/`、`/jjxw/`、`/bxjj/` 互补，均可作为"昨日A股回顾"章节数据源。实测 `/tob/` 当天未发布收评时（2026-07-23案例），收评可能在 `/jjxw/`；而 2026-08-19 案例中 `/dpps/` 稳定可用。**采集时从 Sina 首页按 `href` 关键词（`/tob/`、`/jjxw/`、`/bxjj/`、`/dpps/`）统一扫描**，取命中文章即可，不硬编码单一路径。

## 提取细节（2026-09-09 当日复盘再验证）

`browser_navigate` 访问 `/dpps/` 页面**常报 `Operation timed out`，但页面实际已加载**（手机站重、广告多）。处理：超时后**不要重试导航**，直接用 `browser_console` 提取：

```js
// 提取 <article> 内的全部正文段落（过滤空/过短行）
(() => {
  const art = document.querySelector('article');
  if (!art) return 'NO_ARTICLE';
  return Array.from(art.querySelectorAll('p'))
    .map(p => p.innerText.trim())
    .filter(t => t.length > 10)
    .join('\n---\n').slice(0, 3500);
})()
```

- **纯 `<article>` 段落**比 `browser_snapshot` 全页干净得多——首页 snapshot 可含 2200+ 行导航/直播/推荐噪音，而该 console 提取只返回正文段（指数→板块→个股→消息面逐段分隔）
- 第一段给指数+涨跌家数，中段给领涨/领跌板块+涨停个股（带代码），末段给消息面（动力煤CCI、研报、海外政策等）——一次提取即覆盖复盘大部分字段需求
- 页面底部还有「相关新闻」滚动条（如「A股指数走势分化 周期板块表现强劲」「AI驱动8月进出口高增」），可补充消息面线索

## 提取代码骨架

```python
# 从 Sina 股票首页收集 dpps 文章
url = "https://finance.sina.com.cn/stock/"
html = <browser_console document.body.innerText 或 snapshot>
# 筛选 href 含 /stock/dpps/ 的链接（mobile 域名 .cn）
for href in re.findall(r'href="(https://finance\.sina\.cn/stock/dpps/[^"]+)"', html):
    if 'detail-' in href:
        print(href)
```