#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hanness Framework Runner
========================
MVP 구현 작업을 .page 명세 → .task 체크포인트 방식으로 직렬 실행한다.

사용법:
  python hanness/runner.py --status          # 전체 페이지 상태 출력
  python hanness/runner.py --page P01        # 단일 페이지 명세 출력
  python hanness/runner.py --validate P01    # P01 수락 기준 수동 검증 모드

Step 2 (체크포인트 시스템)에서 --build 플래그와 자동 실행 로직이 추가된다.
"""
from __future__ import annotations

import argparse
import re
import sys
import io
from datetime import datetime
from pathlib import Path

# Windows 터미널 UTF-8 출력
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent
PAGES_DIR = ROOT / "pages"
TASKS_DIR = ROOT / "tasks"

PAGE_ORDER = ["P01", "P02", "P03", "P04", "P05", "P06", "P07", "P08", "P09"]

PAGE_NAMES = {
    "P01": "공통 레이아웃 & 인프라",
    "P02": "홈 / 워드클라우드 메인",
    "P03": "농산물 시세 분석",
    "P04": "카테고리 분석 공통 템플릿",
    "P05": "로그인 / 인증 UX",
    "P06": "마이페이지 대시보드",
    "P07": "저장된 분석 목록",
    "P08": "분석 빌더 / 상세 보기",
    "P09": "ETL 파이프라인 & 인제스트 API",
}


def read_task(page_id: str) -> dict:
    task_file = TASKS_DIR / f"{page_id.lower()}.task"
    if not task_file.exists():
        return {"status": "missing"}
    content = task_file.read_text(encoding="utf-8")
    status_match = re.search(r"^status:\s*(\S+)", content, re.MULTILINE)
    checks = re.findall(r"- \[(x| )\]", content)
    total = len(checks)
    done = sum(1 for c in checks if c == "x")
    return {
        "status": status_match.group(1) if status_match else "unknown",
        "progress": f"{done}/{total}",
    }


def print_status():
    """전체 페이지 상태를 테이블로 출력."""
    print(f"\n{'ID':<6} {'이름':<30} {'상태':<15} {'진행'}")
    print("-" * 65)
    for pid in PAGE_ORDER:
        task = read_task(pid)
        name = PAGE_NAMES.get(pid, "")
        status = task.get("status", "?")
        progress = task.get("progress", "?")
        status_icon = {"pending": "[ ]", "in_progress": "[~]", "done": "[x]", "missing": "[!]"}.get(status, "?")
        print(f"{pid:<6} {name:<30} {status_icon} {status:<12} {progress}")
    print()


def print_page(page_id: str):
    """단일 .page 명세를 출력."""
    page_file = PAGES_DIR / f"{page_id.lower()}.page"
    if not page_file.exists():
        print(f"[ERROR] {page_file} 파일이 없습니다.")
        sys.exit(1)
    print(page_file.read_text(encoding="utf-8"))


def update_task_status(page_id: str, new_status: str):
    """task 파일의 status 필드를 업데이트."""
    task_file = TASKS_DIR / f"{page_id.lower()}.task"
    if not task_file.exists():
        print(f"[ERROR] {task_file} 파일이 없습니다.")
        return
    content = task_file.read_text(encoding="utf-8")
    now = datetime.now().isoformat(timespec="seconds")
    if new_status == "in_progress":
        content = re.sub(r"^started_at:.*$", f"started_at: {now}", content, flags=re.MULTILINE)
    elif new_status == "done":
        content = re.sub(r"^completed_at:.*$", f"completed_at: {now}", content, flags=re.MULTILINE)
    content = re.sub(r"^status:.*$", f"status: {new_status}", content, flags=re.MULTILINE)
    task_file.write_text(content, encoding="utf-8")
    print(f"[{page_id}] status → {new_status}")


def main():
    parser = argparse.ArgumentParser(description="Hanness Framework Runner")
    parser.add_argument("--status", action="store_true", help="전체 페이지 상태 출력")
    parser.add_argument("--page", metavar="ID", help="단일 페이지 명세 출력 (예: P01)")
    parser.add_argument("--validate", metavar="ID", help="수락 기준 체크리스트 출력")
    parser.add_argument("--start", metavar="ID", help="페이지를 in_progress로 마킹")
    parser.add_argument("--done", metavar="ID", help="페이지를 done으로 마킹")

    # Step 2에서 추가될 플래그 예약
    # parser.add_argument("--build", metavar="ID", help="에이전트로 자동 빌드 (Step 3)")
    # parser.add_argument("--all", action="store_true", help="전체 직렬 빌드 (Step 2+3)")

    args = parser.parse_args()

    if args.status:
        print_status()
    elif args.page:
        print_page(args.page.upper())
    elif args.validate:
        print_page(args.validate.upper())
        task = read_task(args.validate.upper())
        print(f"\n현재 상태: {task['status']} | 진행: {task['progress']}")
    elif args.start:
        update_task_status(args.start.upper(), "in_progress")
    elif args.done:
        update_task_status(args.done.upper(), "done")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
