"""Research-only Kronos backtest on stored KRX OHLCV rows.

This script is intentionally isolated from production code. It reads the local
SQLite DB, downloads/loads Kronos weights when allowed by the environment, and
prints a JSON comparison artifact. Do not import it from stock_monitor modules.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from statistics import mean
from typing import Any

import pandas as pd
import torch
from model import Kronos, KronosPredictor, KronosTokenizer


@dataclass(frozen=True)
class Candidate:
    business_date: date
    stock_code: str
    stock_name: str
    mention_count: int


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def _connect(db_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    return connection


def _load_candidates(
    connection: sqlite3.Connection,
    *,
    from_date: date,
    to_date: date,
    mention_threshold: int,
    limit: int,
) -> list[Candidate]:
    rows = connection.execute(
        """
        SELECT business_date, stock_code, stock_name, mention_count
        FROM daily_stock_summaries
        WHERE business_date BETWEEN ? AND ?
          AND stock_code IS NOT NULL
          AND mention_count >= ?
        ORDER BY business_date ASC, mention_count DESC, stock_name ASC, stock_code ASC
        LIMIT ?
        """,
        (from_date.isoformat(), to_date.isoformat(), mention_threshold, limit),
    ).fetchall()
    return [
        Candidate(
            business_date=date.fromisoformat(row["business_date"]),
            stock_code=str(row["stock_code"]),
            stock_name=str(row["stock_name"]),
            mention_count=int(row["mention_count"]),
        )
        for row in rows
    ]


def _load_history(
    connection: sqlite3.Connection,
    *,
    stock_code: str,
    business_date: date,
    lookback: int,
) -> pd.DataFrame:
    rows = connection.execute(
        """
        SELECT business_date, open_price, high_price, low_price, close_price, volume, turnover
        FROM stock_market_daily
        WHERE stock_code = ?
          AND business_date <= ?
          AND close_price IS NOT NULL
        ORDER BY business_date DESC
        LIMIT ?
        """,
        (stock_code, business_date.isoformat(), lookback),
    ).fetchall()
    ordered = list(reversed(rows))
    return pd.DataFrame(
        [
            {
                "timestamps": pd.Timestamp(row["business_date"]),
                "open": int(row["open_price"] or row["close_price"]),
                "high": int(row["high_price"] or row["close_price"]),
                "low": int(row["low_price"] or row["close_price"]),
                "close": int(row["close_price"]),
                "volume": int(row["volume"] or 0),
                "amount": int(row["turnover"] or 0),
            }
            for row in ordered
        ]
    )


def _load_future(
    connection: sqlite3.Connection,
    *,
    stock_code: str,
    business_date: date,
    horizon_days: int,
) -> pd.DataFrame:
    rows = connection.execute(
        """
        SELECT business_date, close_price
        FROM stock_market_daily
        WHERE stock_code = ?
          AND business_date > ?
          AND close_price IS NOT NULL
        ORDER BY business_date ASC
        LIMIT ?
        """,
        (stock_code, business_date.isoformat(), horizon_days),
    ).fetchall()
    return pd.DataFrame(
        [
            {
                "timestamps": pd.Timestamp(row["business_date"]),
                "close": int(row["close_price"]),
            }
            for row in rows
        ]
    )


def _bucket_average(rows: list[dict[str, Any]], *, positive: bool) -> dict[str, Any]:
    picked = [row for row in rows if bool(row["predicted_positive"]) is positive]
    available = [row for row in picked if row.get("actual_return_percent") is not None]
    return {
        "candidate_count": len(picked),
        "available_count": len(available),
        "average_actual_return_percent": round(mean(row["actual_return_percent"] for row in available), 4)
        if available
        else None,
        "rising_count": sum(1 for row in available if row["actual_return_percent"] > 0),
        "falling_count": sum(1 for row in available if row["actual_return_percent"] < 0),
    }


def _mention_bucket(value: int) -> str:
    if value >= 4:
        return "4+"
    return str(value)


def _group_summary(rows: list[dict[str, Any]], *, key: str) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault(str(row[key]), []).append(row)
    summary = []
    for group_key in sorted(groups):
        picked = groups[group_key]
        hits = [row for row in picked if row["direction_hit"]]
        actual_returns = [row["actual_return_percent"] for row in picked if row.get("actual_return_percent") is not None]
        predicted_returns = [row["predicted_return_percent"] for row in picked if row.get("predicted_return_percent") is not None]
        summary.append(
            {
                key: group_key,
                "count": len(picked),
                "direction_hit_rate": round(len(hits) / len(picked), 4) if picked else None,
                "average_predicted_return_percent": round(mean(predicted_returns), 4) if predicted_returns else None,
                "average_actual_return_percent": round(mean(actual_returns), 4) if actual_returns else None,
                "actual_rising_count": sum(1 for value in actual_returns if value > 0),
                "actual_falling_count": sum(1 for value in actual_returns if value < 0),
            }
        )
    return summary


def run_experiment(args: argparse.Namespace) -> dict[str, Any]:
    db_path = Path(args.db_path)
    device = "cuda" if args.device == "auto" and torch.cuda.is_available() else ("cpu" if args.device == "auto" else args.device)
    tokenizer = KronosTokenizer.from_pretrained(args.tokenizer, cache_dir=args.cache_dir)
    model = Kronos.from_pretrained(args.model, cache_dir=args.cache_dir)
    predictor = KronosPredictor(model, tokenizer, max_context=args.max_context, device=device)
    predictor.model.eval()

    results: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    with _connect(db_path) as connection:
        candidates = _load_candidates(
            connection,
            from_date=args.from_date,
            to_date=args.to_date,
            mention_threshold=args.mention_threshold,
            limit=args.max_candidates,
        )
        for candidate in candidates:
            history = _load_history(
                connection,
                stock_code=candidate.stock_code,
                business_date=candidate.business_date,
                lookback=args.lookback,
            )
            future = _load_future(
                connection,
                stock_code=candidate.stock_code,
                business_date=candidate.business_date,
                horizon_days=args.horizon_days,
            )
            if len(history) < args.min_lookback:
                skipped.append({"stock_code": candidate.stock_code, "reason": "insufficient_history", "history_rows": len(history)})
                continue
            if len(future) < args.horizon_days:
                skipped.append({"stock_code": candidate.stock_code, "reason": "insufficient_future", "future_rows": len(future)})
                continue
            x_df = history[["open", "high", "low", "close", "volume", "amount"]]
            x_timestamp = history["timestamps"]
            y_timestamp = future["timestamps"]
            pred_df = predictor.predict(
                df=x_df,
                x_timestamp=x_timestamp,
                y_timestamp=y_timestamp,
                pred_len=args.horizon_days,
                T=args.temperature,
                top_p=args.top_p,
                sample_count=args.sample_count,
                verbose=False,
            )
            current_close = float(history.iloc[-1]["close"])
            predicted_close = float(pred_df.iloc[-1]["close"])
            actual_close = float(future.iloc[-1]["close"])
            predicted_return = ((predicted_close - current_close) / current_close) * 100.0
            actual_return = ((actual_close - current_close) / current_close) * 100.0
            results.append(
                {
                    "business_date": candidate.business_date.isoformat(),
                    "stock_code": candidate.stock_code,
                    "stock_name": candidate.stock_name,
                    "mention_count": candidate.mention_count,
                    "mention_bucket": _mention_bucket(candidate.mention_count),
                    "month": candidate.business_date.isoformat()[:7],
                    "current_close": int(current_close),
                    "predicted_close": round(predicted_close, 4),
                    "actual_close": int(actual_close),
                    "predicted_return_percent": round(predicted_return, 4),
                    "actual_return_percent": round(actual_return, 4),
                    "predicted_positive": predicted_return > 0,
                    "actual_positive": actual_return > 0,
                    "direction_hit": (predicted_return > 0) == (actual_return > 0),
                }
            )

    hits = [row for row in results if row["direction_hit"]]
    payload: dict[str, Any] = {
        "surface": "experimental",
        "read_only": True,
        "production_integration": False,
        "public_score": False,
        "recommendation": False,
        "model": args.model,
        "tokenizer": args.tokenizer,
        "device": device,
        "from_date": args.from_date.isoformat(),
        "to_date": args.to_date.isoformat(),
        "horizon_days": args.horizon_days,
        "lookback": args.lookback,
        "candidate_count": len(results) + len(skipped),
        "evaluated_count": len(results),
        "skipped_count": len(skipped),
        "direction_hit_rate": round(len(hits) / len(results), 4) if results else None,
        "positive_prediction_bucket": _bucket_average(results, positive=True),
        "negative_prediction_bucket": _bucket_average(results, positive=False),
        "by_mention_bucket": _group_summary(results, key="mention_bucket"),
        "by_month": _group_summary(results, key="month"),
        "rows_omitted": bool(args.summary_only),
        "rows_omitted_count": len(results) if args.summary_only else 0,
        "skipped_omitted_count": len(skipped) if args.summary_only else 0,
    }
    if not args.summary_only:
        payload["rows"] = results
        payload["skipped"] = skipped
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db-path", default="data/stock_monitor.db")
    parser.add_argument("--from-date", type=_parse_date, required=True)
    parser.add_argument("--to-date", type=_parse_date, required=True)
    parser.add_argument("--mention-threshold", type=int, default=2)
    parser.add_argument("--horizon-days", type=int, default=20)
    parser.add_argument("--lookback", type=int, default=120)
    parser.add_argument("--min-lookback", type=int, default=40)
    parser.add_argument("--max-candidates", type=int, default=20)
    parser.add_argument("--model", default="NeoQuasar/Kronos-mini")
    parser.add_argument("--tokenizer", default="NeoQuasar/Kronos-Tokenizer-2k")
    parser.add_argument("--cache-dir", default="scripts/experimental/.hf-kronos")
    parser.add_argument("--device", default="auto", choices=("auto", "cpu", "cuda"))
    parser.add_argument("--max-context", type=int, default=512)
    parser.add_argument("--temperature", type=float, default=1.0)
    parser.add_argument("--top-p", type=float, default=0.9)
    parser.add_argument("--sample-count", type=int, default=1)
    parser.add_argument("--summary-only", action="store_true")
    args = parser.parse_args()
    payload = run_experiment(args)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
