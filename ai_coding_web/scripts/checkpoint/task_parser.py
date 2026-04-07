"""
.task / .page 파일 파서
INI 스타일 텍스트 파일을 읽어 Task / Page 객체로 변환한다.

.task 파일 형식:
    [task]
    id = task_001
    name = 공개 메인 페이지
    page = page_001_main.page
    depends_on =
    priority = 1

    [steps]
    1. 백엔드 API 확인
    2. HTML/CSS 구현
    ...

.page 파일 형식:
    [page]
    id = page_001
    name = 메인 페이지
    url_path = /
    template = index.html
    components = header, price-chart, footer

    [acceptance_criteria]
    - 가격 추이 차트 표시
    - Last Updated 표시
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from pathlib import Path

TASKS_DIR = Path(__file__).parent / "tasks"
PAGES_DIR = Path(__file__).parent / "pages"


@dataclass
class Step:
    index: int
    description: str


@dataclass
class Task:
    id: str
    name: str
    page_file: str
    depends_on: list[str]
    priority: int
    steps: list[Step]
    raw_path: Path


@dataclass
class Page:
    id: str
    name: str
    url_path: str
    template: str
    components: list[str]
    acceptance_criteria: list[str]
    raw_path: Path


# ── 파싱 유틸 ──────────────────────────────────────────────────────────────

def _parse_sections(text: str) -> dict[str, list[str]]:
    """[section] 헤더를 기준으로 텍스트를 분리한다."""
    sections: dict[str, list[str]] = {}
    current = None
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        m = re.match(r"^\[(.+)\]$", stripped)
        if m:
            current = m.group(1).strip()
            sections[current] = []
        elif current is not None:
            sections[current].append(stripped)
    return sections


def _kv(lines: list[str]) -> dict[str, str]:
    result = {}
    for line in lines:
        if "=" in line:
            k, _, v = line.partition("=")
            result[k.strip()] = v.strip()
    return result


# ── Task 파서 ──────────────────────────────────────────────────────────────

def parse_task(path: Path) -> Task:
    text = path.read_text(encoding="utf-8")
    secs = _parse_sections(text)

    meta = _kv(secs.get("task", []))
    depends_raw = meta.get("depends_on", "")
    depends = [d.strip() for d in depends_raw.split(",") if d.strip()]

    steps = []
    for line in secs.get("steps", []):
        m = re.match(r"^(\d+)\.\s*(.+)$", line)
        if m:
            steps.append(Step(index=int(m.group(1)), description=m.group(2).strip()))

    return Task(
        id=meta.get("id", path.stem),
        name=meta.get("name", path.stem),
        page_file=meta.get("page", ""),
        depends_on=depends,
        priority=int(meta.get("priority", "99")),
        steps=steps,
        raw_path=path,
    )


def load_all_tasks() -> list[Task]:
    """tasks/ 디렉터리의 모든 .task 파일을 읽어 priority 순으로 반환."""
    TASKS_DIR.mkdir(exist_ok=True)
    tasks = [parse_task(p) for p in sorted(TASKS_DIR.glob("*.task"))]
    tasks.sort(key=lambda t: (t.priority, t.id))
    return tasks


# ── Page 파서 ──────────────────────────────────────────────────────────────

def parse_page(path: Path) -> Page:
    text = path.read_text(encoding="utf-8")
    secs = _parse_sections(text)

    meta = _kv(secs.get("page", []))
    components_raw = meta.get("components", "")
    components = [c.strip() for c in components_raw.split(",") if c.strip()]

    criteria = []
    for line in secs.get("acceptance_criteria", []):
        if line.startswith("-"):
            criteria.append(line[1:].strip())
        else:
            criteria.append(line)

    return Page(
        id=meta.get("id", path.stem),
        name=meta.get("name", path.stem),
        url_path=meta.get("url_path", "/"),
        template=meta.get("template", ""),
        components=components,
        acceptance_criteria=criteria,
        raw_path=path,
    )


def load_page_for_task(task: Task) -> Page | None:
    if not task.page_file:
        return None
    page_path = PAGES_DIR / task.page_file
    if not page_path.exists():
        return None
    return parse_page(page_path)


# ── 의존성 해결 (위상 정렬) ────────────────────────────────────────────────

def topological_sort(tasks: list[Task]) -> list[Task]:
    """depends_on 을 고려해 실행 순서를 결정한다."""
    id_map = {t.id: t for t in tasks}
    visited: set[str] = set()
    order: list[Task] = []

    def visit(task_id: str):
        if task_id in visited:
            return
        t = id_map.get(task_id)
        if t is None:
            return
        for dep in t.depends_on:
            visit(dep)
        visited.add(task_id)
        order.append(t)

    for t in tasks:
        visit(t.id)

    return order
