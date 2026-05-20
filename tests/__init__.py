import sys
from pathlib import Path


WORK_BOARD_REPO = Path(__file__).resolve().parents[2] / "agent-work-boards"
if WORK_BOARD_REPO.exists():
    sys.path.insert(0, str(WORK_BOARD_REPO))
