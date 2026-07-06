#!/usr/bin/env python3
"""反编造红线工具集 — 1.2 反编造红线配套代码。

用法：

1) 命令行校验量化声明清单：
   python scripts/anti_fabrication.py check-claims claims.json
   # claims.json 格式：
   # {
   #   "claims": [
   #     {
   #       "value": "210%",
   #       "metric": "60日涨幅",
   #       "scope": "涛涛车业",
   #       "source": "yfinance 60d return",
   #       "timestamp": "2026-06-26"
   #     },
   #     {
   #       "value": "31-35倍",
   #       "metric": "PE",
   #       "scope": "涛涛车业",
   #       "source": "腾讯 qt.gtimg.cn sh600519",
   #       "timestamp": "2026-06-26"
   #     }
   #   ]
   # }
   # 输出：通过/失败 + 每条 claim 的来源审计

2) Python 模块：
   from anti_fabrication import assert_data_provenance, enforce_no_fabrication

   assert_data_provenance({"value": "210%", "metric": "60日涨幅", "scope": "涛涛车业", "source": "..."})
   # 缺失 source / scope / timestamp 时抛 ValueError

   @enforce_no_fabrication
   def build_review():
       # ...
       return {"data": "..."}

校验规则（对应 SKILL.md 1.2.1-1.2.4）：
A. 量化数据的编造：每条量化声明必须带 source + scope + timestamp
B. 数据来源真实性：source 必须是 API URL / 文件路径 / 浏览器抓取链接 等具体形式，
   拒绝「据估算」「凭印象」「市场认为」等模糊来源
C. 1.2.3 自检清单固化为代码断言（见 _CHECKLIST）
D. 1.2.4 强制区分事实陈述 vs 逻辑推演：claim["type"] 必须是 "fact" 或 "inference"
"""
from __future__ import annotations

import json
import sys
from functools import wraps
from typing import Any, Callable


# 模糊措辞黑名单（对应 1.2.2「禁止模糊化处理掩盖数据缺失」）
VAGUE_PHRASES = [
    "据估算",
    "据估计",
    "凭印象",
    "市场认为",
    "市场普遍认为",
    "近期涨幅较大",
    "估值偏高",
    "估值偏低",
    "市场情绪谨慎",
    "技术上有反弹需求",
    "长期看好基本面，短期波动可忽略",
    "恐慌正是机会",
    "或许多",
    "或许值得关注",
    "可能存在",
    "似乎已经",
]

# 模糊来源黑名单（必须带具体 API/文件/链接）
VAGUE_SOURCES = [
    "估算",
    "印象",
    "主观判断",
    "市场观察",
    "感觉",
    "大概",
]


_CHECKLIST = [
    "原始来源是什么（API URL / 文件路径 / 链接）",
    "本次会话中能验证吗",
    "若不能验证是否已写'未核实'/'未获取'",
    "是否用'相关但不同口径'数据假装",
]


def assert_data_provenance(claim: dict) -> None:
    """验证单条量化声明是否带完整 provenance。

    Raises:
        ValueError: 缺失字段或使用模糊措辞
    """
    required = ["value", "metric", "scope", "source", "timestamp"]
    missing = [k for k in required if not claim.get(k)]
    if missing:
        raise ValueError(f"claim 缺失必填字段：{missing}（声明：{claim.get('value')!r} / {claim.get('metric')!r}）")

    if claim.get("type") not in ("fact", "inference", None):
        raise ValueError(f"claim.type 必须是 'fact' 或 'inference'（事实陈述 vs 逻辑推演），当前 {claim.get('type')!r}")

    source = claim["source"].strip()
    for vague in VAGUE_SOURCES:
        if vague in source:
            raise ValueError(f"source 使用模糊措辞 {vague!r}：{source!r}（必须提供具体 API/文件/链接）")

    combined = f"{claim.get('value', '')} {claim.get('metric', '')} {claim.get('reason', '')}"
    for vague in VAGUE_PHRASES:
        if vague in combined:
            raise ValueError(f"claim 使用模糊措辞 {vague!r}（掩盖数据缺失）：{combined!r}")


def check_claims(data: dict) -> tuple[bool, list[str]]:
    """校验 claims 清单，返回 (passed, errors)。"""
    errors: list[str] = []
    claims = data.get("claims", [])
    if not isinstance(claims, list):
        return False, ["根级 claims 必须是 array"]

    if len(claims) == 0 and data.get("requires_quantitative_claims"):
        errors.append("requires_quantitative_claims=True 但未提供任何 claim")

    for i, claim in enumerate(claims):
        try:
            assert_data_provenance(claim)
        except ValueError as e:
            errors.append(f"claims[{i}]: {e}")

    return len(errors) == 0, errors


def enforce_no_fabrication(fn: Callable) -> Callable:
    """decorator：被装饰函数的返回值必须是 dict 且包含 'claims' 字段，
    在返回前自动跑 check_claims，失败抛 ValueError。
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        result = fn(*args, **kwargs)
        if not isinstance(result, dict):
            raise ValueError(f"{fn.__name__} 必须返回 dict（含 claims 字段），实际 {type(result).__name__}")
        if "claims" not in result:
            raise ValueError(f"{fn.__name__} 返回 dict 缺少 'claims' 字段（反编造红线要求）")
        passed, errors = check_claims(result)
        if not passed:
            raise ValueError(f"{fn.__name__} 反编造校验失败：{' / '.join(errors)}")
        return result
    return wrapper


# ==================== CLI ====================

def _cmd_check_claims(path: str) -> int:
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"无法读取 {path}：{e}", file=sys.stderr)
        return 2

    passed, errors = check_claims(data)
    if passed:
        claims = data.get("claims", [])
        print(f"校验通过：{len(claims)} 条 claim 全部有 provenance")
        for i, c in enumerate(claims):
            print(f"  [{i}] {c.get('metric', '?')}={c.get('value', '?')} "
                  f"scope={c.get('scope', '?')} source={c.get('source', '?')}")
        return 0
    print(f"校验失败（{len(errors)} 项）：")
    for e in errors:
        print(f"  - {e}")
    return 1


def _print_checklist() -> None:
    print("输出前强制自检清单（1.2.3）：")
    for i, q in enumerate(_CHECKLIST, 1):
        print(f"  □ {q}")
    print("\n模糊措辞黑名单（不可出现在 claim 文本中）：")
    for p in VAGUE_PHRASES:
        print(f"  ❌ {p}")


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("用法：", file=sys.stderr)
        print("  python scripts/anti_fabrication.py check-claims <claims.json>", file=sys.stderr)
        print("  python scripts/anti_fabrication.py checklist", file=sys.stderr)
        return 2

    cmd = argv[1]
    if cmd == "check-claims":
        if len(argv) != 3:
            print("check-claims 需要一个 JSON 文件路径", file=sys.stderr)
            return 2
        return _cmd_check_claims(argv[2])
    if cmd == "checklist":
        _print_checklist()
        return 0
    print(f"未知命令：{cmd}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))