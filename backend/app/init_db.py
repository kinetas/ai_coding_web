from __future__ import annotations

from backend.app.bootstrap import init_database


def main() -> None:
  init_database()
  print("Database initialized.")


if __name__ == "__main__":
  main()
