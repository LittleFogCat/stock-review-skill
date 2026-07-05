# Sina 财经早报/操盘必读文章参考

早盘快报模式下，Sina 财经的两类早间专栏文章是获取消息面、隔夜美股、今日关注线索的最佳单一数据来源。

---

## 文章类型

### 1. 操盘必读
- **URL 模式**：`https://finance.sina.com.cn/stock/cpbd/YYYY-MM-DD/doc-*.shtml`
- **标题模式**：`操盘必读：影响股市利好或利空消息_YYYY年M月D日`
- **发布时间**：每日 08:00 前更新
- **内容覆盖**：
  - 隔夜美股收盘数据（道指/纳指/标普/费半等精确涨跌幅）
  - 大宗商品（黄金/白银/原油/基本金属）收盘数据
  - 重大政策（央行/证监会/部委）
  - 行业新闻（AI/芯片/新能源/医药等产业动态）
  - 公司公告精选（回购/定增/投资/停复牌/异动澄清）
  - 国际市场（地缘政治/海外市场/中概股）
  - 投资机会参考（板块催化、机构观点）
  - 连板股和限售股解禁信息

### 2. 财经早报
- **URL 模式**：`https://finance.sina.com.cn/stock/y/YYYY-MM-DD/doc-*.shtml`
- **标题模式**：`财经早报：<要闻摘要>丨YYYY年M月D日`
- **发布时间**：每日 07:30-08:00
- **内容覆盖**：
  - 头版头条/焦点新闻
  - 隔夜全球市场综述（美股/欧股/亚太）
  - 政策新闻深度解读
  - 机构观点/分析师研判
  - 公司新闻/行业动态

---

## 采集方法

### 步骤 1：从 Sina 首页提取文章链接

```python
import urllib.request, re

sina_url = 'https://finance.sina.com.cn/stock/'
req = urllib.request.Request(sina_url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req, timeout=15) as resp:
    html = resp.read().decode('utf-8', errors='replace')

# 查找操盘必读链接
pattern = r'<a[^>]*href="(https://finance\.sina\.com\.cn/stock/cpbd/[^"]*)"[^>]*>([^<]*)</a>'
matches = re.findall(pattern, html)
for href, title in matches:
    print(f'TITLE: {title.strip()}')
    print(f'URL: {href}')

# 查找财经早报链接
pattern2 = r'<a[^>]*href="(https://finance\.sina\.com\.cn/stock/y/[^"]*)"[^>]*>([^<]*)</a>'
matches2 = re.findall(pattern2, html)
for href, title in matches2:
    print(f'TITLE: {title.strip()}')
    print(f'URL: {href}')
```

### 步骤 2：拉取文章全文并提取文本

```python
import urllib.request, re, html

def fetch_article(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=15) as resp:
        art_html = resp.read().decode('utf-8', errors='replace')
    # 去除脚本和样式
    art_text = re.sub(r'<script[^>]*>.*?</script>', '', art_html, flags=re.DOTALL)
    art_text = re.sub(r'<style[^>]*>.*?</style>', '', art_text, flags=re.DOTALL)
    art_text = re.sub(r'<[^>]+>', '\n', art_text)
    art_text = html.unescape(art_text)
    lines = [l.strip() for l in art_text.split('\n') if l.strip() and len(l.strip()) > 5]
    return lines
```

### 步骤 3：按关键词筛选结构化内容

```python
# 提取美股数据
keywords_us = ['道指', '纳指', '标普', '费城半导体', '收跌', '收涨', '收盘']
# 提取板块/新闻
keywords_news = ['央行', '证监会', '美联储', '板块', 'AI', '芯片', '利好', '利空',
                 '关注', '政策', '公告', '回购', '定增', '连板']
# 提取公司公告
keywords_ann = ['公告', '回购', '定增', '投资', '涨停', '停牌']
```

---

## 实测案例（2026-06-24 操盘必读）

**URL**: `https://finance.sina.com.cn/stock/cpbd/2026-06-24/doc-inienicy1500098.shtml`

提取的关键内容结构：
```
市场对美股估值过高的担忧再次引发了一轮剧烈波动...
截至收盘，道指跌0.09%，纳指跌2.21%，标普500指数跌1.43%；
纳斯达克100指数跌3.29%。芯片股重挫，费城半导体指数跌7.87%...
美光科技跌超13%，高通、西部数据跌超8%，台积电、英特尔跌超6%...
现货黄金下跌1.91%，报4111.3美元/盎司...
LME期铜下跌2%，报13371美元/吨...
```

**文章来源可靠性验证**：操盘必读文章的美股数据与 Bloomberg/Reuters 等主流数据源一致，远优于腾讯 API 的美股指数（后者可能返回错误的时间戳数据）。2026-06-24 实测中，腾讯 API 显示道指 +1.08%，而操盘必读文章显示 -0.09%（与市场实际情况吻合）。

---

## 已知风险

1. **文章 URL 可能变化**：文档 ID（`doc-inienicy1500098.shtml`）每天不同，需从首页动态提取。
2. **首页链接可能被新闻客户端链接覆盖**：搜索时可能只找到 `https://finance.sina.com.cn/doc/...` 格式的链接，需确认是目标栏目的文章。
3. **SSL 证书问题**：Sina 使用标准 HTTPS，无需特殊处理。
4. **内容中可能包含 VIP 课程推广**：`VIP课程推荐`、`百位牛人在线解读` 等非新闻内容，应在处理后过滤。
5. **⚠️ cpbd/bxjj/y 路径可能返回 403（2026-06-29 验证）** — 三条路径（`/stock/cpbd/`、`/stock/bxjj/`、`/stock/y/`）均可能同时返回 HTTP 403 Forbidden，导致无法获取早盘文章。此时回退到 Sina 财经首页标题提取（`finance.sina.com.cn/stock/`），该页面在本服务器上始终可用，返回 200+ 新闻标题。

### 403 回退：Sina 首页标题提取

当 cpbd/bxjj/y 三条路经同时 403 时，使用首页标题提取替代：

```python
import urllib.request, re

url = "https://finance.sina.com.cn/stock/"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req, timeout=15) as resp:
    html = resp.read().decode("utf-8", errors="replace")

# 提取所有 8 字符以上的标题
titles = re.findall(r'<a[^>]*href="[^"]*"[^>]*>([^<]{8,60})</a>', html)
seen = set()
news_items = [t.strip() for t in titles if t.strip() not in seen and not seen.add(t.strip())]

# 提取地缘/政策/科技/公司等分类内容
for title in news_items:
    if any(k in title for k in ["美伊", "中俄", "央行", "证监会", "半导体", "光模块",
                                "芯片", "AI", "涨价", "预增", "公告", "定增", "IPO"]):
        print(f"  {title}")
```

**2026-06-29 早盘快报实测**：cpbd/bxjj/y 全部 403，首页提取得到 200+ 条标题，涵盖周末全部重大事件（美伊停火、中俄巡航、GPT-5.6 发布、核聚变突破、恒逸石化预增等），足以支撑完整早盘快报的消息面章节。

---

## 优先级建议

早盘快报数据采集优先级链（按实用性排序）：

### 时间窗口判断（关键）

⚠️ **采集前先判断：今日的财经早报是否已发布？**

| 情况 | 首选数据源 | 理由 |
|------|-----------|------|
| 当前时间在 07:30 之后，今日 `y/` 文章已发布 | **今日财经早报 (`/stock/y/`)** | 覆盖昨夜至今晨最新消息（伊朗货船遇袭、苹果涨价、公司公告等），比前一日 cpbd 更新鲜 |
| 当前时间在 07:30 之前，今日 `y/` 未发布 | **前一日操盘必读 (`/stock/cpbd/`)** | 隔夜美股+商品数据最全 |

### 完整优先级链

1. **今日财经早报 (`/stock/y/`，仅 07:30+）** —— 最新鲜，覆盖昨夜突发消息（地缘事件/公司公告/政策发布/海外市场）
2. **前一日操盘必读 (`/stock/cpbd/`)** —— 数据最全，美股/商品/政策/公告一条龙
3. **Sina 7x24 JSON API** —— 补充获取最新快讯（见 `sina-7x24-news.md` 方法零）
4. **首页标题提取 (`finance.sina.com.cn/stock/`)** —— 当上两类文章找不到时
5. **腾讯 API US 指数** —— 仅在上述都不可用时使用，且需交叉验证

### 2026-06-26 实测对比

| 维度 | 前日 cpbd (6/25) | 同日 y/ (6/26) |
|------|-----------------|---------------|
| 美光财报细节 | ✅ 盘后+16%报道 | ✅ 收盘大涨15.74%，全面公司公告 |
| 兆易创新风险提示 | ❌ 未包含 | ✅ 全文公告+详细解读 |
| 苹果涨价 | ❌ 未包含 | ✅ 全线涨价+存储成本原因 |
| 伊朗货船遇袭 | ❌ 未包含 | ✅ 第一时间报道 |
| 十五五能源规划 | ❌ 未包含 | ✅ 全文发布+专家解读 |
| 中船特气复牌公告 | ❌ 未包含 | ✅ 明确今日复牌+核查结果 |
| 恒逸石化业绩预告 | ❌ 未包含 | ✅ 预增23倍+原因分析 |
| OpenAI GPT-5.6限制 | ❌ 未包含 | ✅ 政府干预详情 |

**结论**：同日的财经早报 (`y/`) 在覆盖昨夜突发消息方面**远优于**前一天的操盘必读。当两个文章都可获取时，应**优先使用同日 y/ 文章**获取最新消息，以前日 cpbd 作为隔夜美股数据的交叉验证。2026-06-26 早盘快报中 y/ 文章一条龙覆盖了全部所需的盘前消息面。

---

## /roll/ 路径在 8:00 前稳定可用（2026-06-30 验证）

### 现象

早盘快报（08:00）触发时尝试拉取以下路径均返回 `HTTP Error 403: Forbidden`：
- `https://finance.sina.com.cn/stock/cpbd/`
- `https://finance.sina.com.cn/stock/cpbd/YYYY-MM-DD/`
- `https://finance.sina.com.cn/stock/y/`
- `https://finance.sina.com.cn/stock/y/YYYY-MM-DD/`

### 根因推测

这些路径的列表页在 8:00 前可能尚未刷新（编辑团队 8:00 后才更新当日内容），Sina 服务端对早期请求返回 403。

### 回退路径

**Sina 财经滚动 `/roll/` 路径在 8:00 前稳定可用**——2026-06-30 早盘实测验证的可靠新闻源。

```python
# ✅ 8:00 早盘快报的数据采集入口（当 /cpbd/ 403 时）
url = "https://finance.sina.com.cn/stock/"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://www.baidu.com/"})
with urllib.request.urlopen(req, timeout=15) as resp:
    html = resp.read().decode("utf-8", errors="replace")

# 找出所有 6/30 当日文章链接
links = re.findall(r'href="(https://finance\.sina\.com\.cn/roll/2026-06-30/doc-[^"]+\.shtml)"', html)
print(f"找到 {len(links)} 篇当日滚动文章")
# 通常 30+ 篇，覆盖：宏观政策、产业新闻、公司公告、环球市场等

# 提取单篇正文（用 <!-- 正文开始 --> 标记，与 cpbd 一致）
url = links[0]
req = urllib.request.Request(url, headers={"User-Agent": "...", "Referer": "..."})
with urllib.request.urlopen(req, timeout=10) as resp:
    html = resp.read().decode("utf-8", errors="replace")
body_match = re.search(r'<!-- 正文开始 -->(.*?)<!-- 正文结束 -->', html, re.DOTALL)
if body_match:
    body = re.sub(r'<[^>]+>', '\n', body_match.group(1))
```

### 操作流程

1. 第一次 GET `https://finance.sina.com.cn/stock/` → 列出所有当天文章链接（30+ 篇）
2. 从标题筛选需要的内容（产业政策、公司公告、环球市场）
3. 逐篇 GET 提取正文（`<!-- 正文开始 -->` 标记）
4. 提取 `<meta name="description">` 作为快速摘要（每个文章页面都有）

### 为什么 /roll/ 可用而 /cpbd/ 不可用

- `/roll/` 是新浪财经的滚动新闻聚合页，每天 0:00 起就持续更新
- `/cpbd/` 是每日 8:00 发布的「操盘必读」专题，8:00 前可能为编辑中状态
- 早盘快报（08:00 触发）踩到 `/cpbd/` 不可用窗口的边界

### JS 渲染数据源（2026-06-30 实测）

- 金十数据 `https://www.jin10.com/`：HTTP 200 + 370KB HTML，但实际快讯内容由 JavaScript 渲染，curl 抓取仅返回导航/链接
- 财联社 `https://www.cls.cn/telegraph`：HTTP 200 + 19 链接，同样无内容
- 格隆汇 `https://www.gelonghui.com/`：HTTP 200 但需 JS 渲染
- 华尔街见闻 `https://wallstreetcn.com/`：HTTP 200 但仅 2.7KB（页面基本是空壳）

**结论**：这些 JS 渲染站点的 curl 抓取**仅返回 HTML 框架，不含数据**。早盘快报建议直接绕过它们，走 Sina `/roll/` 替代。

---

## 美股数据交叉验证：腾讯 API vs 新浪文章

### 现象

腾讯行情 API 的美股指数（`usDJI/usIXIC/usINX`）数据与新浪财经操盘必读文章中的美股收盘数据有时存在显著差异：

- 2026-06-24 早盘快报中实测：腾讯 API 显示道琼斯 **+1.08%**，同日新浪操盘必读文章显示道琼斯 **-0.09%**（方向完全不同，差 1.17 pp）

### 根因推测

腾讯 API 的美股数据可能在非交易时段返回的是期货数据或错误的时间戳数据，而非实际收盘值。新浪操盘必读文章（每日 08:00 前更新）的数据来自编辑团队整理，更接近实际收盘值。

### 优先级建议

1. 美股收盘数据**优先采用新浪操盘必读/财经早报文章**（`/stock/cpbd/` 或 `/stock/y/`），其发布时间与早盘快报匹配，数据经过人工核实
2. 腾讯 API 美股数据（`qt.gtimg.cn/q=usDJI,usIXIC,usINX`）仅作为**补充参考**，使用时务必检查索引 30（日期时间戳）是否指向目标交易日收盘后
3. 若两数据源冲突：操盘必读文章 > 腾讯 API > akshare Sina 美股接口
4. 早盘快报中标注数据来源为新浪操盘必读，而非腾讯 API
