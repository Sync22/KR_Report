from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, time
from pathlib import Path


DEFAULT_MARKET_HOLIDAYS_2024 = frozenset(
    {
        date(2024, 1, 1),
        date(2024, 2, 9),
        date(2024, 2, 12),
        date(2024, 3, 1),
        date(2024, 4, 10),
        date(2024, 5, 1),
        date(2024, 5, 6),
        date(2024, 5, 15),
        date(2024, 6, 6),
        date(2024, 8, 15),
        date(2024, 9, 16),
        date(2024, 9, 17),
        date(2024, 9, 18),
        date(2024, 10, 3),
        date(2024, 10, 9),
        date(2024, 12, 25),
        date(2024, 12, 31),
    }
)


DEFAULT_MARKET_HOLIDAYS_2025 = frozenset(
    {
        date(2025, 1, 1),
        date(2025, 1, 27),
        date(2025, 1, 28),
        date(2025, 1, 29),
        date(2025, 1, 30),
        date(2025, 3, 3),
        date(2025, 5, 1),
        date(2025, 5, 5),
        date(2025, 5, 6),
        date(2025, 6, 3),
        date(2025, 6, 6),
        date(2025, 8, 15),
        date(2025, 10, 3),
        date(2025, 10, 6),
        date(2025, 10, 7),
        date(2025, 10, 8),
        date(2025, 10, 9),
        date(2025, 12, 25),
        date(2025, 12, 31),
    }
)


DEFAULT_MARKET_HOLIDAYS_2026 = frozenset(
    {
        date(2026, 1, 1),
        date(2026, 2, 16),
        date(2026, 2, 17),
        date(2026, 2, 18),
        date(2026, 3, 2),
        date(2026, 5, 1),
        date(2026, 5, 5),
        date(2026, 5, 25),
        date(2026, 8, 17),
        date(2026, 9, 24),
        date(2026, 9, 25),
        date(2026, 10, 5),
        date(2026, 10, 9),
        date(2026, 12, 25),
        date(2026, 12, 31),
    }
)


DEFAULT_MARKET_HOLIDAYS = (
    DEFAULT_MARKET_HOLIDAYS_2024
    | DEFAULT_MARKET_HOLIDAYS_2025
    | DEFAULT_MARKET_HOLIDAYS_2026
)


def _read_dotenv(dotenv_path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not dotenv_path.exists():
        return values
    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key or key in values:
            continue
        values[key] = value.strip()
    return values


def _merged_env(dotenv_path: Path) -> dict[str, str]:
    env = _read_dotenv(dotenv_path)
    env.update(os.environ)
    return env


def _parse_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _parse_date_list(value: str | None) -> frozenset[date]:
    if not value:
        return frozenset()
    parsed: set[date] = set()
    for raw in value.split(","):
        item = raw.strip()
        if not item:
            continue
        parsed.add(date.fromisoformat(item))
    return frozenset(parsed)


def _resolve_holiday_overrides(value: str | None) -> frozenset[date]:
    return DEFAULT_MARKET_HOLIDAYS | _parse_date_list(value)


def _parse_time(value: str, default: str) -> time:
    raw = (value or default).strip()
    hour_str, minute_str = raw.split(":", 1)
    return time(hour=int(hour_str), minute=int(minute_str))


@dataclass(frozen=True)
class RuntimeConfig:
    root_dir: Path
    data_dir: Path
    db_path: Path
    telegram_control_state_path: Path
    rotation_overlay_coordinates_path: Path
    access_code_path: Path
    base_url: str
    timezone: str
    browser_timeout_ms: int
    api_page_size: int
    api_max_pages: int
    poll_start_time: time
    poll_end_time: time
    scheduler_task_prefix: str
    notification_default_limit: int
    daily_summary_min_mention_count: int
    daily_summary_require_target_price: bool
    headless: bool
    holiday_overrides: frozenset[date]
    run_suppressed_dates: frozenset[date]
    telegram_timeout_seconds: float
    telegram_max_retries: int
    telegram_retry_delay_seconds: float
    telegram_bot_token: str | None
    telegram_chat_id: str | None
    krx_auth_key: str | None
    krx_base_url: str
    krx_data_market_base_url: str
    krx_data_market_login_id: str | None
    krx_data_market_login_password: str | None
    krx_timeout_seconds: float

    @classmethod
    def from_env(
        cls,
        root_dir: Path | None = None,
        *,
        db_path: Path | None = None,
        headless: bool | None = None,
    ) -> "RuntimeConfig":
        project_root = root_dir or Path(__file__).resolve().parents[2]
        env = _merged_env(project_root / ".env")
        data_dir = project_root / "data"
        env_db_path = env.get("STOCK_MONITOR_DB_PATH")
        resolved_db_path = db_path or (Path(env_db_path) if env_db_path else data_dir / "stock_monitor.db")
        control_state_path = data_dir / "telegram_control_state.json"
        env_rotation_overlay_coordinates_path = env.get("STOCK_MONITOR_ROTATION_OVERLAY_COORDINATES_PATH")
        rotation_overlay_coordinates_path = (
            (project_root / env_rotation_overlay_coordinates_path)
            if env_rotation_overlay_coordinates_path and not Path(env_rotation_overlay_coordinates_path).is_absolute()
            else Path(env_rotation_overlay_coordinates_path)
            if env_rotation_overlay_coordinates_path
            else data_dir / "rotation_overlay_coordinates.json"
        )
        env_access_code_path = env.get("STOCK_MONITOR_ACCESS_CODE_PATH")
        access_code_path = (
            (project_root / env_access_code_path)
            if env_access_code_path and not Path(env_access_code_path).is_absolute()
            else Path(env_access_code_path)
            if env_access_code_path
            else data_dir / "access_code.json"
        )
        resolved_headless = headless if headless is not None else _parse_bool(
            env.get("STOCK_MONITOR_HEADLESS"),
            True,
        )
        return cls(
            root_dir=project_root,
            data_dir=data_dir,
            db_path=resolved_db_path,
            telegram_control_state_path=control_state_path,
            rotation_overlay_coordinates_path=rotation_overlay_coordinates_path,
            access_code_path=access_code_path,
            base_url=env.get("STOCK_MONITOR_BASE_URL", "https://stock.naver.com/research/company"),
            timezone=env.get("STOCK_MONITOR_TIMEZONE", "Asia/Seoul"),
            browser_timeout_ms=int(env.get("STOCK_MONITOR_BROWSER_TIMEOUT_MS", "30000")),
            api_page_size=int(env.get("STOCK_MONITOR_API_PAGE_SIZE", "50")),
            api_max_pages=int(env.get("STOCK_MONITOR_API_MAX_PAGES", "20")),
            poll_start_time=_parse_time(env.get("STOCK_MONITOR_POLL_START_TIME", "08:30"), "08:30"),
            poll_end_time=_parse_time(env.get("STOCK_MONITOR_POLL_END_TIME", "16:30"), "16:30"),
            scheduler_task_prefix=env.get("STOCK_MONITOR_TASK_PREFIX", "StockMonitor"),
            notification_default_limit=int(env.get("STOCK_MONITOR_NOTIFICATION_DEFAULT_LIMIT", "7")),
            daily_summary_min_mention_count=int(env.get("STOCK_MONITOR_DAILY_SUMMARY_MIN_MENTION_COUNT", "2")),
            daily_summary_require_target_price=_parse_bool(
                env.get("STOCK_MONITOR_DAILY_SUMMARY_REQUIRE_TARGET_PRICE"),
                True,
            ),
            headless=resolved_headless,
            holiday_overrides=_resolve_holiday_overrides(env.get("STOCK_MONITOR_HOLIDAYS")),
            run_suppressed_dates=_parse_date_list(env.get("STOCK_MONITOR_RUN_SUPPRESSED_DATES")),
            telegram_timeout_seconds=float(env.get("STOCK_MONITOR_TELEGRAM_TIMEOUT_SECONDS", "30")),
            telegram_max_retries=int(env.get("STOCK_MONITOR_TELEGRAM_MAX_RETRIES", "3")),
            telegram_retry_delay_seconds=float(env.get("STOCK_MONITOR_TELEGRAM_RETRY_DELAY_SECONDS", "2")),
            telegram_bot_token=env.get("STOCK_MONITOR_TELEGRAM_BOT_TOKEN"),
            telegram_chat_id=env.get("STOCK_MONITOR_TELEGRAM_CHAT_ID"),
            krx_auth_key=env.get("STOCK_MONITOR_KRX_AUTH_KEY"),
            krx_base_url=env.get("STOCK_MONITOR_KRX_BASE_URL", "https://data-dbg.krx.co.kr").rstrip("/"),
            krx_data_market_base_url=env.get(
                "STOCK_MONITOR_KRX_DATA_MARKET_BASE_URL",
                "https://data.krx.co.kr",
            ).rstrip("/"),
            krx_data_market_login_id=env.get("STOCK_MONITOR_KRX_DATA_MARKET_ID") or env.get("KRX_ID"),
            krx_data_market_login_password=env.get("STOCK_MONITOR_KRX_DATA_MARKET_PASSWORD") or env.get("KRX_PW"),
            krx_timeout_seconds=float(env.get("STOCK_MONITOR_KRX_TIMEOUT_SECONDS", "30")),
        )

    def ensure_runtime_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.telegram_control_state_path.parent.mkdir(parents=True, exist_ok=True)
        self.rotation_overlay_coordinates_path.parent.mkdir(parents=True, exist_ok=True)
        self.access_code_path.parent.mkdir(parents=True, exist_ok=True)
