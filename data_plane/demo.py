#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parents[1]
work_board_repo = repo_root.parent / "agent-work-boards"
sys.path.insert(0, str(repo_root))
if work_board_repo.exists():
    sys.path.insert(0, str(work_board_repo))

from data_plane.requests import DataRequest, register_request
from kanban.client import LocalBoardClient


DEFAULT_SYMBOLS = ["AAPL", "MSFT", "NVDA", "SPY"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a small end-to-end Massive data-plane demo.")
    parser.add_argument("--root", default="demo_data/massive_pipeline")
    parser.add_argument("--symbols", nargs="*", default=DEFAULT_SYMBOLS)
    parser.add_argument("--start", default="2024-01-01")
    parser.add_argument("--end", default="2024-03-31")
    parser.add_argument("--symbols-per-card", type=int, default=2)
    parser.add_argument("--artifacts-per-card", type=int, default=2)
    parser.add_argument("--prefetch-workers", type=int, default=2)
    parser.add_argument("--technicals-workers", type=int, default=2)
    parser.add_argument("--live", action="store_true", help="Call Massive instead of writing deterministic demo bars.")
    parser.add_argument("--keep", action="store_true", help="Keep the existing demo root instead of recreating it.")
    parser.add_argument("--verbose", action="store_true", help="Print child worker JSON output.")
    args = parser.parse_args()

    root = Path(args.root)
    if root.exists() and not args.keep:
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)

    db_path = root / "kanban.sqlite"
    board_id = "massive-demo"
    requests_path = root / "requests.json"
    prefetch_dir = root / "prefetch"
    technicals_dir = root / "technicals"

    saved = register_request(
        requests_path,
        DataRequest(strategy="demo-strategy", symbols=args.symbols, interval="1d", provider="massive"),
    )
    print(f"Registered {len(saved.symbols)} symbols: {', '.join(saved.symbols)}")

    prefetch_card_count = math.ceil(len(saved.symbols) / max(args.symbols_per_card, 1))
    technical_card_count = math.ceil(len(saved.symbols) / max(args.artifacts_per_card, 1))

    run(
        [
            sys.executable,
            "data_plane/nightly_plan.py",
            "--requests",
            str(requests_path),
            "seed-prefetch",
            "--start",
            args.start,
            "--end",
            args.end,
            "--board",
            board_id,
            "--backend",
            "sqlite",
            "--db-path",
            str(db_path),
            "--symbols-per-card",
            str(args.symbols_per_card),
        ],
        verbose=args.verbose,
    )

    prefetch_commands = []
    for index in range(min(args.prefetch_workers, prefetch_card_count)):
        command = [
            sys.executable,
            "data_plane/prefetch/worker.py",
            "--backend",
            "sqlite",
            "--db-path",
            str(db_path),
            "--board",
            board_id,
            "--worker-id",
            f"prefetch-{index + 1:02d}",
            "--limit",
            str(math.ceil(prefetch_card_count / max(args.prefetch_workers, 1))),
            "--artifact-dir",
            str(prefetch_dir),
            "--min-symbol-seconds",
            "0",
        ]
        if not args.live:
            command.append("--demo-data")
        prefetch_commands.append(command)
    run_many(prefetch_commands, verbose=args.verbose)

    run(
        [
            sys.executable,
            "data_plane/technicals/planner.py",
            "--backend",
            "sqlite",
            "--db-path",
            str(db_path),
            "--board",
            board_id,
            "--limit",
            str(prefetch_card_count),
            "--artifacts-per-card",
            str(args.artifacts_per_card),
        ],
        verbose=args.verbose,
    )

    technical_commands = []
    for index in range(min(args.technicals_workers, technical_card_count)):
        technical_commands.append(
            [
                sys.executable,
                "data_plane/technicals/worker.py",
                "--backend",
                "sqlite",
                "--db-path",
                str(db_path),
                "--board",
                board_id,
                "--worker-id",
                f"technicals-{index + 1:02d}",
                "--limit",
                str(math.ceil(technical_card_count / max(args.technicals_workers, 1))),
                "--artifact-dir",
                str(technicals_dir),
            ]
        )
    run_many(technical_commands, verbose=args.verbose)

    board = LocalBoardClient(board_id=board_id, backend="sqlite", db_path=str(db_path))
    price_files = sorted(prefetch_dir.rglob("*.parquet"))
    feature_files = sorted(technicals_dir.rglob("*.parquet"))
    summary = {
        "board_counts": board.counts(),
        "db_path": str(db_path),
        "prefetch_artifacts": [str(path) for path in price_files],
        "technical_artifacts": [str(path) for path in feature_files],
        "price_artifact_count": len(price_files),
        "technical_artifact_count": len(feature_files),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    if len(price_files) < len(saved.symbols) or len(feature_files) < len(saved.symbols):
        raise SystemExit("demo did not produce all expected artifacts")


def run(command: list[str], verbose: bool = False) -> None:
    print("+ " + " ".join(command))
    result = subprocess.run(command, check=False, env=_child_env(), text=True, capture_output=not verbose)
    if result.returncode != 0:
        if not verbose:
            print(result.stdout, end="")
            print(result.stderr, end="", file=sys.stderr)
        raise subprocess.CalledProcessError(result.returncode, command)


def run_many(commands: list[list[str]], verbose: bool = False) -> None:
    print(f"Starting {len(commands)} worker process(es)")
    env = _child_env()
    processes = [
        subprocess.Popen(command, env=env, text=True, stdout=None if verbose else subprocess.PIPE, stderr=None if verbose else subprocess.PIPE)
        for command in commands
    ]
    failed = []
    for command, process in zip(commands, processes):
        stdout, stderr = process.communicate()
        code = process.returncode
        if code != 0:
            if not verbose:
                print(stdout or "", end="")
                print(stderr or "", end="", file=sys.stderr)
            failed.append((command, code))
    if failed:
        command, code = failed[0]
        raise subprocess.CalledProcessError(code, command)


def _child_env() -> dict[str, str]:
    paths = [str(repo_root)]
    if work_board_repo.exists():
        paths.append(str(work_board_repo))
    existing = os.environ.get("PYTHONPATH")
    if existing:
        paths.append(existing)
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(paths)
    return env


if __name__ == "__main__":
    main()
