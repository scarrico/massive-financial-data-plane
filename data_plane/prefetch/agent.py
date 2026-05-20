#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from dataclasses import asdict
from pathlib import Path
from time import perf_counter

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agent_runtime.worker_loop import run_worker_loop
from data_plane.prefetch.jobs import finish_symbol_cycle, payload_symbols
from data_plane.prefetch.massive_fetcher import prefetch_massive_to_parquet
from data_plane.prefetch.rate_limit import RateLimiter


def main() -> None:
    parser = argparse.ArgumentParser(description="Medium-lived Massive prefetch agent process.")
    parser.add_argument("--board", default="data-prefetch")
    parser.add_argument("--worker-id")
    parser.add_argument("--transport", default="local", choices=["local", "pubnub"])
    parser.add_argument("--registry-db", default="agent_runtime.sqlite")
    parser.add_argument("--backend", default="jira")
    parser.add_argument("--board-client", default="local")
    parser.add_argument("--board-url")
    parser.add_argument("--ssh-host")
    parser.add_argument("--ssh-root")
    parser.add_argument("--ssh-python", default="python3.11")
    parser.add_argument("--ssh-user")
    parser.add_argument("--ssh-port", type=int)
    parser.add_argument("--ssh-key")
    parser.add_argument("--db-path", default="kanban.sqlite")
    parser.add_argument("--run-id")
    parser.add_argument("--claim-mode", default="direct", choices=["direct", "supervisor"])
    parser.add_argument("--artifact-dir", default="data/data_plane/prefetch")
    parser.add_argument("--massive-limit", "--polygon-limit", dest="massive_limit", type=int, default=50000)
    parser.add_argument("--massive-calls-per-minute", "--polygon-calls-per-minute", dest="massive_calls_per_minute", type=float, default=60)
    parser.add_argument("--min-symbol-seconds", type=float, default=4.0)
    parser.add_argument("--max-cards", type=int)
    parser.add_argument("--idle-sleep", type=float, default=2.0)
    args = parser.parse_args()

    rate_limiter = RateLimiter(args.massive_calls_per_minute)

    def process_card(card, agent_id):
        payload = dict(card.payload)
        if payload.get("job_type") != "market_data_prefetch":
            raise ValueError("unsupported job_type")
        if payload.get("provider") not in {"massive", "polygon"}:
            raise ValueError("unsupported provider")
        results = []
        for symbol in payload_symbols(payload):
            started = perf_counter()
            result = prefetch_massive_to_parquet(
                symbol=symbol,
                start=payload["start"],
                end=payload["end"],
                interval=payload["interval"],
                artifact_dir=args.artifact_dir,
                limit=args.massive_limit,
                rate_limiter=rate_limiter,
            )
            elapsed = finish_symbol_cycle(started, args.min_symbol_seconds)
            results.append({**asdict(result), "elapsed_seconds": round(elapsed, 3)})
        if not results:
            raise ValueError("missing symbols")
        return {
            "artifact_kind": "massive_parquet",
            "artifacts": results,
            "downloaded": len(results),
        }

    run_worker_loop(
        capability="massive_prefetch",
        process_card=process_card,
        board_id=args.board,
        worker_id=args.worker_id,
        transport=args.transport,
        registry_db=args.registry_db,
        backend=args.backend,
        board_client=args.board_client,
        board_url=args.board_url,
        ssh_host=args.ssh_host,
        ssh_root=args.ssh_root,
        ssh_python=args.ssh_python,
        ssh_user=args.ssh_user,
        ssh_port=args.ssh_port,
        ssh_key=args.ssh_key,
        db_path=args.db_path,
        run_id=args.run_id,
        claim_mode=args.claim_mode,
        idle_sleep=args.idle_sleep,
        max_cards=args.max_cards,
    )


if __name__ == "__main__":
    main()
