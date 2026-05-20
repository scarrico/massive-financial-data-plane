import tempfile
import unittest
from pathlib import Path

import pandas as pd

from data_plane.technicals.public_features import compute_public_features
from data_plane.technicals.jobs import artifact_chunks


class PublicTechnicalsTests(unittest.TestCase):
    def test_compute_public_features_writes_parquet(self):
        with tempfile.TemporaryDirectory() as tmp:
            price_path = Path(tmp) / "prices.parquet"
            output_path = Path(tmp) / "features.parquet"
            data = pd.DataFrame(
                {
                    "ticker": ["AAPL"] * 25,
                    "High": [float(value) + 1.0 for value in range(1, 26)],
                    "Low": [float(value) - 1.0 for value in range(1, 26)],
                    "Close": [float(value) for value in range(1, 26)],
                },
                index=pd.date_range("2024-01-01", periods=25),
            )
            data.to_parquet(price_path)

            result = compute_public_features(price_path, output_path)
            features = pd.read_parquet(output_path)

            self.assertEqual(result["rows"], 25)
            self.assertIn("return_1d", features.columns)
            self.assertIn("sma_20", features.columns)
            self.assertIn("atr_14", features.columns)
            self.assertIn("rsi_14", features.columns)
            self.assertEqual(features["sma_20"].iloc[-1], 15.5)
            self.assertEqual(features["atr_14"].iloc[-1], 2.0)
            self.assertEqual(features["rsi_14"].iloc[-1], 100.0)

    def test_artifact_chunks_splits_work(self):
        artifacts = [{"symbol": f"S{i}"} for i in range(5)]

        chunks = artifact_chunks(artifacts, 2)

        self.assertEqual([[item["symbol"] for item in chunk] for chunk in chunks], [["S0", "S1"], ["S2", "S3"], ["S4"]])


if __name__ == "__main__":
    unittest.main()
