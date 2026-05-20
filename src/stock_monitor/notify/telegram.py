from __future__ import annotations

import json
import time
from urllib import error
from urllib import parse, request


def _request_json_with_retries(
    http_request: str | request.Request,
    *,
    timeout_seconds: float,
    max_retries: int,
    retry_delay_seconds: float,
    operation_name: str,
) -> dict:
    attempts = max(1, max_retries)
    last_error: Exception | None = None

    for attempt in range(1, attempts + 1):
        try:
            with request.urlopen(http_request, timeout=timeout_seconds) as response:
                body = response.read().decode("utf-8")
            return json.loads(body)
        except (error.URLError, TimeoutError, OSError) as exc:
            last_error = exc
            if attempt >= attempts:
                break
            time.sleep(retry_delay_seconds)

    raise RuntimeError(f"{operation_name} failed after {attempts} attempts: {last_error}") from last_error


def send_telegram_message(
    bot_token: str,
    chat_id: str,
    text: str,
    *,
    parse_mode: str | None = None,
    timeout_seconds: float = 30,
    max_retries: int = 3,
    retry_delay_seconds: float = 2,
) -> str:
    endpoint = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload_dict = {
        "chat_id": chat_id,
        "text": text,
    }
    if parse_mode:
        payload_dict["parse_mode"] = parse_mode
    payload = parse.urlencode(payload_dict).encode("utf-8")
    http_request = request.Request(endpoint, data=payload, method="POST")
    data = _request_json_with_retries(
        http_request,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
        retry_delay_seconds=retry_delay_seconds,
        operation_name="Telegram sendMessage",
    )
    if not data.get("ok"):
        raise RuntimeError(f"Telegram send failed: {data}")
    message = data.get("result", {})
    return str(message.get("message_id", ""))


def get_telegram_updates(
    bot_token: str,
    *,
    offset: int | None = None,
    timeout_seconds: float = 30,
    max_retries: int = 3,
    retry_delay_seconds: float = 2,
) -> dict:
    endpoint = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    if offset is not None:
        endpoint = f"{endpoint}?offset={offset}"
    data = _request_json_with_retries(
        endpoint,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
        retry_delay_seconds=retry_delay_seconds,
        operation_name="Telegram getUpdates",
    )
    if not data.get("ok"):
        raise RuntimeError(f"Telegram getUpdates failed: {data}")
    return data


def get_telegram_file_path(
    bot_token: str,
    file_id: str,
    *,
    timeout_seconds: float = 30,
    max_retries: int = 3,
    retry_delay_seconds: float = 2,
) -> str:
    endpoint = f"https://api.telegram.org/bot{bot_token}/getFile?file_id={parse.quote(file_id)}"
    data = _request_json_with_retries(
        endpoint,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
        retry_delay_seconds=retry_delay_seconds,
        operation_name="Telegram getFile",
    )
    if not data.get("ok"):
        raise RuntimeError(f"Telegram getFile failed: {data}")
    file_path = str((data.get("result") or {}).get("file_path") or "").strip()
    if not file_path:
        raise RuntimeError("Telegram getFile did not return a file_path.")
    return file_path


def download_telegram_file(
    bot_token: str,
    file_path: str,
    *,
    timeout_seconds: float = 30,
    max_retries: int = 3,
    retry_delay_seconds: float = 2,
) -> bytes:
    safe_path = file_path.lstrip("/")
    endpoint = f"https://api.telegram.org/file/bot{bot_token}/{safe_path}"
    attempts = max(1, max_retries)
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            with request.urlopen(endpoint, timeout=timeout_seconds) as response:
                return response.read()
        except (error.URLError, TimeoutError, OSError) as exc:
            last_error = exc
            if attempt >= attempts:
                break
            time.sleep(retry_delay_seconds)
    raise RuntimeError(f"Telegram file download failed after {attempts} attempts: {last_error}") from last_error
