#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hanness 자율 수행 에이전트 (Autonomous Agent)
==============================================
자율 수행 3단계를 통합해 실행하는 진입점.

  단계 1 — Plan:
    planner.py가 프로젝트를 분석해 gap을 탐지하고
    .task / .page 파일을 자동으로 생성한다.

  단계 2 — Build:
    builders.py의 Step 핸들러를 checkpoint_runner에 등록한다.
    핸들러는 실제 코드(HTML/JS/CSS/Python)를 작성한다.

  단계 3 — Run:
    checkpoint_runner가 위상 정렬된 task 목록을 직렬로 실행하며
    매 step 완료마다 상태를 저장한다 (재시작 가능).

사용법:
  python autonomous_agent.py               # plan → build → run (전체)
  python autonomous_agent.py --plan-only   # plan 단계만 (파일 생성)
  python autonomous_agent.py --build-only  # build 단계만 (기존 task 파일 사용)
  python autonomous_agent.py --status      # 진행 상태 출력
  python autonomous_agent.py --reset       # 체크포인트 초기화 후 처음부터
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── 경로 설정 ──────────────────────────────────────────────────────────────────
_HERE = Path(__file__).parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from logger import get_logger, checkpoint_line
from task_parser import Task, Step
import checkpoint_runner as runner
import planner as planner_mod
import builders as builders_mod

log = get_logger("autonomous")


# ── 자율 모드: 핸들러 없는 step 자동 건너뜀 패치 ─────────────────────────────

def _patch_auto_skip(enabled: bool = True) -> None:
    """
    핸들러가 등록되지 않은 step을 수동 입력 대신 자동으로 건너뛰도록
    checkpoint_runner._run_step을 monkey-patch한다.
    """
    if not enabled:
        return

    original_run_step = runner._run_step

    def auto_run_step(task: Task, step: Step, state: dict) -> None:
        from state_manager import get_task_state, mark_step_done
        task_state = get_task_state(state, task.id)
        if step.index in task_state.get("steps_completed", []):
            log.info(f"  [건너뜀] Step {step.index}: {step.description}")
            return

        handler = runner._find_handler(step)
        if handler:
            log.info(f"  → Step {step.index}: {step.description}")
            handler(task, step, state)
            mark_step_done(state, task.id, step.index)
            log.info(f"  ✓ Step {step.index} 완료")
        else:
            log.warning(f"  [자동 건너뜀] Step {step.index}: {step.description}  (핸들러 미등록)")
            mark_step_done(state, task.id, step.index)

    runner._run_step = auto_run_step
    log.info("자율 모드: 핸들러 미등록 step 자동 건너뜀 활성화")


# ═══════════════════════════════════════════════════════════════════════════════
# 단계 1: PLAN
# ═══════════════════════════════════════════════════════════════════════════════

def phase_plan(verbose: bool = True) -> planner_mod.PlanResult:
    checkpoint_line(log, "PHASE 1 — PLAN  (gap 분석 → .task/.page 자동 생성)")
    result = planner_mod.run_planner(verbose=verbose)
    log.info(
        f"플래너 완료: 생성 {len(result.generated)}개 | "
        f"구현됨 {len(result.skipped_implemented)}개 | "
        f"기존 task {len(result.skipped_existing)}개"
    )
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# 단계 2: BUILD  (Step 핸들러 등록)
# ═══════════════════════════════════════════════════════════════════════════════

def phase_build() -> None:
    checkpoint_line(log, "PHASE 2 — BUILD  (Step 핸들러 등록)")
    builders_mod.register_all_handlers(runner)
    log.info("핸들러 등록 완료. 자율 실행 모드 활성화.")


# ═══════════════════════════════════════════════════════════════════════════════
# 단계 3: RUN  (체크포인트 러너 실행)
# ═══════════════════════════════════════════════════════════════════════════════

def phase_run(args: argparse.Namespace) -> int:
    checkpoint_line(log, "PHASE 3 — RUN  (자율 직렬 실행)")
    # checkpoint_runner.run()이 기대하는 Namespace 필드 맞춤
    runner_args = argparse.Namespace(
        reset=getattr(args, "reset", False),
        status=getattr(args, "status", False),
        list=False,
        retry_failed=getattr(args, "retry_failed", False),
        stop_on_error=getattr(args, "stop_on_error", False),
    )
    return runner.run(runner_args)


# ═══════════════════════════════════════════════════════════════════════════════
# 메인 진입점
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> int:
    p = argparse.ArgumentParser(
        description="Hanness 자율 수행 에이전트",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    p.add_argument("--plan-only", action="store_true", help="plan 단계만 실행 (파일 생성)")
    p.add_argument("--build-only", action="store_true", help="build+run만 실행 (기존 task 사용)")
    p.add_argument("--status", action="store_true", help="진행 상태 출력")
    p.add_argument("--reset", action="store_true", help="체크포인트 초기화 후 재실행")
    p.add_argument("--retry-failed", action="store_true", help="실패한 task 재시도")
    p.add_argument("--stop-on-error", action="store_true", help="오류 발생 시 즉시 중단")
    p.add_argument(
        "--no-auto-skip", action="store_true",
        help="핸들러 미등록 step을 수동 확인 모드로 전환 (기본: 자동 건너뜀)"
    )
    args = p.parse_args()

    # ── --status: 현재 상태만 출력 ──────────────────────────────────────────
    if args.status:
        phase_build()          # 핸들러 등록 (status 표시에도 task 목록 필요)
        return runner.run(args)

    print()
    print("╔══════════════════════════════════════════════════════╗")
    print("║       Hanness 자율 수행 에이전트                     ║")
    print("║       Plan → Build → Run                            ║")
    print("╚══════════════════════════════════════════════════════╝")
    print()

    # ── Plan 단계 ────────────────────────────────────────────────────────────
    if not args.build_only:
        phase_plan(verbose=True)

    if args.plan_only:
        log.info("--plan-only 옵션: plan 단계만 실행하고 종료합니다.")
        return 0

    # ── Build 단계 ───────────────────────────────────────────────────────────
    phase_build()

    # 자율 모드 패치 (--no-auto-skip 없으면 기본 활성화)
    _patch_auto_skip(enabled=not args.no_auto_skip)

    # ── Run 단계 ────────────────────────────────────────────────────────────
    return phase_run(args)


if __name__ == "__main__":
    sys.exit(main())
