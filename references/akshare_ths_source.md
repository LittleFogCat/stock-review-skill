# 金融数据 SDK 参考

本服务器上可用的金融数据 SDK 及其数据源。核心约束：**东财 `push2.eastmoney.com` API 在本服务器上被拦截**，所有依赖它的库/函数均不可用。

## 推荐组合

```
pytdx (通达信协议)     → A股指数 + 个股日K/实时行情
akshare THS (同花顺)  → 行业板块排名
akshare Sina          → 隔夜美股三大指数
腾讯 qt.gtimg.cn      → 个股实时行情（非交易时段用 baostock）
JRJ/Sina 抓取         → 消息面新闻
```

## pytdx — 通达信行情协议

纯 A 股行情数据，走 T2 协议连接通达信公开服务器，免费无需注册。

### 安装

```bash
pip3 install --break-system-packages pytdx
```

### 已验证服务器

| IP | 端口 | 状态 |
|----|------|:--:|
| `60.12.136.250` | 7709 | ✅ 稳定 |
| 120.76.152.2 | 7709 | ❌ 不可用 |
| 121.14.110.210 | 7709 | ❌ 不可用 |

### 指数日K线

```python
from pytdx.hq import TdxHq_API
api = TdxHq_API()
api.connect('60.12.136.250', 7709)

# category=9 (日K), market: 1=上海 0=深圳
# 返回 list[dict], keys: open/close/high/low/vol/amount
data = api.get_index_bars(9, 1, '000001', 0, 3)  # 上证
data = api.get_index_bars(9, 0, '399006', 0, 3)  # 创业板
```

### 个股五档行情

```python
quotes = api.get_security_quotes([(0, '000001'), (1, '600519')])
# 字段: code, price, last_close, open, high, low, bid1-5, ask1-5
# 注意: 该接口不返回股票名称！需从 get_security_list 获取名称映射
```

### 个股日K线

```python
data = api.get_security_bars(9, 0, '000001', 0, 3)
```

### 局限性

- 不返回股票名称（行情接口不含名称字段）
- 服务器不提供板块文件下载（`get_block_info` 返回空）
- 仅 A 股，无美股/港股
- 无新闻数据

## akshare — 多数据源聚合

### 可用函数（非东财数据源）

#### 行业板块排名（同花顺 THS）

```python
import akshare as ak
df = ak.stock_board_industry_summary_ths()
# 列: 板块, 涨跌幅, 总成交额, 净流入, 领涨股, 领涨股-涨跌幅
# 已按涨跌幅降序排列
```

**优势**：一行代码获取排名+涨跌幅+领涨股，走 THS 非东财。比 CLS 侧边栏/腾讯 pt 代码更完整可靠。

#### 美股三大指数（Sina）

```python
df = ak.index_us_stock_sina(symbol='.DJI')   # 道琼斯
df = ak.index_us_stock_sina(symbol='.IXIC')  # 纳斯达克
df = ak.index_us_stock_sina(symbol='.INX')   # 标普500

# 计算涨跌幅
latest, prev = df.iloc[-1], df.iloc[-2]
chg = (latest['close'] - prev['close']) / prev['close'] * 100
```

#### A股指数日线（Sina）

```python
df = ak.stock_zh_index_daily(symbol='sh000001')  # 上证
```

### 不可用函数（东财 EM 后缀）

所有 `_em` 后缀的 akshare 函数底层调用 `push2.eastmoney.com`，本服务器上全部 `RemoteDisconnected`。包括但不限于：
- `stock_zh_index_spot_em()`
- `stock_board_industry_name_em()`
- `stock_board_concept_name_em()`
- `stock_board_concept_spot_em()`

**不要使用任何 `_em` 后缀函数。**

### 安装

```bash
pip3 install --break-system-packages akshare
```

## baostock — 证券宝

免费开源（BSD），无需注册，适合历史日线数据。

### 安装

```bash
pip3 install --break-system-packages baostock
```

### 用法

```python
import baostock as bs
bs.login()
rs = bs.query_history_k_data_plus(
    'sh.000001', 'date,close,pctChg',
    start_date='2026-06-17', end_date='2026-06-18',
    frequency='d', adjustflag='3')
# 遍历: while rs.next(): row = rs.get_row_data()
bs.logout()
```

### 特点

- 仅历史日线，无实时数据
- 指数 + 个股全覆盖
- 速度较快（单次查询 ~0.4s）
- 适合盘后分析，不适合盘中实时

## efinance — 不推荐

efinance 底层完全依赖东财 `push2.eastmoney.com` API，在本服务器上全部不可用。

## tushare — 需注册

tushare 需要注册获取 token，免费版有调用频率限制。旧版 `ts.get_today_all()` 已废弃。

## 各 SDK 对比

| 库 | 数据源 | 免费 | 注册 | 实时 | 本机可用 |
|----|--------|:--:|:--:|:--:|:--:|
| pytdx | 通达信 T2 协议 | ✅ | ❌ | ✅ | ✅ |
| akshare THS | 同花顺 | ✅ | ❌ | ✅ | ✅ |
| akshare EM | 东方财富 | ✅ | ❌ | ✅ | ❌ |
| akshare Sina | 新浪财经 | ✅ | ❌ | ~ | ✅ |
| baostock | 证券宝 | ✅ | ❌ | ❌ | ✅ |
| efinance | 东方财富 | ✅ | ❌ | ✅ | ❌ |
| tushare | 多源 | ~ | ✅ | ~ | ❓ |
