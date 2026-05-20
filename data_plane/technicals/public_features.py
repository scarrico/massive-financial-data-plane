from __future__ import annotations

from pathlib import Path

import pandas as pd


def compute_public_features(price_path: str | Path, output_path: str | Path) -> dict:
    data = pd.read_parquet(price_path).sort_index()
    features = pd.DataFrame(index=data.index)
    features["ticker"] = data["ticker"]
    features["Close"] = data["Close"]
    features["return_1d"] = data["Close"].pct_change()
    features["sma_20"] = data["Close"].rolling(20).mean()
    features["atr_14"] = atr(data, 14)
    features["rsi_14"] = rsi(data["Close"], 14)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    features.to_parquet(output, index=True)
    return {
        "artifact_path": str(output),
        "rows": int(len(features)),
        "columns": list(features.columns),
    }


def atr(data: pd.DataFrame, window: int) -> pd.Series:
    previous_close = data["Close"].shift(1)
    true_range = pd.concat(
        [
            data["High"] - data["Low"],
            (data["High"] - previous_close).abs(),
            (data["Low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return true_range.rolling(window).mean()


def rsi(close: pd.Series, window: int) -> pd.Series:
    delta = close.diff()
    gains = delta.clip(lower=0)
    losses = -delta.clip(upper=0)
    average_gain = gains.rolling(window).mean()
    average_loss = losses.rolling(window).mean()
    relative_strength = average_gain / average_loss
    return 100 - (100 / (1 + relative_strength))
