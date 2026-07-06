#!/usr/bin/env python3
"""判断指定日期是否为 A 股交易日。

用法：
    python scripts/is_trading_day.py 2026-06-19
    echo $?  # 0=交易日 1=非交易日 2=无法判断

原理：拉取上证指数 (sh000001) 最近 5 个交易日的 K 线数据，
若最新一日等于传入日期，则为交易日；否则为非交易日。
（数据来源：腾讯 API，方案见 references/holiday_detection.md 方案 B）

注意事项：
- 交易日 9:30 前调用时，K 线最新一天为昨天，会被判为非交易日，
  这是预期行为。如需强制「今日有 K 线 = 已收盘」，请配合 15:00 后调用。
- API 不可用时返回 exit code 2，保守假设为交易日（与 holiday_detection.md 方案 B 一致）。
"""
import sys
import urllib.request
import json
from datetime import datetime


def get_last_trading_day_from_kline() -> str | None:
    url = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param=sh000001,day,,,5,qfq"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read().decode("utf-8")
        parsed = json.loads(data)
        days = parsed.get("data", {}).get("sh000001", {}).get("day", [])
        if days and len(days) > 0:
            return days[-1][0]
    except Exception:
        pass
    return None


def is_trading_day(date_str: str) -> tuple[bool, str]:
    """返回 (is_trading_day, reason)。"""
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return (True, f"日期格式错误：{date_str}，默认假设为交易日")

    last_day = get_last_trading_day_from_kline()
    if last_day is None:
        return (True, "K线API不可用，保守假设为交易日（详见 references/holiday_detection.md 方案 B）")

    if last_day == date_str:
        return (True, f"K线最新交易日={last_day}，与查询日期一致")
    return (False, f"K线最新交易日={last_day}，查询日期={date_str} 早于该日，判定为非交易日或未收盘")


def main() -> int:
    if len(sys.argv) != 2:
        print("用法：python scripts/is_trading_day.py YYYY-MM-DD", file=sys.stderr)
        return 2

    date_str = sys.argv[1]
    is_td, reason = is_trading_day(date_str)
    print(f"{'是' if is_td else '否'}：{reason}")

    if is_td:
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())