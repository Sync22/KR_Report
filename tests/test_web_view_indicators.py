from datetime import date, timedelta

import pytest

from stock_monitor.web_view_indicators import (
    build_indicator_chart_data,
    build_indicator_confirmation,
    build_indicator_snapshot,
    build_priority_condition_explanation,
    build_priority_condition_status,
    build_reference_conditions,
)


def _bars(count: int, start: date = date(2026, 1, 1)) -> list[dict[str, object]]:
    rows = []
    for index in range(count):
        close = 100.0 + index
        rows.append({
            "time": (start + timedelta(days=index)).isoformat(),
            "open": close - .5,
            "high": close + 2,
            "low": close - 2,
            "close": close,
            "volume": 100 + index,
        })
    return rows


def _snapshot(bars: list[dict[str, object]], **overrides: object) -> dict[str, object]:
    options: dict[str, object] = {
        "code": "005930",
        "symbol": "005930.KS",
        "market": "KOSPI",
        "requested_as_of": bars[-1]["time"] if bars else "2026-01-01",
        "candles": bars,
        "source": "toss_openapi",
        "source_fetched_at": "2026-10-08T10:00:00+09:00",
        "source_date": bars[-1]["time"] if bars else None,
        "bar_status": "confirmed",
        "confirmed_policy": "Toss adjusted daily candle",
    }
    options.update(overrides)
    return build_indicator_snapshot(**options)  # type: ignore[arg-type]


def _confirmation_snapshot() -> dict[str, object]:
    return {
        "price": {"close": 100.0},
        "indicators": {
            "rsi14": {"value": 60.0},
            "macd129": {"macd": 2.0, "signal": 1.0},
            "movingAverages": {
                **{f"{kind}{period}": value for kind, base in (("sma", 95.0), ("ema", 94.0), ("wma", 96.0))
                   for period, value in zip((20, 60, 120, 200), (base, base - 5, base - 10, base - 15))},
            },
            "bollinger20": {"middle": 95.0, "upper": 110.0, "lower": 80.0},
            "donchian20": {"middle": 90.0, "upper": 120.0, "lower": 60.0},
            "obv": {"delta5": 10.0},
            "volume": {"ratio20": 1.2},
            "atr14": {"value": 2.0},
            "volumeProfile12": {"bins": [
                {"low": 90.0, "high": 95.0, "peak": True},
                {"low": 95.0, "high": 100.0, "peak": True},
            ]},
        },
    }


def test_indicator_confirmation_aligns_all_up_components() -> None:
    result = build_indicator_confirmation(_confirmation_snapshot())

    assert result == {
        "directional_alignment_state": "up_aligned",
        "rsi_state": "up",
        "macd_state": "up",
        "moving_average_state": "up",
        "sma_state": "up",
        "ema_state": "up",
        "wma_state": "up",
        "bollinger_state": "up",
        "donchian_state": "up",
        "obv_state": "up",
        "volume_confirmation_state": "confirmed",
        "volume_ratio20": 1.2,
        "atr14_value": 2.0,
        "atr14_percent_of_close": 2.0,
        "volume_profile_state": "within_peak_volume_bins",
        "peak_volume_bins": [{"low": 90.0, "high": 95.0}, {"low": 95.0, "high": 100.0}],
    }


def test_indicator_confirmation_aligns_all_down_components() -> None:
    snapshot = _confirmation_snapshot()
    indicators = snapshot["indicators"]
    indicators["rsi14"]["value"] = 40.0
    indicators["macd129"].update(macd=-2.0, signal=-1.0)
    for kind in ("sma", "ema", "wma"):
        indicators["movingAverages"].update({
            f"{kind}20": 105.0, f"{kind}60": 110.0, f"{kind}120": 115.0, f"{kind}200": 120.0,
        })
    indicators["bollinger20"]["middle"] = 105.0
    indicators["donchian20"]["middle"] = 110.0
    indicators["obv"]["delta5"] = -10.0

    result = build_indicator_confirmation(snapshot)

    assert result["directional_alignment_state"] == "down_aligned"
    assert all(result[key] == "down" for key in (
        "rsi_state", "macd_state", "moving_average_state", "sma_state", "ema_state", "wma_state",
        "bollinger_state", "donchian_state", "obv_state",
    ))


def test_indicator_confirmation_marks_disagreement_and_missing_inputs() -> None:
    mixed = _confirmation_snapshot()
    mixed["indicators"]["macd129"].update(macd=0.0, signal=1.0)
    assert build_indicator_confirmation(mixed)["directional_alignment_state"] == "mixed"

    missing = _confirmation_snapshot()
    missing["indicators"]["movingAverages"]["sma200"] = None
    result = build_indicator_confirmation(missing)
    assert result["directional_alignment_state"] == "insufficient_data"
    assert result["sma_state"] == result["moving_average_state"] == "insufficient_data"


@pytest.mark.parametrize(
    ("price_state", "direction", "volume", "expected"),
    [
        ("insufficient_data", "up_aligned", "confirmed", "판정 불가"),
        ("above_prior_20_bar_high", "insufficient_data", "confirmed", "판정 불가"),
        ("above_prior_20_bar_high", "up_aligned", "missing", "판정 불가"),
        ("unknown", "up_aligned", "confirmed", "판정 불가"),
        ("above_prior_20_bar_high", "up_aligned", "confirmed", "진입 조건 충족"),
        ("below_prior_10_bar_low", "down_aligned", "confirmed", "청산 조건 충족"),
        ("above_prior_20_bar_high", "mixed", "confirmed", "가격 기준 도달 · 보조지표 확인 필요"),
        ("above_prior_20_bar_high", "down_aligned", "confirmed", "가격 기준 도달 · 보조지표 확인 필요"),
        ("above_prior_20_bar_high", "up_aligned", "below_threshold", "가격 기준 도달 · 보조지표 확인 필요"),
        ("within_reference_band", "mixed", "below_threshold", "두 가격 조건 미충족"),
    ],
)
def test_priority_condition_status_missing_inputs_prevent_confirmation(
    price_state: str,
    direction: str,
    volume: str,
    expected: str,
) -> None:
    status = build_priority_condition_status(
        {"price_condition_state": price_state},
        {
            "directional_alignment_state": direction,
            "volume_confirmation_state": volume,
        },
    )

    assert status == expected


def test_priority_condition_explanation_names_the_actual_confirmation_blockers() -> None:
    entry = build_priority_condition_explanation(
        {"price_condition_state": "above_prior_20_bar_high"},
        {
            "directional_alignment_state": "mixed",
            "moving_average_state": "mixed",
            "rsi_state": "up",
            "macd_state": "up",
            "bollinger_state": "up",
            "donchian_state": "up",
            "obv_state": "up",
            "volume_confirmation_state": "confirmed",
            "volume_ratio20": 3.22,
        },
    )
    exit_ = build_priority_condition_explanation(
        {"price_condition_state": "below_prior_10_bar_low"},
        {
            "directional_alignment_state": "mixed",
            "moving_average_state": "mixed",
            "rsi_state": "down",
            "macd_state": "down",
            "bollinger_state": "down",
            "donchian_state": "down",
            "obv_state": "down",
            "volume_confirmation_state": "below_threshold",
            "volume_ratio20": 1.09,
        },
    )

    assert "진입 가격 조건은 도달했지만" in entry
    assert "SMA·EMA·WMA 이동평균 배열이 혼합" in entry
    assert "탈출 가격 조건은 도달했지만" in exit_
    assert "1.09배" in exit_ and "1.2배 기준 미달" in exit_


@pytest.mark.parametrize("close", [100.0, 90.0])
def test_price_explanation_does_not_call_threshold_equality_between(close: float) -> None:
    explanation = build_priority_condition_explanation(
        {
            "price_condition_state": "within_reference_band",
            "reference_close": close,
            "prior_20_bar_high": 100.0,
            "prior_10_bar_low": 90.0,
        },
        {
            "directional_alignment_state": "up_aligned",
            "volume_confirmation_state": "confirmed",
        },
    )

    assert explanation == "현재 종가는 진입 기준을 넘지 않았고 탈출 기준을 하회하지 않았습니다."


def test_bollinger_and_donchian_direction_disagreement_blocks_alignment() -> None:
    snapshot = _confirmation_snapshot()
    snapshot["indicators"]["donchian20"]["middle"] = 110.0

    result = build_indicator_confirmation(snapshot)

    assert result["donchian_state"] == "down"
    assert result["directional_alignment_state"] == "mixed"


def test_disjoint_peak_volume_bins_keep_the_gap_unlabeled_as_peak() -> None:
    snapshot = _confirmation_snapshot()
    snapshot["price"]["close"] = 95.0
    snapshot["indicators"]["volumeProfile12"]["bins"] = [
        {"low": 90.0, "high": 92.0, "peak": True},
        {"low": 98.0, "high": 100.0, "peak": True},
    ]

    result = build_indicator_confirmation(snapshot)

    assert result["volume_profile_state"] == "between_peak_volume_bins"
    assert result["peak_volume_bins"] == [
        {"low": 90.0, "high": 92.0},
        {"low": 98.0, "high": 100.0},
    ]


@pytest.mark.parametrize(
    ("ratio", "expected_state"),
    [(1.199, "below_threshold"), (1.2, "confirmed"), (None, "missing")],
)
def test_volume_confirmation_threshold_does_not_change_directional_alignment(
    ratio: float | None, expected_state: str,
) -> None:
    snapshot = _confirmation_snapshot()
    snapshot["indicators"]["volume"]["ratio20"] = ratio

    result = build_indicator_confirmation(snapshot)

    assert result["volume_confirmation_state"] == expected_state
    assert result["directional_alignment_state"] == "up_aligned"


def test_atr_is_absolute_and_percent_context_only() -> None:
    snapshot = _confirmation_snapshot()
    snapshot["indicators"]["atr14"]["value"] = 4.0

    result = build_indicator_confirmation(snapshot)

    assert result["atr14_value"] == 4.0
    assert result["atr14_percent_of_close"] == 4.0
    assert result["directional_alignment_state"] == "up_aligned"


def test_chart_data_cuts_off_future_bars_sorts_and_aligns_series() -> None:
    bars = _bars(385)
    as_of = bars[383]["time"]
    future = {**bars[384], "time": "2028-01-01"}

    chart = build_indicator_chart_data([*reversed(bars), future], as_of)
    rows = chart["bars"]

    assert len(rows) == 380
    assert rows[0]["time"] == bars[4]["time"]
    assert rows[-1]["time"] == as_of
    assert all(rows[index]["time"] < rows[index + 1]["time"] for index in range(len(rows) - 1))
    assert all("sma20" in row and "rsi14" in row and "macdSignal" in row and "atr14" in row for row in rows)


def test_chart_sma200_uses_history_and_exposes_warmup_values() -> None:
    rows = build_indicator_chart_data(_bars(200), "2026-07-19")["bars"]

    assert len(rows) == 200
    assert rows[198]["sma200"] is None
    assert rows[199]["sma200"] == pytest.approx(199.5)


def test_chart_indicator_values_match_snapshot_calculations() -> None:
    bars = _bars(220)
    chart = build_indicator_chart_data(bars, bars[-1]["time"])["bars"]
    last = chart[-1]
    snapshot = _snapshot(bars)["indicators"]

    assert last["sma20"] == pytest.approx(309.5)
    assert last["sma60"] == pytest.approx(289.5)
    assert last["sma120"] == pytest.approx(259.5)
    assert last["sma200"] == pytest.approx(219.5)
    assert last["rsi14"] == snapshot["rsi14"]["value"] == pytest.approx(100)
    assert last["macd"] == snapshot["macd129"]["macd"]
    assert last["macdSignal"] == snapshot["macd129"]["signal"]
    assert last["macdHistogram"] == snapshot["macd129"]["histogram"]
    assert last["obv"] == snapshot["obv"]["value"] == pytest.approx(45990)
    assert last["atr14"] == snapshot["atr14"]["value"] == pytest.approx(4)


def test_flat_closes_report_neutral_rsi() -> None:
    bars = _bars(20)
    for bar in bars:
        bar.update(open=100, high=100, low=100, close=100)

    snapshot = _snapshot(bars)

    assert snapshot["indicators"]["rsi14"]["value"] == pytest.approx(50.0)
    assert snapshot["indicators"]["rsi14"]["status"] == "ready"
    assert snapshot["calculationVersion"] == "stock-monitor-indicator-v2"
    assert build_indicator_chart_data(bars, bars[-1]["time"])["bars"][-1]["rsi14"] == pytest.approx(50.0)


def test_reference_conditions_compare_close_with_prior_twenty_high_and_ten_low() -> None:
    bars = _bars(21)
    for bar in bars[:-1]:
        bar.update(open=100, high=120, low=80, close=100)
    bars[-1].update(open=120, high=130, low=119, close=121)

    result = build_reference_conditions(bars, bars[-1]["time"])

    assert result == {
        "price_condition_state": "above_prior_20_bar_high",
        "reference_bar_date": bars[-1]["time"],
        "reference_close": 121.0,
        "prior_20_bar_high": 120.0,
        "prior_10_bar_low": 80.0,
    }


def test_reference_conditions_mark_close_below_prior_ten_bar_low() -> None:
    bars = _bars(21)
    for bar in bars[:-1]:
        bar.update(open=100, high=120, low=80, close=100)
    bars[-1].update(open=79, high=81, low=70, close=79)

    result = build_reference_conditions(bars, bars[-1]["time"])

    assert result["price_condition_state"] == "below_prior_10_bar_low"
    assert result["prior_20_bar_high"] == 120.0
    assert result["prior_10_bar_low"] == 80.0


@pytest.mark.parametrize(
    ("latest_close", "expected_state"),
    [
        (120, "within_reference_band"),
        (80, "within_reference_band"),
    ],
)
def test_reference_condition_threshold_equality_does_not_cross(
    latest_close: int, expected_state: str,
) -> None:
    bars = _bars(21)
    for bar in bars[:-1]:
        bar.update(open=100, high=120, low=80, close=100)
    bars[-1].update(open=latest_close, high=latest_close + 1, low=latest_close - 1, close=latest_close)

    result = build_reference_conditions(bars, bars[-1]["time"])

    assert result["price_condition_state"] == expected_state


def test_reference_conditions_need_twenty_prior_bars_and_mark_invalid_prices() -> None:
    short = _bars(20)
    insufficient = build_reference_conditions(short, short[-1]["time"])
    assert insufficient["price_condition_state"] == "insufficient_data"
    assert insufficient["reference_bar_date"] == short[-1]["time"]
    assert insufficient["prior_20_bar_high"] is None
    assert insufficient["prior_10_bar_low"] is not None

    invalid = _bars(21)
    invalid[10]["high"] = float("nan")
    rejected = build_reference_conditions(invalid, invalid[-1]["time"])
    assert rejected["price_condition_state"] == "insufficient_data"
    assert rejected["reference_bar_date"] is None
    assert rejected["reference_close"] is None
    assert rejected["prior_20_bar_high"] is None
    assert rejected["prior_10_bar_low"] is None


def test_reference_conditions_sort_and_cut_off_after_selected_actual_bar() -> None:
    bars = _bars(22)
    selected = bars[20]
    future = {**bars[21], "time": "2027-01-01", "high": 9999, "low": 1, "close": 9998}
    result = build_reference_conditions([future, *reversed(bars[:21])], selected["time"])

    assert result["reference_bar_date"] == selected["time"]
    assert result["reference_close"] == selected["close"]
    assert result["prior_20_bar_high"] == max(float(bar["high"]) for bar in bars[:20])
    assert result["prior_10_bar_low"] == min(float(bar["low"]) for bar in bars[10:20])


def test_all_factual_daily_metrics_use_adjusted_prefix_and_keep_provenance() -> None:
    bars = _bars(220)
    future = {
        "time": "2027-01-01", "open": 1, "high": 1, "low": 1,
        "close": 1, "volume": 999999,
    }
    snapshot = _snapshot(
        [*bars, future],
        requested_as_of=bars[-1]["time"],
        cache_hit=False,
        cache_age=0,
        stale=False,
    )
    indicators = snapshot["indicators"]
    assert isinstance(indicators, dict)
    moving = indicators["movingAverages"]
    assert isinstance(moving, dict)
    assert moving["status"] == "ready"
    assert moving["sma200"] == pytest.approx(219.5)
    alpha = 2 / 201
    expected_ema = sum(100 + index for index in range(200)) / 200
    for close in range(300, 320):
        expected_ema += alpha * (close - expected_ema)
    assert moving["ema200"] == pytest.approx(expected_ema)
    assert moving["wma200"] == pytest.approx(
        sum((120 + index) * (index + 1) / (200 * 201 / 2) for index in range(200))
    )
    assert snapshot["barAsOf"] == bars[-1]["time"]
    assert snapshot["price"] == {
        "open": 318.5, "high": 321.0, "low": 317.0, "close": 319.0, "volume": 319.0,
    }
    assert snapshot["source"] == "toss_openapi"
    assert snapshot["sourceFetchedAt"] == "2026-10-08T10:00:00+09:00"
    assert snapshot["cacheHit"] is False
    assert snapshot["stale"] is False

    bb = indicators["bollinger20"]
    donchian = indicators["donchian20"]
    rsi = indicators["rsi14"]
    atr = indicators["atr14"]
    volume = indicators["volume"]
    macd = indicators["macd129"]
    obv = indicators["obv"]
    profile = indicators["volumeProfile12"]
    assert isinstance(bb, dict) and bb["status"] == "ready"
    assert bb["middle"] == pytest.approx(309.5)
    assert bb["upper"] == pytest.approx(309.5 + 2 * (33.25 ** .5))
    assert isinstance(donchian, dict) and donchian["includeCurrent"] is True
    assert donchian["upper"] == pytest.approx(321.0)
    assert isinstance(rsi, dict) and rsi["value"] == pytest.approx(100.0)
    assert isinstance(atr, dict) and atr["value"] == pytest.approx(4.0)
    assert isinstance(volume, dict) and volume["ratio20"] == pytest.approx(319 / 309.5)
    assert isinstance(macd, dict) and macd["status"] == "ready"
    assert isinstance(obv, dict) and obv["value"] == pytest.approx(45990)
    assert obv["delta5"] == pytest.approx(sum(range(315, 320)))
    assert obv["seedTime"] == bars[0]["time"]
    assert isinstance(profile, dict)
    assert len(profile["bins"]) == 12
    assert sum(item["volume"] for item in profile["bins"]) == pytest.approx(profile["total"])
    assert sum(item["share"] for item in profile["bins"]) == pytest.approx(1.0)


def test_as_of_cutoff_is_applied_before_every_calculation() -> None:
    bars = _bars(50)
    as_of = bars[39]["time"]
    future = {**bars[-1], "time": "2027-01-01", "high": 99999, "close": 99998, "low": 99997}
    snapshot = _snapshot([*bars, future], requested_as_of=as_of)
    indicators = snapshot["indicators"]
    assert snapshot["barAsOf"] == as_of
    assert snapshot["price"]["close"] == bars[39]["close"]
    assert indicators["volumeProfile12"]["to"] == as_of
    assert indicators["donchian20"]["upper"] == bars[39]["high"]


def test_insufficient_history_is_explicit_and_empty_profile_has_no_fake_bins() -> None:
    snapshot = _snapshot(_bars(9))
    indicators = snapshot["indicators"]
    assert indicators["movingAverages"]["status"] == "insufficient-data"
    assert indicators["rsi14"]["status"] == "insufficient-data"
    assert indicators["atr14"]["status"] == "insufficient-data"
    assert indicators["macd129"]["status"] == "insufficient-data"
    assert indicators["macd129"]["macd"] is None
    assert indicators["macd129"]["signal"] is None
    assert indicators["macd129"]["histogram"] is None
    assert indicators["volumeProfile12"]["status"] == "insufficient-data"
    assert indicators["volumeProfile12"]["bins"] == []
    assert snapshot["structureStatus"] == {
        "horizontal": "insufficient-data",
        "flag": "insufficient-data",
        "triangle": "insufficient-data",
    }


def test_horizontal_structures_are_ready_with_twenty_prior_bars_and_current_bar() -> None:
    snapshot = _snapshot(_bars(21))
    structures = snapshot["structures"]

    assert snapshot["structureStatus"]["horizontal"] == "ready"
    assert [item["family"] for item in structures] == ["horizontal", "horizontal"]


def test_flat_hlc3_profile_uses_newbby_single_bin_rule() -> None:
    bars = []
    for index in range(12):
        bars.append({
            "time": (date(2026, 1, 1) + timedelta(days=index)).isoformat(),
            "open": 100, "high": 100, "low": 100, "close": 100, "volume": 10,
        })
    profile = _snapshot(bars)["indicators"]["volumeProfile12"]
    assert profile["status"] == "ready"
    assert profile["binCount"] == 1
    assert profile["bins"] == [{"low": 100.0, "high": 100.0, "volume": 120.0, "share": 1.0, "peak": True}]


def test_triangle_geometry_is_neutral_and_labels_all_three_extrapolations() -> None:
    bars = []
    highs = {18, 22, 26, 30}
    lows = {20, 24, 28, 32}
    for index in range(35):
        upper = 160 - 1.3 * index
        lower = 60 + 1.3 * index
        high = upper if index in highs else upper - 4
        low = lower if index in lows else lower + 4
        close = 110.0
        bars.append({
            "time": (date(2026, 1, 1) + timedelta(days=index)).isoformat(),
            "open": close,
            "high": high,
            "low": low,
            "close": close,
            "volume": 1000 + index,
        })
    snapshot = _snapshot(bars)
    structures = snapshot["structures"]
    triangles = [item for item in structures if item["family"] == "triangle"]
    assert len(triangles) == 1
    measurements = {item["name"]: item for item in triangles[0]["measurements"]}
    assert measurements["geometry.points.2.price"]["label"] == "삼각형 교점 · 직선 외삽값(목표가 아님)"
    assert measurements["geometry.points.2.logicalOffset"]["label"] == "삼각형 시작점부터 교점까지 봉 수 · 직선 외삽"
    assert measurements["apexRemainingBars"]["label"] == "삼각형 교점까지 남은 봉 · 직선 외삽"
    assert measurements["geometry.points.2.logicalOffset"]["value"] > 0
    assert snapshot["structureStatus"]["triangle"] == "ready"
    assert all(not any(term in item["name"].lower() for term in ("trigger", "invalidation", "signal", "score", "grade", "entry", "exit"))
               for item in triangles[0]["measurements"])


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("code", "ABC123"),
        ("market", "UNKNOWN"),
        ("requested_as_of", "2026-02-30"),
    ],
)
def test_invalid_identity_or_cutoff_is_rejected(field: str, value: str) -> None:
    with pytest.raises(ValueError):
        _snapshot(_bars(20), **{field: value})


def test_unknown_market_keeps_numeric_symbol_and_computes_indicators() -> None:
    snapshot = _snapshot(_bars(220), market="unknown", symbol="005930")

    assert snapshot["market"] == "unknown"
    assert snapshot["symbol"] == "005930"
    assert snapshot["indicators"]["movingAverages"]["sma200"] is not None

    with pytest.raises(ValueError, match="symbol-does-not-match-market"):
        _snapshot(_bars(20), market="unknown")


def test_invalid_adjusted_ohlcv_is_rejected() -> None:
    bars = _bars(20)
    bars[-1]["high"] = bars[-1]["close"] - 1
    with pytest.raises(ValueError, match="invalid-daily-ohlcv"):
        _snapshot(bars)
