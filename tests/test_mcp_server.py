import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from _paths import add_work_board_repo

add_work_board_repo()

from data_plane.mcp_server import data_plane_status, register_data_request, seed_prefetch_cards, write_stock_bars_parquet


class MassiveMCPServerTests(unittest.TestCase):
    def test_mcp_tools_use_data_plane_request_boundary(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            requests_path = root / "requests.json"
            db_path = root / "kanban.sqlite"

            registered = register_data_request("demo", ["msft", "AAPL"], requests_path=str(requests_path))
            seeded = seed_prefetch_cards(
                "2024-01-01",
                "2024-02-01",
                requests_path=str(requests_path),
                db_path=str(db_path),
                symbols_per_card=2,
            )
            status = data_plane_status(db_path=str(db_path))

        self.assertEqual(registered["symbols"], ["AAPL", "MSFT"])
        self.assertEqual(seeded["seeded"], 1)
        self.assertEqual(status["counts"]["todo"], 1)

    def test_write_stock_bars_parquet_can_use_demo_data(self):
        with TemporaryDirectory() as tmp:
            result = write_stock_bars_parquet("AAPL", "2024-01-01", "2024-01-31", artifact_dir=tmp, live=False)

        self.assertEqual(result["symbol"], "AAPL")
        self.assertGreater(result["rows"], 10)
        self.assertTrue(result["artifact_path"].endswith("AAPL.parquet"))


if __name__ == "__main__":
    unittest.main()
