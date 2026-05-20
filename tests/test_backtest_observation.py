from datetime import date, datetime

from stock_monitor.analysis.backtest_observation import (
    build_backtest_observation_rows,
    build_feature_availability_audit,
    build_feature_comparison_audit,
    build_hidden_score_prototype,
    build_hidden_score_holdout_validation,
    build_hidden_score_holdout_sweep,
    build_reaction_distribution_audit,
    build_weight_draft_audit,
)
from stock_monitor.db.repository import StockMonitorRepository
from stock_monitor.models import (
    InvestorNetBuyTopDaily,
    Opinion,
    Report,
    StockInvestorFlowDaily,
    StockMarketDailySnapshot,
)


def _report(
    *,
    source_id: str,
    stock_name: str = "삼성전자",
    stock_code: str | None = "005930",
    broker_name: str = "NH투자증권",
    business_date: date = date(2026, 5, 4),
    target_price_value: int | None = 150_000,
) -> Report:
    return Report(
        stock_name=stock_name,
        stock_code=stock_code,
        title=f"{stock_name} 관찰 리포트 {source_id}",
        broker_name=broker_name,
        published_at=datetime.combine(business_date, datetime.min.time()),
        collected_at=datetime(2026, 5, 13, 8, 0, 0),
        business_date=business_date,
        target_price_raw=str(target_price_value) if target_price_value is not None else "N/A",
        target_price_value=target_price_value,
        opinion_raw="Buy",
        opinion_normalized=Opinion.BUY.value,
        source_url=f"https://stock.naver.com/research/company/{source_id}",
        source_id=source_id,
    )


def _stock_market(
    business_date: date,
    *,
    close_price: int,
    stock_code: str = "005930",
    stock_name: str = "삼성전자",
    turnover: int = 1_000_000_000,
    volume: int = 100_000,
) -> StockMarketDailySnapshot:
    return StockMarketDailySnapshot(
        business_date=business_date,
        stock_code=stock_code,
        stock_name=stock_name,
        market="KOSPI",
        close_price=close_price,
        volume=volume,
        turnover=turnover,
        fetched_at=datetime(2026, 5, 13, 8, 10, 0),
    )


def _repository(tmp_path) -> StockMonitorRepository:
    repository = StockMonitorRepository(tmp_path / "stock_monitor.db")
    repository.initialize()
    return repository


def test_backtest_observation_uses_mention_threshold_and_exact_horizon_rows(tmp_path) -> None:
    repository = _repository(tmp_path)
    business_date = date(2026, 5, 4)
    repository.insert_reports(
        [
            _report(source_id="1", broker_name="NH투자증권", business_date=business_date),
            _report(source_id="2", broker_name="KB증권", business_date=business_date),
            _report(
                source_id="3",
                stock_name="SK텔레콤",
                stock_code="017670",
                broker_name="하나증권",
                business_date=business_date,
            ),
        ]
    )
    repository.rebuild_daily_summaries(business_date)
    repository.upsert_stock_market_daily(
        [
            _stock_market(date(2026, 5, 4), close_price=100_000, turnover=1_000),
            _stock_market(date(2026, 5, 6), close_price=110_000, turnover=2_000),
            _stock_market(date(2026, 5, 7), close_price=105_000, turnover=3_000),
            _stock_market(date(2026, 5, 8), close_price=120_000, turnover=4_000),
        ]
    )

    rows = build_backtest_observation_rows(
        repository,
        business_date=business_date,
        mention_threshold=2,
        horizons=(1, 3),
    )

    assert [row.summary.stock_code for row in rows] == ["005930"]
    assert rows[0].base_market.close_price == 100_000
    assert rows[0].reaction_windows[0].horizon_days == 1
    assert rows[0].reaction_windows[0].horizon_date == date(2026, 5, 6)
    assert rows[0].reaction_windows[0].close_return_percent == 10.0
    assert rows[0].reaction_windows[1].horizon_days == 3
    assert rows[0].reaction_windows[1].horizon_date == date(2026, 5, 8)
    assert rows[0].reaction_windows[1].close_return_percent == 20.0


def test_backtest_observation_target_gap_and_progress_ignore_missing_target_values(tmp_path) -> None:
    repository = _repository(tmp_path)
    baseline_date = date(2026, 5, 4)
    business_date = date(2026, 5, 8)
    repository.insert_reports(
        [
            _report(source_id="baseline", business_date=baseline_date, target_price_value=150_000),
            _report(source_id="current-1", business_date=business_date, target_price_value=150_000),
            _report(source_id="current-2", broker_name="KB증권", business_date=business_date, target_price_value=200_000),
            _report(source_id="missing-target", broker_name="미래에셋증권", business_date=business_date, target_price_value=None),
        ]
    )
    repository.rebuild_daily_summaries(baseline_date)
    repository.rebuild_daily_summaries(business_date)
    repository.upsert_stock_market_daily(
        [
            _stock_market(baseline_date, close_price=80_000),
            _stock_market(business_date, close_price=100_000),
            _stock_market(date(2026, 5, 11), close_price=120_000),
        ]
    )

    rows = build_backtest_observation_rows(
        repository,
        business_date=business_date,
        mention_threshold=2,
        horizons=(1,),
    )

    target = rows[0].target_observation
    assert target.available is True
    assert target.target_price_min == 150_000
    assert target.target_price_max == 200_000
    assert target.target_gap_min_percent == 50.0
    assert target.target_gap_max_percent == 100.0
    assert target.baseline_date == baseline_date
    assert target.baseline_price == 80_000
    assert target.progress_to_min_percent == 28.57
    assert target.progress_to_max_percent == 16.67
    assert target.progress_caution is False
    assert target.progress_notice == "baseline_below_target_range"


def test_backtest_observation_target_validation_tracks_max_progress_and_hit_days(tmp_path) -> None:
    repository = _repository(tmp_path)
    baseline_date = date(2026, 5, 4)
    business_date = date(2026, 5, 8)
    repository.insert_reports(
        [
            _report(source_id="baseline", business_date=baseline_date, target_price_value=150_000),
            _report(source_id="current-1", business_date=business_date, target_price_value=150_000),
            _report(source_id="current-2", broker_name="KB증권", business_date=business_date, target_price_value=200_000),
        ]
    )
    repository.rebuild_daily_summaries(baseline_date)
    repository.rebuild_daily_summaries(business_date)
    repository.upsert_stock_market_daily(
        [
            _stock_market(baseline_date, close_price=100_000),
            _stock_market(business_date, close_price=120_000),
            _stock_market(date(2026, 5, 11), close_price=140_000),
            _stock_market(date(2026, 5, 12), close_price=160_000),
            _stock_market(date(2026, 5, 13), close_price=155_000),
        ]
    )

    rows = build_backtest_observation_rows(
        repository,
        business_date=business_date,
        mention_threshold=2,
        horizons=(1, 3),
    )

    target = rows[0].target_observation
    assert target.validation_available is True
    assert target.validation_window_days == 3
    assert target.max_progress_to_min_percent == 120.0
    assert target.max_progress_to_max_percent == 60.0
    assert target.hit_min_horizon_days == 2
    assert target.hit_max_horizon_days is None
    assert target.validation_notice == "stored_window_only"


def test_backtest_observation_marks_target_progress_caution_when_baseline_is_above_target(tmp_path) -> None:
    repository = _repository(tmp_path)
    baseline_date = date(2026, 5, 4)
    business_date = date(2026, 5, 8)
    repository.insert_reports(
        [
            _report(source_id="baseline", business_date=baseline_date, target_price_value=90_000),
            _report(source_id="current-1", business_date=business_date, target_price_value=90_000),
            _report(source_id="current-2", broker_name="KB증권", business_date=business_date, target_price_value=95_000),
        ]
    )
    repository.rebuild_daily_summaries(baseline_date)
    repository.rebuild_daily_summaries(business_date)
    repository.upsert_stock_market_daily(
        [
            _stock_market(baseline_date, close_price=100_000),
            _stock_market(business_date, close_price=80_000),
            _stock_market(date(2026, 5, 11), close_price=82_000),
        ]
    )

    rows = build_backtest_observation_rows(
        repository,
        business_date=business_date,
        mention_threshold=2,
        horizons=(1,),
    )

    target = rows[0].target_observation
    assert target.available is True
    assert target.progress_available is True
    assert target.progress_caution is True
    assert target.progress_notice == "baseline_above_target_range"


def test_backtest_observation_attaches_same_date_flow_turnover_and_net_buy_top_only(tmp_path) -> None:
    repository = _repository(tmp_path)
    business_date = date(2026, 5, 8)
    repository.insert_reports(
        [
            _report(source_id="1", business_date=business_date),
            _report(source_id="2", broker_name="KB증권", business_date=business_date),
        ]
    )
    repository.rebuild_daily_summaries(business_date)
    repository.upsert_stock_market_daily(
        [
            _stock_market(business_date, close_price=100_000, turnover=9_000_000, volume=1_000),
            _stock_market(date(2026, 5, 11), close_price=101_000, turnover=10_000_000, volume=2_000),
        ]
    )
    repository.upsert_stock_investor_flow_daily(
        [
            StockInvestorFlowDaily(
                business_date=business_date,
                stock_code="005930",
                stock_name="삼성전자",
                market="KOSPI",
                investor_type="개인",
                net_buy_volume=-100,
                net_buy_amount=-1_000,
                fetched_at=datetime(2026, 5, 13, 8, 10, 0),
            ),
            StockInvestorFlowDaily(
                business_date=business_date,
                stock_code="005930",
                stock_name="삼성전자",
                market="KOSPI",
                investor_type="외국인",
                net_buy_volume=70,
                net_buy_amount=700,
                fetched_at=datetime(2026, 5, 13, 8, 10, 0),
            ),
            StockInvestorFlowDaily(
                business_date=business_date,
                stock_code="005930",
                stock_name="삼성전자",
                market="KOSPI",
                investor_type="기관합계",
                net_buy_volume=30,
                net_buy_amount=300,
                fetched_at=datetime(2026, 5, 13, 8, 10, 0),
            ),
        ]
    )
    repository.upsert_investor_net_buy_top_daily(
        [
            InvestorNetBuyTopDaily(
                business_date=business_date,
                market="KOSPI",
                investor_type="foreign",
                rank=3,
                stock_code="005930",
                stock_name="삼성전자",
                net_buy_volume=70,
                net_buy_amount=700,
                fetched_at=datetime(2026, 5, 13, 8, 10, 0),
            ),
            InvestorNetBuyTopDaily(
                business_date=date(2026, 5, 11),
                market="KOSPI",
                investor_type="foreign",
                rank=1,
                stock_code="005930",
                stock_name="삼성전자",
                net_buy_volume=999,
                net_buy_amount=999,
                fetched_at=datetime(2026, 5, 13, 8, 10, 0),
            ),
        ]
    )

    rows = build_backtest_observation_rows(
        repository,
        business_date=business_date,
        mention_threshold=2,
        horizons=(1,),
    )

    row = rows[0]
    assert row.base_market.turnover == 9_000_000
    assert row.stock_flow_observation.available is True
    assert row.stock_flow_observation.individual_net_buy_volume == -100
    assert row.stock_flow_observation.foreign_net_buy_volume == 70
    assert row.stock_flow_observation.institution_net_buy_volume == 30
    assert row.net_buy_top_observation.available is True
    assert row.net_buy_top_observation.foreign_top_rank == 3
    assert row.net_buy_top_observation.net_buy_amount == 700
    assert row.reaction_windows[0].horizon_turnover == 10_000_000


def test_feature_availability_audit_counts_candidate_feature_coverage(tmp_path) -> None:
    repository = _repository(tmp_path)
    first_date = date(2026, 5, 4)
    second_date = date(2026, 5, 8)
    repository.insert_reports(
        [
            _report(source_id="a1", business_date=first_date, target_price_value=150_000),
            _report(source_id="a2", broker_name="KB증권", business_date=first_date, target_price_value=160_000),
            _report(source_id="b1", stock_name="SK텔레콤", stock_code="017670", business_date=second_date, target_price_value=None),
            _report(source_id="b2", stock_name="SK텔레콤", stock_code="017670", broker_name="KB증권", business_date=second_date, target_price_value=None),
        ]
    )
    repository.rebuild_daily_summaries(first_date)
    repository.rebuild_daily_summaries(second_date)
    repository.upsert_stock_market_daily(
        [
            _stock_market(first_date, close_price=100_000, turnover=1_000),
            _stock_market(date(2026, 5, 6), close_price=110_000, turnover=2_000),
            _stock_market(second_date, stock_code="017670", stock_name="SK텔레콤", close_price=50_000, turnover=3_000),
        ]
    )
    repository.upsert_stock_investor_flow_daily(
        [
            StockInvestorFlowDaily(
                business_date=first_date,
                stock_code="005930",
                stock_name="삼성전자",
                investor_type="외국인",
                net_buy_volume=10,
                net_buy_amount=20,
                fetched_at=datetime(2026, 5, 13, 8, 10, 0),
            )
        ]
    )
    repository.upsert_investor_net_buy_top_daily(
        [
            InvestorNetBuyTopDaily(
                business_date=first_date,
                market="KOSPI",
                investor_type="foreign",
                rank=7,
                stock_code="005930",
                stock_name="삼성전자",
                fetched_at=datetime(2026, 5, 13, 8, 10, 0),
            )
        ]
    )

    audit = build_feature_availability_audit(
        repository,
        from_date=first_date,
        to_date=second_date,
        mention_threshold=2,
        horizons=(1, 5),
    )

    assert audit.from_date == first_date
    assert audit.to_date == second_date
    assert audit.mention_threshold == 2
    assert audit.candidate_count == 2
    assert audit.feature_counts["base_market"] == 2
    assert audit.feature_counts["target_observation"] == 1
    assert audit.feature_counts["stock_flow"] == 1
    assert audit.feature_counts["foreign_net_buy_top"] == 1
    assert audit.reaction_counts[1] == 1
    assert audit.reaction_counts[5] == 0
    assert audit.rows_by_date == {"2026-05-04": 1, "2026-05-08": 1}


def test_reaction_distribution_audit_groups_by_mention_target_and_flow(tmp_path) -> None:
    repository = _repository(tmp_path)
    business_date = date(2026, 5, 4)
    repository.insert_reports(
        [
            _report(source_id="a1", business_date=business_date, target_price_value=90_000),
            _report(source_id="a2", broker_name="KB증권", business_date=business_date, target_price_value=95_000),
            _report(source_id="b1", stock_name="SK텔레콤", stock_code="017670", business_date=business_date, target_price_value=None),
            _report(source_id="b2", stock_name="SK텔레콤", stock_code="017670", broker_name="KB증권", business_date=business_date, target_price_value=None),
            _report(source_id="b3", stock_name="SK텔레콤", stock_code="017670", broker_name="하나증권", business_date=business_date, target_price_value=None),
        ]
    )
    repository.rebuild_daily_summaries(business_date)
    repository.upsert_stock_market_daily(
        [
            _stock_market(business_date, close_price=100_000),
            _stock_market(date(2026, 5, 6), close_price=110_000),
            _stock_market(business_date, stock_code="017670", stock_name="SK텔레콤", close_price=50_000),
            _stock_market(date(2026, 5, 6), stock_code="017670", stock_name="SK텔레콤", close_price=45_000),
        ]
    )
    repository.upsert_stock_investor_flow_daily(
        [
            StockInvestorFlowDaily(
                business_date=business_date,
                stock_code="005930",
                stock_name="삼성전자",
                investor_type="외국인",
                net_buy_volume=10,
                net_buy_amount=20,
                fetched_at=datetime(2026, 5, 13, 8, 10, 0),
            )
        ]
    )

    audit = build_reaction_distribution_audit(
        repository,
        from_date=business_date,
        to_date=business_date,
        mention_threshold=2,
        horizons=(1,),
    )

    groups = {
        (group.mention_bucket, group.target_available, group.stock_flow_available, group.horizon_days): group
        for group in audit.groups
    }
    target_flow_group = groups[("2", True, True, 1)]
    assert target_flow_group.candidate_count == 1
    assert target_flow_group.available_count == 1
    assert target_flow_group.rising_count == 1
    assert target_flow_group.falling_count == 0
    assert target_flow_group.average_return_percent == 10.0

    no_target_no_flow_group = groups[("3", False, False, 1)]
    assert no_target_no_flow_group.candidate_count == 1
    assert no_target_no_flow_group.available_count == 1
    assert no_target_no_flow_group.rising_count == 0
    assert no_target_no_flow_group.falling_count == 1
    assert no_target_no_flow_group.average_return_percent == -10.0


def test_feature_comparison_audit_compares_independent_features(tmp_path) -> None:
    repository = _repository(tmp_path)
    business_date = date(2026, 5, 4)
    repository.insert_reports(
        [
            _report(source_id="a1", business_date=business_date, target_price_value=90_000),
            _report(source_id="a2", broker_name="KB증권", business_date=business_date, target_price_value=95_000),
            _report(source_id="b1", stock_name="SK텔레콤", stock_code="017670", business_date=business_date, target_price_value=None),
            _report(source_id="b2", stock_name="SK텔레콤", stock_code="017670", broker_name="KB증권", business_date=business_date, target_price_value=None),
        ]
    )
    repository.rebuild_daily_summaries(business_date)
    repository.upsert_stock_market_daily(
        [
            _stock_market(business_date, close_price=100_000),
            _stock_market(date(2026, 5, 6), close_price=110_000),
            _stock_market(business_date, stock_code="017670", stock_name="SK텔레콤", close_price=50_000),
            _stock_market(date(2026, 5, 6), stock_code="017670", stock_name="SK텔레콤", close_price=45_000),
        ]
    )
    repository.upsert_stock_investor_flow_daily(
        [
            StockInvestorFlowDaily(
                business_date=business_date,
                stock_code="005930",
                stock_name="삼성전자",
                investor_type="외국인",
                net_buy_volume=10,
                net_buy_amount=20,
                fetched_at=datetime(2026, 5, 13, 8, 10, 0),
            )
        ]
    )

    audit = build_feature_comparison_audit(
        repository,
        from_date=business_date,
        to_date=business_date,
        mention_threshold=2,
        horizons=(1,),
    )

    groups = {
        (group.feature_name, group.feature_value, group.horizon_days): group
        for group in audit.groups
    }
    assert groups[("target_available", "yes", 1)].average_return_percent == 10.0
    assert groups[("target_available", "no", 1)].average_return_percent == -10.0
    assert groups[("stock_flow_available", "yes", 1)].rising_count == 1
    assert groups[("stock_flow_available", "no", 1)].falling_count == 1
    assert groups[("mention_bucket", "2", 1)].candidate_count == 2


def test_weight_draft_audit_proposes_internal_weights_from_feature_deltas(tmp_path) -> None:
    repository = _repository(tmp_path)
    business_date = date(2026, 5, 4)
    repository.insert_reports(
        [
            _report(source_id="a1", business_date=business_date, target_price_value=150_000),
            _report(source_id="a2", broker_name="KB증권", business_date=business_date, target_price_value=160_000),
            _report(source_id="b1", stock_name="SK텔레콤", stock_code="017670", business_date=business_date, target_price_value=None),
            _report(source_id="b2", stock_name="SK텔레콤", stock_code="017670", broker_name="KB증권", business_date=business_date, target_price_value=None),
        ]
    )
    repository.rebuild_daily_summaries(business_date)
    repository.upsert_stock_market_daily(
        [
            _stock_market(business_date, close_price=100_000),
            _stock_market(date(2026, 5, 6), close_price=110_000),
            _stock_market(business_date, stock_code="017670", stock_name="SK텔레콤", close_price=50_000),
            _stock_market(date(2026, 5, 6), stock_code="017670", stock_name="SK텔레콤", close_price=45_000),
        ]
    )

    audit = build_weight_draft_audit(
        repository,
        from_date=business_date,
        to_date=business_date,
        mention_threshold=2,
        horizons=(1,),
        min_sample_size=1,
    )

    proposals = {
        (proposal.feature_name, proposal.feature_value, proposal.horizon_days): proposal
        for proposal in audit.proposals
    }
    target_yes = proposals[("target_available", "yes", 1)]
    target_no = proposals[("target_available", "no", 1)]
    assert target_yes.direction == "positive"
    assert target_yes.draft_weight > 0
    assert target_no.direction == "unknown"
    assert target_no.draft_weight == 0
    assert target_no.caution == "missing_is_unknown"
    assert audit.internal_only is True
    assert audit.no_public_decision is True


def test_weight_draft_audit_keeps_missing_and_caution_features_at_zero_weight(tmp_path) -> None:
    repository = _repository(tmp_path)
    business_date = date(2026, 5, 4)
    repository.insert_reports(
        [
            _report(source_id="a1", business_date=business_date, target_price_value=90_000),
            _report(source_id="a2", broker_name="KB증권", business_date=business_date, target_price_value=95_000),
            _report(source_id="b1", stock_name="SK텔레콤", stock_code="017670", business_date=business_date, target_price_value=None),
            _report(source_id="b2", stock_name="SK텔레콤", stock_code="017670", broker_name="KB증권", business_date=business_date, target_price_value=None),
        ]
    )
    repository.rebuild_daily_summaries(business_date)
    repository.upsert_stock_market_daily(
        [
            _stock_market(business_date, close_price=100_000),
            _stock_market(date(2026, 5, 6), close_price=110_000),
            _stock_market(business_date, stock_code="017670", stock_name="SK텔레콤", close_price=50_000),
            _stock_market(date(2026, 5, 6), stock_code="017670", stock_name="SK텔레콤", close_price=45_000),
        ]
    )

    audit = build_weight_draft_audit(
        repository,
        from_date=business_date,
        to_date=business_date,
        mention_threshold=2,
        horizons=(1,),
        min_sample_size=1,
    )

    proposals = {
        (proposal.feature_name, proposal.feature_value, proposal.horizon_days): proposal
        for proposal in audit.proposals
    }
    for key in (
        ("target_available", "no", 1),
        ("stock_flow_available", "no", 1),
        ("target_progress_caution", "yes", 1),
    ):
        proposal = proposals[key]
        assert proposal.draft_weight == 0
        assert proposal.direction in {"unknown", "separate_review"}
        assert proposal.caution in {"missing_is_unknown", "caution_separate_review"}


def test_weight_draft_audit_marks_small_samples_as_zero_weight(tmp_path) -> None:
    repository = _repository(tmp_path)
    business_date = date(2026, 5, 4)
    repository.insert_reports(
        [
            _report(source_id="a1", business_date=business_date, target_price_value=150_000),
            _report(source_id="a2", broker_name="KB증권", business_date=business_date, target_price_value=160_000),
        ]
    )
    repository.rebuild_daily_summaries(business_date)
    repository.upsert_stock_market_daily(
        [
            _stock_market(business_date, close_price=100_000),
            _stock_market(date(2026, 5, 6), close_price=110_000),
        ]
    )

    audit = build_weight_draft_audit(
        repository,
        from_date=business_date,
        to_date=business_date,
        mention_threshold=2,
        horizons=(1,),
        min_sample_size=2,
    )

    target_yes = next(
        proposal
        for proposal in audit.proposals
        if proposal.feature_name == "target_available" and proposal.feature_value == "yes"
    )
    assert target_yes.draft_weight == 0
    assert target_yes.direction == "insufficient"
    assert target_yes.caution == "sample_too_small"


def test_hidden_score_prototype_applies_internal_weights_without_ranking(tmp_path) -> None:
    repository = _repository(tmp_path)
    business_date = date(2026, 5, 4)
    repository.insert_reports(
        [
            _report(source_id="a1", business_date=business_date, target_price_value=150_000),
            _report(source_id="a2", broker_name="KB증권", business_date=business_date, target_price_value=160_000),
            _report(source_id="b1", stock_name="SK텔레콤", stock_code="017670", business_date=business_date, target_price_value=None),
            _report(source_id="b2", stock_name="SK텔레콤", stock_code="017670", broker_name="KB증권", business_date=business_date, target_price_value=None),
        ]
    )
    repository.rebuild_daily_summaries(business_date)
    repository.upsert_stock_market_daily(
        [
            _stock_market(business_date, close_price=100_000),
            _stock_market(date(2026, 5, 6), close_price=110_000),
            _stock_market(business_date, stock_code="017670", stock_name="SK텔레콤", close_price=50_000),
            _stock_market(date(2026, 5, 6), stock_code="017670", stock_name="SK텔레콤", close_price=45_000),
        ]
    )

    prototype = build_hidden_score_prototype(
        repository,
        from_date=business_date,
        to_date=business_date,
        mention_threshold=2,
        horizon_days=1,
        min_sample_size=1,
    )

    assert prototype.internal_only is True
    assert prototype.no_public_decision is True
    assert prototype.horizon_days == 1
    assert [row.stock_code for row in prototype.rows] == ["005930", "017670"]
    assert prototype.rows[0].prototype_value > prototype.rows[1].prototype_value
    assert prototype.rows[0].components
    assert prototype.rows[0].rank is None


def test_hidden_score_prototype_separates_training_and_apply_ranges(tmp_path) -> None:
    repository = _repository(tmp_path)
    train_date = date(2026, 5, 4)
    apply_date = date(2026, 5, 8)
    repository.insert_reports(
        [
            _report(source_id="train-a1", business_date=train_date, target_price_value=150_000),
            _report(source_id="train-a2", broker_name="KB증권", business_date=train_date, target_price_value=160_000),
            _report(source_id="train-b1", stock_name="SK텔레콤", stock_code="017670", business_date=train_date, target_price_value=None),
            _report(source_id="train-b2", stock_name="SK텔레콤", stock_code="017670", broker_name="KB증권", business_date=train_date, target_price_value=None),
            _report(source_id="apply-a1", business_date=apply_date, target_price_value=150_000),
            _report(source_id="apply-a2", broker_name="KB증권", business_date=apply_date, target_price_value=160_000),
        ]
    )
    repository.rebuild_daily_summaries(train_date)
    repository.rebuild_daily_summaries(apply_date)
    repository.upsert_stock_market_daily(
        [
            _stock_market(train_date, close_price=100_000),
            _stock_market(date(2026, 5, 6), close_price=110_000),
            _stock_market(train_date, stock_code="017670", stock_name="SK텔레콤", close_price=50_000),
            _stock_market(date(2026, 5, 6), stock_code="017670", stock_name="SK텔레콤", close_price=45_000),
            _stock_market(apply_date, close_price=120_000),
        ]
    )

    prototype = build_hidden_score_prototype(
        repository,
        train_from_date=train_date,
        train_to_date=train_date,
        from_date=apply_date,
        to_date=apply_date,
        mention_threshold=2,
        horizon_days=1,
        min_sample_size=1,
    )

    assert prototype.train_from_date == train_date
    assert prototype.train_to_date == train_date
    assert [row.business_date for row in prototype.rows] == [apply_date]
    assert prototype.rows[0].stock_code == "005930"
    assert prototype.rows[0].prototype_value > 0


def test_hidden_score_prototype_prunes_excluded_features(tmp_path) -> None:
    repository = _repository(tmp_path)
    business_date = date(2026, 5, 4)
    repository.insert_reports(
        [
            _report(source_id="a1", business_date=business_date, target_price_value=150_000),
            _report(source_id="a2", broker_name="KB증권", business_date=business_date, target_price_value=160_000),
        ]
    )
    repository.rebuild_daily_summaries(business_date)
    repository.upsert_stock_market_daily(
        [
            _stock_market(business_date, close_price=100_000),
            _stock_market(date(2026, 5, 6), close_price=110_000),
        ]
    )

    prototype = build_hidden_score_prototype(
        repository,
        from_date=business_date,
        to_date=business_date,
        mention_threshold=2,
        horizon_days=1,
        min_sample_size=1,
        excluded_features=("target_available", "base_turnover_available"),
    )

    assert prototype.excluded_features == ("target_available", "base_turnover_available")
    assert prototype.rows
    assert {
        component.feature_name
        for row in prototype.rows
        for component in row.components
    }.isdisjoint({"target_available", "base_turnover_available"})


def test_hidden_score_holdout_validation_groups_internal_values_against_reactions(tmp_path) -> None:
    repository = _repository(tmp_path)
    train_date = date(2026, 5, 4)
    holdout_date = date(2026, 5, 8)
    repository.insert_reports(
        [
            _report(source_id="train-a1", business_date=train_date, target_price_value=150_000),
            _report(source_id="train-a2", broker_name="KB증권", business_date=train_date, target_price_value=160_000),
            _report(source_id="train-b1", stock_name="SK텔레콤", stock_code="017670", business_date=train_date, target_price_value=None),
            _report(source_id="train-b2", stock_name="SK텔레콤", stock_code="017670", broker_name="KB증권", business_date=train_date, target_price_value=None),
            _report(source_id="holdout-a1", business_date=holdout_date, target_price_value=155_000),
            _report(source_id="holdout-a2", broker_name="KB증권", business_date=holdout_date, target_price_value=165_000),
        ]
    )
    repository.rebuild_daily_summaries(train_date)
    repository.rebuild_daily_summaries(holdout_date)
    repository.upsert_stock_market_daily(
        [
            _stock_market(train_date, close_price=100_000),
            _stock_market(date(2026, 5, 6), close_price=110_000),
            _stock_market(train_date, stock_code="017670", stock_name="SK텔레콤", close_price=50_000),
            _stock_market(date(2026, 5, 6), stock_code="017670", stock_name="SK텔레콤", close_price=45_000),
            _stock_market(holdout_date, close_price=120_000),
            _stock_market(date(2026, 5, 11), close_price=126_000),
        ]
    )

    validation = build_hidden_score_holdout_validation(
        repository,
        train_from_date=train_date,
        train_to_date=train_date,
        holdout_from_date=holdout_date,
        holdout_to_date=holdout_date,
        mention_threshold=2,
        horizon_days=1,
        min_sample_size=1,
    )

    assert validation.internal_only is True
    assert validation.no_public_decision is True
    assert validation.candidate_count == 1
    assert validation.available_count == 1
    assert validation.scoring is False
    assert validation.recommendation is False
    assert [bucket.bucket_name for bucket in validation.buckets] == ["positive"]
    assert validation.buckets[0].average_return_percent == 5.0
    assert validation.buckets[0].prototype_value_min > 0
    assert validation.buckets[0].prototype_value_max > 0


def test_hidden_score_holdout_sweep_runs_multiple_windows_and_horizons(tmp_path) -> None:
    repository = _repository(tmp_path)
    train_date = date(2026, 5, 4)
    holdout_a = date(2026, 5, 8)
    holdout_b = date(2026, 5, 12)
    repository.insert_reports(
        [
            _report(source_id="train-a1", business_date=train_date, target_price_value=150_000),
            _report(source_id="train-a2", broker_name="KB증권", business_date=train_date, target_price_value=160_000),
            _report(source_id="holdout-a1", business_date=holdout_a, target_price_value=155_000),
            _report(source_id="holdout-a2", broker_name="KB증권", business_date=holdout_a, target_price_value=165_000),
            _report(source_id="holdout-b1", business_date=holdout_b, target_price_value=155_000),
            _report(source_id="holdout-b2", broker_name="KB증권", business_date=holdout_b, target_price_value=165_000),
        ]
    )
    for business_date in (train_date, holdout_a, holdout_b):
        repository.rebuild_daily_summaries(business_date)
    repository.upsert_stock_market_daily(
        [
            _stock_market(train_date, close_price=100_000),
            _stock_market(date(2026, 5, 6), close_price=110_000),
            _stock_market(holdout_a, close_price=120_000),
            _stock_market(date(2026, 5, 11), close_price=126_000),
            _stock_market(holdout_b, close_price=130_000),
            _stock_market(date(2026, 5, 13), close_price=131_300),
        ]
    )

    sweep = build_hidden_score_holdout_sweep(
        repository,
        train_from_date=train_date,
        train_to_date=train_date,
        holdout_from_date=holdout_a,
        holdout_to_date=holdout_b,
        mention_threshold=2,
        horizon_days=(1, 5),
        min_sample_size=1,
        window_days=3,
        excluded_features=("target_progress_caution",),
    )

    assert sweep.internal_only is True
    assert sweep.no_public_decision is True
    assert sweep.scoring is False
    assert sweep.recommendation is False
    assert sweep.excluded_features == ("target_progress_caution",)
    assert {(item.holdout_from_date, item.horizon_days) for item in sweep.validations} == {
        (holdout_a, 1),
        (holdout_a, 5),
        (date(2026, 5, 11), 1),
        (date(2026, 5, 11), 5),
    }
