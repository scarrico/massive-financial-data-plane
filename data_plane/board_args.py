from __future__ import annotations


def add_board_args(parser, default_backend: str = "jira") -> None:
    parser.add_argument("--backend", default=default_backend)
    parser.add_argument("--board-client", default="local")
    parser.add_argument("--board-url")
    parser.add_argument("--ssh-host")
    parser.add_argument("--ssh-root")
    parser.add_argument("--ssh-python", default="python3.11")
    parser.add_argument("--ssh-user")
    parser.add_argument("--ssh-port", type=int)
    parser.add_argument("--ssh-key")
    parser.add_argument("--db-path", default="kanban.sqlite")
    parser.add_argument("--board", default="data-prefetch")


def board_client_kwargs(args) -> dict:
    return {
        "board_id": args.board,
        "backend": args.backend,
        "board_url": args.board_url,
        "db_path": args.db_path,
        "ssh_host": args.ssh_host,
        "ssh_root": args.ssh_root,
        "ssh_python": args.ssh_python,
        "ssh_user": args.ssh_user,
        "ssh_port": args.ssh_port,
        "ssh_key": args.ssh_key,
    }
