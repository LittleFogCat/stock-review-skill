#!/usr/bin/env python3
"""早盘快报「隔夜美股」数据源解析（纯日历计算，含美股节假日回退）。

用法：
    python scripts/resolve_overnight_us.py 2026-06-29

JSON 输出：
    {
      "trigger_date": "2026-06-29",
      "us_data_date": "2026-06-26",     # 真实应使用日期（已剔除美股节假日）
      "warning": null,                   # 若剔除美股节假日时填说明
      "reason": "...",
      "label": "..."                     # 已根据真实日期校正
    }

两层日历判断（无需联网）：
1. A 股日历：按 A 股侧的「周几」决定理论偏移（A 股周末会让 -3 天到 -1 天）
2. 美股日历：若理论日期落在美股节假日（如美国独立日），则继续回退到上一个美股交易日
   美股节假日来源：NYSE/NASDAQ 联邦假日表，覆盖 9 大节日 + 浮动日期算法

返回 0 = 成功；日期格式错误返回 2。
"""
import json
import sys
from datetime import date, timedelta


# 美股节假日表（固定日期 + 浮动日期由算法生成）
# 数据源：NYSE/NASDAQ 联邦假日（与 references/holiday_detection.md 末节一致）
def _us_holidays_for_year(year: int) -> set[date]:
    """返回指定年份的美股节假日集合。"""
    holidays: set[date] = set()

    # 固定日期
    holidays.add(date(year, 1, 1))    # 元旦
    holidays.add(date(year, 6, 19))   # Juneteenth 六月节
    holidays.add(date(year, 7, 4))    # 独立日
    holidays.add(date(year, 12, 25))  # 圣诞节

    # 浮动日期：第 N 个周 X
    holidays.add(_nth_weekday(year, 1, 0, 3))   # MLK 日：1月第三个周一
    holidays.add(_nth_weekday(year, 2, 0, 3))   # 总统日：2月第三个周一
    holidays.add(_last_weekday(year, 5, 0))      # 阵亡将士纪念日：5月最后一个周一
    holidays.add(_nth_weekday(year, 9, 0, 1))   # 劳动节：9月第一个周一
    holidays.add(_nth_weekday(year, 11, 3, 4))  # 感恩节：11月第四个周四

    return holidays


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    """返回指定年份月份的第 n 个周 weekday（0=Mon, 6=Sun）。"""
    first = date(year, month, 1)
    days_ahead = (weekday - first.weekday()) % 7
    first_target = first + timedelta(days=days_ahead)
    return first_target + timedelta(days=7 * (n - 1))


def _last_weekday(year: int, month: int, weekday: int) -> date:
    """返回指定年份月份的最后一个周 weekday。"""
    if month == 12:
        next_month_first = date(year + 1, 1, 1)
    else:
        next_month_first = date(year, month + 1, 1)
    last_day = next_month_first - timedelta(days=1)
    days_back = (last_day.weekday() - weekday) % 7
    return last_day - timedelta(days=days_back)


def _previous_us_trading_day(d: date) -> date:
    """返回 d 的上一个美股交易日（跳过周末 + 美股节假日）。"""
    candidate = d - timedelta(days=1)
    # 限定最多回退 10 天（理论上不会遇到长假期，但保险起见）
    for _ in range(10):
        if candidate.weekday() >= 5:
            candidate -= timedelta(days=1)
            continue
        if candidate in _us_holidays_for_year(candidate.year):
            candidate -= timedelta(days=1)
            continue
        return candidate
    return candidate


def _us_holiday_name(d: date) -> str | None:
    """若 d 是美股节假日，返回名称；否则返回 None。"""
    if d not in _us_holidays_for_year(d.year):
        return None
    md = d.strftime("%m-%d")
    fixed = {
        "01-01": "元旦",
        "06-19": "Juneteenth（六月节）",
        "07-04": "独立日",
        "12-25": "圣诞节",
    }
    if md in fixed:
        return fixed[md]
    if d.month == 1 and d.weekday() == 0:
        return "MLK 日（马丁·路德·金纪念日）"
    if d.month == 2 and d.weekday() == 0:
        return "总统日"
    if d.month == 5 and d.weekday() == 0:
        return "阵亡将士纪念日"
    if d.month == 9 and d.weekday() == 0:
        return "劳动节"
    if d.month == 11 and d.weekday() == 3:
        return "感恩节"
    return "美国联邦节假日"


def resolve(trigger_date_str: str) -> dict:
    trigger_date = date.fromisoformat(trigger_date_str)
    weekday = trigger_date.weekday()

    # 第一层：A 股日历维度（按周几决定偏移）
    if weekday == 0:
        candidate = trigger_date - timedelta(days=3)
        a_side_reason = "周一早盘 → 跨周末，美股周六周日休市，「隔夜」取上周五收盘"
    elif 1 <= weekday <= 4:
        candidate = trigger_date - timedelta(days=1)
        a_side_reason = "工作日早盘 → 「隔夜」取前一个交易日美股收盘"
    elif weekday == 5:
        candidate = trigger_date - timedelta(days=1)
        a_side_reason = "周六非早盘触发日；如需查询，美股周五仍为最新交易日"
    else:
        candidate = trigger_date - timedelta(days=2)
        a_side_reason = "周日非早盘触发日；如需查询，美股上周五仍为最新交易日"

    # 第二层：美股日历维度（剔除美股节假日）
    holiday_name = _us_holiday_name(candidate)
    warning = None
    if holiday_name:
        actual_us = _previous_us_trading_day(candidate)
        warning = (
            f"美股原定为 {candidate.isoformat()}（{holiday_name}）休市，"
            f"已自动回退到上一美股交易日 {actual_us.isoformat()}。"
            f"请在报告开头标注：因美国 {holiday_name}，隔夜美股数据为 {actual_us} 收盘。"
        )
        us_date = actual_us
    else:
        us_date = candidate

    # 生成 label（按是否跨周末分两种措辞）
    if weekday == 0 or weekday >= 5:
        label = f"上一交易日收盘（{us_date.isoformat()}{f'，因美国{holiday_name}' if holiday_name else ''}）"
    else:
        label = f"前一日美股收盘（{us_date.isoformat()}{f'，因美国{holiday_name}' if holiday_name else ''}）"

    return {
        "trigger_date": trigger_date.isoformat(),
        "weekday": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][weekday],
        "us_data_date": us_date.isoformat(),
        "warning": warning,
        "reason": a_side_reason,
        "label": label,
    }


def main() -> int:
    if len(sys.argv) != 2:
        print("用法：python scripts/resolve_overnight_us.py YYYY-MM-DD", file=sys.stderr)
        return 2

    trigger = sys.argv[1]
    try:
        result = resolve(trigger)
    except ValueError as e:
        print(f"日期格式错误：{e}", file=sys.stderr)
        return 2

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())