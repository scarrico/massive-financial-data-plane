from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import sys
from typing import Any

work_board_repo = Path(__file__).resolve().parents[2] / "agent-work-boards"
if work_board_repo.exists():
    sys.path.insert(0, str(work_board_repo))

from data_plane.prefetch.massive_fetcher import (
    MASSIVE_MAX_AGGS_LIMIT,
    fetch_massive_bars,
    prefetch_massive_to_parquet,
    write_demo_bars_to_parquet,
)
from data_plane.request import DEFAULT_REQUESTS_PATH, execute_data_plane_request
from data_plane.massive_rest import get_last_quote, get_last_trade, get_stock_snapshot, list_stock_quotes
from kanban.config import load_dotenv


def register_data_request(
    strategy: str,
    symbols: list[str],
    interval: str = "1d",
    provider: str = "massive",
    enabled: bool = True,
    requests_path: str = DEFAULT_REQUESTS_PATH,
) -> dict[str, Any]:
    return execute_data_plane_request(
        {
            "action": "register_request",
            "strategy": strategy,
            "symbols": symbols,
            "interval": interval,
            "provider": provider,
            "enabled": enabled,
            "requests_path": requests_path,
        }
    )


def plan_requested_symbols(
    interval: str = "1d",
    provider: str = "massive",
    requests_path: str = DEFAULT_REQUESTS_PATH,
) -> dict[str, Any]:
    return execute_data_plane_request(
        {
            "action": "plan",
            "interval": interval,
            "provider": provider,
            "requests_path": requests_path,
        }
    )


def seed_prefetch_cards(
    start: str,
    end: str,
    symbols: list[str] | None = None,
    interval: str = "1d",
    provider: str = "massive",
    symbols_per_card: int = 2,
    priority: int = 10,
    board_client: str = "local",
    board_id: str = "data-prefetch",
    backend: str = "sqlite",
    db_path: str = "kanban.sqlite",
    requests_path: str = DEFAULT_REQUESTS_PATH,
) -> dict[str, Any]:
    return execute_data_plane_request(
        {
            "action": "seed_prefetch",
            "symbols": symbols,
            "start": start,
            "end": end,
            "interval": interval,
            "provider": provider,
            "symbols_per_card": symbols_per_card,
            "priority": priority,
            "board_client": board_client,
            "board_id": board_id,
            "backend": backend,
            "db_path": db_path,
            "requests_path": requests_path,
        }
    )


def plan_technical_cards(
    artifacts_per_card: int = 2,
    board_client: str = "local",
    board_id: str = "data-prefetch",
    backend: str = "sqlite",
    db_path: str = "kanban.sqlite",
    worker_id: str = "technicals-planner",
) -> dict[str, Any]:
    return execute_data_plane_request(
        {
            "action": "plan_technicals",
            "artifacts_per_card": artifacts_per_card,
            "board_client": board_client,
            "board_id": board_id,
            "backend": backend,
            "db_path": db_path,
            "worker_id": worker_id,
        }
    )


def data_plane_status(
    board_client: str = "local",
    board_id: str = "data-prefetch",
    backend: str = "sqlite",
    db_path: str = "kanban.sqlite",
    column: str | None = None,
) -> dict[str, Any] | list[dict[str, Any]]:
    return execute_data_plane_request(
        {
            "action": "status",
            "board_client": board_client,
            "board_id": board_id,
            "backend": backend,
            "db_path": db_path,
            "column": column,
        }
    )


def get_stock_bars(
    symbol: str,
    start: str,
    end: str,
    interval: str = "1d",
    adjusted: bool = True,
    limit: int = MASSIVE_MAX_AGGS_LIMIT,
    max_rows: int = 20,
) -> dict[str, Any]:
    data = fetch_massive_bars(symbol, start, end, interval=interval, adjusted=adjusted, limit=limit)
    sample = data.head(max_rows).reset_index()
    if "timestamp" in sample.columns:
        sample["timestamp"] = sample["timestamp"].astype(str)
    return {
        "symbol": symbol.upper(),
        "interval": interval,
        "start": start,
        "end": end,
        "rows": int(len(data)),
        "returned_rows": int(len(sample)),
        "data": sample.to_dict(orient="records"),
    }


def write_stock_bars_parquet(
    symbol: str,
    start: str,
    end: str,
    interval: str = "1d",
    artifact_dir: str = "data/market_data",
    live: bool = True,
) -> dict[str, Any]:
    if live:
        return asdict(prefetch_massive_to_parquet(symbol, start, end, interval, artifact_dir))
    return asdict(write_demo_bars_to_parquet(symbol, start, end, interval, artifact_dir))


def get_stock_last_quote(symbol: str, timeout: float = 30.0) -> dict[str, Any]:
    return get_last_quote(symbol, timeout=timeout)


def get_stock_last_trade(symbol: str, timeout: float = 30.0) -> dict[str, Any]:
    return get_last_trade(symbol, timeout=timeout)


def get_stock_quotes(
    symbol: str,
    timestamp: str | None = None,
    timestamp_gte: str | None = None,
    timestamp_lte: str | None = None,
    limit: int = 10,
    order: str = "desc",
    sort: str = "timestamp",
    timeout: float = 30.0,
) -> dict[str, Any]:
    return list_stock_quotes(
        symbol,
        timestamp=timestamp,
        timestamp_gte=timestamp_gte,
        timestamp_lte=timestamp_lte,
        limit=limit,
        order=order,
        sort=sort,
        timeout=timeout,
    )


def get_stock_market_snapshot(symbol: str, timeout: float = 30.0) -> dict[str, Any]:
    return get_stock_snapshot(symbol, timeout=timeout)


def build_mcp():
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:
        raise RuntimeError("Install the MCP extra to run MCP: python3.11 -m pip install -e '.[mcp]'") from exc

    mcp = FastMCP(
        "massive_financial_data_plane",
        instructions="Agent-friendly Massive market data and data-plane orchestration tools.",
    )
    for tool in [
        register_data_request,
        plan_requested_symbols,
        seed_prefetch_cards,
        plan_technical_cards,
        data_plane_status,
        get_stock_bars,
        write_stock_bars_parquet,
        get_stock_last_quote,
        get_stock_last_trade,
        get_stock_quotes,
        get_stock_market_snapshot,
    ]:
        mcp.tool()(tool)
    return mcp


def main() -> None:
    load_dotenv()
    build_mcp().run("stdio")


if __name__ == "__main__":
    main()
