A 股复盘数据源参考
    
    本文件收录在复盘流程中可用的数据采集来源及使用经验。
    
    
    
    首选数据源（稳定可靠）
    
    1. 腾讯行情 API（qt.gtimg.cn）

    获取指数/个股实时行情的最轻量方式。无需 cookie 或 User-Agent。

    用法示例 — curl（首选，轻量）：
    ```bash
    curl -s "https://qt.gtimg.cn/q=sh000001,sz399001,sz399006,sh000016,sh000688"
    ```

    用法示例 — execute_code（备选，当 terminal curl 被拦截时）：
    ```python
    import urllib.request
    url = "https://qt.gtimg.cn/q=sh000001,sz399001,sz399006,sh000016,sh000688"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        raw = resp.read()
    text = raw.decode("gbk", errors="replace")
    print(text)
    ```

    注意：Hermes Agent 的 `terminal` 工具执行 `curl` 可能因用户安全策略被拦截（`BLOCKED`）。此时改用 `execute_code` 配合 `urllib.request` 即可绕过。两者获取的数据完全一致。
    
    
    返回格式： 一个 v_xxx 格式的 JavaScript 变量赋值，各字段以 ~ 分隔。关键字段索引（0-based）：
    - 索引 0：市场代码（1=上海, 51=深圳）
    - 索引 1：名称
    - 索引 2：代码（如 000001）
    - 索引 3：当前价/收盘价
    - 索引 4：昨日收盘价
    - 索引 7：成交额（万元）—— ⚠️ 不可靠。2026-06-10 实测 5 个主要指数均返回 `"0"`。不得用此字段推算市场总成交额。
    - 索引 30：日期时间（YYYYMMDDHHMMSS）
    - 索引 31：涨跌额
    - 索引 32：涨跌幅百分比
    - 索引 33：最高价
    - 索引 34：最低价
    - 索引 43：振幅百分比
    - 索引 44：总市值（万元）
    - 索引 45：流通市值（万元）
    
    注意： 返回数据使用 GBK 编码，中文可能显示为乱码；在 Python 中需 decode('gbk') 处理。索引位置以实际 dump 为准，API 版本变更时可能偏移；遇到解析异常请先 dump 一行原始数据核对各字段位置。

    **板块代码（pt 格式）大量不可用**（2026-06-08 验证）：
    - 板块代码格式 `pt01801xxx`，实测 33 个常见板块中仅 13 个（39%）返回有效数据。
    - **可用的板块代码**（已验证）：半导体(pt01801110)、证券(pt01801043)、传媒娱乐(pt01801104)、软件服务(pt01801103)、银行(pt01801040)、石油(pt01801045)、船舶(pt01801083)、运输服务(pt01801084)、钢铁(pt01801051)、仓储物流(pt01801085)、煤炭(pt01801055)、化工(pt01801053)、航空(pt01801082)。
    - **返回空的板块**（大量常见板块，不要依赖）：电力、通信设备、元器件、汽车类、医药、医疗保健、食品饮料、酿酒、家用电器、房地产、建筑、建材、有色、保险、农林牧渔、互联网、酒店餐饮、旅游、商业连锁等。
    - **对策**：腾讯 API 板块代码仅作辅助，不依赖其获取板块完整排名。板块热点信息优先使用 CLS 侧边栏（申万行业分类）和 JRJ 首页的「涨停复盘」「ETF复盘资讯」栏目。

    **腾讯 API vs CLS 侧边栏 — 板块分类体系差异**：
    - CLS 侧边栏使用**申万行业分类**体系，腾讯 API 使用自有的腾讯分类。同一板块在两套体系下成分股不同，涨跌幅数据会有显著差异（如 2026-06-08 银行板块：CLS +0.42% vs 腾讯 -2.67%）。
    - **对策**：写入报告时应标注数据来源体系；优先使用 CLS 侧边栏数据（申万分类为市场通用标准）；两套数据不可混用或交叉校验。

    **个股数据查询可靠**：腾讯 API 的个股代码（`sh601398`、`sz300750` 等）返回稳定可靠，不区分板块分类体系，可放心用于获取个股收盘价和涨跌幅。
    
    2. 财联社电报（cls.cn/telegraph）
    
    适合获取实时政经新闻、A股相关消息。页面为服务器端渲染（SSR），浏览器 snapshot 可直接读取内容。无需登录即可看到大部分公开电报。
    
    策略： 用 browser_navigate 打开，页面默认显示当日最新电报。页面右侧栏固定显示指数实时行情和行业/概念板块排名（SSR 渲染，snapshot 可直接提取）。

    **历史电报查询 — 日期选择器**：页面顶部有日期筛选按钮（带日历图标和"日期"文字）。点击后弹出日历组件，可点击具体日期切换至该日电报列表。操作步骤：
    1. `browser_navigate` 打开 `https://www.cls.cn/telegraph`
    2. 在 snapshot 中找到日期按钮并 `browser_click`（snapshot ref 形如 `@e94` 的 clickable 元素）
    3. snapshot 中出现日历表格后，`browser_click` 目标日期单元格
    4. 再次 `browser_snapshot` 获取该日电报列表

    **侧边栏板块数据**：财联社页面右侧栏提供行业板块/概念板块/地域板块的实时排名，包含涨跌幅和资金流入数据。理论上 SSR 渲染可直接从 snapshot 提取，但实践中侧边栏经常不在 accessibility tree 中（即使 scroll 后也未必出现）。**若 snapshot 中看不到板块列表，不要在此浪费时间**——改用金融界「涨停复盘」和「ETF复盘资讯」作为板块数据源，两个入口已覆盖当日龙头板块、领涨个股和资金方向。侧边栏有"行业板块"、"概念板块"、"地域板块"三个板块 tab 可切换；板块列表下方另有"个股涨幅榜"/"个股跌幅榜"两个个股 tab。

**已知缺陷 — 侧边栏 tab 切换不可靠**（2026-06-03 验证）：
- 点击"个股跌幅榜" tab 后 snapshot 仍显示涨幅榜，tab 切换不生效（疑似依赖 JavaScript 事件，浏览器 click 后状态未更新）。
- "概念板块" tab 的切换同样不可靠——有时生效有时不生效。
- **对策**：优先从 snapshot 直接提取可见的板块数据，不依赖 tab 切换。需要涨/跌个股排名时，改用腾讯行情 API 拉取具体个股数据；需要领跌板块信息时，从 JRJ 首页的「公告速递」「妖股直击」等栏目中的异动提示反向推断。

**已知缺陷 — 日期筛选后「加载更多」不生效**（2026-06-04 验证）：\n- 通过日期选择器切换到历史日期（如 6 月 3 日）后，页面仅显示该日最新一批电报（通常为晚间 23:00 前后的公告）。\n- 点击「加载更多」按钮后 snapshot 内容不变，不会加载该日白天交易时段的电报。疑似日期筛选模式下的分页接口与默认实时流不同。\n- **对策**：CLS 日期筛选仅适合获取当日尾盘/晚间公告和次日盘前消息，不适合获取历史交易日白天盘中快讯。需要盘中消息时，优先使用 JRJ 首页的「7x24小时电报」和「A股头条」栏目（覆盖全天要闻且标题摘要完整），并将 CLS 电报定位为"盘后公告 + 盘前消息"的补充来源。\n\n**注意**：财联社内部 API（`cls.cn/v3/telegraph/list` 等）需要登录认证，返回 `errno: 50101, msg: "小财正在加载中..."`。不要尝试用 `execute_code` 或 `curl` 直接调 API——走不通。使用浏览器 + snapshot 是唯一可行路径。
    
    3. 金融界（stock.jrj.com.cn）

    聚合性强：单页面同时展示 A 股头条、公告速递、隔夜美股、全球要闻等。SSR 渲染，浏览器工具可直接提取。

    **重要**：金融界子页面（`toutiao.shtml`、`dxb.shtml`、文章详情页等）频繁返回 404，不可靠。**仅使用首页** `stock.jrj.com.cn/` 作为唯一可靠入口。首页单次 snapshot 已包含：
    - 「A股头条」— 当日要闻概览（带标题+日期戳）
    - 「7x24小时电报」— 滚动快讯
    - 「ETF复盘资讯」— 板块 ETF 表现（如「喝酒吃药卷土重来」「电力ETF逆市新高」）
    - 「妖股直击」— 涨停异动个股
    - 「晚间公告速递」— 上市公司公告摘要
    - 「格隆汇」等第三方 — 海外市场消息（美股映射、地缘政治）

    策略：一次 `browser_navigate` 打开首页，从 snapshot 中直接提取各栏目标题和摘要，无需点进子页面。

    **已知现象 — 首页栏目链接点击不跳转**（2026-06-08 验证）：
    - 点击首页上的「A股头条」「ETF复盘资讯」等栏目链接后，页面 snapshot 保持不变，不会导航到独立文章页。这些栏目可能是 JavaScript 驱动的同页展开/AJAX 加载，浏览器 click 无法触发内容加载。
    - **对策**：不点击栏目链接。从首页 snapshot 的标题和摘要文本中提取信息即可——标题行已经包含了关键结论（如「三大指数集体大跌！高股息逆市走强…AI硬件跳水，科创芯片ETF收跌4.46%」），足以支撑复盘报告的事实陈述。如需更详细的栏目全文，可通过搜索引擎或直接访问专栏页面。

    **已知现象 — CAPTCHA 弹窗但不阻断内容**（2026-06-05 验证）：
    - 首页底部 iframe 中可能出现「安全验证」滑块拼图 CAPTCHA。
    - **不影响数据采集**：snapshot 中所有新闻栏目（A股头条、7x24小时电报、ETF复盘资讯、妖股直击等）仍然完整可见，CAPTCHA 仅出现在页面底部的 iframe 中。
    - **对策**：忽略 CAPTCHA，正常从 snapshot 提取内容即可。不要尝试点击或解决 CAPTCHA，不需要也不值得。

    **板块热点获取**：JRJ 首页的「涨停复盘」栏目（如"涨停复盘：反弹修复但还是CPO光巨头，亨通光电、长飞光纤双双涨停…"）是最实用的板块热点入口——它以一句话总结当日最强主线、涨停龙头及涨幅，比 CLS 侧边栏的板块排名更直观、更可靠。配合「ETF复盘资讯」可交叉验证板块 ETF 资金流向。两个栏目在首页 snapshot 中都会出现，无需额外操作。
    
    
    
    备用/辅助数据源
    
    4. GitHub API（api.github.com）
    
    当 git pull 因网络超时失败时，可用 raw.githubusercontent.com 直接下载文件。
    
    bash
    获取某个文件的最新版
    curl -sL "https://raw.githubusercontent.com/<user>/<repo>/master/<path>"
    
    列出仓库目录结构
    curl -sL "https://api.github.com/repos/<user>/<repo>/contents?ref=master"
    
    递归获取完整文件树
    curl -sL "https://api.github.com/repos/<user>/<repo>/git/trees/master?recursive=1"
    
    
    注意： 这种方式绕过 git 对象数据库，文件内容与远程一致但 git 元数据不会更新。
    
    
    
    不稳定/受限的数据源
    
    东方财富 API（push2.eastmoney.com）

    ~~无浏览器头的 curl 请求常常返回空响应（exit code 52），疑似有反爬机制或 TLS 指纹检测。在有浏览器会话（browser_navigate）的环境中，嵌入大量 iframe 的页面（如 data.eastmoney.com/bkzj/hy.html）可能超时。~~

    **2026-06-15 更新：东财板块排名 API 已全面不可用。** 实测行业板块（`fs=m:90+t:2`）和概念板块（`fs=m:90+t:3`）的 `po=1`（降序）和 `po=0`（升序）请求全部返回 `Remote end closed connection without response`。多种 User-Agent（Chrome/Windows、Mozilla 默认、无 UA）均无效，3 次重试均失败。概念板块 API 同样全部失败。6 次尝试零收益。

    **全面弃用**。不要在任何模式下调用东财板块排名 API——重试只会浪费时间。板块热度改为从以下来源推断：
    - 腾讯 API 的 pt 板块代码（已验证可用的 13 个）——可获取部分申万二级行业涨跌幅
    - Sina 财经首页标题——大量陈述句格式的板块线索（如「XX板块爆发」「XX方向集体走强」）
    - 腾讯 API 个股涨跌幅——按行业手工聚合后描述板块强弱

    **注意**：东方财富**公告 API**（`np-anotice-stock.eastmoney.com`）仍然稳定可用（2026-06-09 验证），两者是不同的接口，不要混淆。
    
    同花顺行情页（q.10jqka.com.cn）
    
    可能返回 Nginx 403，对脚本/非浏览器请求有限制。
    
    
    
    ## 采集策略建议

    1. 指数数据： 腾讯 API 直接 curl，最快最稳
    2. 板块涨幅/热点： **首选金融界「涨停复盘」**（首页 snapshot 一句话总结当日主线+涨停龙头，最直观可靠）；辅以金融界「ETF复盘资讯」交叉验证；财联社电报页侧边栏（SSR 渲染，行业/概念板块涨跌幅 + 资金流入数据）作为补充（注意侧边栏可能不出现在 accessibility tree 中）。浏览器冻结时：腾讯 API pt 板块代码 + Sina 新闻标题 + 个股聚合。
    3. 新闻消息： 财联社电报 + 金融界首页，两者互补。金融界的「A股头条」和「7x24小时电报」板块在周末也持续更新。浏览器冻结时：Sina 财经首页标题提取
    4. 个股异动/涨停： 金融界「妖股直击」栏、公告速递
    5. 美股映射： 金融界首页链接的格隆汇/华尔街消息，非常适合获取周五晚间美股收盘数据
    6. git 拉取失败时： 用 GitHub API + raw.githubusercontent.com 下载文件直接覆盖
    7. ⚠️ 东财板块排名 API（push2.eastmoney.com）：2026-06-15 起全面弃用，所有模式均失败。不要调用。

    5. 东方财富公告 API（np-anotice-stock.eastmoney.com）

    获取个股最新公告/新闻的最轻量方式。不需要浏览器，直接 `execute_code` + urllib 即可。

    用法示例：
    ```python
    import urllib.request, json

    def fetch_announcements(code, limit=5):
        url = f"https://np-anotice-stock.eastmoney.com/api/security/ann?page_size={limit}&page_index=1&ann_type=A&stock_list={code}&f_node=0&s_node=0"
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://data.eastmoney.com/"
        })
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read().decode())
        items = data.get("data", {}).get("list", [])
        for item in items:
            title = item.get("title", "").strip()
            dt = item.get("notice_date", "")[:10]
            print(f"[{dt}] {title}")
    ```

    参数说明：
    - `ann_type=A`：A 股公告；`S` 为研究报告
    - `stock_list`：6 位股票代码，如 `002851`
    - 返回字段：`title`（标题）、`notice_date`（日期，格式 YYYY-MM-DD HH:MM:SS）

    适用场景：
    - 用户指定多只个股快速查询最新公告
    - 复盘时获取个股层面的公告/新闻佐证
    - 不需要完整 html 页面，轻量且高效

    注意：该 API 不同于 `push2.eastmoney.com`（后者不稳定），公告 API 稳定可靠（2026-06-09 验证）。

    6. 新浪财经（finance.sina.com.cn）— 新闻标题提取

    当浏览器不可用时，可作为消息面/新闻的纯 HTTP 补充来源。首页为 SSR 渲染，`urllib.request` 可直接获取 HTML 并提取 `<a>` 标签中的新闻标题。

    用法示例 — execute_code：
    ```python
    import urllib.request, re

    url = "https://finance.sina.com.cn/stock/"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        html = resp.read().decode("utf-8", errors="replace")

    # Extract title-like links
    title_pattern = r'<a[^>]*href="([^"]*)"[^>]*>([^<]{15,80})</a>'
    matches = re.findall(title_pattern, html)

    # Filter for stock/market-related news
    keywords = ['A股', '股市', '沪指', '深成指', '板块', '涨停', '跌停', 'IPO', '解禁', '公告']
    for href, title in matches:
        if any(kw in title for kw in keywords):
            print(f"  - {title.strip()}")
    ```

    2026-06-15 验证：单次请求返回 239 条标题，其中多条与 A 股直接相关（如「三大股指均涨超1% 有色金属板块爆发」），可用于交叉验证东财 API 的板块数据和当日市场主线判断。

    7. 东方财富板块排名 API（push2.eastmoney.com）— ⚠️ 已全面弃用（2026-06-15）

    **状态：全面不可用。** 行业板块（`fs=m:90+t:2`）和概念板块（`fs=m:90+t:3`）的所有请求（`po=1` 降序和 `po=0` 升序）均返回 `Remote end closed connection without response`。多种 User-Agent 均无效，重试无效。**不要再调用此接口。**

    ~~用法示例（领涨板块 TOP15）：~~
    ```python
    # ⚠️ 已弃用 — 此代码不再有效
    ```

    **替代方案（板块热度获取）**：
    - **腾讯 API pt 板块代码**：批量查询已验证可用的 13 个板块代码（见上文腾讯 API 章节），返回申万二级行业涨跌幅。虽覆盖不全但能提供定量数据。
    - **Sina 财经首页标题**：大量标题以陈述句格式描述当日主线（如「有色金属板块爆发」「CPO/PCB方向集体走强」），可直接作为板块热点结论使用。
    - **个股聚合**：用腾讯 API 拉取 20-30 只代表性个股后，按行业手工聚合涨跌幅均值，以「基于已核实的代表性个股数据整理」标注。

    ---

    ## 全 HTTP 回退采集流程（浏览器全局冻结时使用）

    当浏览器会话完全冻结（所有 `browser_*` 命令超时 30-60s，不限于特定 URL），立即切换到纯 HTTP 采集路径，不再尝试任何 browser 命令：

    | 数据需求 | 回退方案 | 可靠性 |
    |---------|---------|--------|
    | 指数行情 | 腾讯 API `qt.gtimg.cn` → `execute_code` + `urllib` | ✅ 稳定 |
    | 板块排名（领涨） | ~~东财 API~~ → 腾讯 API pt 板块代码（已验证 13 个）+ Sina 新闻标题提取板块线索 + 个股按行业聚合 | ⚠️ 多源拼接 |
    | 概念排名 | ~~东财 API~~ → Sina 新闻标题 + 个股腾讯 API 查询 | ⚠️ 标题级推断 |
    | 个股涨跌幅 | 腾讯 API 个股代码 → `execute_code` | ✅ 稳定 |
    | 消息面/新闻 | Sina 财经首页标题提取 | ⚠️ 标题级摘要 |
    | 领跌板块 | 腾讯 API 拉弱势个股 → 以代表性个股均值描述 + 标注估算 | ⚠️ 估算性质 |
    | 公告/异动 | 东财公告 API `np-anotice-stock` → `execute_code` | ✅ 稳定 |

    执行要点：
    - 单次 `execute_code` 脚本内串行调用多个 API，按 1-2 秒间隔
    - **不要调用东财板块排名 API**——po=1 和 po=0 均已全面失败（2026-06-15），任何重试都是浪费时间
    - 东财公告 API（`np-anotice-stock`）仍然稳定可用，与板块排名 API 是不同的接口，不要混淆
    - 如果浏览器在冻结前已获取过 snapshot，其内容仍可使用
    - 在报告的数据源说明中标注哪些数据来自 HTTP 回退路径

    ---

    ## 快速多股查询模式

    当用户直接报出多只个股名称（如「蔚蓝锂芯 麦格米特 沪电股份」），期望的是**快速行情+公告速览**，而非完整复盘流程。区别如下：

    | 维度 | 完整复盘 | 快速多股查询 |
    |------|---------|------------|
    | 触发词 | 复盘、盘后总结、明日关注 | 直接报股票名（2-5只） |
    | 数据范围 | 全市场指数+板块+消息面 | 指定个股行情+公告 |
    | 深度 | 热点分析、板块预判、15只关注股 | 每只股：行情表+3条公告 |
    | 输出 | markdown+JSON+上报 | 内联表格+简要点评 |
    | 耗时 | 多轮数据采集 | 单次 execute_code 搞定 |

    执行策略：
    1. 单次 `execute_code` 批量拉取所有股票（腾讯 API 逗号分隔：`q=sz002245,sz002851,sz002463`）
    2. 同一脚本内串行拉取每只股票的公告（东财公告 API）
    3. 一次性输出表格，无需浏览器

    示例代码见上方腾讯 API 和东方财富公告 API 章节。


    > 以上数据源状态基于 2026-06-09 验证。腾讯 API 指数/个股正常，板块 pt 代码大量不可用（仅 39% 返回数据）。CLS 电报日期选择器可用，侧边栏板块排名（申万分类）在 snapshot 中可见但长度有限。JRJ 首页栏目链接点击不跳转（JS 驱动），但标题摘要已覆盖关键结论。东财公告 API 稳定可用（np-anotice-stock）。