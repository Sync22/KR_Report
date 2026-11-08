from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from threading import Event, Lock

import stock_monitor.cli as cli_module
from stock_monitor.config import RuntimeConfig
from stock_monitor.db.repository import StockMonitorRepository
from stock_monitor.models import DeliveryLog
from stock_monitor.notify.telegram import TelegramRequestError
import stock_monitor.fetch.krx_kind as krx_kind_module
from stock_monitor.fetch.krx_kind import fetch_krx_kind_market_actions, parse_krx_kind_market_actions
from stock_monitor.fetch.krx_kind import KrxKindMarketAction


def test_parse_krx_kind_market_actions_keeps_official_notice_identity_and_time() -> None:
    payload = """
    <table><tbody>
      <tr>
        <td>7</td><td>2026-07-29 12:32</td><td></td>
        <td><a onclick="openDisclsViewer('20260729000359','')" title="유가증권시장 매매거래 일시중단(1단계 CB 발동)">유가증권시장 매매거래 일시중단(1단계 CB 발동)</a></td>
        <td>유가증권시장본부</td>
      </tr>
      <tr>
        <td>6</td><td>2026-07-29 10:55</td><td></td>
        <td><a onclick="openDisclsViewer('20260729000240','')" title="유가증권시장 매도 사이드카(Side car) 발동">유가증권시장 매도 사이드카(Side car) 발동</a></td>
        <td>유가증권시장본부</td>
      </tr>
    </tbody></table>
    """

    notices = parse_krx_kind_market_actions(payload)

    assert [(item.acceptance_number, item.published_at, item.title, item.submitter) for item in notices] == [
        (
            "20260729000359",
            datetime(2026, 7, 29, 12, 32),
            "유가증권시장 매매거래 일시중단(1단계 CB 발동)",
            "유가증권시장본부",
        ),
        (
            "20260729000240",
            datetime(2026, 7, 29, 10, 55),
            "유가증권시장 매도 사이드카(Side car) 발동",
            "유가증권시장본부",
        ),
    ]


def test_parse_krx_kind_market_actions_ignores_rows_without_a_notice_identity() -> None:
    payload = "<table><tbody><tr><td>1</td><td>2026-08-23 09:01</td><td></td><td>제목만 있음</td><td>유가증권시장본부</td></tr></tbody></table>"

    assert parse_krx_kind_market_actions(payload) == []


def test_fetch_krx_kind_market_actions_posts_only_the_market_action_category(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class _Response:
        def read(self, _limit: int) -> bytes:
            return b"<table><tbody></tbody></table>"

        def __enter__(self):
            return self

        def __exit__(self, *_args) -> None:
            return None

    def fake_urlopen(http_request, *, timeout: float):
        captured["url"] = http_request.full_url
        captured["body"] = http_request.data.decode("ascii")
        captured["timeout"] = timeout
        return _Response()

    monkeypatch.setattr(krx_kind_module.request, "urlopen", fake_urlopen)

    assert fetch_krx_kind_market_actions(date(2026, 7, 29), timeout_seconds=7) == []
    assert captured["url"] == "https://kind.krx.co.kr/disclosure/details.do"
    assert "disclosureTypeArr02=0347" in captured["body"]
    assert "pDisclosureType20=" in captured["body"]
    assert "enterprise=" in captured["body"]
    assert "fromDate=2026-07-29" in captured["body"]
    assert captured["timeout"] == 7


def test_kind_market_action_check_sends_each_official_notice_once(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("STOCK_MONITOR_TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("STOCK_MONITOR_TELEGRAM_CHAT_ID", "chat")
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    notices = [
        KrxKindMarketAction(
            acceptance_number="20260729000359",
            published_at=datetime(2026, 7, 29, 12, 32),
            title="유가증권시장 매매거래 일시중단(1단계 CB 발동)",
            submitter="유가증권시장본부",
        )
    ]
    monkeypatch.setattr(cli_module, "fetch_krx_kind_market_actions", lambda *_args, **_kwargs: notices)
    sent_messages: list[str] = []
    monkeypatch.setattr(
        cli_module,
        "send_telegram_message",
        lambda *_args, **_kwargs: sent_messages.append(str(_args[2])) or "kind-message-1",
    )

    first = cli_module._run_krx_kind_market_action_check(
        config,
        repository,
        current=datetime(2026, 7, 29, 12, 34),
    )
    second = cli_module._run_krx_kind_market_action_check(
        config,
        repository,
        current=datetime(2026, 7, 29, 12, 35),
    )

    assert first == 0
    assert second == 0
    assert len(sent_messages) == 1
    assert "KRX 공식 시장조치 확인" in sent_messages[0]
    assert "매수" not in sent_messages[0]
    assert "추천" not in sent_messages[0]
    assert repository.has_successful_delivery(
        date(2026, 7, 29),
        "telegram_krx_kind_market_action:20260729000359",
    )


def test_kind_market_action_check_dry_run_never_sends_or_writes_delivery(tmp_path, monkeypatch, capsys) -> None:
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    monkeypatch.setattr(
        cli_module,
        "fetch_krx_kind_market_actions",
        lambda *_args, **_kwargs: [
            KrxKindMarketAction(
                acceptance_number="20260729000240",
                published_at=datetime(2026, 7, 29, 10, 55),
                title="유가증권시장 매도 사이드카(Side car) 발동",
                submitter="유가증권시장본부",
            )
        ],
    )
    monkeypatch.setattr(cli_module, "send_telegram_message", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError()))

    result = cli_module._run_krx_kind_market_action_check(
        config,
        repository,
        current=datetime(2026, 7, 29, 10, 56),
        dry_run=True,
    )

    assert result == 0
    assert "Would alert KRX KIND market action" in capsys.readouterr().out
    assert repository.has_successful_delivery(
        date(2026, 7, 29),
        "telegram_krx_kind_market_action:20260729000240",
    ) is False


def test_kind_market_action_claims_delivery_before_one_ambiguous_post(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("STOCK_MONITOR_TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("STOCK_MONITOR_TELEGRAM_CHAT_ID", "chat")
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    notice = KrxKindMarketAction(
        acceptance_number="20260729000359",
        published_at=datetime(2026, 7, 29, 12, 32),
        title="유가증권시장 매매거래 일시중단",
        submitter="유가증권시장본부",
    )
    monkeypatch.setattr(cli_module, "fetch_krx_kind_market_actions", lambda *_args, **_kwargs: [notice])
    calls = 0

    def ambiguous_send(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        with repository.connect() as connection:
            row = connection.execute(
                "SELECT status FROM delivery_log WHERE business_date = ? AND channel = ? ORDER BY id DESC LIMIT 1",
                ("2026-07-29", "telegram_krx_kind_market_action:20260729000359"),
            ).fetchone()
        assert row is not None and row["status"] == "sending"
        raise TelegramRequestError("Telegram sendMessage", 1, error_kind="TimeoutError", ambiguous=True)

    monkeypatch.setattr(cli_module, "send_telegram_message", ambiguous_send)
    current = datetime(2026, 7, 29, 12, 34)

    try:
        cli_module._run_krx_kind_market_action_check(config, repository, current=current)
    except RuntimeError:
        pass
    else:
        raise AssertionError("Expected the ambiguous Telegram send to fail")
    cli_module._run_krx_kind_market_action_check(config, repository, current=current)

    assert calls == 1
    assert repository.has_latest_delivery_status(
        date(2026, 7, 29), "telegram_krx_kind_market_action:20260729000359", status="ambiguous"
    )

    monkeypatch.setattr(cli_module, "send_telegram_message", lambda *_args, **_kwargs: "reviewed-message")
    assert cli_module._run_krx_kind_market_action_check(
        config,
        repository,
        current=current,
        retry_ambiguous=True,
    ) == 0
    with repository.connect() as connection:
        statuses = connection.execute(
            "SELECT status FROM delivery_log WHERE business_date = ? AND channel = ? ORDER BY id",
            ("2026-07-29", "telegram_krx_kind_market_action:20260729000359"),
        ).fetchall()
    assert [row["status"] for row in statuses] == ["ambiguous", "sent"]


def test_kind_market_action_claim_is_atomic_across_workers(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("STOCK_MONITOR_TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("STOCK_MONITOR_TELEGRAM_CHAT_ID", "chat")
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    notice = KrxKindMarketAction(
        acceptance_number="20260729000359",
        published_at=datetime(2026, 7, 29, 12, 32),
        title="유가증권시장 매매거래 일시중단",
        submitter="유가증권시장본부",
    )
    monkeypatch.setattr(cli_module, "fetch_krx_kind_market_actions", lambda *_args, **_kwargs: [notice])
    send_entered = Event()
    release_send = Event()
    lock = Lock()
    calls = 0

    def fake_send(*_args, **_kwargs):
        nonlocal calls
        with lock:
            calls += 1
            call_number = calls
        if call_number == 1:
            send_entered.set()
            assert release_send.wait(timeout=3)
        return f"message-{call_number}"

    monkeypatch.setattr(cli_module, "send_telegram_message", fake_send)
    current = datetime(2026, 7, 29, 12, 34)
    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(cli_module._run_krx_kind_market_action_check, config, repository, current=current)
        assert send_entered.wait(timeout=3)
        second = executor.submit(cli_module._run_krx_kind_market_action_check, config, repository, current=current)
        second.result(timeout=3)
        release_send.set()
        first.result(timeout=3)

    assert calls == 1


def test_kind_market_action_definite_rejection_is_failed_and_retryable(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("STOCK_MONITOR_TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("STOCK_MONITOR_TELEGRAM_CHAT_ID", "chat")
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    notice = KrxKindMarketAction(
        acceptance_number="20260729000359",
        published_at=datetime(2026, 7, 29, 12, 32),
        title="유가증권시장 매매거래 일시중단",
        submitter="유가증권시장본부",
    )
    monkeypatch.setattr(cli_module, "fetch_krx_kind_market_actions", lambda *_args, **_kwargs: [notice])
    calls = 0

    def reject_once(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise TelegramRequestError("Telegram sendMessage", 1, error_kind="api_rejected")
        return "accepted-message"

    monkeypatch.setattr(cli_module, "send_telegram_message", reject_once)
    current = datetime(2026, 7, 29, 12, 34)
    try:
        cli_module._run_krx_kind_market_action_check(config, repository, current=current)
    except TelegramRequestError:
        pass
    else:
        raise AssertionError("Expected the definite Telegram rejection")
    cli_module._run_krx_kind_market_action_check(config, repository, current=current)

    with repository.connect() as connection:
        statuses = connection.execute(
            "SELECT status FROM delivery_log WHERE business_date = ? AND channel = ? ORDER BY id",
            ("2026-07-29", "telegram_krx_kind_market_action:20260729000359"),
        ).fetchall()
    assert [row["status"] for row in statuses] == ["failed", "sent"]


def test_kind_market_action_stale_claim_becomes_ambiguous_without_resend(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("STOCK_MONITOR_TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("STOCK_MONITOR_TELEGRAM_CHAT_ID", "chat")
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    business_date = date(2026, 7, 29)
    channel = "telegram_krx_kind_market_action:20260729000359"
    repository.record_delivery(
        DeliveryLog(
            business_date=business_date,
            channel=channel,
            status="sending",
            delivered_at=datetime.fromisoformat("2026-07-29T11:00:00+09:00"),
            detail="source=krx-kind; acceptance_number=20260729000359",
        )
    )
    monkeypatch.setattr(
        cli_module,
        "fetch_krx_kind_market_actions",
        lambda *_args, **_kwargs: [
            KrxKindMarketAction(
                acceptance_number="20260729000359",
                published_at=datetime(2026, 7, 29, 12, 32),
                title="유가증권시장 매매거래 일시중단",
                submitter="유가증권시장본부",
            )
        ],
    )
    sends: list[str] = []
    monkeypatch.setattr(cli_module, "send_telegram_message", lambda *_args, **_kwargs: sends.append("sent"))

    assert cli_module._run_krx_kind_market_action_check(
        config,
        repository,
        current=datetime(2026, 7, 29, 12, 34),
    ) == 0

    assert sends == []
    assert repository.has_latest_delivery_status(business_date, channel, status="ambiguous")


def test_kind_market_action_explicit_retry_claims_after_marking_stale_send_ambiguous(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("STOCK_MONITOR_TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("STOCK_MONITOR_TELEGRAM_CHAT_ID", "chat")
    config = RuntimeConfig.from_env(root_dir=tmp_path)
    repository = StockMonitorRepository(config.db_path, timezone=config.timezone)
    repository.initialize()
    business_date = date(2026, 7, 29)
    channel = "telegram_krx_kind_market_action:20260729000359"
    repository.record_delivery(
        DeliveryLog(
            business_date=business_date,
            channel=channel,
            status="sending",
            delivered_at=datetime.fromisoformat("2026-07-29T11:00:00+09:00"),
            detail="source=krx-kind; acceptance_number=20260729000359",
        )
    )
    monkeypatch.setattr(
        cli_module,
        "fetch_krx_kind_market_actions",
        lambda *_args, **_kwargs: [
            KrxKindMarketAction(
                acceptance_number="20260729000359",
                published_at=datetime(2026, 7, 29, 12, 32),
                title="유가증권시장 매매거래 일시중단",
                submitter="유가증권시장본부",
            )
        ],
    )

    def approved_send(*_args, **_kwargs):
        with repository.connect() as connection:
            statuses = connection.execute(
                "SELECT status FROM delivery_log WHERE business_date = ? AND channel = ? ORDER BY id",
                (business_date.isoformat(), channel),
            ).fetchall()
        assert [row["status"] for row in statuses] == ["ambiguous", "sending"]
        return "reviewed-message"

    monkeypatch.setattr(cli_module, "send_telegram_message", approved_send)

    assert cli_module._run_krx_kind_market_action_check(
        config,
        repository,
        current=datetime(2026, 7, 29, 12, 34),
        retry_ambiguous=True,
    ) == 0

    assert repository.has_successful_delivery(business_date, channel)


def test_kind_market_action_retry_approval_flag_is_manual_and_defaults_off() -> None:
    parser = cli_module.build_parser()

    default_args = parser.parse_args(["krx-kind-market-action-check"])
    approved_args = parser.parse_args(["krx-kind-market-action-check", "--retry-ambiguous"])

    assert default_args.retry_ambiguous is False
    assert approved_args.retry_ambiguous is True
