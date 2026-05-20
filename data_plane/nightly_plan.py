#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from data_plane.requests import DataRequest, load_requests, register_request, requested_symbols


DEFAULT_REQUESTS_PATH = "data/data_plane/requests.json"


def main() -> None:
    parser = argparse.ArgumentParser(description="Build nightly data-plane requests.")
    parser.add_argument("--requests", default=DEFAULT_REQUESTS_PATH)
    sub = parser.add_subparsers(dest="command", required=True)

    register = sub.add_parser("register", help="Register symbols requested by a strategy")
    register.add_argument("strategy")
    register.add_argument("symbols", nargs="+")
    register.add_argument("--interval", default="1d")
    register.add_argument("--provider", default="massive")
    register.add_argument("--disabled", action="store_true")

    register_file = sub.add_parser("register-file", help="Register symbols from a CSV file")
    register_file.add_argument("strategy")
    register_file.add_argument("path")
    register_file.add_argument("--column", default="ticker")
    register_file.add_argument("--limit", type=int)
    register_file.add_argument("--interval", default="1d")
    register_file.add_argument("--provider", default="massive")
    register_file.add_argument("--disabled", action="store_true")

    plan = sub.add_parser("plan", help="Print the deduplicated symbols for the nightly run")
    plan.add_argument("--interval", default="1d")
    plan.add_argument("--provider", default="massive")

    seed = sub.add_parser("seed-prefetch", help="Seed prefetch jobs for the nightly run")
    seed.add_argument("--interval", default="1d")
    seed.add_argument("--provider", default="massive")
    seed.add_argument("--start", required=True)
    seed.add_argument("--end", required=True)
    seed.add_argument("--board", default="data-prefetch")
    seed.add_argument("--backend", default="sqlite")
    seed.add_argument("--board-client", default="local")
    seed.add_argument("--board-url")
    seed.add_argument("--ssh-host")
    seed.add_argument("--ssh-root")
    seed.add_argument("--ssh-python", default="python3.11")
    seed.add_argument("--ssh-user")
    seed.add_argument("--ssh-port", type=int)
    seed.add_argument("--ssh-key")
    seed.add_argument("--db-path", default="kanban.sqlite")
    seed.add_argument("--priority", type=int, default=10)
    seed.add_argument("--symbols-per-card", type=int, default=2)

    args = parser.parse_args()
    if args.command == "register":
        request = register_request(
            args.requests,
            DataRequest(
                strategy=args.strategy,
                symbols=args.symbols,
                interval=args.interval,
                provider=args.provider,
                enabled=not args.disabled,
            ),
        )
        print(json.dumps(asdict(request), indent=2, sort_keys=True))
        return
    if args.command == "register-file":
        symbols = read_symbols_csv(args.path, args.column, args.limit)
        request = register_request(
            args.requests,
            DataRequest(
                strategy=args.strategy,
                symbols=symbols,
                interval=args.interval,
                provider=args.provider,
                enabled=not args.disabled,
            ),
        )
        print(json.dumps(asdict(request), indent=2, sort_keys=True))
        return

    requests = load_requests(args.requests)
    symbols = requested_symbols(requests, interval=args.interval, provider=args.provider)
    if args.command == "plan":
        print(json.dumps({"symbols": symbols, "count": len(symbols)}, indent=2, sort_keys=True))
        return
    if args.command == "seed-prefetch":
        if not symbols:
            print(json.dumps({"symbols": [], "seeded": 0}, indent=2, sort_keys=True))
            return
        cmd = [
            sys.executable,
            str(Path(__file__).parent / "prefetch" / "seed_jobs.py"),
            *symbols,
            "--board", args.board,
            "--backend", args.backend,
            "--board-client", args.board_client,
            "--db-path", args.db_path,
            "--start", args.start,
            "--end", args.end,
            "--interval", args.interval,
            "--priority", str(args.priority),
            "--provider", args.provider,
            "--symbols-per-card", str(args.symbols_per_card),
        ]
        if args.board_url:
            cmd.extend(["--board-url", args.board_url])
        for attr, flag in [
            ("ssh_host", "--ssh-host"),
            ("ssh_root", "--ssh-root"),
            ("ssh_python", "--ssh-python"),
            ("ssh_user", "--ssh-user"),
            ("ssh_key", "--ssh-key"),
        ]:
            value = getattr(args, attr)
            if value:
                cmd.extend([flag, str(value)])
        if args.ssh_port is not None:
            cmd.extend(["--ssh-port", str(args.ssh_port)])
        subprocess.run(cmd, check=True)


def read_symbols_csv(path: str | Path, column: str, limit: int | None = None) -> list[str]:
    symbols = []
    with Path(path).open(newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            symbol = (row.get(column) or "").strip()
            if not symbol:
                continue
            symbols.append(symbol)
            if limit is not None and len(symbols) >= limit:
                break
    return symbols


if __name__ == "__main__":
    main()
