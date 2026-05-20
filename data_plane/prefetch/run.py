#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from kanban.config import load_dotenv


def main() -> None:
    parser = argparse.ArgumentParser(description="Prefetch data via Kanban when available, otherwise plain parallel workers.")
    parser.add_argument("symbols", nargs="+")
    parser.add_argument("--start", default="2024-01-01")
    parser.add_argument("--end", default="2026-05-20")
    parser.add_argument("--interval", default="1d")
    parser.add_argument("--artifact-dir", default="data/data_plane/prefetch")
    parser.add_argument("--board", default="data-prefetch")
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
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--massive-limit", "--polygon-limit", dest="massive_limit", type=int, default=50000)
    parser.add_argument("--massive-calls-per-minute", "--polygon-calls-per-minute", dest="massive_calls_per_minute", type=float, default=60)
    parser.add_argument("--min-symbol-seconds", type=float, default=4.0)
    parser.add_argument("--symbols-per-card", type=int, default=2)
    parser.add_argument("--mode", choices=["auto", "kanban", "parallel"], default="auto")
    args = parser.parse_args()

    load_dotenv()
    if args.mode == "parallel":
        run_parallel(args)
        return
    if args.mode == "kanban":
        run_kanban(args)
        return
    try:
        run_kanban(args)
    except Exception as exc:
        print(json.dumps({"mode": "parallel_fallback", "reason": str(exc)}, indent=2), file=sys.stderr)
        run_parallel(args)


def run_parallel(args) -> None:
    cmd = [
        sys.executable,
        str(Path(__file__).with_name("parallel_runner.py")),
        *args.symbols,
        "--start", args.start,
        "--end", args.end,
        "--interval", args.interval,
        "--artifact-dir", args.artifact_dir,
        "--workers", str(args.workers),
        "--massive-limit", str(args.massive_limit),
        "--massive-calls-per-minute", str(args.massive_calls_per_minute),
    ]
    subprocess.run(cmd, check=True)


def run_kanban(args) -> None:
    seed_cmd = [
        sys.executable,
        str(Path(__file__).with_name("seed_jobs.py")),
        *args.symbols,
        "--board", args.board,
        "--backend", args.backend,
        "--board-client", args.board_client,
        "--db-path", args.db_path,
        "--start", args.start,
        "--end", args.end,
        "--interval", args.interval,
        "--priority", "10",
        "--provider", "massive",
        "--symbols-per-card", str(args.symbols_per_card),
    ]
    if args.board_url:
        seed_cmd.extend(["--board-url", args.board_url])
    add_ssh_args(seed_cmd, args)
    subprocess.run(seed_cmd, check=True)
    for index in range(args.workers):
        worker_cmd = [
            sys.executable,
            str(Path(__file__).with_name("worker.py")),
            "--board", args.board,
            "--backend", args.backend,
            "--board-client", args.board_client,
            "--db-path", args.db_path,
            "--worker-id", f"prefetch-worker-{index + 1}",
            "--limit", str((len(args.symbols) // args.workers) + 2),
            "--artifact-dir", args.artifact_dir,
            "--massive-limit", str(args.massive_limit),
            "--massive-calls-per-minute", str(args.massive_calls_per_minute),
            "--min-symbol-seconds", str(args.min_symbol_seconds),
        ]
        if args.board_url:
            worker_cmd.extend(["--board-url", args.board_url])
        add_ssh_args(worker_cmd, args)
        subprocess.run(worker_cmd, check=True)


def add_ssh_args(cmd: list[str], args) -> None:
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


if __name__ == "__main__":
    main()
