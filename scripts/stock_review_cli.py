from __future__ import annotations

import argparse
import getpass
import json
import os
import platform
import sys
from pathlib import Path
from typing import Any
from urllib import error, request


API_URL = "https://xiaoniu.tech/api/stock/reviews"
ENV_KEY = "STOCK_REVIEW_API_KEY"
REQUIRED_TOP_LEVEL_KEYS = [
    "date",
    "markets",
    "todayHot",
    "news",
    "focusSectors",
    "focusStocks",
    "title",
    "content",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Persist STOCK_REVIEW_API_KEY and report stock review payloads."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    set_key_parser = subparsers.add_parser(
        "set-api-key",
        help="Prompt for the API key and persist it as STOCK_REVIEW_API_KEY.",
    )
    set_key_parser.add_argument(
        "--api-key",
        help="Optional API key value. Prefer omitting this so the script prompts securely.",
    )
    set_key_parser.set_defaults(handler=handle_set_api_key)

    report_parser = subparsers.add_parser(
        "report",
        help="Send a review JSON payload to the stock review API.",
    )
    report_parser.add_argument(
        "--json-file",
        required=True,
        help="Path to the JSON payload file that matches the review model.",
    )
    report_parser.add_argument(
        "--api-url",
        default=API_URL,
        help="Override the default report API endpoint.",
    )
    report_parser.set_defaults(handler=handle_report)

    return parser


def handle_set_api_key(args: argparse.Namespace) -> int:
    api_key = read_api_key_input(args.api_key)
    persist_api_key(api_key)
    print(f"API key has been persisted as {ENV_KEY}.")
    print("Open a new terminal session if your current shell does not pick up user-level environment changes automatically.")
    return 0


def handle_report(args: argparse.Namespace) -> int:
    payload_path = Path(args.json_file).expanduser().resolve()
    payload = load_payload(payload_path)
    validate_payload(payload)
    api_key = load_api_key_from_env()
    response_status, response_body = submit_review(
        api_url=args.api_url,
        api_key=api_key,
        payload=payload,
    )
    response_code = validate_report_response(response_status, response_body)
    print(f"Report succeeded with HTTP {response_status} and API code {response_code}.")
    if response_body:
        print(response_body)
    return 0


def read_api_key_input(cli_value: str | None) -> str:
    if cli_value:
        api_key = cli_value.strip()
    else:
        if not sys.stdin.isatty():
            raise ValueError("No API key was provided. Re-run with --api-key or in an interactive terminal.")
        api_key = getpass.getpass("Enter stock review API key: ").strip()

    if not api_key:
        raise ValueError("API key cannot be empty.")
    return api_key


def persist_api_key(api_key: str) -> None:
    os.environ[ENV_KEY] = api_key

    system = platform.system().lower()
    if system == "windows":
        persist_api_key_windows(api_key)
        return

    persist_api_key_posix(api_key)


def persist_api_key_windows(api_key: str) -> None:
    try:
        import ctypes
        import winreg
    except ImportError as exc:
        raise RuntimeError("Windows environment persistence requires winreg and ctypes.") from exc

    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        "Environment",
        0,
        winreg.KEY_SET_VALUE,
    ) as registry_key:
        winreg.SetValueEx(registry_key, ENV_KEY, 0, winreg.REG_EXPAND_SZ, api_key)

    hwnd_broadcast = 0xFFFF
    wm_settingchange = 0x001A
    smto_abortifhung = 0x0002
    ctypes.windll.user32.SendMessageTimeoutW(
        hwnd_broadcast,
        wm_settingchange,
        0,
        "Environment",
        smto_abortifhung,
        5000,
        None,
    )


def persist_api_key_posix(api_key: str) -> None:
    profile_path = resolve_shell_profile()
    export_line = f'export {ENV_KEY}={shell_quote(api_key)}'

    existing_lines: list[str] = []
    if profile_path.exists():
        existing_lines = profile_path.read_text(encoding="utf-8").splitlines()

    updated = False
    for index, line in enumerate(existing_lines):
        if line.startswith(f"export {ENV_KEY}="):
            existing_lines[index] = export_line
            updated = True
            break

    if not updated:
        if existing_lines and existing_lines[-1].strip():
            existing_lines.append("")
        existing_lines.append(export_line)

    profile_path.parent.mkdir(parents=True, exist_ok=True)
    profile_path.write_text("\n".join(existing_lines) + "\n", encoding="utf-8")


def resolve_shell_profile() -> Path:
    shell = Path(os.environ.get("SHELL", "")).name.lower()
    home = Path.home()

    if shell == "zsh":
        return home / ".zshrc"
    # NOTE: Use .profile for bash because .bashrc typically has a
    # non-interactive guard ([ -z "$PS1" ] && return) that prevents
    # env vars from loading in CI/CD, SSH commands, and subprocess
    # shells. .profile is the POSIX standard and has no such guard.
    if shell == "bash":
        return home / ".profile"
    return home / ".profile"


def shell_quote(value: str) -> str:
    escaped = value.replace("'", "'\"'\"'")
    return f"'{escaped}'"


def load_payload(payload_path: Path) -> dict[str, Any]:
    if not payload_path.exists():
        raise FileNotFoundError(f"JSON file does not exist: {payload_path}")

    try:
        raw_text = payload_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"JSON file is not valid UTF-8: {payload_path}") from exc

    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON payload is invalid: {exc}") from exc

    if not isinstance(payload, dict):
        raise ValueError("JSON payload must be an object.")
    return payload


def validate_payload(payload: dict[str, Any]) -> None:
    missing_keys = [key for key in REQUIRED_TOP_LEVEL_KEYS if key not in payload]
    if missing_keys:
        joined = ", ".join(missing_keys)
        raise ValueError(f"JSON payload is missing required top-level keys: {joined}")


def load_api_key_from_env() -> str:
    api_key = os.environ.get(ENV_KEY, "").strip()
    if api_key:
        return api_key
    raise ValueError(
        f"{ENV_KEY} is not configured. The review workflow cannot start until you run 'python scripts/stock_review_cli.py set-api-key'."
    )


def validate_report_response(response_status: int, response_body: str) -> int:
    if not response_body.strip():
        raise RuntimeError(
            f"Report failed because the API returned an empty body with HTTP {response_status}."
        )

    try:
        parsed_body = json.loads(response_body)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Report failed because the API returned a non-JSON body with HTTP {response_status}: {response_body}"
        ) from exc

    if not isinstance(parsed_body, dict):
        raise RuntimeError(
            f"Report failed because the API returned a non-object JSON body with HTTP {response_status}: {response_body}"
        )

    response_code = parsed_body.get("code")
    if response_code != 200:
        raise RuntimeError(
            "Report failed because the API returned a non-success business code: "
            f"HTTP {response_status}, code={response_code}, message={parsed_body.get('message')}"
        )

    return response_code


def submit_review(api_url: str, api_key: str, payload: dict[str, Any]) -> tuple[int, str]:
    request_body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    http_request = request.Request(
        api_url,
        data=request_body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with request.urlopen(http_request, timeout=30) as response:
            return response.getcode(), response.read().decode("utf-8")
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Report failed with HTTP {exc.code}: {body}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"Report failed because the API endpoint could not be reached: {exc}") from exc


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        return args.handler(args)
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())