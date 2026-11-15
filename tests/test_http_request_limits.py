from io import BytesIO

import pytest

from stock_monitor.cli import _read_access_code_from_form
from stock_monitor.web_view_http import discard_http_request_body


class _Handler:
    def __init__(self, headers, body):
        self.headers = headers
        self.rfile = body
        self.close_connection = False


class _NoRead:
    def read(self, *_args):
        raise AssertionError("request body should not be read")


def test_discard_http_request_body_closes_without_reading() -> None:
    handler = _Handler({"Content-Length": "1000000000"}, _NoRead())

    discard_http_request_body(handler)

    assert handler.close_connection is True


@pytest.mark.parametrize("content_length", ["-1", "invalid", "4097"])
def test_access_code_form_rejects_invalid_or_oversized_length_without_reading(content_length: str) -> None:
    handler = _Handler({"Content-Length": content_length}, _NoRead())

    assert _read_access_code_from_form(handler) == ""
    assert handler.close_connection is True


def test_access_code_form_reads_small_url_encoded_body() -> None:
    body = b"access_code=pass1234"
    handler = _Handler(
        {"Content-Length": str(len(body)), "Content-Type": "application/x-www-form-urlencoded"},
        BytesIO(body),
    )

    assert _read_access_code_from_form(handler) == "pass1234"
    assert handler.close_connection is False


def test_access_code_form_reads_small_json_object() -> None:
    body = b'{"access_code":"pass1234"}'
    handler = _Handler(
        {"Content-Length": str(len(body)), "Content-Type": "application/json"},
        BytesIO(body),
    )

    assert _read_access_code_from_form(handler) == "pass1234"
    assert handler.close_connection is False


def test_access_code_form_rejects_invalid_utf8_and_non_object_json() -> None:
    invalid_utf8 = _Handler({"Content-Length": "1"}, BytesIO(b"\xff"))
    non_object_json = _Handler(
        {"Content-Length": "2", "Content-Type": "application/json"},
        BytesIO(b"[]"),
    )

    assert _read_access_code_from_form(invalid_utf8) == ""
    assert invalid_utf8.close_connection is True
    assert _read_access_code_from_form(non_object_json) == ""
    assert non_object_json.close_connection is True
