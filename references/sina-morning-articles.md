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
