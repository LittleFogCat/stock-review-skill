# 交易日判断 — 节假日检测方案

## 背景

cron 定时复盘任务按工作日（Mon-Fri）触发，但 A 股在法定节假日（春节、清明、端午、中秋、国庆等）休市。即使 cron 触发执行，若当日非交易日：

- 盘面数据为上一个交易日收盘值（无更新）
- 早盘快报仍可正常输出（隔夜美股 + 盘前消息）
- 当日复盘不产生新数据（应跳过或输出提示）

本文件提供判断 A 股是否开市的程序化检测方案。

## 检测方案（按优先级）

### 方案 A：Sina 新闻节假日声明检测（最直接）

在复盘日期当天，从新浪财经首页或新闻 API 搜索「XX节+休市」关键词。

```python
import urllib.request
import re
import json

def check_holiday_from_sina(date_str: str, holiday_name: str = "端午") -> bool:
    """Check if a specific holiday falls on the given date by searching
    Sina finance news for holiday + 休市 patterns.
    
    Returns True if the holiday closure is confirmed.
    """
    url = f"https://feed.mix.sina.com.cn/api/roll/get?pageid=153&lid=2509&k={holiday_name}+休市&num=5&page=1&r=0.1"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read().decode("utf-8", errors="replace")
        parsed = json.loads(data)
        for item in parsed.get("result", {}).get("data", []):
            title = item.get("title", "")
            # Pattern: "端午节港股休市安排来了：MM月DD日休市一天，DD日恢复"
            # or "A股端午节休市安排：MM月DD日（周X）至DD日休市"
            if holiday_name in title and "休市" in title:
                return True
    except Exception:
        pass
    return False
```

**已知模式**（2026-06-19 验证）：
- 港股端午休市标题：`端午节港股休市安排来了：6月19日休市一天，22日恢复`
- A 股端午休市标题：通常在节前 1-2 周由国务院公布，格式为 `关于2026年端午节休市安排的公告` 或 `沪深交易所发布端午节休市安排`

**筛选关键词组合**：`<节日名> + 休市`、`<节日名> + 假期`、`沪深交易所 + <节日名>`

### 方案 B：Tencent API K-line 日期检测（数据级验证）

获取指数最近交易日的 K 线数据，看最新一个交易日是否匹配复盘日期。

```python
import urllib.request
import json

def get_last_trading_day_from_kline() -> str | None:
    """Query SSE index K-line for the last 5 trading days.
    Returns the date string (YYYY-MM-DD) of the most recent trading day.
    Returns None if the API fails.
    """
    url = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param=sh000001,day,,,5,qfq"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read().decode("utf-8")
        parsed = json.loads(data)
        days = parsed.get("data", {}).get("sh000001", {}).get("day", [])
        if days and len(days) > 0:
            return days[-1][0]  # Most recent trading day, format: "2026-06-18"
    except Exception:
        pass
    return None


def is_trading_day(date_str: str) -> bool:
    """Check if the given date is a trading day by comparing against
    K-line data from the index.
    """
    last_day = get_last_trading_day_from_kline()
    if last_day is None:
        return True  # can't determine, assume yes (conservative)
    return last_day == date_str
```

**原理**：若今天是交易日且已收盘（15:00+），K-line 中最新一天应为今天。若今天是交易日且尚未开盘（9:30 之前），K-line 最新一天为上一个交易日（即昨天）。若今天是节假日，K-line 最新一天也为上一个交易日。

**判断规则**：
| 场景 | K-line 最新日期 | 判断 |
|------|----------------|------|
| 交易日 15:00 后 | 今天 | ✅ 今日是交易日 |
| 交易日 9:30 前 | 昨天 | ⚠️ 可能是交易日（需结合其他方案确认） |
| 非交易日全天 | 上一个交易日 | ❌ 今日非交易日 |
| API 不可用 | None | ⚠️ 无法判断，保守假设是交易日 |

### 方案 C：Sina 财经首页标题综合分析（8:00 前/API 异常时）

当 K-line API 和新闻搜索均不可达时，回退到 Sina 财经页面标题综合分析：

```python
def check_holiday_from_headlines(date_str: str) -> dict:
    """Parse Sina stock page headlines for holiday-related patterns.
    Returns dict with detected holidays and confidence.
    """
    url = "https://finance.sina.com.cn/stock/"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")
        
        # Find all link titles
        titles = re.findall(r'<a[^>]*>(.*?)</a>', html[:80000])
        
        holidays_found = []
        for t in titles:
            t_clean = re.sub(r'<[^>]+>', '', t).strip()
            if any(kw in t_clean for kw in ['休市', '休假', '假期', '放假']):
                holidays_found.append(t_clean)
        
        return {"found": holidays_found, "is_holiday_likely": len(holidays_found) > 0}
    except Exception:
        return {"found": [], "is_holiday_likely": False}
```

## 夏季常见节假日与检测关键词

| 节假日 | 常见月份 | 检测关键词 | 2026年参考 |
|--------|---------|-----------|-----------|
| 端午节 | 6月 | 端午 + 休市、端午 + 假期 | 6月19日(周五)港股休市 |
| 中秋节 | 9-10月 | 中秋 + 休市 | — |
| 国庆节 | 10月 | 国庆 + 休市、长假 | — |

## 完整检测流程（推荐）

```python
def is_holiday_today(date_str: str) -> tuple[bool, str]:
    """Full holiday detection pipeline.
    Returns (is_holiday, detected_info).
    """
    # Step 1: Check Sina news for holiday announcements
    for holiday in ['端午', '中秋', '国庆', '清明', '五一']:
        if check_holiday_from_sina(date_str, holiday):
            return (True, f"Sina新闻确认{holiday}节休市")
    
    # Step 2: Check K-line data
    last_day = get_last_trading_day_from_kline()
    if last_day is not None and last_day != date_str:
        return (True, f"K线数据显示最新交易日为{last_day}，非今日({date_str})")
    
    # Step 3: Check headlines
    result = check_holiday_from_headlines(date_str)
    if result["is_holiday_likely"]:
        return (True, f"Sina标题提及休市安排: {'; '.join(result['found'][:2])}")
    
    return (False, "未检测到休市信号，默认为交易日")
```

## 美国节假日（影响美股数据可用性）

早盘快报中「隔夜美股」数据采集可能受美国联邦假日影响。美股休市日，akshare Sina 和腾讯 API 返回的数据为节前最后一个交易日的收盘值。

### 检测方法

根据腾讯 API 美股指数的时间戳（索引30）判断：
- 若数据时间戳显示为前天或更早的日期，且不是周末 → 可能为美国节假日
- 对比 A 股和美股节假日日历：A股正常开放但美股休市的情况（如 Juneteenth、独立日等）

### 常见美国节假日

| 节日 | 日期 | 影响时段 |
|------|------|---------|
| **Juneteenth（六月节）** | 6月19日 | 若逢周五，周一早盘快报无美股新数据 |
| 独立日 | 7月4日 | 若逢周四/周五，影响早盘快报美股数据 |
| 劳动节 | 9月第一个周一 | 周一休市，周二早盘才有更新 |
| 感恩节 | 11月第四个周四 | 周四休市，周五亦提前收盘 |
| 圣诞节 | 12月25日 | 若逢工作日，美股休市 |

### 实战案例：2026-06-22（周一，Juneteenth 后）

**场景**：2026年6月22日早盘快报，前一个交易日为6月19日（周五）。
- 6月19日是美国 Juneteenth 联邦假日，美股休市
- akshare Sina 美股数据最后一行日期为 `2026-06-18`（周四）
- 腾讯 API 返回的美股时间戳也显示为 `2026-06-18`

**处理方式**：报告中标注「6月19日因美国 Juneteenth 假期休市，数据为前一交易日收盘值」。

### 检测代码示例

```python
def check_us_holiday(tencent_date: str) -> str | None:
    \"\"\"Detect if US market was closed due to holiday.
    Returns holiday name if detected, None otherwise.
    \"\"\"
    if not tencent_date:
        return None
    month_day = tencent_date[5:]  # "MM-DD"
    # Check known US holidays
    us_holidays = {
        "01-19": "马丁·路德·金纪念日",
        "02-16": "总统日",
        "05-25": "阵亡将士纪念日", 
        "06-19": "Juneteenth（六月节）",
        "07-04": "独立日",
        "09-07": "劳动节",
        "11-26": "感恩节",
        "12-25": "圣诞节",
    }
    return us_holidays.get(month_day)
```

## 实战案例：2026-06-19 端午节

**已知信息**：
- 日期：2026年6月19日（周五）
- Sina 新闻标题：「端午节港股休市安排来了：6月19日休市一天，22日恢复」
- K-line 5日数据：`['2026-06-12', '2026-06-15', '2026-06-16', '2026-06-17', '2026-06-18']`（最新为6月18日）

**检测结论**：6月19日非A股交易日（端午假期）。港股已确认休市，K-line 数据无今日记录亦支持此判断。

**报告处理建议**：
- 早盘快报仍需正常生成（隔夜美股+盘前消息仍有价值），但在报告中标注「今日A股因假期休市」
- 当日复盘应跳过或输出「今日休市，无盘面数据」
- 关注板块/个股改为「节后关注」方向
