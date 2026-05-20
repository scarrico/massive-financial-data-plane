from __future__ import annotations

from time import perf_counter, sleep


def payload_symbols(payload: dict) -> list[str]:
    if "symbols" in payload:
        return [str(symbol).strip().upper() for symbol in payload["symbols"] if str(symbol).strip()]
    if "symbol" in payload:
        symbol = str(payload["symbol"]).strip().upper()
        return [symbol] if symbol else []
    return []


def finish_symbol_cycle(started_at: float, min_seconds: float) -> float:
    elapsed = perf_counter() - started_at
    remaining = max(float(min_seconds) - elapsed, 0.0)
    if remaining:
        sleep(remaining)
    return perf_counter() - started_at
