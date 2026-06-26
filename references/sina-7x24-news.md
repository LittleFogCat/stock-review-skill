# Sina 7x24 小时快讯数据采集参考

## URL
`https://finance.sina.com.cn/7x24/`

## 适用场景
早盘快报、当日复盘的消息面采集。该页面聚合了 7x24 小时滚动财经快讯，包含宏观政策、国际地缘、产业新闻、公司公告等多类信息，**每个新闻条目直接以富文本 HTML 形式嵌入页面**，无需 JavaScript 渲染即可通过 `curl + grep` 提取。

## 采集方法

### 方法零：7x24 API 接口（推荐，结构化 JSON，2026-06-26 实测）

早盘快报/当日复盘模式下，可通过 Sina 7x24 的 JSON API 接口获取结构化快讯，无需解析 HTML：

```python
import urllib.request, re

url = 'https://feed.mix.sina.com.cn/api/roll/get?pageid=153&lid=2516&k=&num=30&page=1'
req = urllib.request.Request(url, headers={
    'User-Agent': 'Mozilla/5.0',
    'Referer': 'https://finance.sina.com.cn'
})
resp = urllib.request.urlopen(req, timeout=15)
data = resp.read().decode('utf-8', errors='replace')

# 提取新闻标题（API 返回 UTF-8 JSON）
for m in re.finditer(r'"title":"([^"]+)"', data):
    title = m.group(1)
    if len(title) >= 10:
        print(title)
```

**优势**：结构化 JSON，无需解析 HTML；单条新闻标题可直接提取；数据与 7x24 页面同步。
**2026-06-26 实测成功**：提取到「伊朗货船遭袭」「三星投资1000万亿韩元」「日本CPI超预期」「领益智造登陆港交所」等当日早盘消息。

### 方法一：curl + grep（cron 模式安全）
```bash
# 保存页面
curl -s -o /tmp/sina_7x24.html 'https://finance.sina.com.cn/7x24/'

# 提取所有新闻标题（含富文本）
grep -oP '(target="_blank"|>)[^>]*>[^<]{10,}' /tmp/sina_7x24.html | sed 's/.*>//' | sort -u

# 提取特定关键词的新闻
grep -oP '(target="_blank")[^>]*>[^<]{10,}' /tmp/sina_7x24.html | grep -i 'AI\|半导体\|美股\|黄金\|银行' | sed 's/.*>//'
```

### 方法二：write_file + python3（cron 模式安全）
```python
import urllib.request, re

url = 'https://finance.sina.com.cn/7x24/'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
resp = urllib.request.urlopen(req, timeout=15)
data = resp.read().decode('utf-8', errors='replace')

# 提取富文本新闻内容
# 典型格式：<a href="..." target="_blank">新闻标题</a>
titles = re.findall(r'target="_blank"[^>]*>([^<]{15,})', data)
for t in sorted(set(titles)):
    print(t.strip())
```

## 新闻内容特点

- **每条新闻都包含完整标题**，部分含摘要，可直接提取
- **国际新闻丰富**：美股收盘、中东地缘、欧洲央行、日本政策等均有覆盖
- **分类清晰**：宏观政策、产业动态、公司公告等自然分布在页面中
- **发布时间**：页面顶部公告 `published at YYYY-MM-DD HH:MM:SS`，可用于判断数据时效性

## 与操盘必读文章的区别

| 维度 | Sina 7x24 快讯 | Sina 操盘必读 `cpbd` |
|------|---------------|---------------------|
| 更新频率 | 实时滚动 | 每日 08:00 前更新 |
| 覆盖范围 | 全部财经新闻 | 精选晨间要闻 |
| 美股数据 | 散落在各条快讯中 | 直接提供三大指数涨跌幅表格 |
| 采集难度 | curl+grep 即可 | 需解析文章正文 |
| 适用于 | 早盘快报+当日复盘消息面 | 早盘快报首选 |

## 2026-06-24 实测数据

该页面成功提取到以下关键新闻：
- 日本计划14年投资2.3万亿美元押注AI与半导体
- 特朗普称伊朗霍尔木兹收费谈判终止
- 特朗普取消两党住房法案签署仪式
- 国际海事组织公布霍尔木兹海峡撤离计划操作细则
- 中芯国际406亿定增落地
- 宁泉杨东警示AI泡沫
- 华恒生物：实控人因涉嫌非法吸收公众存款罪被刑事拘留
- 乌军打击俄罗斯天然气精炼厂和氦气厂
- 以色列无人机低空飞越贝鲁特上空
- 欧洲央行管委：即便达成停火也不能放松警惕

## 注意事项

- 页面内容为 UTF-8 编码，无需 GBK 解码
- 页面较大（~138KB），单次 curl 可完整下载
- 提取时过滤掉 `%`、`www.`、`=`、`+` 等拼接 JS 模板残留
- 新闻时效性标注在页面注释中（`<!-- [ published at XX:XX:XX ] -->`）
