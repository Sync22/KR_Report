"""Pure, point-in-time daily indicators for the WebView Main candidates."""

from __future__ import annotations

from datetime import date
import hashlib
import json
import math
from typing import Mapping, Sequence


CALCULATION_VERSION = "stock-monitor-indicator-v1"
TECHNICAL_VERSION = "technical-v3"
PROFILE_VERSION = "vp-1"
_PERIODS = (20, 60, 120, 200)
_ACTION_TERMS = (
    "entry", "exit", "trigger", "invalidation", "recommend", "score", "grade",
    "signal", "direction", "buy", "sell",
)
_NON_MEASUREMENTS = {
    "patternid", "eventid", "eventtype", "ruleversion", "reason", "symbol",
    "timeframe", "startindex", "endindex", "poleindex", "confirmedindex",
    "terminalindex", "apexindex", "fittoleranceatr", "minimumcontainment",
    "maxoutsiderun", "maxretracement", "maxadjustmentbars", "provisionalinvalidation",
}


def _number(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return result if math.isfinite(result) else None


def _status(values: Sequence[object]) -> str:
    count = sum(value is not None for value in values)
    return "ready" if count == len(values) else "partial-data" if count else "insufficient-data"


def _sma(values: Sequence[float], period: int) -> list[float | None]:
    result: list[float | None] = [None] * len(values)
    for i in range(period - 1, len(values)):
        window = values[i - period + 1:i + 1]
        if all(math.isfinite(value) for value in window):
            result[i] = sum(value / period for value in window)
    return result


def _ema(values: Sequence[float], period: int) -> list[float | None]:
    result: list[float | None] = [None] * len(values)
    alpha = 2 / (period + 1)
    seed: list[float] = []
    previous: float | None = None
    for i, value in enumerate(values):
        if not math.isfinite(value):
            seed, previous = [], None
            continue
        if previous is None:
            seed.append(value)
            if len(seed) < period:
                continue
            previous = sum(item / period for item in seed)
            seed = []
        else:
            previous += alpha * (value - previous)
        if math.isfinite(previous):
            result[i] = previous
        else:
            seed, previous = [], None
    return result


def _wma(values: Sequence[float], period: int) -> list[float | None]:
    result: list[float | None] = [None] * len(values)
    denominator = period * (period + 1) / 2
    for i in range(period - 1, len(values)):
        window = values[i - period + 1:i + 1]
        if all(math.isfinite(value) for value in window):
            result[i] = sum(value * (j + 1) / denominator for j, value in enumerate(window))
    return result


def _bollinger(values: Sequence[float], period: int = 20) -> dict[str, float] | None:
    if len(values) < period:
        return None
    window = values[-period:]
    if not all(math.isfinite(value) for value in window):
        return None
    middle = sum(value / period for value in window)
    deviation = math.sqrt(sum((value - middle) ** 2 / period for value in window))
    return {"middle": middle, "upper": middle + 2 * deviation, "lower": middle - 2 * deviation}


def _donchian(bars: Sequence[Mapping[str, object]], period: int = 20) -> dict[str, float] | None:
    if len(bars) < period:
        return None
    window = bars[-period:]
    upper, lower = max(float(row["high"]) for row in window), min(float(row["low"]) for row in window)
    return {"upper": upper, "middle": upper / 2 + lower / 2, "lower": lower}


def _rsi_series(values: Sequence[float], period: int = 14) -> list[float | None]:
    # Newbby seeds from the first period price changes, then applies Wilder smoothing.
    result: list[float | None] = [None] * len(values)
    if len(values) <= period:
        return result
    changes = [values[i] - values[i - 1] for i in range(1, len(values))]
    gains = [max(change, 0.0) for change in changes]
    losses = [max(-change, 0.0) for change in changes]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    result[period] = 100.0 if avg_loss == 0 else 100 - 100 / (1 + avg_gain / avg_loss)
    for index, (gain, loss) in enumerate(zip(gains[period:], losses[period:]), start=period + 1):
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
        result[index] = 100.0 if avg_loss == 0 else 100 - 100 / (1 + avg_gain / avg_loss)
    return result


def _rsi(values: Sequence[float], period: int = 14) -> float | None:
    series = _rsi_series(values, period)
    return series[-1] if series else None


def _true_ranges(bars: Sequence[Mapping[str, object]]) -> list[float]:
    result = []
    for i, bar in enumerate(bars):
        previous = float(bars[i - 1]["close"]) if i else float(bar["close"])
        high, low = float(bar["high"]), float(bar["low"])
        result.append(max(high - low, abs(high - previous), abs(low - previous)))
    return result


def _atr(bars: Sequence[Mapping[str, object]], period: int = 14) -> list[float | None]:
    tr = _true_ranges(bars)
    result: list[float | None] = [None] * len(tr)
    if len(tr) < period:
        return result
    result[period - 1] = sum(tr[:period]) / period
    for i in range(period, len(tr)):
        result[i] = (result[i - 1] * (period - 1) + tr[i]) / period  # type: ignore[operator]
    return result


def _volume_profile(bars: Sequence[Mapping[str, object]]) -> dict[str, object]:
    if len(bars) < 10:
        return {"version": PROFILE_VERSION, "method": "hlc3", "from": None, "to": None,
                "count": len(bars), "total": 0, "bins": [], "status": "insufficient-data"}
    low = min(float(row["low"]) for row in bars)
    high = max(float(row["high"]) for row in bars)
    count = 1 if high == low else 12
    step = (high - low) / count
    bins = [{"low": low + i * step, "high": low + (i + 1) * step, "volume": 0.0}
            for i in range(count)]
    for row in bars:
        typical = (float(row["high"]) + float(row["low"]) + float(row["close"])) / 3
        index = min(count - 1, max(0, int((typical - low) / step))) if step else 0
        bins[index]["volume"] += float(row["volume"])
    total = sum(float(item["volume"]) for item in bins)
    peak = max(float(item["volume"]) for item in bins)
    return {
        "version": PROFILE_VERSION,
        "method": "hlc3",
        "from": bars[0]["time"],
        "to": bars[-1]["time"],
        "count": len(bars),
        "total": total,
        "binCount": count,
        "bins": [{**item, "share": float(item["volume"]) / total if total else 0.0,
                  "peak": bool(total and item["volume"] == peak)} for item in bins],
        "status": "ready",
    }


def _line(model: Mapping[str, float], index: float) -> float:
    return model["intercept"] + model["slope"] * index


def _fit(points: Sequence[tuple[int, float]]) -> dict[str, float] | None:
    if len(points) < 2:
        return None
    mean_x = sum(index for index, _ in points) / len(points)
    mean_y = sum(value for _, value in points) / len(points)
    denominator = sum((index - mean_x) ** 2 for index, _ in points)
    if denominator == 0:
        return None
    slope = sum((index - mean_x) * (value - mean_y) for index, value in points) / denominator
    return {"slope": slope, "intercept": mean_y - slope * mean_x}


def _pivots(bars: Sequence[Mapping[str, object]], through: int) -> tuple[list[tuple[int, float]], list[tuple[int, float]]]:
    highs, lows = [], []
    for index in range(2, through - 1):
        high, low = float(bars[index]["high"]), float(bars[index]["low"])
        if (all(high >= float(bars[k]["high"]) for k in (index - 2, index - 1))
                and all(high > float(bars[k]["high"]) for k in (index + 1, index + 2))):
            highs.append((index, high))
        if (all(low <= float(bars[k]["low"]) for k in (index - 2, index - 1))
                and all(low < float(bars[k]["low"]) for k in (index + 1, index + 2))):
            lows.append((index, low))
    return highs, lows


def _coverage(
    bars: Sequence[Mapping[str, object]], start: int, end: int,
    upper: Mapping[str, float], lower: Mapping[str, float], tolerance: float,
) -> tuple[float, int]:
    inside = run = longest = 0
    for index in range(start, end + 1):
        contained = (float(bars[index]["high"]) <= _line(upper, index) + tolerance
                     and float(bars[index]["low"]) >= _line(lower, index) - tolerance)
        if contained:
            inside, run = inside + 1, 0
        else:
            run += 1
            longest = max(longest, run)
    return (inside / (end - start + 1), longest) if end >= start else (0.0, 0)


def _measurement_unit(name: str, value: object) -> str:
    key = name.rsplit(".", 1)[-1].lower()
    if isinstance(value, str):
        return "date" if "time" in key or key == "observedthrough" else "state"
    if "price" in key or key in {"open", "high", "low", "close", "boundary", "polemove", "poleatr", "atr14previous"} or key.endswith("intercept"):
        return "price"
    if "slope" in key:
        return "price-per-bar"
    if "volume" in key and "ratio" not in key:
        return "volume"
    if "ratio" in key or "containment" in key or "retracement" in key:
        return "ratio"
    if "bar" in key or "offset" in key:
        return "bars"
    if "count" in key:
        return "count"
    return "number"


def _collect_measurements(item: Mapping[str, object], family: str) -> list[dict[str, object]]:
    output: list[dict[str, object]] = []

    def collect(name: str, value: object) -> None:
        key = name.rsplit(".", 1)[-1].lower()
        if any(term in key for term in _ACTION_TERMS) or key in _NON_MEASUREMENTS:
            return
        if isinstance(value, Mapping):
            for child, nested in value.items():
                collect(f"{name}.{child}" if name else str(child), nested)
        elif isinstance(value, (list, tuple)):
            if key.endswith("times"):
                output.append({"name": name, "label": name, "value": len(value), "unit": "count"})
            for index, nested in enumerate(value, 1):
                collect(f"{name}.{index}", nested)
        elif isinstance(value, str):
            if key in {"type", "kind", "volumeevidence", "time", "observedthrough", "poleendtime", "polestarttime"} or "time" in name.lower():
                if key == "type" and family == "flag":
                    value = "channel"
                elif key == "type" and family == "triangle":
                    value = "triangle"
                label, unit = name, _measurement_unit(name, value)
                if family == "triangle":
                    if name.lower() == "geometry.points.2.price":
                        label, unit = "삼각형 교점 · 직선 외삽값(목표가 아님)", "projected-price"
                    elif name.lower() == "geometry.points.2.logicaloffset":
                        label, unit = "삼각형 시작점부터 교점까지 봉 수 · 직선 외삽", "projected-bars"
                    elif name.lower() == "apexremainingbars":
                        label, unit = "삼각형 교점까지 남은 봉 · 직선 외삽", "projected-bars"
                output.append({"name": name, "label": label, "value": value, "unit": unit})
        elif isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value)):
            label, unit = name, _measurement_unit(name, value)
            if family == "triangle":
                if name.lower() == "geometry.points.2.price":
                    label, unit = "삼각형 교점 · 직선 외삽값(목표가 아님)", "projected-price"
                elif name.lower() == "geometry.points.2.logicaloffset":
                    label, unit = "삼각형 시작점부터 교점까지 봉 수 · 직선 외삽", "projected-bars"
                elif name.lower() == "apexremainingbars":
                    label, unit = "삼각형 교점까지 남은 봉 · 직선 외삽", "projected-bars"
            output.append({"name": name, "label": label, "value": float(value), "unit": unit})

    for key, value in item.items():
        if key not in {"status", "timeframe", "barTime"}:
            collect(key, value)
    return output


def _flag_candidates(
    bars: Sequence[Mapping[str, object]], atr: Sequence[float | None],
    highs: Sequence[tuple[int, float]], lows: Sequence[tuple[int, float]],
) -> list[dict[str, object]]:
    end = len(bars) - 1
    if end < 20:
        return []
    found: list[dict[str, object]] = []
    # Newbby's balanced profile: 2.5 ATR pole, 0.4 ATR fit, 70% wick containment.
    for start in range(max(17, end - 30 + 1), end - 3):
        choices = []
        for length in range(3, 11):
            pole = start - length
            if pole < 14 or atr[pole - 1] is None:
                continue
            delta = float(bars[start - 1]["close"]) - float(bars[pole]["close"])
            if abs(delta) >= 2.5 * float(atr[pole - 1]):
                choices.append((abs(delta), length, pole, delta))
        if not choices or atr[start - 1] is None:
            continue
        move, length, pole, delta = sorted(choices, key=lambda item: (-item[0], item[1]))[0]
        sign = 1 if delta > 0 else -1
        if sign * (float(bars[start]["close"]) - float(bars[start - 1]["close"])) > .5 * float(atr[start - 1]):
            continue
        hp = [(i, value) for i, value in highs if start <= i <= end - 2]
        lp = [(i, value) for i, value in lows if start <= i <= end - 2]
        if len(hp) < 2 or len(lp) < 2 or atr[end - 1] is None or float(atr[end - 1]) <= 0:
            continue
        upper, lower = _fit(hp), _fit(lp)
        if upper is None or lower is None:
            continue
        a = float(atr[end - 1])
        if any(sign * model["slope"] > .03 * a for model in (upper, lower)):
            continue
        if abs(upper["slope"] - lower["slope"]) > .12 * a:
            continue
        if any(abs(value - _line(model, i)) > .4 * a
               for points, model in ((hp, upper), (lp, lower)) for i, value in points):
            continue
        if any(_line(upper, i) <= _line(lower, i) for i in range(start, end + 1)):
            continue
        contained, outside_run = _coverage(bars, start, end, upper, lower, .4 * a)
        if contained < .7 or outside_run > 2:
            continue
        extreme = (min(float(row["low"]) for row in bars[start:end + 1]) if sign == 1
                   else max(float(row["high"]) for row in bars[start:end + 1]))
        retracement = max(0.0, ((float(bars[start - 1]["close"]) - extreme) if sign == 1
                                else (extreme - float(bars[start - 1]["close"]))) / move)
        if retracement > .618:
            continue
        pole_volume = sum(float(row["volume"]) for row in bars[pole:start]) / length
        adjustment_volume = sum(float(row["volume"]) for row in bars[start:end + 1]) / (end - start + 1)
        found.append({
            "type": "bull-flag" if sign == 1 else "bear-flag",
            "status": "forming",
            "timeframe": "D",
            "barTime": bars[end]["time"],
            "adjustmentStartTime": bars[start]["time"],
            "poleStartTime": bars[pole]["time"],
            "poleEndTime": bars[start - 1]["time"],
            "poleStartPrice": float(bars[pole]["close"]),
            "poleEndPrice": float(bars[start - 1]["close"]),
            "poleMove": move,
            "poleAtr": float(atr[pole - 1]),
            "upper": upper,
            "lower": lower,
            "pivotHighTimes": [bars[i]["time"] for i, _ in hp],
            "pivotLowTimes": [bars[i]["time"] for i, _ in lp],
            "containment": contained,
            "adjustmentVolumeRatio": adjustment_volume / pole_volume if pole_volume else None,
            "retracementRatio": retracement,
            "geometry": {
                "kind": "channel",
                "points": [
                    {"time": bars[start]["time"], "price": _line(upper, start)},
                    {"time": bars[end]["time"], "price": _line(upper, end)},
                    {"time": bars[end]["time"], "price": _line(lower, end)},
                    {"time": bars[start]["time"], "price": _line(lower, start)},
                ],
                "pole": [
                    {"time": bars[pole]["time"], "price": float(bars[pole]["close"])},
                    {"time": bars[start - 1]["time"], "price": float(bars[start - 1]["close"])},
                ],
            },
        })
    # One latest neutral shape per side; no event history or trade-state is inferred.
    return [max((row for row in found if row["type"] == kind), key=lambda row: str(row["adjustmentStartTime"]))
            for kind in ("bull-flag", "bear-flag") if any(row["type"] == kind for row in found)]


def _triangle_candidate(
    bars: Sequence[Mapping[str, object]], atr: Sequence[float | None],
    highs: Sequence[tuple[int, float]], lows: Sequence[tuple[int, float]],
) -> dict[str, object] | None:
    end = len(bars) - 1
    if end < 20 or atr[end - 1] is None or float(atr[end - 1]) <= 0:
        return None
    a = float(atr[end - 1])
    for requested_start in range(max(14, end - 59), end - 8 + 2):
        hp = [(i, value) for i, value in highs if requested_start <= i <= end - 2]
        lp = [(i, value) for i, value in lows if requested_start <= i <= end - 2]
        if len(hp) < 2 or len(lp) < 2 or len(hp) + len(lp) < 5:
            continue
        start = min(hp[0][0], lp[0][0])
        if not 8 <= end - start + 1 <= 60:
            continue
        upper, lower = _fit(hp), _fit(lp)
        if upper is None or lower is None:
            continue
        upper_slope, lower_slope = upper["slope"], lower["slope"]
        if upper_slope <= -.02 * a and lower_slope >= .02 * a:
            kind = "symmetrical-triangle"
        elif abs(upper_slope) <= .03 * a and lower_slope >= .02 * a:
            kind = "ascending-triangle"
        elif upper_slope <= -.02 * a and abs(lower_slope) <= .03 * a:
            kind = "descending-triangle"
        else:
            continue
        if any(abs(value - _line(model, i)) > .4 * a
               for points, model in ((hp, upper), (lp, lower)) for i, value in points):
            continue
        width = _line(upper, start) - _line(lower, start)
        last_width = _line(upper, end) - _line(lower, end)
        if width <= 0 or last_width <= 0 or last_width / width > .75:
            continue
        denominator = upper_slope - lower_slope
        if denominator == 0:
            continue
        apex = (lower["intercept"] - upper["intercept"]) / denominator
        if apex <= end:
            continue
        contained, outside_run = _coverage(bars, start, end, upper, lower, .4 * a)
        if contained < .7 or outside_run > 2:
            continue
        apex_price = _line(upper, apex)
        return {
            "type": kind,
            "status": "forming",
            "timeframe": "D",
            "barTime": bars[end]["time"],
            "structureStartTime": bars[start]["time"],
            "upper": upper,
            "lower": lower,
            "contactCount": len(hp) + len(lp),
            "containment": contained,
            "convergenceRatio": last_width / width,
            "apexRemainingBars": apex - end,
            "pivotHighTimes": [bars[i]["time"] for i, _ in hp],
            "pivotLowTimes": [bars[i]["time"] for i, _ in lp],
            "geometry": {
                "kind": "triangle",
                "points": [
                    {"time": bars[start]["time"], "price": _line(upper, start)},
                    {"anchorTime": bars[start]["time"], "logicalOffset": apex - start, "price": apex_price},
                    {"time": bars[start]["time"], "price": _line(lower, start)},
                ],
                "observedThrough": bars[end]["time"],
            },
        }
    return None


def _structures(bars: Sequence[Mapping[str, object]], atr: Sequence[float | None]) -> tuple[list[dict[str, object]], dict[str, str]]:
    if not bars:
        return [], {"horizontal": "insufficient-data", "flag": "insufficient-data", "triangle": "insufficient-data"}
    structures: list[dict[str, object]] = []
    statuses = {"horizontal": "insufficient-data", "flag": "insufficient-data", "triangle": "insufficient-data"}
    end = len(bars) - 1
    if len(bars) >= 21 and atr[end - 1] is not None:
        previous_high = max(float(row["high"]) for row in bars[-21:-1])
        previous_low = min(float(row["low"]) for row in bars[-11:-1])
        previous_atr = float(atr[end - 1])
        for kind, boundary in (("prior-20-high", previous_high), ("prior-10-low", previous_low)):
            item = {
                "type": kind, "status": "forming", "timeframe": "D", "barTime": bars[end]["time"],
                "boundary": boundary, "close": float(bars[end]["close"]), "atr14Previous": previous_atr,
                "rvol20Previous": (float(bars[end]["volume"]) / (sum(float(row["volume"]) for row in bars[end - 20:end]) / 20)
                                    if end >= 20 and sum(float(row["volume"]) for row in bars[end - 20:end]) > 0 else None),
                "volumeEvidence": "volume-confirmed" if end >= 20 and sum(float(row["volume"]) for row in bars[end - 20:end]) > 0
                                  and float(bars[end]["volume"]) / (sum(float(row["volume"]) for row in bars[end - 20:end]) / 20) >= 1.2
                                  else "volume-insufficient",
            }
            structures.append({"family": "horizontal", "status": item["status"], "timeframe": "D",
                               "barTime": bars[end]["time"], "measurements": _collect_measurements(item, "horizontal")})
        statuses["horizontal"] = "ready"
    elif len(bars) >= 21:
        statuses["horizontal"] = "partial-data"

    highs, lows = _pivots(bars, end)
    flags = _flag_candidates(bars, atr, highs, lows) if len(bars) >= 21 else []
    if flags:
        for item in flags:
            structures.append({"family": "flag", "status": "forming", "timeframe": "D",
                               "barTime": item["barTime"], "measurements": _collect_measurements(item, "flag")})
    statuses["flag"] = "ready" if flags else "no-geometry" if len(bars) >= 31 else "insufficient-data"
    triangle = _triangle_candidate(bars, atr, highs, lows) if len(bars) >= 21 else None
    if triangle:
        structures.append({"family": "triangle", "status": "forming", "timeframe": "D",
                           "barTime": triangle["barTime"], "measurements": _collect_measurements(triangle, "triangle")})
    statuses["triangle"] = "ready" if triangle else "no-geometry" if len(bars) >= 31 else "insufficient-data"
    return structures, statuses


def _validate_bars(candles: Sequence[Mapping[str, object]], requested_as_of: str) -> list[dict[str, object]]:
    selected: list[dict[str, object]] = []
    seen: set[str] = set()
    for raw in candles:
        stamp = raw.get("time")
        if not isinstance(stamp, str):
            raise ValueError("invalid-daily-bar-date")
        try:
            parsed = date.fromisoformat(stamp)
        except ValueError as error:
            raise ValueError("invalid-daily-bar-date") from error
        if parsed.isoformat() != stamp:
            raise ValueError("invalid-daily-bar-date")
        if stamp > requested_as_of:
            continue
        if stamp in seen:
            raise ValueError("duplicate-daily-bar-date")
        row = {"time": stamp}
        for key in ("open", "high", "low", "close", "volume"):
            number = _number(raw.get(key))
            if number is None or number <= 0 and key != "volume" or key == "volume" and number < 0:
                raise ValueError("invalid-daily-ohlcv")
            row[key] = number
        if (float(row["high"]) < max(float(row["open"]), float(row["low"]), float(row["close"]))
                or float(row["low"]) > min(float(row["open"]), float(row["high"]), float(row["close"]))):
            raise ValueError("invalid-daily-ohlcv")
        seen.add(stamp)
        selected.append(row)
    selected.sort(key=lambda row: str(row["time"]))
    return selected


def build_indicator_chart_data(
    candles: Sequence[Mapping[str, object]], requested_as_of: str
) -> dict[str, object]:
    """Build aligned chart bars from validated adjusted OHLCV, without I/O."""
    if not isinstance(requested_as_of, str):
        raise ValueError("requested-as-of-must-be-YYYY-MM-DD")
    try:
        parsed_as_of = date.fromisoformat(requested_as_of)
    except ValueError as error:
        raise ValueError("requested-as-of-must-be-YYYY-MM-DD") from error
    if parsed_as_of.isoformat() != requested_as_of:
        raise ValueError("requested-as-of-must-be-YYYY-MM-DD")

    bars = _validate_bars(candles, requested_as_of)
    closes = [float(row["close"]) for row in bars]
    moving = {f"sma{period}": _sma(closes, period) for period in _PERIODS}
    rsi = _rsi_series(closes)
    atr = _atr(bars)
    fast, slow = _ema(closes, 12), _ema(closes, 26)
    macd = [fast[i] - slow[i] if fast[i] is not None and slow[i] is not None else math.nan
            for i in range(len(bars))]
    signal = _ema(macd, 9)
    obv: list[float] = []
    for index, row in enumerate(bars):
        direction = (1 if closes[index] > closes[index - 1] else -1 if closes[index] < closes[index - 1] else 0) if index else 0
        obv.append((obv[-1] if obv else 0.0) + direction * float(row["volume"]))

    start = max(0, len(bars) - 380)
    chart_bars = []
    for index in range(start, len(bars)):
        chart_bars.append({
            **bars[index],
            **{name: series[index] for name, series in moving.items()},
            "rsi14": rsi[index],
            "macd": macd[index] if math.isfinite(macd[index]) else None,
            "macdSignal": signal[index] if signal[index] is not None and math.isfinite(signal[index]) else None,
            "macdHistogram": (macd[index] - signal[index]
                              if math.isfinite(macd[index]) and signal[index] is not None and math.isfinite(signal[index])
                              else None),
            "obv": obv[index],
            "atr14": atr[index],
        })
    return {"bars": chart_bars}


def build_indicator_snapshot(
    *,
    code: str,
    symbol: str,
    market: str,
    requested_as_of: str,
    candles: Sequence[Mapping[str, object]],
    source: str,
    source_fetched_at: str | None,
    source_date: str | None = None,
    bar_status: str = "unknown",
    confirmed_policy: str = "unknown",
    cache_hit: bool | None = None,
    cache_age: float | None = None,
    stale: bool | None = None,
    last_success_at: str | None = None,
    source_calculation_version: str | None = None,
) -> dict[str, object]:
    """Build schema-v1 indicators from adjusted daily bars without I/O.

    ``candles`` must contain normalized adjusted OHLCV rows with ISO ``time``.
    Rows after ``requested_as_of`` are ignored; all calculations use the remaining
    ascending date prefix. Provider/source freshness facts are caller-supplied.
    """
    if not isinstance(requested_as_of, str):
        raise ValueError("requested-as-of-must-be-YYYY-MM-DD")
    try:
        parsed_as_of = date.fromisoformat(requested_as_of)
    except ValueError as error:
        raise ValueError("requested-as-of-must-be-YYYY-MM-DD") from error
    if parsed_as_of.isoformat() != requested_as_of:
        raise ValueError("requested-as-of-must-be-YYYY-MM-DD")
    if not isinstance(code, str) or len(code) != 6 or not code.isascii() or not code.isdecimal():
        raise ValueError("code-must-be-six-digits")
    if not isinstance(market, str) or market not in {"KOSPI", "KOSDAQ", "unknown"}:
        raise ValueError("market-must-be-KOSPI-KOSDAQ-or-unknown")
    expected_symbol = f"{code}.KS" if market == "KOSPI" else f"{code}.KQ" if market == "KOSDAQ" else code
    if not isinstance(symbol, str) or symbol != expected_symbol:
        raise ValueError("symbol-does-not-match-market")
    if not isinstance(source, str) or not source:
        raise ValueError("source-required")
    if not isinstance(confirmed_policy, str):
        raise ValueError("invalid-confirmed-policy")
    for value, field in (
        (source_fetched_at, "source-fetched-at"),
        (source_date, "source-date"),
        (last_success_at, "last-success-at"),
        (source_calculation_version, "source-calculation-version"),
    ):
        if value is not None and not isinstance(value, str):
            raise ValueError(f"invalid-{field}")
    if bar_status not in {"confirmed", "provisional", "unknown"}:
        raise ValueError("invalid-bar-status")
    for value, field in ((cache_hit, "cache-hit"), (stale, "stale")):
        if value is not None and not isinstance(value, bool):
            raise ValueError(f"invalid-{field}")
    if cache_age is not None and (_number(cache_age) is None or float(cache_age) < 0):
        raise ValueError("invalid-cache-age")

    bars = _validate_bars(candles, requested_as_of)
    closes = [float(row["close"]) for row in bars]
    volumes = [float(row["volume"]) for row in bars]
    moving: dict[str, float | None] = {}
    for kind, compute in (("sma", _sma), ("ema", _ema), ("wma", _wma)):
        for period in _PERIODS:
            series = compute(closes, period)
            moving[f"{kind}{period}"] = series[-1] if series else None
    moving_values = list(moving.values())

    bb = _bollinger(closes)
    donchian = _donchian(bars)
    rsi, atr_series = _rsi(closes), _atr(bars)
    atr = atr_series[-1] if atr_series else None
    ratio = volumes[-1] / (sum(volumes[-20:]) / 20) if len(volumes) >= 20 and sum(volumes[-20:]) > 0 else None
    fast, slow = _ema(closes, 12), _ema(closes, 26)
    macd_series = [fast[i] - slow[i] if fast[i] is not None and slow[i] is not None else math.nan
                   for i in range(len(bars))]
    signal = _ema(macd_series, 9)
    macd_line = macd_series[-1] if macd_series and math.isfinite(macd_series[-1]) else None
    signal_line = signal[-1] if signal and signal[-1] is not None and math.isfinite(signal[-1]) else None
    histogram = macd_line - signal_line if macd_line is not None and signal_line is not None else None
    obv_values: list[float] = []
    for index, row in enumerate(bars):
        change = (1 if closes[index] > closes[index - 1] else -1 if closes[index] < closes[index - 1] else 0) if index else 0
        obv_values.append((obv_values[-1] if obv_values else 0.0) + change * float(row["volume"]))
    obv = obv_values[-1] if obv_values else None
    delta5 = obv_values[-1] - obv_values[-6] if len(obv_values) >= 6 else None
    profile = _volume_profile(bars)
    structures, structure_status = _structures(bars, atr_series)
    price = {key: (float(bars[-1][key]) if bars else None)
             for key in ("open", "high", "low", "close", "volume")}
    macd_obj = {"macd": macd_line, "signal": signal_line, "histogram": histogram}
    volume_status = "ready" if price["volume"] is not None and ratio is not None else "partial-data" if price["volume"] is not None else "insufficient-data"
    obv_status = "ready" if obv is not None and delta5 is not None else "partial-data" if obv is not None else "insufficient-data"
    revision_payload = json.dumps(bars, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    data_revision = "sha256:" + hashlib.sha256(revision_payload).hexdigest()

    return {
        "schemaVersion": 1,
        "code": code,
        "symbol": symbol,
        "market": market,
        "timeframe": "D",
        "requestedAsOf": requested_as_of,
        "barAsOf": bars[-1]["time"] if bars else None,
        "source": source,
        "sourceFetchedAt": source_fetched_at,
        "sourceDate": source_date or max((str(row["time"]) for row in candles), default=None),
        "barStatus": bar_status if bars else "unknown",
        "confirmedPolicy": confirmed_policy,
        "cacheHit": cache_hit,
        "cacheAge": float(cache_age) if cache_age is not None else None,
        "stale": stale,
        "lastSuccessAt": last_success_at or source_fetched_at,
        "dataRevision": data_revision,
        "calculationVersion": CALCULATION_VERSION,
        "sourceCalculationVersion": source_calculation_version,
        "calculationBasis": {
            "ohlcv": "provider-adjusted daily candles",
            "cutoff": "last candle on or before requestedAsOf; calculations use only that prefix",
            "candlePrecision": "source OHLC precision preserved; volume as provided",
            "sourceSeries": "all indicators calculated from the same adjusted OHLCV prefix",
        },
        "price": price,
        "indicators": {
            "movingAverages": {**moving, "status": _status(moving_values),
                                "calculationVersion": TECHNICAL_VERSION,
                                "emaSeedPolicy": "sma-period",
                                "wmaWeights": "linear-oldest-1-newest-period"},
            "bollinger20": {**(bb or {"middle": None, "upper": None, "lower": None}),
                            "status": _status(list((bb or {"middle": None, "upper": None, "lower": None}).values())),
                            "period": 20, "multiplier": 2, "stddev": "population",
                            "calculationVersion": TECHNICAL_VERSION},
            "donchian20": {**(donchian or {"upper": None, "middle": None, "lower": None}),
                           "status": _status(list((donchian or {"upper": None, "middle": None, "lower": None}).values())),
                           "period": 20, "includeCurrent": True,
                           "calculationVersion": TECHNICAL_VERSION},
            "rsi14": {"value": rsi, "status": "ready" if rsi is not None else "insufficient-data",
                      "provisional": True if bar_status == "provisional" else False if bar_status == "confirmed" else None,
                      "method": "wilder", "seedPolicy": "simple-average-14-changes"},
            "atr14": {"value": atr, "status": "ready" if atr is not None else "insufficient-data",
                      "provisional": True if bar_status == "provisional" else False if bar_status == "confirmed" else None,
                      "method": "wilder", "seedPolicy": "simple-average-14-true-ranges"},
            "volume": {"barVolume": price["volume"], "ratio20": ratio, "status": volume_status,
                       "period": 20, "includeCurrent": True},
            "macd129": {**macd_obj, "status": _status(list(macd_obj.values())),
                        "fast": 12, "slow": 26, "signalPeriod": 9,
                        "seedPolicy": "sma-period", "calculationVersion": TECHNICAL_VERSION},
            "obv": {"value": obv, "delta5": delta5,
                    "seedTime": bars[0]["time"] if bars else None, "status": obv_status,
                    "delta5Status": "ready" if delta5 is not None else "insufficient-data",
                    "seedPolicy": "first-bar-zero-stop-on-gap", "calculationVersion": TECHNICAL_VERSION},
            "volumeProfile12": profile,
        },
        "structures": structures,
        "structureStatus": structure_status,
    }
