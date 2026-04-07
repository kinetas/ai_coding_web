"""
체크포인트 상태 관리자
직렬 처리 방식으로 .task/.page 파일의 진행 상태를 JSON으로 저장/복원한다.
"""
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

STATE_DIR = Path(__file__).parent / "state"
STATE_FILE = STATE_DIR / "checkpoint_state.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_state() -> dict:
    """저장된 체크포인트 상태를 불러온다. 없으면 빈 상태를 반환."""
    STATE_DIR.mkdir(exist_ok=True)
    if STATE_FILE.exists():
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return _empty_state()


def save_state(state: dict) -> None:
    STATE_DIR.mkdir(exist_ok=True)
    state["last_updated"] = _now()
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def _empty_state() -> dict:
    return {
        "session_id": str(uuid.uuid4()),
        "started_at": _now(),
        "last_updated": _now(),
        "current_task_id": None,
        "current_step": None,
        "tasks": {},
        "completed_count": 0,
        "total_count": 0,
        "status": "idle",  # idle | running | paused | done | failed
    }


def reset_state() -> dict:
    """상태를 초기화하고 새 세션을 시작한다."""
    state = _empty_state()
    save_state(state)
    return state


# ── Task 단위 헬퍼 ──────────────────────────────────────────────────────────

def get_task_state(state: dict, task_id: str) -> dict:
    return state["tasks"].get(task_id, {
        "status": "pending",
        "started_at": None,
        "completed_at": None,
        "steps_completed": [],
        "error": None,
    })


def mark_task_started(state: dict, task_id: str) -> None:
    ts = state["tasks"].setdefault(task_id, {
        "status": "pending",
        "started_at": None,
        "completed_at": None,
        "steps_completed": [],
        "error": None,
    })
    ts["status"] = "running"
    ts["started_at"] = _now()
    state["current_task_id"] = task_id
    state["current_step"] = None
    state["status"] = "running"
    save_state(state)


def mark_step_done(state: dict, task_id: str, step_index: int) -> None:
    ts = state["tasks"].setdefault(task_id, {
        "status": "running",
        "started_at": _now(),
        "completed_at": None,
        "steps_completed": [],
        "error": None,
    })
    if step_index not in ts["steps_completed"]:
        ts["steps_completed"].append(step_index)
    state["current_step"] = step_index
    save_state(state)


def mark_task_done(state: dict, task_id: str) -> None:
    ts = state["tasks"][task_id]
    ts["status"] = "completed"
    ts["completed_at"] = _now()
    state["completed_count"] = sum(
        1 for t in state["tasks"].values() if t.get("status") == "completed"
    )
    state["current_task_id"] = None
    state["current_step"] = None
    save_state(state)


def mark_task_failed(state: dict, task_id: str, error: str) -> None:
    ts = state["tasks"].setdefault(task_id, {
        "status": "pending",
        "started_at": None,
        "completed_at": None,
        "steps_completed": [],
        "error": None,
    })
    ts["status"] = "failed"
    ts["error"] = error
    state["status"] = "failed"
    save_state(state)


def mark_task_skipped(state: dict, task_id: str, reason: str = "") -> None:
    state["tasks"][task_id] = {
        "status": "skipped",
        "started_at": None,
        "completed_at": _now(),
        "steps_completed": [],
        "error": reason,
    }
    save_state(state)


def is_task_done(state: dict, task_id: str) -> bool:
    return state["tasks"].get(task_id, {}).get("status") == "completed"


def is_task_failed(state: dict, task_id: str) -> bool:
    return state["tasks"].get(task_id, {}).get("status") == "failed"


def summary(state: dict) -> str:
    total = state.get("total_count", 0)
    done = state.get("completed_count", 0)
    failed = sum(1 for t in state["tasks"].values() if t.get("status") == "failed")
    skipped = sum(1 for t in state["tasks"].values() if t.get("status") == "skipped")
    return (
        f"[체크포인트] 전체 {total}개 | 완료 {done}개 | "
        f"실패 {failed}개 | 건너뜀 {skipped}개 | 상태: {state['status']}"
    )
