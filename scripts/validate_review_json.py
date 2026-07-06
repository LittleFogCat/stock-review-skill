#!/usr/bin/env python3
"""复盘 JSON 上报前预校验。

用法：
    python scripts/validate_review_json.py path/to/file.json
    # 通过 stdout 报告错误，exit 0 = 全部通过，exit 1 = 有错误

校验范围（详见 references/review_model.md + references/review_api.md 常见错误码）：
- 顶层必填字段：date / title / type / markets / todayHot
- title 正则（当日复盘 / 早盘快报）
- type ∈ {1, 2}
- markets 必须是对象（含 summary/indices/volume），不允许 null/array
- todayHot 必须是对象（含空数组也合法），不允许 null
- markets.indices[].changePercent 必须是 number
- markets.indices[].reason 不能为空
- news[].content 必须是数组（即使只有一条）
- 早盘快报：focusSectors 必填非空，字段名是 name 不是 sector
- 早盘快报：focusStocks 必填非空，字段名是 sector，stocks 必须是数组
- 当日复盘：focusSectors / focusStocks 必须不存在
"""
import json
import re
import sys
from typing import Any


TITLE_PATTERNS = {
    1: re.compile(r"^\d{4}年\d{1,2}月\d{1,2}日早盘快报$"),
    2: re.compile(r"^\d{4}年\d{1,2}月\d{1,2}日（周[一二三四五六日]）A股复盘$"),
}

errors: list[str] = []


def add_error(path: str, msg: str) -> None:
    errors.append(f"{path}: {msg}")


def is_dict(v: Any) -> bool:
    return isinstance(v, dict)


def is_array(v: Any) -> bool:
    return isinstance(v, list)


def is_number(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def is_nonempty_string(v: Any) -> bool:
    return isinstance(v, str) and len(v.strip()) > 0


def validate_top(data: Any) -> None:
    if not is_dict(data):
        add_error("<root>", "根必须是 JSON 对象")
        return

    if not is_nonempty_string(data.get("date")):
        add_error("date", "必须是 string")

    title = data.get("title")
    if not is_nonempty_string(title):
        add_error("title", "必须是 string")

    report_type = None
    if "type" not in data:
        add_error("type", "缺失（必填，1=早盘快报 / 2=当日复盘）")
    elif not is_number(data["type"]) or data["type"] not in (1, 2):
        add_error("type", f"必须为 1 或 2，实际为 {data['type']!r}")
    else:
        report_type = data["type"]

    if report_type is not None and is_nonempty_string(title):
        if not TITLE_PATTERNS[report_type].match(title):
            add_error(
                "title",
                f"不匹配正则 {TITLE_PATTERNS[report_type].pattern}，当前为 {title!r}",
            )

    validate_markets(data.get("markets"))
    validate_today_hot(data.get("todayHot"))
    validate_news(data.get("news"))

    if report_type == 1:
        validate_focus_sectors(data.get("focusSectors"))
        validate_focus_stocks(data.get("focusStocks"))
    elif report_type == 2:
        if "focusSectors" in data and data["focusSectors"] not in (None, []):
            add_error("focusSectors", "当日复盘不应包含 focusSectors（仅早盘快报使用）")
        if "focusStocks" in data and data["focusStocks"] not in (None, []):
            add_error("focusStocks", "当日复盘不应包含 focusStocks（仅早盘快报使用）")
    # report_type is None → 跳过 type 相关检查，只关注其他字段错误


def validate_markets(markets: Any) -> None:
    if markets is None:
        add_error("markets", "缺失（必填）")
        return
    if not is_dict(markets):
        add_error("markets", f"必须是对象，实际为 {type(markets).__name__}")
        return

    if not isinstance(markets.get("summary"), str):
        add_error("markets.summary", "必须是 string")

    if not isinstance(markets.get("volume"), str):
        add_error("markets.volume", "必须是 string")

    indices = markets.get("indices")
    if not is_array(indices):
        add_error("markets.indices", "必须是 array")
        return
    for i, idx in enumerate(indices):
        path = f"markets.indices[{i}]"
        if not is_dict(idx):
            add_error(path, "必须是对象")
            continue
        if not is_nonempty_string(idx.get("code")):
            add_error(f"{path}.code", "不能为空")
        if not is_nonempty_string(idx.get("name")):
            add_error(f"{path}.name", "不能为空")
        if not is_number(idx.get("close")):
            add_error(f"{path}.close", "必须是 number")
        if not is_number(idx.get("changePercent")):
            add_error(f"{path}.changePercent", f"必须是 number（不可为字符串），实际 {idx.get('changePercent')!r}")
        if not is_nonempty_string(idx.get("reason")):
            add_error(f"{path}.reason", "不能为空")


def validate_today_hot(today_hot: Any) -> None:
    if today_hot is None:
        add_error("todayHot", "缺失（必填；即使无数据也要填含空数组的对象）")
        return
    if not is_dict(today_hot):
        add_error("todayHot", f"必须是对象，实际为 {type(today_hot).__name__}")
        return

    if not isinstance(today_hot.get("summary"), str):
        add_error("todayHot.summary", "必须是 string")

    for field in ("topSectors", "concepts", "fallingSectors"):
        arr = today_hot.get(field)
        if not is_array(arr):
            add_error(f"todayHot.{field}", "必须是 array")
            continue
        for j, item in enumerate(arr):
            validate_sector_item(f"todayHot.{field}[{j}]", item, with_stocks=True)


def validate_sector_item(path: str, item: Any, with_stocks: bool) -> None:
    if not is_dict(item):
        add_error(path, "必须是对象")
        return
    if not is_nonempty_string(item.get("name")):
        add_error(f"{path}.name", "不能为空")
    if not is_number(item.get("changePercent")):
        add_error(f"{path}.changePercent", f"必须是 number，实际 {item.get('changePercent')!r}")
    if not is_nonempty_string(item.get("reason")):
        add_error(f"{path}.reason", "不能为空")

    if with_stocks:
        stocks = item.get("stocks")
        if not is_array(stocks):
            add_error(f"{path}.stocks", "必须是 array")
            return
        for k, st in enumerate(stocks):
            sp = f"{path}.stocks[{k}]"
            if not is_dict(st):
                add_error(sp, "必须是对象")
                continue
            if not is_nonempty_string(st.get("code")):
                add_error(f"{sp}.code", "不能为空")
            if not is_nonempty_string(st.get("name")):
                add_error(f"{sp}.name", "不能为空")
            if "changePercent" in st and not is_number(st["changePercent"]):
                add_error(f"{sp}.changePercent", "必须是 number")


def validate_news(news: Any) -> None:
    if news is None:
        return
    if not is_array(news):
        add_error("news", "必须是 array")
        return
    for i, item in enumerate(news):
        path = f"news[{i}]"
        if not is_dict(item):
            add_error(path, "必须是对象")
            continue
        if not is_nonempty_string(item.get("title")):
            add_error(f"{path}.title", "不能为空")
        content = item.get("content")
        if not is_array(content):
            add_error(f"{path}.content", f"必须是 array（单条也要包成数组），实际为 {type(content).__name__}")


def validate_focus_sectors(sectors: Any) -> None:
    if not is_array(sectors) or len(sectors) == 0:
        add_error("focusSectors", "早盘快报必填且非空")
        return
    for i, item in enumerate(sectors):
        path = f"focusSectors[{i}]"
        if not is_dict(item):
            add_error(path, "必须是对象")
            continue
        if not is_nonempty_string(item.get("name")):
            add_error(f"{path}.name", "字段名应为 name（不是 sector），且不能为空")
        if not is_nonempty_string(item.get("reason")):
            add_error(f"{path}.reason", "不能为空")
        if "sector" in item:
            add_error(f"{path}.sector", "不应使用 sector 字段名（应使用 name）")


def validate_focus_stocks(stocks: Any) -> None:
    if not is_array(stocks) or len(stocks) == 0:
        add_error("focusStocks", "早盘快报必填且非空")
        return
    for i, item in enumerate(stocks):
        path = f"focusStocks[{i}]"
        if not is_dict(item):
            add_error(path, "必须是对象")
            continue
        if not is_nonempty_string(item.get("sector")):
            add_error(f"{path}.sector", "字段名应为 sector（与 focusSectors.name 不同），且不能为空")
        if "name" in item:
            add_error(f"{path}.name", "不应使用 name 字段名（应使用 sector）")
        sub_stocks = item.get("stocks")
        if not is_array(sub_stocks):
            add_error(f"{path}.stocks", "必须是 array（按板块分组的嵌套结构）")
            continue
        for j, st in enumerate(sub_stocks):
            sp = f"{path}.stocks[{j}]"
            if not is_dict(st):
                add_error(sp, "必须是对象")
                continue
            if not is_nonempty_string(st.get("code")):
                add_error(f"{sp}.code", "不能为空")
            if not is_nonempty_string(st.get("name")):
                add_error(f"{sp}.name", "不能为空")
            if not is_nonempty_string(st.get("reason")):
                add_error(f"{sp}.reason", "不能为空")


def main() -> int:
    if len(sys.argv) != 2:
        print("用法：python scripts/validate_review_json.py <file.json>", file=sys.stderr)
        return 2

    path = sys.argv[1]
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"无法解析 JSON：{e}", file=sys.stderr)
        return 2

    validate_top(data)

    if errors:
        print(f"校验失败（{len(errors)} 项）：")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("校验通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())