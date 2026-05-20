from datetime import datetime

from stock_monitor.models import build_report_identity


def test_build_report_identity_prefers_source_id_when_present() -> None:
    published_at = datetime(2026, 4, 24, 0, 0, 0)

    identity_a = build_report_identity(
        "삼성전자",
        "업황 회복 가시화",
        "NH투자증권",
        published_at,
        source_id="91999",
    )
    identity_b = build_report_identity(
        "현대차",
        "다른 제목",
        "교보증권",
        published_at,
        source_id="91999",
    )

    assert identity_a == identity_b
