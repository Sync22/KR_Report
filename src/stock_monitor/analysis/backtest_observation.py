from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from stock_monitor.db.repository import StockMonitorRepository
from stock_monitor.models import (
    DailyStockSummary,
    InvestorNetBuyTopDaily,
    StockInvestorFlowDaily,
    StockMarketDailySnapshot,
)

COMPARISON_FEATURE_NAMES = (
    "mention_bucket",
    "target_available",
    "target_progress_caution",
    "stock_flow_available",
    "foreign_net_buy_top",
    "base_turnover_available",
)


@dataclass(frozen=True)
class ReactionWindow:
    horizon_days: int
    available: bool
    horizon_date: date | None
    base_close_price: int | None
    horizon_close_price: int | None
    close_return_percent: float | None
    horizon_volume: int | None
    horizon_turnover: int | None
    unavailable_reason: str | None = None


@dataclass(frozen=True)
class TargetObservation:
    available: bool
    gap_available: bool
    progress_available: bool
    validation_available: bool = False
    baseline_date: date | None = None
    baseline_price: int | None = None
    current_date: date | None = None
    current_price: int | None = None
    target_price_min: int | None = None
    target_price_max: int | None = None
    target_gap_min_percent: float | None = None
    target_gap_max_percent: float | None = None
    progress_to_min_percent: float | None = None
    progress_to_max_percent: float | None = None
    progress_caution: bool = False
    progress_notice: str | None = None
    validation_window_days: int | None = None
    max_progress_to_min_percent: float | None = None
    max_progress_to_max_percent: float | None = None
    hit_min_horizon_days: int | None = None
    hit_max_horizon_days: int | None = None
    validation_notice: str | None = None
    unavailable_reason: str | None = None


@dataclass(frozen=True)
class StockFlowObservation:
    available: bool
    individual_net_buy_volume: int | None = None
    foreign_net_buy_volume: int | None = None
    institution_net_buy_volume: int | None = None
    individual_net_buy_amount: int | None = None
    foreign_net_buy_amount: int | None = None
    institution_net_buy_amount: int | None = None
    investor_types: tuple[str, ...] = ()


@dataclass(frozen=True)
class NetBuyTopObservation:
    available: bool
    foreign_top_rank: int | None = None
    market: str | None = None
    net_buy_volume: int | None = None
    net_buy_amount: int | None = None


@dataclass(frozen=True)
class BacktestObservationRow:
    summary: DailyStockSummary
    base_market: StockMarketDailySnapshot | None
    reaction_windows: tuple[ReactionWindow, ...]
    target_observation: TargetObservation
    stock_flow_observation: StockFlowObservation
    net_buy_top_observation: NetBuyTopObservation


@dataclass(frozen=True)
class FeatureAvailabilityAudit:
    from_date: date
    to_date: date
    mention_threshold: int
    candidate_count: int
    feature_counts: dict[str, int]
    reaction_counts: dict[int, int]
    rows_by_date: dict[str, int]


@dataclass(frozen=True)
class ReactionDistributionGroup:
    mention_bucket: str
    target_available: bool
    stock_flow_available: bool
    horizon_days: int
    candidate_count: int
    available_count: int
    rising_count: int
    falling_count: int
    flat_count: int
    missing_count: int
    average_return_percent: float | None
    min_return_percent: float | None
    max_return_percent: float | None


@dataclass(frozen=True)
class ReactionDistributionAudit:
    from_date: date
    to_date: date
    mention_threshold: int
    candidate_count: int
    groups: tuple[ReactionDistributionGroup, ...]


@dataclass(frozen=True)
class FeatureComparisonGroup:
    feature_name: str
    feature_value: str
    horizon_days: int
    candidate_count: int
    available_count: int
    rising_count: int
    falling_count: int
    flat_count: int
    missing_count: int
    average_return_percent: float | None
    min_return_percent: float | None
    max_return_percent: float | None


@dataclass(frozen=True)
class FeatureComparisonAudit:
    from_date: date
    to_date: date
    mention_threshold: int
    candidate_count: int
    groups: tuple[FeatureComparisonGroup, ...]


@dataclass(frozen=True)
class WeightDraftProposal:
    feature_name: str
    feature_value: str
    horizon_days: int
    sample_size: int
    baseline_average_return_percent: float | None
    feature_average_return_percent: float | None
    delta_return_percent: float | None
    coverage_ratio: float
    direction: str
    draft_weight: int
    caution: str | None = None


@dataclass(frozen=True)
class WeightDraftAudit:
    from_date: date
    to_date: date
    mention_threshold: int
    min_sample_size: int
    internal_only: bool
    no_public_decision: bool
    proposals: tuple[WeightDraftProposal, ...]


@dataclass(frozen=True)
class HiddenScoreComponent:
    feature_name: str
    feature_value: str
    draft_weight: int
    direction: str
    caution: str | None = None


@dataclass(frozen=True)
class HiddenScorePrototypeRow:
    business_date: date
    stock_code: str
    stock_name: str
    mention_count: int
    horizon_days: int
    prototype_value: int
    rank: None
    components: tuple[HiddenScoreComponent, ...]


@dataclass(frozen=True)
class HiddenScorePrototype:
    train_from_date: date
    train_to_date: date
    from_date: date
    to_date: date
    mention_threshold: int
    horizon_days: int
    internal_only: bool
    no_public_decision: bool
    excluded_features: tuple[str, ...]
    rows: tuple[HiddenScorePrototypeRow, ...]


@dataclass(frozen=True)
class HiddenScoreHoldoutBucket:
    bucket_name: str
    candidate_count: int
    available_count: int
    rising_count: int
    falling_count: int
    flat_count: int
    missing_count: int
    average_return_percent: float | None
    prototype_value_min: int | None
    prototype_value_max: int | None


@dataclass(frozen=True)
class HiddenScoreHoldoutValidation:
    train_from_date: date
    train_to_date: date
    holdout_from_date: date
    holdout_to_date: date
    mention_threshold: int
    horizon_days: int
    min_sample_size: int
    candidate_count: int
    available_count: int
    internal_only: bool
    no_public_decision: bool
    scoring: bool
    recommendation: bool
    excluded_features: tuple[str, ...]
    buckets: tuple[HiddenScoreHoldoutBucket, ...]


@dataclass(frozen=True)
class HiddenScoreHoldoutSweep:
    train_from_date: date
    train_to_date: date
    holdout_from_date: date
    holdout_to_date: date
    mention_threshold: int
    horizon_days: tuple[int, ...]
    min_sample_size: int
    window_days: int
    internal_only: bool
    no_public_decision: bool
    scoring: bool
    recommendation: bool
    excluded_features: tuple[str, ...]
    validations: tuple[HiddenScoreHoldoutValidation, ...]


def build_backtest_observation_rows(
    repository: StockMonitorRepository,
    *,
    business_date: date,
    mention_threshold: int = 2,
    horizons: tuple[int, ...] = (1, 5, 10, 20),
) -> list[BacktestObservationRow]:
    summaries = repository.list_daily_summaries_for_backtest_observation(
        business_date,
        min_mention_count=mention_threshold,
    )
    stock_codes = [summary.stock_code for summary in summaries if summary.stock_code]
    base_markets = {
        item.stock_code: item
        for item in repository.list_stock_market_daily_for_codes(business_date, stock_codes)
    }

    rows: list[BacktestObservationRow] = []
    for summary in summaries:
        stock_code = summary.stock_code or ""
        base_market = base_markets.get(stock_code)
        market_series = repository.list_stock_market_daily_for_code_on_or_after(
            business_date,
            stock_code,
            limit=(max(horizons) + 1 if horizons else 1),
        )
        flow_rows = repository.list_stock_investor_flow_daily(business_date, stock_code)
        foreign_top = repository.find_investor_net_buy_top_for_stock(
            business_date,
            stock_code,
            "foreign",
        )
        rows.append(
            BacktestObservationRow(
                summary=summary,
                base_market=base_market,
                reaction_windows=tuple(
                    _build_reaction_window(
                        horizon,
                        base_market=base_market,
                        market_series=market_series,
                    )
                    for horizon in horizons
                ),
                target_observation=_build_target_observation(repository, summary, base_market, market_series),
                stock_flow_observation=_build_stock_flow_observation(flow_rows),
                net_buy_top_observation=_build_net_buy_top_observation(foreign_top),
            )
        )
    return rows


def build_feature_availability_audit(
    repository: StockMonitorRepository,
    *,
    from_date: date,
    to_date: date,
    mention_threshold: int = 2,
    horizons: tuple[int, ...] = (1, 5, 10, 20),
) -> FeatureAvailabilityAudit:
    candidate_rows: list[BacktestObservationRow] = []
    rows_by_date: dict[str, int] = {}
    for business_date in _list_backtest_candidate_dates(
        repository,
        from_date=from_date,
        to_date=to_date,
        mention_threshold=mention_threshold,
    ):
        rows = build_backtest_observation_rows(
            repository,
            business_date=business_date,
            mention_threshold=mention_threshold,
            horizons=horizons,
        )
        if rows:
            rows_by_date[business_date.isoformat()] = len(rows)
            candidate_rows.extend(rows)

    feature_counts = {
        "base_market": sum(1 for row in candidate_rows if row.base_market is not None and row.base_market.close_price is not None),
        "target_observation": sum(1 for row in candidate_rows if row.target_observation.available),
        "target_progress_caution": sum(1 for row in candidate_rows if row.target_observation.progress_caution),
        "stock_flow": sum(1 for row in candidate_rows if row.stock_flow_observation.available),
        "foreign_net_buy_top": sum(1 for row in candidate_rows if row.net_buy_top_observation.available),
        "base_turnover": sum(1 for row in candidate_rows if row.base_market is not None and row.base_market.turnover is not None),
    }
    reaction_counts = {
        horizon: sum(
            1
            for row in candidate_rows
            for window in row.reaction_windows
            if window.horizon_days == horizon and window.available
        )
        for horizon in horizons
    }
    return FeatureAvailabilityAudit(
        from_date=from_date,
        to_date=to_date,
        mention_threshold=mention_threshold,
        candidate_count=len(candidate_rows),
        feature_counts=feature_counts,
        reaction_counts=reaction_counts,
        rows_by_date=rows_by_date,
    )


def build_reaction_distribution_audit(
    repository: StockMonitorRepository,
    *,
    from_date: date,
    to_date: date,
    mention_threshold: int = 2,
    horizons: tuple[int, ...] = (1, 5, 10, 20),
) -> ReactionDistributionAudit:
    candidate_rows: list[BacktestObservationRow] = []
    for business_date in _list_backtest_candidate_dates(
        repository,
        from_date=from_date,
        to_date=to_date,
        mention_threshold=mention_threshold,
    ):
        candidate_rows.extend(
            build_backtest_observation_rows(
                repository,
                business_date=business_date,
                mention_threshold=mention_threshold,
                horizons=horizons,
            )
        )

    grouped: dict[tuple[str, bool, bool, int], list[ReactionWindow]] = {}
    for row in candidate_rows:
        mention_bucket = _mention_bucket(row.summary.mention_count)
        target_available = row.target_observation.available
        flow_available = row.stock_flow_observation.available
        for window in row.reaction_windows:
            key = (mention_bucket, target_available, flow_available, window.horizon_days)
            grouped.setdefault(key, []).append(window)

    groups = []
    for key, windows in sorted(grouped.items(), key=lambda item: (item[0][3], item[0][0], item[0][1], item[0][2])):
        mention_bucket, target_available, flow_available, horizon_days = key
        returns = [
            window.close_return_percent
            for window in windows
            if window.available and window.close_return_percent is not None
        ]
        groups.append(
            ReactionDistributionGroup(
                mention_bucket=mention_bucket,
                target_available=target_available,
                stock_flow_available=flow_available,
                horizon_days=horizon_days,
                candidate_count=len(windows),
                available_count=len(returns),
                rising_count=sum(1 for value in returns if value > 0),
                falling_count=sum(1 for value in returns if value < 0),
                flat_count=sum(1 for value in returns if value == 0),
                missing_count=len(windows) - len(returns),
                average_return_percent=round(sum(returns) / len(returns), 2) if returns else None,
                min_return_percent=min(returns) if returns else None,
                max_return_percent=max(returns) if returns else None,
            )
        )

    return ReactionDistributionAudit(
        from_date=from_date,
        to_date=to_date,
        mention_threshold=mention_threshold,
        candidate_count=len(candidate_rows),
        groups=tuple(groups),
    )


def build_feature_comparison_audit(
    repository: StockMonitorRepository,
    *,
    from_date: date,
    to_date: date,
    mention_threshold: int = 2,
    horizons: tuple[int, ...] = (1, 5, 10, 20),
) -> FeatureComparisonAudit:
    candidate_rows: list[BacktestObservationRow] = []
    for business_date in _list_backtest_candidate_dates(
        repository,
        from_date=from_date,
        to_date=to_date,
        mention_threshold=mention_threshold,
    ):
        candidate_rows.extend(
            build_backtest_observation_rows(
                repository,
                business_date=business_date,
                mention_threshold=mention_threshold,
                horizons=horizons,
            )
        )

    grouped: dict[tuple[str, str, int], list[ReactionWindow]] = {}
    for row in candidate_rows:
        features = _comparison_features(row)
        for window in row.reaction_windows:
            for feature_name, feature_value in features:
                grouped.setdefault((feature_name, feature_value, window.horizon_days), []).append(window)

    groups = [
        _build_feature_comparison_group(feature_name, feature_value, horizon_days, windows)
        for (feature_name, feature_value, horizon_days), windows in sorted(
            grouped.items(),
            key=lambda item: (item[0][2], item[0][0], item[0][1]),
        )
    ]
    return FeatureComparisonAudit(
        from_date=from_date,
        to_date=to_date,
        mention_threshold=mention_threshold,
        candidate_count=len(candidate_rows),
        groups=tuple(groups),
    )


def build_hidden_score_prototype(
    repository: StockMonitorRepository,
    *,
    train_from_date: date | None = None,
    train_to_date: date | None = None,
    from_date: date,
    to_date: date,
    mention_threshold: int = 2,
    horizon_days: int = 20,
    min_sample_size: int = 20,
    excluded_features: tuple[str, ...] = (),
) -> HiddenScorePrototype:
    pruned_features = _normalize_excluded_features(excluded_features)
    effective_train_from_date = train_from_date or from_date
    effective_train_to_date = train_to_date or to_date
    weight_draft = build_weight_draft_audit(
        repository,
        from_date=effective_train_from_date,
        to_date=effective_train_to_date,
        mention_threshold=mention_threshold,
        horizons=(horizon_days,),
        min_sample_size=min_sample_size,
    )
    weights = {
        (proposal.feature_name, proposal.feature_value): proposal
        for proposal in weight_draft.proposals
        if proposal.horizon_days == horizon_days
        and proposal.feature_name not in pruned_features
    }
    rows: list[HiddenScorePrototypeRow] = []
    for business_date in _list_backtest_candidate_dates(
        repository,
        from_date=from_date,
        to_date=to_date,
        mention_threshold=mention_threshold,
    ):
        observation_rows = build_backtest_observation_rows(
            repository,
            business_date=business_date,
            mention_threshold=mention_threshold,
            horizons=(horizon_days,),
        )
        for row in observation_rows:
            components = []
            for feature_name, feature_value in _comparison_features(row):
                if feature_name in pruned_features:
                    continue
                proposal = weights.get((feature_name, feature_value))
                if proposal is None:
                    continue
                components.append(
                    HiddenScoreComponent(
                        feature_name=feature_name,
                        feature_value=feature_value,
                        draft_weight=proposal.draft_weight,
                        direction=proposal.direction,
                        caution=proposal.caution,
                    )
                )
            rows.append(
                HiddenScorePrototypeRow(
                    business_date=business_date,
                    stock_code=row.summary.stock_code or "",
                    stock_name=row.summary.stock_name,
                    mention_count=row.summary.mention_count,
                    horizon_days=horizon_days,
                    prototype_value=sum(component.draft_weight for component in components),
                    rank=None,
                    components=tuple(components),
                )
            )
    return HiddenScorePrototype(
        train_from_date=effective_train_from_date,
        train_to_date=effective_train_to_date,
        from_date=from_date,
        to_date=to_date,
        mention_threshold=mention_threshold,
        horizon_days=horizon_days,
        internal_only=True,
        no_public_decision=True,
        excluded_features=pruned_features,
        rows=tuple(sorted(rows, key=lambda item: (item.business_date, item.stock_code, item.stock_name))),
    )


def build_hidden_score_holdout_validation(
    repository: StockMonitorRepository,
    *,
    train_from_date: date,
    train_to_date: date,
    holdout_from_date: date,
    holdout_to_date: date,
    mention_threshold: int = 2,
    horizon_days: int = 20,
    min_sample_size: int = 20,
    excluded_features: tuple[str, ...] = (),
) -> HiddenScoreHoldoutValidation:
    _validate_holdout_ranges(train_from_date, train_to_date, holdout_from_date, holdout_to_date)
    pruned_features = _normalize_excluded_features(excluded_features)
    prototype = build_hidden_score_prototype(
        repository,
        train_from_date=train_from_date,
        train_to_date=train_to_date,
        from_date=holdout_from_date,
        to_date=holdout_to_date,
        mention_threshold=mention_threshold,
        horizon_days=horizon_days,
        min_sample_size=min_sample_size,
        excluded_features=pruned_features,
    )
    reaction_by_key: dict[tuple[date, str], ReactionWindow] = {}
    for business_date in _list_backtest_candidate_dates(
        repository,
        from_date=holdout_from_date,
        to_date=holdout_to_date,
        mention_threshold=mention_threshold,
    ):
        for row in build_backtest_observation_rows(
            repository,
            business_date=business_date,
            mention_threshold=mention_threshold,
            horizons=(horizon_days,),
        ):
            if not row.summary.stock_code:
                continue
            window = next(
                (item for item in row.reaction_windows if item.horizon_days == horizon_days),
                None,
            )
            if window is not None:
                reaction_by_key[(business_date, row.summary.stock_code)] = window

    grouped: dict[str, list[tuple[HiddenScorePrototypeRow, ReactionWindow | None]]] = {}
    for row in prototype.rows:
        key = _prototype_value_bucket(row.prototype_value)
        grouped.setdefault(key, []).append((row, reaction_by_key.get((row.business_date, row.stock_code))))

    buckets = tuple(
        _build_hidden_score_holdout_bucket(bucket_name, items)
        for bucket_name, items in sorted(grouped.items(), key=lambda item: _prototype_bucket_sort_key(item[0]))
    )
    return HiddenScoreHoldoutValidation(
        train_from_date=train_from_date,
        train_to_date=train_to_date,
        holdout_from_date=holdout_from_date,
        holdout_to_date=holdout_to_date,
        mention_threshold=mention_threshold,
        horizon_days=horizon_days,
        min_sample_size=min_sample_size,
        candidate_count=len(prototype.rows),
        available_count=sum(bucket.available_count for bucket in buckets),
        internal_only=True,
        no_public_decision=True,
        scoring=False,
        recommendation=False,
        excluded_features=pruned_features,
        buckets=buckets,
    )


def build_hidden_score_holdout_sweep(
    repository: StockMonitorRepository,
    *,
    train_from_date: date,
    train_to_date: date,
    holdout_from_date: date,
    holdout_to_date: date,
    mention_threshold: int = 2,
    horizon_days: tuple[int, ...] = (20,),
    min_sample_size: int = 20,
    window_days: int = 5,
    excluded_features: tuple[str, ...] = (),
) -> HiddenScoreHoldoutSweep:
    _validate_holdout_ranges(train_from_date, train_to_date, holdout_from_date, holdout_to_date)
    if window_days < 1:
        raise ValueError("window_days must be greater than or equal to 1")
    unique_horizons = tuple(dict.fromkeys(horizon_days))
    validations: list[HiddenScoreHoldoutValidation] = []
    window_start = holdout_from_date
    while window_start <= holdout_to_date:
        window_end = min(window_start + timedelta(days=window_days - 1), holdout_to_date)
        for horizon in unique_horizons:
            validations.append(
                build_hidden_score_holdout_validation(
                    repository,
                    train_from_date=train_from_date,
                    train_to_date=train_to_date,
                    holdout_from_date=window_start,
                    holdout_to_date=window_end,
                    mention_threshold=mention_threshold,
                    horizon_days=horizon,
                    min_sample_size=min_sample_size,
                    excluded_features=excluded_features,
                )
            )
        window_start = window_end + timedelta(days=1)
    return HiddenScoreHoldoutSweep(
        train_from_date=train_from_date,
        train_to_date=train_to_date,
        holdout_from_date=holdout_from_date,
        holdout_to_date=holdout_to_date,
        mention_threshold=mention_threshold,
        horizon_days=unique_horizons,
        min_sample_size=min_sample_size,
        window_days=window_days,
        internal_only=True,
        no_public_decision=True,
        scoring=False,
        recommendation=False,
        excluded_features=tuple(dict.fromkeys(excluded_features)),
        validations=tuple(validations),
    )


def build_weight_draft_audit(
    repository: StockMonitorRepository,
    *,
    from_date: date,
    to_date: date,
    mention_threshold: int = 2,
    horizons: tuple[int, ...] = (1, 5, 10, 20),
    min_sample_size: int = 20,
) -> WeightDraftAudit:
    comparison = build_feature_comparison_audit(
        repository,
        from_date=from_date,
        to_date=to_date,
        mention_threshold=mention_threshold,
        horizons=horizons,
    )
    baseline_by_horizon = _baseline_average_by_horizon(comparison.groups)
    proposals = []
    for group in comparison.groups:
        baseline_average = baseline_by_horizon.get(group.horizon_days)
        delta = (
            round(group.average_return_percent - baseline_average, 2)
            if group.average_return_percent is not None and baseline_average is not None
            else None
        )
        coverage_ratio = round(group.available_count / group.candidate_count, 4) if group.candidate_count else 0.0
        caution = _forced_weight_caution(group.feature_name, group.feature_value)
        if caution is None and group.available_count < min_sample_size:
            caution = "sample_too_small"
        elif caution is None and delta is None:
            caution = "missing_average"
        proposals.append(
            WeightDraftProposal(
                feature_name=group.feature_name,
                feature_value=group.feature_value,
                horizon_days=group.horizon_days,
                sample_size=group.available_count,
                baseline_average_return_percent=baseline_average,
                feature_average_return_percent=group.average_return_percent,
                delta_return_percent=delta,
                coverage_ratio=coverage_ratio,
                direction=_draft_direction(delta, caution),
                draft_weight=0 if caution else _draft_weight(delta),
                caution=caution,
            )
        )
    return WeightDraftAudit(
        from_date=from_date,
        to_date=to_date,
        mention_threshold=mention_threshold,
        min_sample_size=min_sample_size,
        internal_only=True,
        no_public_decision=True,
        proposals=tuple(proposals),
    )


def _list_backtest_candidate_dates(
    repository: StockMonitorRepository,
    *,
    from_date: date,
    to_date: date,
    mention_threshold: int,
) -> list[date]:
    with repository.connect() as connection:
        rows = connection.execute(
            """
            SELECT business_date
            FROM daily_stock_summaries
            WHERE business_date BETWEEN ? AND ?
              AND stock_code IS NOT NULL
              AND TRIM(stock_code) <> ''
              AND mention_count >= ?
            GROUP BY business_date
            ORDER BY business_date ASC
            """,
            (from_date.isoformat(), to_date.isoformat(), mention_threshold),
        ).fetchall()
    return [date.fromisoformat(row["business_date"]) for row in rows]


def _baseline_average_by_horizon(groups: tuple[FeatureComparisonGroup, ...]) -> dict[int, float]:
    weighted_returns: dict[int, tuple[float, int]] = {}
    for group in groups:
        if group.feature_name != "base_turnover_available":
            continue
        if group.feature_value != "yes":
            continue
        if group.average_return_percent is None or group.available_count <= 0:
            continue
        total, count = weighted_returns.get(group.horizon_days, (0.0, 0))
        weighted_returns[group.horizon_days] = (
            total + (group.average_return_percent * group.available_count),
            count + group.available_count,
        )
    return {
        horizon: round(total / count, 2)
        for horizon, (total, count) in weighted_returns.items()
        if count > 0
    }


def _draft_direction(delta: float | None, caution: str | None) -> str:
    if caution == "missing_is_unknown":
        return "unknown"
    if caution == "caution_separate_review":
        return "separate_review"
    if caution or delta is None:
        return "insufficient"
    if delta >= 1.0:
        return "positive"
    if delta <= -1.0:
        return "negative"
    return "neutral"


def _draft_weight(delta: float | None) -> int:
    if delta is None:
        return 0
    magnitude = abs(delta)
    if magnitude < 1.0:
        return 0
    if magnitude < 3.0:
        weight = 1
    elif magnitude < 7.0:
        weight = 2
    else:
        weight = 3
    return weight if delta > 0 else -weight


def _prototype_value_bucket(value: int) -> str:
    if value > 0:
        return "positive"
    if value < 0:
        return "negative"
    return "neutral"


def _normalize_excluded_features(excluded_features: tuple[str, ...]) -> tuple[str, ...]:
    normalized = tuple(dict.fromkeys(item.strip() for item in excluded_features if item and item.strip()))
    unknown = [item for item in normalized if item not in COMPARISON_FEATURE_NAMES]
    if unknown:
        allowed = ", ".join(COMPARISON_FEATURE_NAMES)
        raise ValueError(f"Unknown exclude feature: {', '.join(unknown)}. Allowed: {allowed}")
    return normalized


def _validate_holdout_ranges(
    train_from_date: date,
    train_to_date: date,
    holdout_from_date: date,
    holdout_to_date: date,
) -> None:
    if train_from_date > train_to_date:
        raise ValueError("train range start must be earlier than or equal to train range end")
    if holdout_from_date > holdout_to_date:
        raise ValueError("holdout range start must be earlier than or equal to holdout range end")
    if holdout_from_date <= train_to_date:
        raise ValueError("holdout range must start after train range")


def _prototype_bucket_sort_key(bucket_name: str) -> tuple[int, str]:
    order = {"positive": 0, "neutral": 1, "negative": 2}
    return (order.get(bucket_name, 99), bucket_name)


def _build_hidden_score_holdout_bucket(
    bucket_name: str,
    items: list[tuple[HiddenScorePrototypeRow, ReactionWindow | None]],
) -> HiddenScoreHoldoutBucket:
    returns = [
        window.close_return_percent
        for _row, window in items
        if window is not None and window.available and window.close_return_percent is not None
    ]
    prototype_values = [row.prototype_value for row, _window in items]
    return HiddenScoreHoldoutBucket(
        bucket_name=bucket_name,
        candidate_count=len(items),
        available_count=len(returns),
        rising_count=sum(1 for value in returns if value > 0),
        falling_count=sum(1 for value in returns if value < 0),
        flat_count=sum(1 for value in returns if value == 0),
        missing_count=len(items) - len(returns),
        average_return_percent=round(sum(returns) / len(returns), 2) if returns else None,
        prototype_value_min=min(prototype_values) if prototype_values else None,
        prototype_value_max=max(prototype_values) if prototype_values else None,
    )


def _forced_weight_caution(feature_name: str, feature_value: str) -> str | None:
    if feature_value == "no" and feature_name in {
        "target_available",
        "stock_flow_available",
        "base_turnover_available",
    }:
        return "missing_is_unknown"
    if feature_name == "target_progress_caution" and feature_value == "yes":
        return "caution_separate_review"
    return None


def _comparison_features(row: BacktestObservationRow) -> tuple[tuple[str, str], ...]:
    return (
        ("mention_bucket", _mention_bucket(row.summary.mention_count)),
        ("target_available", _yes_no(row.target_observation.available)),
        ("target_progress_caution", _yes_no(row.target_observation.progress_caution)),
        ("stock_flow_available", _yes_no(row.stock_flow_observation.available)),
        ("foreign_net_buy_top", _yes_no(row.net_buy_top_observation.available)),
        ("base_turnover_available", _yes_no(row.base_market is not None and row.base_market.turnover is not None)),
    )


def _build_feature_comparison_group(
    feature_name: str,
    feature_value: str,
    horizon_days: int,
    windows: list[ReactionWindow],
) -> FeatureComparisonGroup:
    returns = [
        window.close_return_percent
        for window in windows
        if window.available and window.close_return_percent is not None
    ]
    return FeatureComparisonGroup(
        feature_name=feature_name,
        feature_value=feature_value,
        horizon_days=horizon_days,
        candidate_count=len(windows),
        available_count=len(returns),
        rising_count=sum(1 for value in returns if value > 0),
        falling_count=sum(1 for value in returns if value < 0),
        flat_count=sum(1 for value in returns if value == 0),
        missing_count=len(windows) - len(returns),
        average_return_percent=round(sum(returns) / len(returns), 2) if returns else None,
        min_return_percent=min(returns) if returns else None,
        max_return_percent=max(returns) if returns else None,
    )


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


def _mention_bucket(mention_count: int) -> str:
    if mention_count <= 2:
        return "2"
    if mention_count == 3:
        return "3"
    return "4+"


def _build_reaction_window(
    horizon_days: int,
    *,
    base_market: StockMarketDailySnapshot | None,
    market_series: list[StockMarketDailySnapshot],
) -> ReactionWindow:
    if base_market is None:
        return ReactionWindow(
            horizon_days=horizon_days,
            available=False,
            horizon_date=None,
            base_close_price=None,
            horizon_close_price=None,
            close_return_percent=None,
            horizon_volume=None,
            horizon_turnover=None,
            unavailable_reason="missing_base_market",
        )
    if base_market.close_price is None:
        return ReactionWindow(
            horizon_days=horizon_days,
            available=False,
            horizon_date=None,
            base_close_price=None,
            horizon_close_price=None,
            close_return_percent=None,
            horizon_volume=None,
            horizon_turnover=None,
            unavailable_reason="missing_base_close_price",
        )
    if len(market_series) <= horizon_days:
        return ReactionWindow(
            horizon_days=horizon_days,
            available=False,
            horizon_date=None,
            base_close_price=base_market.close_price,
            horizon_close_price=None,
            close_return_percent=None,
            horizon_volume=None,
            horizon_turnover=None,
            unavailable_reason="missing_horizon_market",
        )

    horizon_market = market_series[horizon_days]
    if horizon_market.close_price is None:
        return ReactionWindow(
            horizon_days=horizon_days,
            available=False,
            horizon_date=horizon_market.business_date,
            base_close_price=base_market.close_price,
            horizon_close_price=None,
            close_return_percent=None,
            horizon_volume=horizon_market.volume,
            horizon_turnover=horizon_market.turnover,
            unavailable_reason="missing_horizon_close_price",
        )

    return ReactionWindow(
        horizon_days=horizon_days,
        available=True,
        horizon_date=horizon_market.business_date,
        base_close_price=base_market.close_price,
        horizon_close_price=horizon_market.close_price,
        close_return_percent=_percent(horizon_market.close_price - base_market.close_price, base_market.close_price),
        horizon_volume=horizon_market.volume,
        horizon_turnover=horizon_market.turnover,
    )


def _build_target_observation(
    repository: StockMonitorRepository,
    summary: DailyStockSummary,
    base_market: StockMarketDailySnapshot | None,
    market_series: list[StockMarketDailySnapshot],
) -> TargetObservation:
    target_values = [value for value in (summary.target_price_min, summary.target_price_max) if value is not None]
    if not summary.stock_code or not target_values:
        return TargetObservation(
            available=False,
            gap_available=False,
            progress_available=False,
            unavailable_reason="missing_target_price",
        )
    if base_market is None or base_market.close_price is None:
        return TargetObservation(
            available=False,
            gap_available=False,
            progress_available=False,
            unavailable_reason="missing_base_close_price",
        )

    target_min = min(target_values)
    target_max = max(target_values)
    current_price = base_market.close_price
    gap_values = [
        _percent(target_min - current_price, current_price),
        _percent(target_max - current_price, current_price),
    ]
    baseline_date = repository.get_first_target_report_date(summary.stock_code, on_or_before=summary.business_date)
    baseline_price = None
    if baseline_date:
        baseline_markets = repository.list_stock_market_daily_for_codes(baseline_date, [summary.stock_code])
        if baseline_markets:
            baseline_price = baseline_markets[0].close_price

    progress_to_min = (
        _target_progress_percent(current_price, baseline_price, target_min)
        if baseline_price is not None
        else None
    )
    progress_to_max = (
        _target_progress_percent(current_price, baseline_price, target_max)
        if baseline_price is not None
        else None
    )
    valid_gaps = [value for value in gap_values if value is not None]
    valid_progress = [value for value in (progress_to_min, progress_to_max) if value is not None]
    progress_notice = _target_progress_notice(baseline_price, target_min, target_max)
    validation = _build_target_validation(
        market_series,
        baseline_price=baseline_price,
        target_min=target_min,
        target_max=target_max,
        progress_notice=progress_notice,
    )
    return TargetObservation(
        available=bool(valid_gaps or valid_progress),
        gap_available=bool(valid_gaps),
        progress_available=bool(valid_progress),
        validation_available=validation["validation_available"],
        baseline_date=baseline_date,
        baseline_price=baseline_price,
        current_date=summary.business_date,
        current_price=current_price,
        target_price_min=target_min,
        target_price_max=target_max,
        target_gap_min_percent=min(valid_gaps) if valid_gaps else None,
        target_gap_max_percent=max(valid_gaps) if valid_gaps else None,
        progress_to_min_percent=progress_to_min,
        progress_to_max_percent=progress_to_max,
        progress_caution=progress_notice != "baseline_below_target_range",
        progress_notice=progress_notice,
        validation_window_days=validation["validation_window_days"],
        max_progress_to_min_percent=validation["max_progress_to_min_percent"],
        max_progress_to_max_percent=validation["max_progress_to_max_percent"],
        hit_min_horizon_days=validation["hit_min_horizon_days"],
        hit_max_horizon_days=validation["hit_max_horizon_days"],
        validation_notice=validation["validation_notice"],
    )


def _build_stock_flow_observation(rows: list[StockInvestorFlowDaily]) -> StockFlowObservation:
    return StockFlowObservation(
        available=bool(rows),
        individual_net_buy_volume=_sum_flow(rows, {"개인"}, "net_buy_volume"),
        foreign_net_buy_volume=_sum_flow(rows, {"외국인"}, "net_buy_volume"),
        institution_net_buy_volume=_sum_flow(rows, {"기관", "기관합계"}, "net_buy_volume"),
        individual_net_buy_amount=_sum_flow(rows, {"개인"}, "net_buy_amount"),
        foreign_net_buy_amount=_sum_flow(rows, {"외국인"}, "net_buy_amount"),
        institution_net_buy_amount=_sum_flow(rows, {"기관", "기관합계"}, "net_buy_amount"),
        investor_types=tuple(sorted({row.investor_type for row in rows})),
    )


def _build_net_buy_top_observation(row: InvestorNetBuyTopDaily | None) -> NetBuyTopObservation:
    if row is None:
        return NetBuyTopObservation(available=False)
    return NetBuyTopObservation(
        available=True,
        foreign_top_rank=row.rank,
        market=row.market,
        net_buy_volume=row.net_buy_volume,
        net_buy_amount=row.net_buy_amount,
    )


def _build_target_validation(
    market_series: list[StockMarketDailySnapshot],
    *,
    baseline_price: int | None,
    target_min: int,
    target_max: int,
    progress_notice: str | None,
) -> dict[str, object]:
    if baseline_price is None:
        return _empty_target_validation("missing_baseline_price")
    if progress_notice != "baseline_below_target_range":
        return _empty_target_validation(progress_notice or "unsupported_target_direction")
    observed = [
        (index, item)
        for index, item in enumerate(market_series)
        if item.close_price is not None
    ]
    if not observed:
        return _empty_target_validation("missing_market_series")
    progress_to_min = [
        _target_progress_percent(item.close_price, baseline_price, target_min)
        for _index, item in observed
    ]
    progress_to_max = [
        _target_progress_percent(item.close_price, baseline_price, target_max)
        for _index, item in observed
    ]
    valid_min_progress = [value for value in progress_to_min if value is not None]
    valid_max_progress = [value for value in progress_to_max if value is not None]
    hit_min = next((index for index, item in observed if item.close_price >= target_min), None)
    hit_max = next((index for index, item in observed if item.close_price >= target_max), None)
    return {
        "validation_available": bool(valid_min_progress or valid_max_progress or hit_min is not None or hit_max is not None),
        "validation_window_days": max(index for index, _item in observed),
        "max_progress_to_min_percent": max(valid_min_progress) if valid_min_progress else None,
        "max_progress_to_max_percent": max(valid_max_progress) if valid_max_progress else None,
        "hit_min_horizon_days": hit_min,
        "hit_max_horizon_days": hit_max,
        "validation_notice": "stored_window_only",
    }


def _empty_target_validation(reason: str) -> dict[str, object]:
    return {
        "validation_available": False,
        "validation_window_days": None,
        "max_progress_to_min_percent": None,
        "max_progress_to_max_percent": None,
        "hit_min_horizon_days": None,
        "hit_max_horizon_days": None,
        "validation_notice": reason,
    }


def _sum_flow(rows: list[StockInvestorFlowDaily], investor_types: set[str], field: str) -> int | None:
    values = [
        getattr(row, field)
        for row in rows
        if row.investor_type in investor_types and getattr(row, field) is not None
    ]
    if not values:
        return None
    return int(sum(values))


def _percent(numerator: float, denominator: float) -> float | None:
    if denominator == 0:
        return None
    return round((numerator / denominator) * 100, 2)


def _target_progress_percent(current_price: int, baseline_price: int, target_price: int) -> float | None:
    denominator = target_price - baseline_price
    numerator = current_price - baseline_price
    if denominator == 0:
        return 0.0 if numerator == 0 else None
    return _percent(numerator, denominator)


def _target_progress_notice(baseline_price: int | None, target_min: int, target_max: int) -> str | None:
    if baseline_price is None:
        return None
    if baseline_price < target_min:
        return "baseline_below_target_range"
    if baseline_price > target_max:
        return "baseline_above_target_range"
    return "baseline_inside_target_range"
