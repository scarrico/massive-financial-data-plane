import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from _paths import add_work_board_repo

add_work_board_repo()

from data_plane.request import execute_data_plane_request


class DataPlaneRequestTests(unittest.TestCase):
    def test_register_plan_and_seed_prefetch(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            requests_path = root / "requests.json"
            db_path = root / "board.sqlite"

            registered = execute_data_plane_request(
                {
                    "action": "register_request",
                    "requests_path": str(requests_path),
                    "strategy": "demo",
                    "symbols": ["msft", "AAPL"],
                }
            )
            plan = execute_data_plane_request(
                {
                    "action": "plan",
                    "requests_path": str(requests_path),
                }
            )
            seeded = execute_data_plane_request(
                {
                    "action": "seed_prefetch",
                    "requests_path": str(requests_path),
                    "start": "2024-01-01",
                    "end": "2026-05-20",
                    "backend": "sqlite",
                    "db_path": str(db_path),
                    "symbols_per_card": 2,
                }
            )
            status = execute_data_plane_request(
                {
                    "action": "status",
                    "backend": "sqlite",
                    "db_path": str(db_path),
                }
            )

        self.assertEqual(registered["symbols"], ["AAPL", "MSFT"])
        self.assertEqual(plan["count"], 2)
        self.assertEqual(seeded["seeded"], 1)
        self.assertEqual(status["counts"]["todo"], 1)

    def test_handler_returns_json_envelope(self):
        with TemporaryDirectory() as tmp:
            db_path = str(Path(tmp) / "board.sqlite")
            root = Path(__file__).resolve().parents[1]
            request = {
                "action": "seed_prefetch",
                "symbols": ["AAPL"],
                "start": "2024-01-01",
                "end": "2026-05-20",
                "backend": "sqlite",
                "db_path": db_path,
            }
            result = subprocess.run(
                [sys.executable, str(root / "data_plane_handler.py")],
                input=json.dumps(request),
                text=True,
                capture_output=True,
                check=True,
                cwd=root,
            )
            envelope = json.loads(result.stdout)

        self.assertTrue(envelope["ok"])
        self.assertEqual(envelope["result"]["seeded"], 1)


if __name__ == "__main__":
    unittest.main()
