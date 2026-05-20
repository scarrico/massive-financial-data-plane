#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from data_plane.board_args import add_board_args, board_client_kwargs
from kanban.config import load_dotenv
from kanban.client import create_board_client


def symbol_chunks(symbols: list[str], size: int) -> list[list[str]]:
    if size < 1:
        raise ValueError("symbols_per_card must be at least 1")
    normalized = [symbol.strip().upper() for symbol in symbols if symbol.strip()]
    return [normalized[index : index + size] for index in range(0, len(normalized), size)]


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed market-data prefetch jobs onto a Kanban board.")
    parser.add_argument("symbols", nargs="+")
    add_board_args(parser)
    parser.add_argument("--start", default="2024-01-01")
    parser.add_argument("--end", default="2026-05-20")
    parser.add_argument("--interval", default="1d")
    parser.add_argument("--priority", type=int, default=0)
    parser.add_argument("--provider", default="massive")
    parser.add_argument("--symbols-per-card", type=int, default=100)
    args = parser.parse_args()

    load_dotenv()
    board = create_board_client(args.board_client, **board_client_kwargs(args))
    cards = []
    for symbols in symbol_chunks(args.symbols, args.symbols_per_card):
        if len(symbols) == 1:
            title = f"Prefetch {symbols[0]}"
            symbol_payload = {"symbol": symbols[0]}
        else:
            title = f"Prefetch {symbols[0]}..{symbols[-1]} ({len(symbols)} symbols)"
            symbol_payload = {"symbols": symbols}
        card = board.add_card(
            title,
            payload={
                "job_type": "market_data_prefetch",
                **symbol_payload,
                "provider": args.provider,
                "start": args.start,
                "end": args.end,
                "interval": args.interval,
            },
            priority=args.priority,
            actor="prefetch-seeder",
        )
        cards.append(asdict(card))

    print(json.dumps(cards, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
