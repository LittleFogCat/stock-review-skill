A 股复盘数据源参考
    
    本文件收录在复盘流程中可用的数据采集来源及使用经验。
    
    
    
    首选数据源（稳定可靠）
    
    1. 腾讯行情 API（qt.gtimg.cn）
    
    获取指数/个股实时行情的最轻量方式，curl 即可，无需 cookie 或 User-Agent。
    
    用法示例：
    
    bash
    获取主要指数（上证、深证、创业板、上证50、科创50）
    curl -s "https://qt.gtimg.cn/q=sh000001,sz399001,sz399006,sh000016,sh000688"
    
    
    返回格式： 一个 v_xxx 格式的 JavaScript 变量赋值，各字段以 ~ 分隔。关键字段索引（0-based）：
    - 索引 1：名称
    - 索引 3：收盘价
    - 索引 5：今日开盘价
    - 索引 32：日期时间（YYYYMMDDHHMMSS）
    - 索引 33：涨跌额
    - 索引 34：涨跌幅百分比
    - 索引 43：最高价
    - 索引 44：最低价
    
    注意： 返回数据使用 GBK 编码，中文可能显示为乱码；在 Python 中需 decode('gbk') 处理。
    
    2. 财联社电报（cls.cn/telegraph）
    
    适合获取实时政经新闻、A股相关消息。页面为服务器端渲染（SSR），浏览器 snapshot 可直接读取内容。无需登录即可看到大部分公开电报。
    
    策略： 用 browser_navigate 打开，滚动以加载更多历史消息。对于指定日期的历史新闻，可尝试搜索 cls.cn/searchPage。
    
    3. 金融界（stock.jrj.com.cn）
    
    聚合性强：单页面同时展示 A 股头条、公告速递、隔夜美股、全球要闻等。SSR 渲染，浏览器工具可直接提取。
    
    亮点：
    - 页面上方 7x24 小时电报区包含大量 5/29 收盘后及 5/30 早间新闻
    - 左侧"A股头条""ETF复盘资讯"等文章摘要可直接点开查看
    
    
    
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
    
    无浏览器头的 curl 请求常常返回空响应（exit code 52），疑似有反爬机制或 TLS 指纹检测。在有浏览器会话（browser_navigate）的环境中，嵌入大量 iframe 的页面（如 data.eastmoney.com/bkzj/hy.html）可能超时。
    
    不建议作为主力数据源。 腾讯行情 API 是更可靠的替代。
    
    同花顺行情页（q.10jqka.com.cn）
    
    可能返回 Nginx 403，对脚本/非浏览器请求有限制。
    
    
    
    ## 采集策略建议

    1. 指数数据： 腾讯 API 直接 curl，最快最稳
    2. 板块涨幅/热点： 结合财联社电报中的 ETF 复盘资讯、金融界 A 股头条推断；或使用同花顺/东财浏览器版（如能成功加载）
    3. 新闻消息： 财联社电报 + 金融界首页，两者互补。金融界的「A股头条」和「7x24小时电报」板块在周末也持续更新
    4. 个股异动/涨停： 金融界「妖股直击」栏、公告速递
    5. 美股映射： 金融界首页链接的格隆汇/华尔街消息，非常适合获取周五晚间美股收盘数据
    6. git 拉取失败时： 用 GitHub API + raw.githubusercontent.com 下载文件直接覆盖

    > 以上数据源状态基于 2026-05-31 验证。复盘上报 API (xiaoniu.tech/api/stock/reviews) 已验证可用，HTTP 200 + code 200 正常。