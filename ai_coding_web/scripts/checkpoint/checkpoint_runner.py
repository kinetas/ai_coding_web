#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hanness 프레임워크 - 체크포인트 시스템 (직렬 처리)
=====================================================
사용법:
  python checkpoint_runner.py            # 이어서 실행 (resume)
  python checkpoint_runner.py --reset    # 상태 초기화 후 처음부터 실행
  python checkpoint_runner.py --status   # 현재 진행 상태만 출력
  python checkpoint_runner.py --list     # task 목록 출력

흐름:
  1. tasks/ 디렉터리의 .task 파일을 읽는다.
  2. 의존성(depends_on)을 고려해 위상 정렬한다.
  3. 이미 완료된 task는 건너뛴다 (체크포인트 복원).
  4. 각 task의 step을 하나씩 직렬로 실행한다.
  5. 매 step 완료 시 상태를 저장한다.
"""
from __future__ import annotations

import argparse
import io
import sys
import time
import traceback
from pathlib import Path
from typing import Callable

# Windows 콘솔 UTF-8 강제 설정
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# 같은 패키지 내 모듈
from task_parser import load_all_tasks, load_page_for_task, topological_sort, Task, Step
from state_manager import (
    load_state, save_state, reset_state, summary,
    mark_task_started, mark_task_done, mark_task_failed,
    mark_task_skipped, mark_step_done,
    is_task_done, is_task_failed,
    get_task_state,
)
from logger import get_logger, checkpoint_line

log = get_logger("checkpoint")

# ── Step 실행기 등록 테이블 ────────────────────────────────────────────────
# 실제 구현 단계에서 각 step description에 매핑되는 함수를 등록한다.
# 키: step description의 정규식 또는 정확한 문자열
# 값: Callable[[Task, Step, dict], None]  (state dict 전달)
_STEP_HANDLERS: dict[str, Callable] = {}


def register_step(keyword: str):
    """step description에 keyword가 포함된 step에 실행 함수를 등록하는 데코레이터."""
    def decorator(fn: Callable):
        _STEP_HANDLERS[keyword] = fn
        return fn
    return decorator


def _find_handler(step: Step) -> Callable | None:
    for kw, fn in _STEP_HANDLERS.items():
        if kw.lower() in step.description.lower():
            return fn
    return None


# ── Step 기본 실행 로직 ────────────────────────────────────────────────────

def _run_step(task: Task, step: Step, state: dict) -> None:
    """
    step을 실행한다.
    - 등록된 핸들러가 있으면 호출한다.
    - 없으면 '확인 필요' 메시지를 출력하고 수동 확인을 기다린다.
    """
    task_state = get_task_state(state, task.id)
    if step.index in task_state.get("steps_completed", []):
        log.info(f"  [건너뜀] Step {step.index}: {step.description}")
        return

    log.info(f"  → Step {step.index}: {step.description}")

    handler = _find_handler(step)
    if handler:
        handler(task, step, state)
    else:
        # 핸들러 미등록 step: 사람이 수동으로 진행하고 Enter를 눌러 계속
        print(f"\n  [수동 확인 필요] Step {step.index}: {step.description}")
        print("  완료되면 Enter를 누르세요 (s = 건너뜀, q = 중단): ", end="", flush=True)
        ans = input().strip().lower()
        if ans == "q":
            raise KeyboardInterrupt("사용자가 중단했습니다.")
        if ans == "s":
            log.warning(f"  Step {step.index} 건너뜀 (수동)")
            return

    mark_step_done(state, task.id, step.index)
    log.info(f"  ✓ Step {step.index} 완료")


# ── Task 실행 ──────────────────────────────────────────────────────────────

def _run_task(task: Task, state: dict) -> None:
    page = load_page_for_task(task)

    checkpoint_line(
        log,
        f"TASK {task.id} 시작  [{task.name}]"
        + (f"  →  {page.name} ({page.url_path})" if page else ""),
    )

    mark_task_started(state, task.id)

    if page:
        log.info(f"  페이지: {page.name}  |  URL: {page.url_path}")
        log.info(f"  컴포넌트: {', '.join(page.components)}")
        log.info(f"  수용 기준: {len(page.acceptance_criteria)}개")

    for step in task.steps:
        _run_step(task, step, state)

    mark_task_done(state, task.id)
    checkpoint_line(log, f"TASK {task.id} 완료  [{task.name}]")
    log.info(summary(state))


# ── 메인 러너 ─────────────────────────────────────────────────────────────

def run(args: argparse.Namespace) -> int:
    # 상태 로드 / 초기화
    if args.reset:
        state = reset_state()
        log.info("체크포인트 상태를 초기화했습니다.")
    else:
        state = load_state()

    # task 목록 로드 + 의존성 정렬
    tasks = topological_sort(load_all_tasks())

    if not tasks:
        log.warning("tasks/ 디렉터리에 .task 파일이 없습니다.")
        return 0

    state["total_count"] = len(tasks)
    save_state(state)

    # --status
    if args.status:
        print(summary(state))
        for t in tasks:
            ts = get_task_state(state, t.id)
            icon = {"completed": "✓", "failed": "✗", "running": "▶", "skipped": "─"}.get(
                ts["status"], "○"
            )
            steps_done = len(ts.get("steps_completed", []))
            print(f"  {icon} [{t.id}] {t.name}  ({steps_done}/{len(t.steps)} steps)")
        return 0

    # --list
    if args.list:
        for t in tasks:
            deps = ", ".join(t.depends_on) or "none"
            print(f"  [{t.id}] p={t.priority}  {t.name}  (depends: {deps}  steps: {len(t.steps)})")
        return 0

    # ── 직렬 실행 루프 ─────────────────────────────────────────────────────
    log.info(f"총 {len(tasks)}개 task 직렬 실행 시작")
    state["status"] = "running"
    save_state(state)

    for task in tasks:
        if is_task_done(state, task.id):
            log.info(f"[건너뜀] {task.id}: {task.name}  (이미 완료)")
            continue

        if is_task_failed(state, task.id) and not args.retry_failed:
            log.warning(f"[건너뜀] {task.id}: {task.name}  (실패 상태, --retry-failed 로 재시도 가능)")
            continue

        # 의존 task가 미완료면 실행 불가
        unmet = [d for d in task.depends_on if not is_task_done(state, d)]
        if unmet:
            log.warning(f"[건너뜀] {task.id}: 의존성 미충족 → {unmet}")
            mark_task_skipped(state, task.id, reason=f"depends not met: {unmet}")
            continue

        try:
            _run_task(task, state)
        except KeyboardInterrupt:
            log.warning(f"\n중단됨. 마지막 체크포인트: task={task.id}")
            state["status"] = "paused"
            save_state(state)
            return 1
        except Exception as exc:
            tb = traceback.format_exc()
            log.error(f"[오류] {task.id}: {exc}\n{tb}")
            mark_task_failed(state, task.id, str(exc))
            if args.stop_on_error:
                log.error("--stop-on-error 옵션으로 인해 중단합니다.")
                return 2
            # 기본: 오류 task는 건너뛰고 계속
            continue

    # 완료
    state["status"] = "done"
    save_state(state)
    checkpoint_line(log, "전체 실행 완료")
    log.info(summary(state))
    return 0


# ── CLI 진입점 ─────────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Hanness 체크포인트 러너 – MVP 구현 직렬 처리",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    p.add_argument("--reset", action="store_true", help="상태를 초기화하고 처음부터 실행")
    p.add_argument("--status", action="store_true", help="현재 진행 상태만 출력")
    p.add_argument("--list", action="store_true", help="task 목록 출력")
    p.add_argument("--retry-failed", action="store_true", help="실패한 task를 재시도")
    p.add_argument("--stop-on-error", action="store_true", help="오류 발생 시 즉시 중단")
    return p


if __name__ == "__main__":
    sys.exit(run(_build_parser().parse_args()))
