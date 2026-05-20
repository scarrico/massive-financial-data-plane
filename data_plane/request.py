from __future__ import annotations

from dataclasses import asdict
from typing import Any

from data_plane.prefetch.seed_jobs import symbol_chunks
from data_plane.requests import DataRequest, load_requests, register_request, requested_symbols
from data_plane.technicals.jobs import artifact_chunks
from kanban.client import create_board_client


DEFAULT_REQUESTS_PATH = "data/data_plane/requests.json"


def execute_data_plane_request(request: dict[str, Any]) -> dict[str, Any] | list[dict[str, Any]]:
    action = request["action"]
    if action == "register_request":
        saved = register_request(
            request.get("requests_path") or DEFAULT_REQUESTS_PATH,
            DataRequest(
                strategy=request["strategy"],
                symbols=list(request["symbols"]),
                interval=request.get("interval", "1d"),
                provider=request.get("provider", "massive"),
                enabled=bool(request.get("enabled", True)),
            ),
        )
        return asdict(saved)
    if action == "plan":
        symbols = requested_symbols(
            load_requests(request.get("requests_path") or DEFAULT_REQUESTS_PATH),
            interval=request.get("interval", "1d"),
            provider=request.get("provider", "massive"),
        )
        return {"symbols": symbols, "count": len(symbols)}
    if action == "seed_prefetch":
        symbols = list(request.get("symbols") or requested_symbols(
            load_requests(request.get("requests_path") or DEFAULT_REQUESTS_PATH),
            interval=request.get("interval", "1d"),
            provider=request.get("provider", "massive"),
        ))
        board = _board(request)
        cards = []
        for chunk in symbol_chunks(symbols, int(request.get("symbols_per_card", 2))):
            symbol_payload = {"symbol": chunk[0]} if len(chunk) == 1 else {"symbols": chunk}
            title = f"Prefetch {chunk[0]}" if len(chunk) == 1 else f"Prefetch {chunk[0]}..{chunk[-1]} ({len(chunk)} symbols)"
            card = board.add_card(
                title,
                payload={
                    "job_type": "market_data_prefetch",
                    **symbol_payload,
                    "provider": request.get("provider", "massive"),
                    "start": request["start"],
                    "end": request["end"],
                    "interval": request.get("interval", "1d"),
                },
                priority=int(request.get("priority", 10)),
                actor=request.get("actor", "massive-financial-data-plane"),
            )
            cards.append(asdict(card))
        return {"seeded": len(cards), "cards": cards}
    if action == "plan_technicals":
        board = _board(request)
        worker_id = request.get("worker_id", "technicals-planner")
        parent = board.claim_next(worker_id, strategy="priority_fifo", columns=("technicals",))
        if parent is None:
            return {"planned": 0, "parent": None, "children": []}
        artifacts = parent.payload.get("artifacts") or []
        if not artifacts:
            failed = board.move_failed(parent.id, actor=worker_id, error="missing downloaded artifacts")
            return {"planned": 0, "parent": asdict(failed), "children": []}
        children = []
        for index, chunk in enumerate(artifact_chunks(artifacts, int(request.get("artifacts_per_card", 2))), start=1):
            child = board.add_card(
                f"Technicals {parent.id} part {index} ({len(chunk)} symbols)",
                payload={"job_type": "public_technicals", "source_card_id": parent.id, "artifacts": chunk},
                priority=int(request.get("priority", 10)),
                actor=worker_id,
            )
            child = board.move_technicals(child.id, actor=worker_id)
            children.append(asdict(child))
        done = board.move_done(
            parent.id,
            actor=worker_id,
            payload_update={
                "technical_work_cards": [child["id"] for child in children],
                "technical_work_card_count": len(children),
                "artifacts_per_card": int(request.get("artifacts_per_card", 2)),
            },
        )
        return {"planned": len(children), "parent": asdict(done), "children": children}
    if action == "status":
        board = _board(request)
        return {"counts": board.counts(), "cards": [asdict(card) for card in board.list_cards(request.get("column"))]}
    raise ValueError(f"Unsupported data plane action: {action}")


def _board(request: dict[str, Any]):
    return create_board_client(
        request.get("board_client", "local"),
        board_id=request.get("board_id", "data-prefetch"),
        backend=request.get("backend", "sqlite"),
        board_url=request.get("board_url"),
        db_path=request.get("db_path", "kanban.sqlite"),
        ssh_host=request.get("ssh_host"),
        ssh_root=request.get("ssh_root"),
        ssh_python=request.get("ssh_python", "python3.11"),
        ssh_user=request.get("ssh_user"),
        ssh_port=request.get("ssh_port"),
        ssh_key=request.get("ssh_key"),
    )
