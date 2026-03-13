from __future__ import annotations

import os
import sys

if __name__ == "__main__" and (__package__ is None or __package__ == ""):
  # `python backend/app/init_db.py` 실행 시에도 workspace 루트를 import 경로에 포함
  sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.app.bootstrap import init_database


def main() -> None:
  init_database()
  print("Database initialized.")


if __name__ == "__main__":
  main()
