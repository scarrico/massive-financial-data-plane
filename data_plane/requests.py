from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class DataRequest:
    strategy: str
    symbols: list[str]
    interval: str = "1d"
    provider: str = "massive"
    enabled: bool = True


def normalize_symbol(symbol: str) -> str:
    return symbol.strip().upper()


def load_requests(path: str | Path) -> list[DataRequest]:
    request_path = Path(path)
    if not request_path.exists():
        return []
    raw = json.loads(request_path.read_text())
    return [DataRequest(**item) for item in raw]


def save_requests(path: str | Path, requests: Iterable[DataRequest]) -> None:
    request_path = Path(path)
    request_path.parent.mkdir(parents=True, exist_ok=True)
    request_path.write_text(json.dumps([asdict(item) for item in requests], indent=2, sort_keys=True) + "\n")


def register_request(path: str | Path, request: DataRequest) -> DataRequest:
    requests = [item for item in load_requests(path) if item.strategy != request.strategy]
    normalized = DataRequest(
        strategy=request.strategy,
        symbols=sorted({normalize_symbol(symbol) for symbol in request.symbols if normalize_symbol(symbol)}),
        interval=request.interval,
        provider=request.provider,
        enabled=request.enabled,
    )
    requests.append(normalized)
    requests.sort(key=lambda item: item.strategy)
    save_requests(path, requests)
    return normalized


def requested_symbols(requests: Iterable[DataRequest], interval: str | None = None, provider: str | None = None) -> list[str]:
    symbols: set[str] = set()
    for request in requests:
        if not request.enabled:
            continue
        if interval is not None and request.interval != interval:
            continue
        if provider is not None and _provider_key(request.provider) != _provider_key(provider):
            continue
        symbols.update(normalize_symbol(symbol) for symbol in request.symbols)
    return sorted(symbol for symbol in symbols if symbol)


def _provider_key(provider: str) -> str:
    return "massive" if provider == "polygon" else provider
