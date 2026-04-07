# -*- coding: utf-8 -*-
"""
체크포인트 러너 전용 로거
콘솔 컬러 출력 + 날짜별 로그 파일 저장
"""
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
import logging
from datetime import datetime
from pathlib import Path

LOGS_DIR = Path(__file__).parent / "logs"

# ANSI 컬러
_RESET = "\033[0m"
_COLORS = {
    "DEBUG":    "\033[36m",   # 청록
    "INFO":     "\033[32m",   # 초록
    "WARNING":  "\033[33m",   # 노랑
    "ERROR":    "\033[31m",   # 빨강
    "CRITICAL": "\033[35m",   # 보라
}
_CHECKPOINT = "\033[34m"      # 파랑 – 체크포인트 전용


class _ColorFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        color = _COLORS.get(record.levelname, "")
        msg = super().format(record)
        return f"{color}{msg}{_RESET}"


def get_logger(name: str = "checkpoint") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    # 콘솔 핸들러
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(_ColorFormatter("[%(asctime)s] %(levelname)s  %(message)s", "%H:%M:%S"))
    logger.addHandler(ch)

    # 파일 핸들러
    LOGS_DIR.mkdir(exist_ok=True)
    log_file = LOGS_DIR / f"checkpoint_{datetime.now().strftime('%Y%m%d')}.log"
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        "[%(asctime)s] %(levelname)s  %(message)s", "%Y-%m-%d %H:%M:%S"
    ))
    logger.addHandler(fh)

    return logger


def checkpoint_line(logger: logging.Logger, msg: str) -> None:
    """체크포인트 전용 강조 출력."""
    print(f"{_CHECKPOINT}{'-'*60}")
    print(f"{_CHECKPOINT}  CHECKPOINT  {msg}{_RESET}")
    print(f"{_CHECKPOINT}{'-'*60}{_RESET}")
    logger.debug(f"[CHECKPOINT] {msg}")
