#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from data_plane.board_args import add_board_args, board_client_kwargs
from data_plane.technicals.public_features import compute_public_features
from kanban.client import create_board_client
from kanban.config import load_dotenv


def main() -> None:
    parser = argparse.ArgumentParser(description="Claim downloaded market-data cards and write public technical feature artifacts.")
    add_board_args(parser, default_backend="sqlite")
    parser.add_argument("--worker-id", required=True)
    parser.add_argument("--limit", type=int, default=1)
    parser.add_argument("--artifact-dir", default="data/data_plane/technicals")
    args = parser.parse_args()

    load_dotenv()
    board = create_board_client(args.board_client, **board_client_kwargs(args))

    completed = []
    for _ in range(args.limit):
        card = board.claim_next(args.worker_id, strategy="priority_fifo", columns=("technicals",))
        if card is None:
            break
        try:
            if card.payload.get("job_type") not in {"public_technicals", "market_data_prefetch"}:
                raise ValueError("unsupported job_type")
            outputs = []
            for artifact in card.payload.get("artifacts") or []:
                symbol = artifact["symbol"]
                interval = artifact.get("interval") or card.payload.get("interval") or "1d"
                output_path = Path(args.artifact_dir) / interval / f"{symbol}.parquet"
                feature = compute_public_features(artifact["artifact_path"], output_path)
                outputs.append({"symbol": symbol, "interval": interval, **feature})
            if not outputs:
                raise ValueError("missing downloaded artifacts")
            done = board.move_done(
                card.id,
                actor=args.worker_id,
                payload_update={
                    "feature_artifact_kind": "public_technicals_parquet",
                    "feature_artifacts": outputs,
                    "featured": len(outputs),
                },
            )
            completed.append(asdict(done))
        except Exception as exc:
            failed = board.move_failed(card.id, actor=args.worker_id, error=str(exc))
            completed.append(asdict(failed))

    print(json.dumps(completed, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
