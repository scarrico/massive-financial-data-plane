from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd

from kanban.config import load_dotenv, required_env


MASSIVE_RENAME_COLS = {
    "o": "Open",
    "l": "Low",
    "h": "High",
    "c": "Close",
    "v": "Volume",
    "vw": "Vwap",
}

MASSIVE_MAX_AGGS_LIMIT = 50000
DEFAULT_MASSIVE_CALLS_PER_MINUTE = 60

INTERVAL_TO_MASSIVE = {
    "1d": (1, "day"),
    "1day": (1, "day"),
    "1wk": (1, "week"),
    "1week": (1, "week"),
    "1h": (1, "hour"),
    "1hour": (1, "hour"),
    "1m": (1, "minute"),
    "1min": (1, "minute"),
}


@dataclass(frozen=True)
class PrefetchResult:
    symbol: str
    provider: str
    interval: str
    start: str
    end: str
    artifact_path: str
    rows: int
    min_timestamp: str | None
    max_timestamp: str | None


def fetch_massive_bars(
    symbol: str,
    start: str,
    end: str,
    interval: str = "1d",
    adjusted: bool = True,
    limit: int = MASSIVE_MAX_AGGS_LIMIT,
) -> pd.DataFrame:
    load_dotenv()
    api_key = _provider_api_key()
    multiplier, timespan = _interval_to_massive(interval)
    client = _rest_client(api_key)
    aggs = client.get_aggs(
        ticker=symbol,
        multiplier=multiplier,
        timespan=timespan,
        from_=start,
        to=end,
        adjusted=adjusted,
        sort="asc",
        limit=limit,
    )
    rows = []
    for agg in aggs:
        rows.append(_agg_to_dict(agg))
    if not rows:
        return _empty_frame(symbol)

    data = pd.DataFrame(rows)
    data["timestamp"] = pd.to_datetime(data["t"], unit="ms", origin="unix", utc=True)
    data["timestamp"] = data["timestamp"].dt.tz_convert("US/Eastern").dt.tz_localize(None)
    data = data.rename(columns=MASSIVE_RENAME_COLS)
    data["ticker"] = symbol
    data["Adj Close"] = data["Close"]
    data["Date_str"] = data["timestamp"].dt.strftime("%Y-%m-%d")
    data = data.set_index("timestamp").sort_index()
    keep = ["ticker", "Open", "High", "Low", "Close", "Adj Close", "Volume", "Date_str"]
    optional = [col for col in ["Vwap", "n"] if col in data.columns]
    return data[keep + optional]


def prefetch_massive_to_parquet(
    symbol: str,
    start: str,
    end: str,
    interval: str,
    artifact_dir: str | Path,
    limit: int = MASSIVE_MAX_AGGS_LIMIT,
    rate_limiter=None,
) -> PrefetchResult:
    artifact_dir = Path(artifact_dir)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    if rate_limiter is not None:
        rate_limiter.wait()
    data = fetch_massive_bars(symbol, start, end, interval, limit=limit)
    artifact_path = artifact_dir / interval / f"{clean_symbol(symbol)}.parquet"
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    data.to_parquet(artifact_path, index=True)
    return PrefetchResult(
        symbol=symbol,
        provider="massive",
        interval=interval,
        start=start,
        end=end,
        artifact_path=str(artifact_path),
        rows=int(len(data)),
        min_timestamp=data.index.min().isoformat() if len(data) else None,
        max_timestamp=data.index.max().isoformat() if len(data) else None,
    )


def clean_symbol(symbol: str) -> str:
    return str(symbol).replace("/", "_").replace("^", "INDEX_").replace(".", "_").upper()


def _interval_to_massive(interval: str) -> tuple[int, str]:
    key = interval.lower()
    if key not in INTERVAL_TO_MASSIVE:
        raise ValueError(f"Unsupported Massive interval: {interval}")
    return INTERVAL_TO_MASSIVE[key]


def _provider_api_key() -> str:
    if os.environ.get("MASSIVE_API_KEY"):
        return required_env("MASSIVE_API_KEY")
    if os.environ.get("POLYGON_API_KEY"):
        return required_env("POLYGON_API_KEY")
    raise RuntimeError("Missing required environment variable: MASSIVE_API_KEY")


def _rest_client(api_key: str):
    try:
        from massive import RESTClient
    except ImportError:
        from polygon import RESTClient
    return RESTClient(api_key=api_key)


POLYGON_RENAME_COLS = MASSIVE_RENAME_COLS
POLYGON_MAX_AGGS_LIMIT = MASSIVE_MAX_AGGS_LIMIT
DEFAULT_POLYGON_CALLS_PER_MINUTE = DEFAULT_MASSIVE_CALLS_PER_MINUTE
INTERVAL_TO_POLYGON = INTERVAL_TO_MASSIVE
fetch_polygon_bars = fetch_massive_bars
prefetch_polygon_to_parquet = prefetch_massive_to_parquet
_interval_to_polygon = _interval_to_massive


def _agg_to_dict(agg) -> dict:
    if isinstance(agg, dict):
        raw = agg
    elif hasattr(agg, "__dict__"):
        raw = dict(agg.__dict__)
    else:
        raw = {}
    result = dict(raw)
    for source, target in [
        ("open", "o"),
        ("high", "h"),
        ("low", "l"),
        ("close", "c"),
        ("volume", "v"),
        ("vwap", "vw"),
        ("timestamp", "t"),
        ("transactions", "n"),
    ]:
        if source in raw and target not in result:
            result[target] = raw[source]
        elif hasattr(agg, source) and target not in result:
            result[target] = getattr(agg, source)
    return result


def _empty_frame(symbol: str) -> pd.DataFrame:
    index = pd.DatetimeIndex([], name="timestamp")
    return pd.DataFrame(
        columns=["ticker", "Open", "High", "Low", "Close", "Adj Close", "Volume", "Date_str"],
        index=index,
    )
