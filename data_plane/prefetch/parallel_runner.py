#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from kanban.config import load_dotenv
from data_plane.prefetch.massive_fetcher import prefetch_massive_to_parquet
from data_plane.prefetch.rate_limit import RateLimiter


def main() -> None:
    parser = argparse.ArgumentParser(description="Plain local parallel Massive prefetch fallback.")
    parser.add_argument("symbols", nargs="+")
    parser.add_argument("--start", default="2024-01-01")
    parser.add_argument("--end", default="2026-05-20")
    parser.add_argument("--interval", default="1d")
    parser.add_argument("--artifact-dir", default="data/data_plane/prefetch")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--massive-limit", "--polygon-limit", dest="massive_limit", type=int, default=50000)
    parser.add_argument("--massive-calls-per-minute", "--polygon-calls-per-minute", dest="massive_calls_per_minute", type=float, default=60)
    args = parser.parse_args()

    load_dotenv()
    results = []
    rate_limiter = RateLimiter(args.massive_calls_per_minute)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(
                prefetch_massive_to_parquet,
                symbol.upper(),
                args.start,
                args.end,
                args.interval,
                args.artifact_dir,
                args.massive_limit,
                rate_limiter,
            ): symbol.upper()
            for symbol in args.symbols
        }
        for future in as_completed(futures):
            symbol = futures[future]
            try:
                results.append({"status": "done", **asdict(future.result())})
            except Exception as exc:
                results.append({"status": "failed", "symbol": symbol, "error": str(exc)})

    print(json.dumps(sorted(results, key=lambda row: row["symbol"]), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
