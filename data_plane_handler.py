#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

work_board_repo = Path(__file__).resolve().parents[1] / "agent-work-boards"
if work_board_repo.exists():
    sys.path.insert(0, str(work_board_repo))

from data_plane.request import execute_data_plane_request
from kanban.config import load_dotenv


def main() -> None:
    load_dotenv()
    request = json.load(sys.stdin)
    try:
        output = {"ok": True, "result": execute_data_plane_request(request)}
    except Exception as exc:
        output = {"ok": False, "error": str(exc)}
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
