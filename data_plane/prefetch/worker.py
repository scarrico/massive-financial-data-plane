#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from time import perf_counter, sleep

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from data_plane.board_args import add_board_args, board_client_kwargs
from kanban.client import create_board_client
from kanban.config import load_dotenv
from kanban.workflows import complete_work_item
from data_plane.prefetch.jobs import finish_symbol_cycle, payload_symbols
from data_plane.prefetch.massive_fetcher import prefetch_massive_to_parquet
from data_plane.prefetch.rate_limit import RateLimiter


def main() -> None:
    parser = argparse.ArgumentParser(description="Claim market-data prefetch jobs and write Massive Parquet artifacts.")
    add_board_args(parser)
    parser.add_argument("--worker-id", required=True)
    parser.add_argument("--limit", type=int, default=1)
    parser.add_argument("--artifact-dir", default="data/data_plane/prefetch")
    parser.add_argument("--massive-limit", "--polygon-limit", dest="massive_limit", type=int, default=50000)
    parser.add_argument("--massive-calls-per-minute", "--polygon-calls-per-minute", dest="massive_calls_per_minute", type=float, default=60)
    parser.add_argument("--min-symbol-seconds", type=float, default=4.0)
    parser.add_argument("--sleep", type=float, default=0.0)
    args = parser.parse_args()

    load_dotenv()
    board = create_board_client(args.board_client, **board_client_kwargs(args))
    rate_limiter = RateLimiter(args.massive_calls_per_minute)
    artifact_dir = Path(args.artifact_dir)
    artifact_dir.mkdir(parents=True, exist_ok=True)

    completed = []
    for _ in range(args.limit):
        card = board.claim_next(args.worker_id, strategy="priority_fifo")
        if card is None:
            break
        payload = dict(card.payload)
        if payload.get("job_type") != "market_data_prefetch":
            board.move_blocked(card.id, actor=args.worker_id, error="unsupported job_type")
            continue
        if payload.get("provider") not in {"massive", "polygon"}:
            board.move_blocked(card.id, actor=args.worker_id, error="unsupported provider")
            continue

        if args.sleep:
            sleep(args.sleep)

        try:
            results = []
            for symbol in payload_symbols(payload):
                started = perf_counter()
                result = prefetch_massive_to_parquet(
                    symbol=symbol,
                    start=payload["start"],
                    end=payload["end"],
                    interval=payload["interval"],
                    artifact_dir=artifact_dir,
                    limit=args.massive_limit,
                    rate_limiter=rate_limiter,
                )
                elapsed = finish_symbol_cycle(started, args.min_symbol_seconds)
                results.append({**asdict(result), "elapsed_seconds": round(elapsed, 3)})
            if not results:
                raise ValueError("missing symbols")
            done = complete_work_item(
                board,
                card,
                actor=args.worker_id,
                payload_update={
                    "artifact_kind": "massive_parquet",
                    "artifacts": results,
                    "downloaded": len(results),
                },
            )
            completed.append(asdict(done))
        except Exception as exc:
            failed = board.move_failed(card.id, actor=args.worker_id, error=str(exc))
            completed.append(asdict(failed))

    print(json.dumps(completed, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
