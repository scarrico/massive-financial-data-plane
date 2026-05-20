import sys
from pathlib import Path


def add_work_board_repo() -> None:
    work_board_repo = Path(__file__).resolve().parents[2] / "agent-work-boards"
    if work_board_repo.exists():
        sys.path.insert(0, str(work_board_repo))
