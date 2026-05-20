import tempfile
import unittest
from pathlib import Path

from _paths import add_work_board_repo

add_work_board_repo()

from data_plane.requests import DataRequest, load_requests, register_request, requested_symbols
from data_plane.prefetch.jobs import payload_symbols
from data_plane.prefetch.seed_jobs import symbol_chunks
from data_plane.nightly_plan import read_symbols_csv


class DataRequestTests(unittest.TestCase):
    def test_register_request_normalizes_and_replaces_strategy(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "requests.json"

            register_request(path, DataRequest(strategy="alpha", symbols=["msft", "AAPL", "aapl"]))
            register_request(path, DataRequest(strategy="alpha", symbols=["spy"]))

            requests = load_requests(path)
            self.assertEqual(len(requests), 1)
            self.assertEqual(requests[0].symbols, ["SPY"])

    def test_requested_symbols_deduplicates_enabled_requests(self):
        requests = [
            DataRequest(strategy="alpha", symbols=["AAPL", "MSFT"]),
            DataRequest(strategy="beta", symbols=["msft", "SPY"]),
            DataRequest(strategy="gamma", symbols=["QQQ"], enabled=False),
        ]

        self.assertEqual(requested_symbols(requests), ["AAPL", "MSFT", "SPY"])

    def test_symbol_chunks_default_shape(self):
        self.assertEqual(symbol_chunks(["aapl", "msft", "spy"], 2), [["AAPL", "MSFT"], ["SPY"]])

    def test_payload_symbols_accepts_single_or_chunk(self):
        self.assertEqual(payload_symbols({"symbol": "aapl"}), ["AAPL"])
        self.assertEqual(payload_symbols({"symbols": ["aapl", "MSFT"]}), ["AAPL", "MSFT"])

    def test_read_symbols_csv_uses_named_column_and_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "symbols.csv"
            path.write_text("Company,ticker\nA,AAPL\nB,MSFT\nC,SPY\n")

            self.assertEqual(read_symbols_csv(path, "ticker", limit=2), ["AAPL", "MSFT"])


if __name__ == "__main__":
    unittest.main()
