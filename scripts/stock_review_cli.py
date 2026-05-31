from __future__ import annotations

import argparse
import getpass
import json
import os
import platform
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib import error, request


API_URL = "https://xiaoniu.tech/api/stock/reviews"
ENV_KEY = "STOCK_REVIEW_API_KEY"
API_URL_ENV_KEY = "STOCK_REVIEW_API_URL"
UPLOAD_ENABLED_ENV_KEY = "STOCK_REVIEW_UPLOAD_ENABLED"
TIMEOUT_ENV_KEY = "STOCK_REVIEW_API_TIMEOUT_SECONDS"
CONFIG_PATH_ENV_KEY = "STOCK_REVIEW_CONFIG_FILE"
DEFAULT_CONFIG_FILE = "config.yml"
DEFAULT_CONFIG_EXAMPLE_FILE = "config.example.yml"
DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_API_PATH = "/stock/reviews"
DEFAULT_LOCAL_OUTPUT_PATH = "/usr/local/files/docs/stock"
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

DEFAULT_RUNTIME_CONFIG: dict[str, Any] = {
    "review": {
        "upload": {
            "enabled": False,
            "apiUrl": API_URL,
            "apiKey": "",
            "timeoutSeconds": DEFAULT_TIMEOUT_SECONDS,
        },
        "local": {
            "doc": {
                "enabled": True,
                "path": DEFAULT_LOCAL_OUTPUT_PATH,
            },
            "json": {
                "enabled": True,
                "path": DEFAULT_LOCAL_OUTPUT_PATH,
            },
        },
    }
}


@dataclass(frozen=True)
class ReportSettings:
    config_path: Path | None
    upload_enabled: bool
    api_url: str
    api_key: str | None
    timeout_seconds: int


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
        "--config-file",
        help=f"Path to the runtime config file. Defaults to {CONFIG_PATH_ENV_KEY} or ./{DEFAULT_CONFIG_FILE}.",
    )
    report_parser.add_argument(
        "--api-url",
        help="Override the report API endpoint.",
    )
    report_parser.add_argument(
        "--api-key",
        help="Override the API key for this command. Prefer environment variables or set-api-key for secrets.",
    )
    report_parser.add_argument(
        "--timeout-seconds",
        type=int,
        help="Override the HTTP timeout in seconds.",
    )
    upload_enabled_group = report_parser.add_mutually_exclusive_group()
    upload_enabled_group.add_argument(
        "--upload-enabled",
        dest="upload_enabled",
        action="store_true",
        default=None,
        help="Force-enable upload for this command.",
    )
    upload_enabled_group.add_argument(
        "--upload-disabled",
        dest="upload_enabled",
        action="store_false",
        help="Force-disable upload for this command.",
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
    settings = resolve_report_settings(args)
    if not settings.upload_enabled:
        config_hint = f" in {settings.config_path}" if settings.config_path else ""
        raise ValueError(
            "Upload is disabled by configuration"
            f"{config_hint}. Set review.upload.enabled=true, set {UPLOAD_ENABLED_ENV_KEY}=true, or pass --upload-enabled."
        )

    payload_path = Path(args.json_file).expanduser().resolve()
    payload = load_payload(payload_path)
    validate_payload(payload)
    response_status, response_body = submit_review(
        api_url=settings.api_url,
        api_key=settings.api_key or "",
        payload=payload,
        timeout_seconds=settings.timeout_seconds,
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


def resolve_report_settings(args: argparse.Namespace) -> ReportSettings:
    config_path = resolve_config_path(args.config_file)
    config = load_runtime_config(config_path)

    upload_enabled = resolve_bool_setting(
        cli_value=args.upload_enabled,
        env_key=UPLOAD_ENABLED_ENV_KEY,
        config_value=get_review_upload_config_value(config, "enabled"),
        default=False,
        setting_label="review.upload.enabled",
    )
    api_url = resolve_string_setting(
        cli_value=args.api_url,
        env_key=API_URL_ENV_KEY,
        config_value=get_review_upload_config_value(config, "apiUrl"),
        default=API_URL,
    )
    api_key = None
    if upload_enabled:
        api_key = resolve_required_string_setting(
            cli_value=args.api_key,
            env_key=ENV_KEY,
            config_value=get_review_upload_config_value(config, "apiKey"),
            error_message=(
                f"{ENV_KEY} is not configured. Upload is enabled, so provide --api-key, set the environment variable, "
                f"or configure review.upload.apiKey in {config_path or DEFAULT_CONFIG_FILE}."
            ),
        )
    timeout_seconds = resolve_int_setting(
        cli_value=args.timeout_seconds,
        env_key=TIMEOUT_ENV_KEY,
        config_value=get_review_upload_config_value(config, "timeoutSeconds"),
        default=DEFAULT_TIMEOUT_SECONDS,
        minimum=1,
        setting_label="review.upload.timeoutSeconds",
    )

    return ReportSettings(
        config_path=config_path,
        upload_enabled=upload_enabled,
        api_url=api_url,
        api_key=api_key,
        timeout_seconds=timeout_seconds,
    )


def resolve_config_path(cli_value: str | None) -> Path | None:
    env_value = read_env_string(CONFIG_PATH_ENV_KEY)
    explicit_path = normalize_optional_string(cli_value) or env_value
    if explicit_path is not None:
        path = Path(explicit_path).expanduser()
        if path.exists():
            return path.resolve()
        raise FileNotFoundError(f"Config file does not exist: {path}")

    for candidate in iter_default_config_candidates(DEFAULT_CONFIG_FILE):
        if candidate.exists():
            return candidate.resolve()
    return None


def load_runtime_config(config_path: Path | None) -> dict[str, Any]:
    config = load_default_runtime_config()
    if config_path is None:
        return config

    parsed = load_yaml_config_file(config_path)
    return merge_nested_dicts(config, parsed)


def load_default_runtime_config() -> dict[str, Any]:
    config = merge_nested_dicts({}, DEFAULT_RUNTIME_CONFIG)

    for candidate in iter_default_config_candidates(DEFAULT_CONFIG_EXAMPLE_FILE):
        if not candidate.exists():
            continue
        parsed = load_yaml_config_file(candidate)
        return merge_nested_dicts(config, parsed)

    return config


def load_yaml_config_file(config_path: Path) -> dict[str, Any]:
    try:
        raw_text = config_path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError(f"Config file is not valid UTF-8: {config_path}") from exc

    parsed = parse_simple_yaml(raw_text, config_path)
    return normalize_runtime_config(parsed)


def iter_default_config_candidates(file_name: str) -> list[Path]:
    script_root = Path(__file__).resolve().parent.parent
    candidates = [Path.cwd() / file_name, script_root / file_name]
    unique_candidates: list[Path] = []
    seen: set[str] = set()

    for candidate in candidates:
        normalized = str(candidate.resolve(strict=False))
        if normalized in seen:
            continue
        seen.add(normalized)
        unique_candidates.append(candidate)

    return unique_candidates


def parse_simple_yaml(raw_text: str, config_path: Path) -> dict[str, Any]:
    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(-1, root)]

    for line_number, raw_line in enumerate(raw_text.splitlines(), start=1):
        if "\t" in raw_line:
            raise ValueError(f"Tabs are not supported in config file {config_path}:{line_number}")

        line = strip_inline_comment(raw_line)
        if not line.strip():
            continue

        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()
        if ":" not in stripped:
            raise ValueError(f"Invalid config line in {config_path}:{line_number}: {raw_line}")

        key, raw_value = stripped.split(":", 1)
        key = key.strip()
        raw_value = raw_value.strip()
        if not key:
            raise ValueError(f"Config key cannot be empty in {config_path}:{line_number}")

        while len(stack) > 1 and indent <= stack[-1][0]:
            stack.pop()

        current = stack[-1][1]
        if not raw_value:
            child: dict[str, Any] = {}
            current[key] = child
            stack.append((indent, child))
            continue

        current[key] = parse_yaml_scalar(raw_value, config_path, line_number)

    return root


def strip_inline_comment(line: str) -> str:
    in_single_quote = False
    in_double_quote = False
    escaped = False

    for index, char in enumerate(line):
        if escaped:
            escaped = False
            continue
        if char == "\\" and in_double_quote:
            escaped = True
            continue
        if char == "'" and not in_double_quote:
            in_single_quote = not in_single_quote
            continue
        if char == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
            continue
        if char == "#" and not in_single_quote and not in_double_quote:
            return line[:index].rstrip()

    return line.rstrip()


def parse_yaml_scalar(raw_value: str, config_path: Path, line_number: int) -> Any:
    if (raw_value.startswith('"') and raw_value.endswith('"')) or (
        raw_value.startswith("'") and raw_value.endswith("'")
    ):
        return raw_value[1:-1]

    lower_value = raw_value.lower()
    if lower_value == "true":
        return True
    if lower_value == "false":
        return False
    if lower_value in {"null", "none"}:
        return None
    if raw_value.isdigit() or (raw_value.startswith("-") and raw_value[1:].isdigit()):
        return int(raw_value)
    if raw_value.startswith("[") or raw_value.startswith("{"):
        raise ValueError(
            f"Lists and inline objects are not supported in {config_path}:{line_number}. Use simple key/value mappings only."
        )
    return raw_value


def normalize_runtime_config(config: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(config)
    review = as_mapping(normalized.get("review"))
    upload = {**as_mapping(normalized.get("upload-review")), **as_mapping(review.get("upload"))}
    local = as_mapping(review.get("local"))

    base_url = normalize_optional_string(upload.get("baseUrl"))
    if normalize_optional_string(upload.get("apiUrl")) is None and base_url is not None:
        upload["apiUrl"] = build_api_url_from_base(base_url)

    legacy_doc_path = normalize_optional_string(normalized.get("doc-path"))
    if legacy_doc_path is not None:
        doc = {**as_mapping(local.get("doc"))}
        doc.setdefault("path", legacy_doc_path)
        local["doc"] = doc

    review = dict(review)
    if upload:
        review["upload"] = upload
    if local:
        review["local"] = local
    normalized["review"] = review
    return normalized


def merge_nested_dicts(base: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)

    for key, value in overrides.items():
        existing = merged.get(key)
        if isinstance(existing, dict) and isinstance(value, dict):
            merged[key] = merge_nested_dicts(existing, value)
        else:
            merged[key] = value

    return merged


def as_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def build_api_url_from_base(base_url: str) -> str:
    trimmed = base_url.rstrip("/")
    if trimmed.endswith(DEFAULT_API_PATH):
        return trimmed
    return f"{trimmed}{DEFAULT_API_PATH}"


def get_review_upload_config_value(config: dict[str, Any], key: str) -> Any:
    review = config.get("review")
    if not isinstance(review, dict):
        return None
    upload = review.get("upload")
    if not isinstance(upload, dict):
        return None
    return upload.get(key)


def resolve_string_setting(
    cli_value: Any,
    env_key: str | None,
    config_value: Any,
    default: str,
) -> str:
    cli_string = normalize_optional_string(cli_value)
    if cli_string is not None:
        return cli_string

    env_string = read_env_string(env_key) if env_key else None
    if env_string is not None:
        return env_string

    config_string = normalize_optional_string(config_value)
    if config_string is not None:
        return config_string
    return default


def resolve_required_string_setting(
    cli_value: Any,
    env_key: str | None,
    config_value: Any,
    error_message: str,
) -> str:
    resolved = resolve_optional_string_setting(cli_value, env_key, config_value)
    if resolved is not None:
        return resolved
    raise ValueError(error_message)


def resolve_optional_string_setting(
    cli_value: Any,
    env_key: str | None,
    config_value: Any,
) -> str | None:
    cli_string = normalize_optional_string(cli_value)
    if cli_string is not None:
        return cli_string

    env_string = read_env_string(env_key) if env_key else None
    if env_string is not None:
        return env_string

    return normalize_optional_string(config_value)


def resolve_bool_setting(
    cli_value: bool | None,
    env_key: str | None,
    config_value: Any,
    default: bool,
    setting_label: str,
) -> bool:
    if cli_value is not None:
        return cli_value

    env_string = read_env_string(env_key) if env_key else None
    if env_string is not None:
        return parse_bool_like(env_string, f"environment variable {env_key}")

    if config_value is not None:
        return parse_bool_like(config_value, f"config key {setting_label}")
    return default


def resolve_int_setting(
    cli_value: int | None,
    env_key: str | None,
    config_value: Any,
    default: int,
    minimum: int,
    setting_label: str,
) -> int:
    if cli_value is not None:
        return parse_int_like(cli_value, "command line option --timeout-seconds", minimum)

    env_string = read_env_string(env_key) if env_key else None
    if env_string is not None:
        return parse_int_like(env_string, f"environment variable {env_key}", minimum)

    if config_value is not None:
        return parse_int_like(config_value, f"config key {setting_label}", minimum)
    return default


def parse_bool_like(value: Any, source: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    raise ValueError(f"Invalid boolean value for {source}: {value}")


def parse_int_like(value: Any, source: str, minimum: int) -> int:
    if isinstance(value, bool):
        raise ValueError(f"Invalid integer value for {source}: {value}")
    if isinstance(value, int):
        parsed = value
    elif isinstance(value, str) and value.strip():
        try:
            parsed = int(value.strip())
        except ValueError as exc:
            raise ValueError(f"Invalid integer value for {source}: {value}") from exc
    else:
        raise ValueError(f"Invalid integer value for {source}: {value}")

    if parsed < minimum:
        raise ValueError(f"Value for {source} must be >= {minimum}: {parsed}")
    return parsed


def normalize_optional_string(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return str(value).strip() or None


def read_env_string(env_key: str | None) -> str | None:
    if env_key is None:
        return None
    return normalize_optional_string(os.environ.get(env_key))


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


def submit_review(api_url: str, api_key: str, payload: dict[str, Any], timeout_seconds: int) -> tuple[int, str]:
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
        with request.urlopen(http_request, timeout=timeout_seconds) as response:
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