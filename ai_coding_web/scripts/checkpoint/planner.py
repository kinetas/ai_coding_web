#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hanness 자율 플래너 (Autonomous Planner)
=========================================
프로젝트 컨텍스트를 읽어 아직 구현되지 않은 기능을 파악하고,
해당 기능에 대한 .task / .page 파일을 자동으로 생성한다.

흐름:
  1. 기존 .task 파일 목록 수집 (중복 방지)
  2. 프론트엔드 / 백엔드 코드를 스캔해 "이미 구현된 것" 탐지
  3. CLAUDE.md 우선순위 목록과 대조해 "gap(미구현)"을 추출
  4. gap 마다 .task + .page 파일 생성
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent.parent.parent  # ai_coding_web/
CHECKPOINT_DIR = Path(__file__).parent
TASKS_DIR = CHECKPOINT_DIR / "tasks"
PAGES_DIR = CHECKPOINT_DIR / "pages"
FRONTEND_DIR = ROOT / "frontend"
BACKEND_DIR = ROOT / "backend" / "app"


# ── 기능 명세 (CLAUDE.md 우선순위 기반) ──────────────────────────────────────

@dataclass
class FeatureSpec:
    """단기·중기 로드맵에서 파생한 구현 가능한 기능 단위."""
    id: str                     # 고유 ID  (예: feat_last_updated)
    name: str                   # 사람이 읽는 이름
    priority: int               # 낮을수록 먼저 실행
    detect_pattern: str         # 이미 구현됐으면 매칭되는 코드 패턴 (정규식)
    detect_files: list[str]     # 탐지 대상 glob 패턴
    page_url: str               # URL 경로
    page_template: str          # HTML 파일명
    page_components: list[str]  # 컴포넌트 이름 목록
    acceptance_criteria: list[str]
    steps: list[str]            # 구현 단계 문자열 목록
    depends_on: list[str] = field(default_factory=list)


FEATURE_CATALOG: list[FeatureSpec] = [
    # ── 단기 우선순위 ─────────────────────────────────────────────────────────
    FeatureSpec(
        id="feat_last_updated",
        name="Last Updated 갱신 시각 표시",
        priority=10,
        detect_pattern=r"last.?updated|lastUpdated|last_updated",
        detect_files=["frontend/assets/js/*.js", "frontend/*.html"],
        page_url="/",
        page_template="index.html",
        page_components=["last-updated-bar"],
        acceptance_criteria=[
            "메인 페이지에 데이터 최신 갱신 시각(KST)이 표시된다",
            "갱신 시각은 ISO 문자열을 toLocaleString으로 변환해 출력한다",
            "데이터 fetch 실패 시 '알 수 없음'으로 fallback 표시한다",
        ],
        steps=[
            "backend API 응답에 last_updated 필드 포함 여부 확인",
            "index.html에 #last-updated-bar 요소 추가",
            "index.js에 fetchLastUpdated() 함수 구현 및 KST 변환 로직 작성",
            "CSS에 .last-updated-bar 스타일(작은 회색 텍스트) 추가",
        ],
    ),
    FeatureSpec(
        id="feat_data_status_message",
        name="데이터 수집 진행 상태 메시지",
        priority=11,
        detect_pattern=r"수집 중|collecting|data.?status|etl.?status",
        detect_files=["frontend/assets/js/*.js", "frontend/*.html"],
        page_url="/",
        page_template="index.html",
        page_components=["data-status-banner"],
        acceptance_criteria=[
            "데이터가 없을 때 '수집 중' 진행형 메시지가 표시된다",
            "워드클라우드 단어 수가 임계치 미달이면 '수집 중 (N/15 단어)' 표시",
            "'데이터 없음' 대신 맥락을 설명하는 메시지를 제공한다",
        ],
        steps=[
            "backend /api/public/news/wordcloud 응답의 word_count 필드 확인",
            "index.html에 #data-status-msg 요소 추가",
            "word_count < 5 조건 분기: 진행 중 vs 완료 메시지 렌더링 로직 구현",
            "CSS에 .data-status-msg 스타일(노란 배너) 추가",
        ],
    ),
    FeatureSpec(
        id="feat_template_presets",
        name="My Page 기본 템플릿 프리셋",
        priority=12,
        detect_pattern=r"template.?preset|templatePreset|기본 템플릿",
        detect_files=["frontend/assets/js/mypage.js", "frontend/mypage.html"],
        page_url="/mypage",
        page_template="mypage.html",
        page_components=["template-preset-bar", "preset-card"],
        acceptance_criteria=[
            "My Page 상단에 '빠른 시작' 템플릿 프리셋 3종이 표시된다",
            "프리셋 클릭 시 해당 위젯(차트/워드클라우드)이 즉시 추가된다",
            "비로그인 상태에서 프리셋 클릭 시 로그인 안내 모달이 표시된다",
        ],
        steps=[
            "PRESET_TEMPLATES 상수 정의 (농산물 가격 추이 / 주간 뉴스 키워드 / 카테고리별 이슈)",
            "mypage.html에 #preset-bar 섹션 추가 (카드 3개)",
            "mypage.js에 applyPreset(presetId) 함수 구현",
            "프리셋 적용 시 /api/builder/widget POST 호출 로직 연결",
            "CSS에 .preset-card hover 애니메이션 추가",
        ],
        depends_on=["task_004"],
    ),
    FeatureSpec(
        id="feat_mobile_responsive",
        name="모바일 반응형 대시보드",
        priority=13,
        detect_pattern=r"@media.*max-width.*375|mobile.?responsive|반응형",
        detect_files=["frontend/assets/css/styles.css"],
        page_url="/mypage",
        page_template="mypage.html",
        page_components=["responsive-grid"],
        acceptance_criteria=[
            "375px 뷰포트에서 위젯 그리드가 1열로 전환된다",
            "차트 캔버스가 컨테이너 너비에 맞게 자동 조정된다",
            "헤더 네비게이션이 햄버거 메뉴로 전환된다",
        ],
        steps=[
            "styles.css에 @media (max-width: 768px) 대시보드 그리드 규칙 추가",
            "styles.css에 @media (max-width: 375px) 차트 캔버스 width: 100% 적용",
            "헤더 햄버거 메뉴 토글 JS 로직 추가",
            "Chart.js responsive: true 옵션 활성화 확인",
        ],
    ),
    FeatureSpec(
        id="feat_etl_backoff",
        name="ETL 지수 백오프 재시도",
        priority=20,
        detect_pattern=r"exponential.?backoff|backoff|지수.*백오프|retry.*delay",
        detect_files=["etl.py", "crawler/*.py"],
        page_url="/admin/etl",
        page_template="admin-etl.html",
        page_components=["etl-retry-log"],
        acceptance_criteria=[
            "ETL 실패 시 1초 → 2초 → 4초 지수 백오프로 최대 3회 재시도한다",
            "재시도 횟수와 대기 시간이 로그에 기록된다",
            "외부 소스 전체 실패 시 기존 캐시 데이터를 유지한다",
        ],
        steps=[
            "etl.py에 retry_with_backoff(fn, max_retries=3) 데코레이터 함수 구현",
            "crawler/news_pipeline.py의 fetch 함수에 @retry_with_backoff 적용",
            "crawler/at_price_trend.py의 fetch 함수에 @retry_with_backoff 적용",
            "실패 후 기존 캐시 데이터 반환 fallback 로직 추가",
        ],
    ),
    FeatureSpec(
        id="feat_stopword_enhancement",
        name="카테고리별 불용어 사전 강화",
        priority=21,
        detect_pattern=r"STOPWORDS|stopwords|불용어|stop_words",
        detect_files=["crawler/news_pipeline.py"],
        page_url="/admin/etl",
        page_template="admin-etl.html",
        page_components=["stopword-config"],
        acceptance_criteria=[
            "카테고리별 특수 불용어가 분리 관리된다",
            "뉴스 URL, 언론사명, 날짜 패턴이 자동으로 제거된다",
            "워드클라우드에서 의미 없는 단어 출현 빈도가 감소한다",
        ],
        steps=[
            "crawler/news_pipeline.py에 CATEGORY_STOPWORDS dict 추가 (농산물/경제/사회 등)",
            "공통 불용어에 뉴스 패턴 추가 (기자, 뉴스, 특파원 등)",
            "토큰화 후 카테고리 불용어 필터링 단계 추가",
            "필터링 전후 단어 수를 로그로 기록",
        ],
    ),
]


# ── 코드 탐지 ─────────────────────────────────────────────────────────────────

def _is_implemented(spec: FeatureSpec) -> bool:
    """코드베이스를 스캔해 해당 기능이 이미 구현됐는지 확인."""
    pattern = re.compile(spec.detect_pattern, re.IGNORECASE)
    for glob_pattern in spec.detect_files:
        for path in ROOT.glob(glob_pattern):
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
                if pattern.search(text):
                    return True
            except (OSError, PermissionError):
                continue
    return False


def _existing_task_ids() -> set[str]:
    """
    tasks/ 디렉터리에 이미 있는 task id + 파일명 목록 반환.
    feature id 중복 탐지를 위해 파일명도 포함한다.
    """
    ids = set()
    TASKS_DIR.mkdir(exist_ok=True)
    for path in TASKS_DIR.glob("*.task"):
        # 파일명 자체도 포함 (feat_last_updated 등)
        ids.add(path.stem)
        ids.add(path.name)
        text = path.read_text(encoding="utf-8", errors="ignore")
        m = re.search(r"^id\s*=\s*(\S+)", text, re.MULTILINE)
        if m:
            ids.add(m.group(1))
    return ids


def _next_task_number() -> int:
    """tasks/ 디렉터리의 최대 번호 + 1 반환."""
    nums = []
    for path in TASKS_DIR.glob("*.task"):
        m = re.search(r"task_(\d+)", path.name)
        if m:
            nums.append(int(m.group(1)))
    return (max(nums) + 1) if nums else 1


def _next_page_number() -> int:
    """pages/ 디렉터리의 최대 번호 + 1 반환."""
    nums = []
    for path in PAGES_DIR.glob("*.page"):
        m = re.search(r"page_(\d+)", path.name)
        if m:
            nums.append(int(m.group(1)))
    return (max(nums) + 1) if nums else 1


# ── 파일 생성 ─────────────────────────────────────────────────────────────────

def _write_task_file(
    task_num: int,
    spec: FeatureSpec,
    page_filename: str,
) -> Path:
    task_id = f"task_{task_num:03d}"
    filename = f"{task_id}_{spec.id}.task"
    path = TASKS_DIR / filename

    depends_str = ", ".join(spec.depends_on) if spec.depends_on else ""
    steps_str = "\n".join(f"{i+1}. {s}" for i, s in enumerate(spec.steps))

    content = f"""[task]
id = {task_id}
name = {spec.name}
page = {page_filename}
depends_on = {depends_str}
priority = {spec.priority}

[steps]
{steps_str}
"""
    path.write_text(content, encoding="utf-8")
    return path


def _write_page_file(
    page_num: int,
    task_num: int,
    spec: FeatureSpec,
) -> tuple[str, Path]:
    page_id = f"page_{page_num:03d}"
    filename = f"{page_id}_{spec.id}.page"
    path = PAGES_DIR / filename

    components_str = ", ".join(spec.page_components)
    criteria_str = "\n".join(f"- {c}" for c in spec.acceptance_criteria)

    content = f"""[page]
id = {page_id}
name = {spec.name}
url_path = {spec.page_url}
template = {spec.page_template}
components = {components_str}

[acceptance_criteria]
{criteria_str}
"""
    PAGES_DIR.mkdir(exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return filename, path


# ── 메인 플래너 ────────────────────────────────────────────────────────────────

@dataclass
class PlanResult:
    generated: list[tuple[Path, Path]]  # (task_path, page_path)
    skipped_implemented: list[str]      # 이미 구현된 feature id
    skipped_existing: list[str]         # 이미 task가 있는 feature id


def run_planner(verbose: bool = True) -> PlanResult:
    """
    gap 분석 → .task / .page 파일 자동 생성.
    이미 구현됐거나 task 파일이 있는 기능은 건너뜀.
    """
    TASKS_DIR.mkdir(exist_ok=True)
    PAGES_DIR.mkdir(exist_ok=True)

    existing_ids = _existing_task_ids()
    result = PlanResult(generated=[], skipped_implemented=[], skipped_existing=[])

    for spec in sorted(FEATURE_CATALOG, key=lambda s: s.priority):
        # 이미 task 파일이 있으면 생성 불필요
        # (feature id가 기존 task id / 파일명에 포함돼 있는지로 판단)
        already_has_task = any(spec.id in entry for entry in existing_ids)
        if already_has_task:
            result.skipped_existing.append(spec.id)
            if verbose:
                print(f"  [건너뜀] {spec.name}  (task 파일 이미 존재)")
            continue

        # 코드베이스에 이미 구현됐으면 생성 불필요
        if _is_implemented(spec):
            result.skipped_implemented.append(spec.id)
            if verbose:
                print(f"  [건너뜀] {spec.name}  (코드베이스에 이미 구현됨)")
            continue

        # task / page 번호 결정
        task_num = _next_task_number()
        page_num = _next_page_number()

        # page 파일 먼저 생성
        page_filename, page_path = _write_page_file(page_num, task_num, spec)

        # task 파일 생성
        task_path = _write_task_file(task_num, spec, page_filename)

        result.generated.append((task_path, page_path))
        if verbose:
            print(f"  [생성] task={task_path.name}  page={page_path.name}")

    return result


# ── CLI ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  Hanness 자율 플래너 실행")
    print("=" * 60)
    result = run_planner(verbose=True)
    print()
    print(f"생성된 파일 쌍: {len(result.generated)}개")
    print(f"이미 구현됨: {len(result.skipped_implemented)}개")
    print(f"기존 task 존재: {len(result.skipped_existing)}개")
