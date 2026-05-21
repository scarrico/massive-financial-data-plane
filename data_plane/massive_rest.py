from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from data_plane.prefetch.massive_fetcher import _provider_api_key
from kanban.config import load_dotenv


MASSIVE_API_BASE = "https://api.massive.com"


def massive_get(path: str, params: dict[str, Any] | None = None, timeout: float = 30.0) -> dict[str, Any]:
    load_dotenv()
    query = {key: value for key, value in (params or {}).items() if value is not None}
    query["apiKey"] = _provider_api_key()
    url = f"{MASSIVE_API_BASE}{path}?{urlencode(query, doseq=True)}"
    request = Request(url, headers={"Accept": "application/json"})
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def get_last_quote(symbol: str, timeout: float = 30.0) -> dict[str, Any]:
    return massive_get(f"/v2/last/nbbo/{symbol.upper()}", timeout=timeout)


def get_last_trade(symbol: str, timeout: float = 30.0) -> dict[str, Any]:
    return massive_get(f"/v2/last/trade/{symbol.upper()}", timeout=timeout)


def get_stock_snapshot(symbol: str, timeout: float = 30.0) -> dict[str, Any]:
    return massive_get(f"/v2/snapshot/locale/us/markets/stocks/tickers/{symbol.upper()}", timeout=timeout)


def list_stock_quotes(
    symbol: str,
    timestamp: str | None = None,
    timestamp_gte: str | None = None,
    timestamp_lte: str | None = None,
    limit: int = 10,
    order: str = "desc",
    sort: str = "timestamp",
    timeout: float = 30.0,
) -> dict[str, Any]:
    return massive_get(
        f"/v3/quotes/{symbol.upper()}",
        params={
            "timestamp": timestamp,
            "timestamp.gte": timestamp_gte,
            "timestamp.lte": timestamp_lte,
            "limit": limit,
            "order": order,
            "sort": sort,
        },
        timeout=timeout,
    )
