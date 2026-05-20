#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from data_plane.board_args import add_board_args, board_client_kwargs
from data_plane.technicals.jobs import artifact_chunks
from kanban.client import create_board_client
from kanban.config import load_dotenv


def main() -> None:
    parser = argparse.ArgumentParser(description="Split downloaded market-data cards into technical feature work cards.")
    add_board_args(parser, default_backend="sqlite")
    parser.add_argument("--worker-id", default="technicals-planner")
    parser.add_argument("--limit", type=int, default=1)
    parser.add_argument("--artifacts-per-card", type=int, default=25)
    parser.add_argument("--priority", type=int, default=10)
    args = parser.parse_args()

    load_dotenv()
    board = create_board_client(args.board_client, **board_client_kwargs(args))

    completed = []
    for _ in range(args.limit):
        parent = board.claim_next(args.worker_id, strategy="priority_fifo", columns=("technicals",))
        if parent is None:
            break
        try:
            artifacts = parent.payload.get("artifacts") or []
            if not artifacts:
                raise ValueError("missing downloaded artifacts")
            child_cards = []
            for index, chunk in enumerate(artifact_chunks(artifacts, args.artifacts_per_card), start=1):
                title = f"Technicals {parent.id} part {index} ({len(chunk)} symbols)"
                child = board.add_card(
                    title,
                    payload={
                        "job_type": "public_technicals",
                        "source_card_id": parent.id,
                        "artifacts": chunk,
                    },
                    priority=args.priority,
                    actor=args.worker_id,
                )
                child = board.move_technicals(child.id, actor=args.worker_id)
                child_cards.append(asdict(child))
            parent_done = board.move_done(
                parent.id,
                actor=args.worker_id,
                payload_update={
                    "technical_work_cards": [card["id"] for card in child_cards],
                    "technical_work_card_count": len(child_cards),
                    "artifacts_per_card": args.artifacts_per_card,
                },
            )
            completed.append({"parent": asdict(parent_done), "children": child_cards})
        except Exception as exc:
            failed = board.move_failed(parent.id, actor=args.worker_id, error=str(exc))
            completed.append({"parent": asdict(failed), "children": []})

    print(json.dumps(completed, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
