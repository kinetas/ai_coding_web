#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hanness 자율 빌더 (Step Handler Implementations)
=================================================
각 step description 키워드에 매핑되는 실제 구현 함수 모음.

등록 방식:
  from builders import register_all_handlers
  register_all_handlers(runner_module)

핸들러 시그니처:
  def handler(task: Task, step: Step, state: dict) -> None
"""
from __future__ import annotations

import re
import sys
import textwrap
from pathlib import Path
from typing import Callable, TYPE_CHECKING

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

if TYPE_CHECKING:
    from task_parser import Task, Step

ROOT = Path(__file__).parent.parent.parent  # ai_coding_web/
FRONTEND_DIR = ROOT / "frontend"
BACKEND_DIR = ROOT / "backend" / "app"
CRAWLER_DIR = ROOT / "crawler"

# ── 공통 유틸 ─────────────────────────────────────────────────────────────────

def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"    [write] {path.relative_to(ROOT)}")


def _inject_before_tag(html: str, tag: str, snippet: str) -> str:
    """HTML 내 <tag> 바로 앞에 snippet을 삽입."""
    return html.replace(f"<{tag}", f"{snippet}\n<{tag}", 1)


def _inject_after_tag(html: str, closing_tag: str, snippet: str) -> str:
    """HTML 내 </tag> 바로 뒤에 snippet을 삽입."""
    return html.replace(f"</{closing_tag}>", f"</{closing_tag}>\n{snippet}", 1)


def _insert_before_closing_body(html: str, snippet: str) -> str:
    return html.replace("</body>", f"{snippet}\n</body>", 1)


def _append_to_js(js_path: Path, code: str) -> None:
    existing = _read(js_path)
    if code.strip().split("(")[0].strip() in existing:
        print(f"    [skip] 이미 존재: {js_path.name}")
        return
    _write(js_path, existing + "\n\n" + code)


def _file_contains(path: Path, pattern: str) -> bool:
    return bool(re.search(pattern, _read(path), re.IGNORECASE))


# ═══════════════════════════════════════════════════════════════════════════════
# 핸들러 정의
# ═══════════════════════════════════════════════════════════════════════════════

# ── 1. Last Updated ────────────────────────────────────────────────────────────

def handle_last_updated_html(task, step, state):
    """index.html에 #last-updated-bar 요소 추가."""
    path = FRONTEND_DIR / "index.html"
    html = _read(path)
    if "last-updated-bar" in html:
        print("    [skip] last-updated-bar 이미 존재")
        return
    bar_html = '  <div id="last-updated-bar" class="last-updated-bar">데이터 갱신 시각 확인 중...</div>'
    # <main> 태그 바로 뒤에 삽입, 없으면 <body> 앞에
    if "<main" in html:
        html = re.sub(r"(<main[^>]*>)", r"\1\n" + bar_html, html, count=1)
    else:
        html = _insert_before_closing_body(html, bar_html)
    _write(path, html)


def handle_last_updated_js(task, step, state):
    """index.js(또는 common.js)에 fetchLastUpdated() 함수 추가."""
    # index.js 우선, 없으면 common.js
    candidates = [
        FRONTEND_DIR / "assets" / "js" / "index.js",
        FRONTEND_DIR / "assets" / "js" / "common.js",
    ]
    js_path = next((p for p in candidates if p.exists()), candidates[0])

    code = textwrap.dedent("""\
        // ── Last Updated 갱신 시각 표시 ──────────────────────────────────────
        async function fetchLastUpdated() {
          const el = document.getElementById('last-updated-bar');
          if (!el) return;
          try {
            const res = await fetch('/api/public/price?limit=1');
            const data = await res.json();
            const raw = data?.last_updated || data?.items?.[0]?.updated_at || null;
            if (!raw) { el.textContent = '갱신 시각: 알 수 없음'; return; }
            const dt = new Date(raw);
            el.textContent = '마지막 갱신: ' + dt.toLocaleString('ko-KR', {
              timeZone: 'Asia/Seoul',
              year: 'numeric', month: '2-digit', day: '2-digit',
              hour: '2-digit', minute: '2-digit'
            });
          } catch (e) {
            el.textContent = '갱신 시각: 알 수 없음';
          }
        }
        document.addEventListener('DOMContentLoaded', fetchLastUpdated);
    """)
    _append_to_js(js_path, code)


def handle_last_updated_css(task, step, state):
    """styles.css에 .last-updated-bar 스타일 추가."""
    css_path = FRONTEND_DIR / "assets" / "css" / "styles.css"
    css = _read(css_path)
    if "last-updated-bar" in css:
        print("    [skip] .last-updated-bar 스타일 이미 존재")
        return
    snippet = textwrap.dedent("""\

        /* ── Last Updated Bar ── */
        .last-updated-bar {
          font-size: 0.75rem;
          color: #888;
          text-align: right;
          padding: 4px 16px;
          background: #f9f9f9;
          border-bottom: 1px solid #eee;
        }
    """)
    _write(css_path, css + snippet)


# ── 2. 데이터 수집 상태 메시지 ────────────────────────────────────────────────

def handle_data_status_html(task, step, state):
    """index.html에 #data-status-msg 요소 추가."""
    path = FRONTEND_DIR / "index.html"
    html = _read(path)
    if "data-status-msg" in html:
        print("    [skip] data-status-msg 이미 존재")
        return
    snippet = '  <div id="data-status-msg" class="data-status-msg" style="display:none"></div>'
    if "<main" in html:
        html = re.sub(r"(<main[^>]*>)", r"\1\n" + snippet, html, count=1)
    else:
        html = _insert_before_closing_body(html, snippet)
    _write(path, html)


def handle_data_status_js(task, step, state):
    """word_count 기반 상태 메시지 JS 로직 추가."""
    candidates = [
        FRONTEND_DIR / "assets" / "js" / "index.js",
        FRONTEND_DIR / "assets" / "js" / "common.js",
    ]
    js_path = next((p for p in candidates if p.exists()), candidates[0])
    code = textwrap.dedent("""\
        // ── 데이터 수집 진행 상태 메시지 ────────────────────────────────────
        async function fetchDataStatus() {
          const el = document.getElementById('data-status-msg');
          if (!el) return;
          try {
            const res = await fetch('/api/public/news/wordcloud');
            const data = await res.json();
            const count = data?.word_count ?? (data?.words?.length ?? 0);
            const MIN_WORDS = 5;
            if (count < MIN_WORDS) {
              el.style.display = 'block';
              el.textContent = `데이터를 수집하고 있습니다 (${count}/15 단어 확보됨). 잠시 후 다시 확인해 주세요.`;
              el.className = 'data-status-msg collecting';
            } else {
              el.style.display = 'none';
            }
          } catch (e) {
            // API 호출 실패 시 무시
          }
        }
        document.addEventListener('DOMContentLoaded', fetchDataStatus);
    """)
    _append_to_js(js_path, code)


def handle_data_status_css(task, step, state):
    css_path = FRONTEND_DIR / "assets" / "css" / "styles.css"
    css = _read(css_path)
    if "data-status-msg" in css:
        print("    [skip] .data-status-msg 스타일 이미 존재")
        return
    snippet = textwrap.dedent("""\

        /* ── 데이터 수집 상태 배너 ── */
        .data-status-msg {
          background: #fff8e1;
          border: 1px solid #ffe082;
          border-radius: 4px;
          color: #6d4c00;
          font-size: 0.85rem;
          padding: 8px 16px;
          margin: 8px 16px;
        }
        .data-status-msg.collecting::before {
          content: '⏳ ';
        }
    """)
    _write(css_path, css + snippet)


# ── 3. 템플릿 프리셋 ────────────────────────────────────────────────────────────

def handle_preset_constants(task, step, state):
    """mypage.js에 PRESET_TEMPLATES 상수 추가."""
    js_path = FRONTEND_DIR / "assets" / "js" / "mypage.js"
    if not js_path.exists():
        print(f"    [skip] {js_path.name} 없음")
        return
    code = textwrap.dedent("""\
        // ── 기본 템플릿 프리셋 상수 ──────────────────────────────────────────
        const PRESET_TEMPLATES = [
          {
            id: 'agri_price',
            label: '농산물 가격 추이',
            icon: '🥬',
            desc: '주요 농산물 가격 변동을 한눈에',
            widget: { type: 'chart', endpoint: '/api/public/price', chart_type: 'line' }
          },
          {
            id: 'weekly_news',
            label: '주간 뉴스 키워드',
            icon: '📰',
            desc: '이번 주 주목받은 키워드 워드클라우드',
            widget: { type: 'wordcloud', endpoint: '/api/public/news/wordcloud' }
          },
          {
            id: 'category_issue',
            label: '카테고리별 이슈 변화',
            icon: '📊',
            desc: '카테고리별 뉴스 빈도 추이',
            widget: { type: 'chart', endpoint: '/api/public/category', chart_type: 'bar' }
          }
        ];
    """)
    _append_to_js(js_path, code)


def handle_preset_html(task, step, state):
    """mypage.html에 #preset-bar 섹션 추가."""
    path = FRONTEND_DIR / "mypage.html"
    html = _read(path)
    if "preset-bar" in html:
        print("    [skip] preset-bar 이미 존재")
        return
    preset_html = textwrap.dedent("""\
        <!-- ── 빠른 시작 템플릿 프리셋 ── -->
        <section id="preset-bar" class="preset-bar">
          <h3 class="preset-bar__title">빠른 시작</h3>
          <div class="preset-card-grid" id="preset-card-grid">
            <!-- JS로 렌더링 -->
          </div>
        </section>
    """)
    # <main> 또는 .dashboard 앞에 삽입
    if 'id="dashboard"' in html or 'class="dashboard"' in html:
        html = re.sub(
            r'(<(?:div|section)[^>]*(?:id|class)="dashboard"[^>]*>)',
            preset_html + r"\1",
            html, count=1
        )
    elif "<main" in html:
        html = re.sub(r"(<main[^>]*>)", r"\1\n" + preset_html, html, count=1)
    else:
        html = _insert_before_closing_body(html, preset_html)
    _write(path, html)


def handle_preset_apply_js(task, step, state):
    """applyPreset() + renderPresetCards() 함수 추가."""
    js_path = FRONTEND_DIR / "assets" / "js" / "mypage.js"
    if not js_path.exists():
        print(f"    [skip] {js_path.name} 없음")
        return
    code = textwrap.dedent("""\
        // ── 프리셋 카드 렌더링 ────────────────────────────────────────────────
        function renderPresetCards() {
          const grid = document.getElementById('preset-card-grid');
          if (!grid || typeof PRESET_TEMPLATES === 'undefined') return;
          grid.innerHTML = PRESET_TEMPLATES.map(t => `
            <div class="preset-card" onclick="applyPreset('${t.id}')">
              <span class="preset-card__icon">${t.icon}</span>
              <strong class="preset-card__label">${t.label}</strong>
              <p class="preset-card__desc">${t.desc}</p>
            </div>
          `).join('');
        }

        async function applyPreset(presetId) {
          const preset = (PRESET_TEMPLATES || []).find(t => t.id === presetId);
          if (!preset) return;
          // 비로그인 체크
          const token = localStorage.getItem('access_token');
          if (!token) {
            alert('로그인 후 이용할 수 있습니다.');
            window.location.href = '/login.html';
            return;
          }
          try {
            const res = await fetch('/api/builder/widget', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
              body: JSON.stringify({ name: preset.label, config: preset.widget })
            });
            if (res.ok) {
              alert(`'${preset.label}' 위젯이 추가됐습니다.`);
              location.reload();
            } else {
              alert('위젯 추가에 실패했습니다. 다시 시도해 주세요.');
            }
          } catch (e) {
            alert('네트워크 오류가 발생했습니다.');
          }
        }

        document.addEventListener('DOMContentLoaded', renderPresetCards);
    """)
    _append_to_js(js_path, code)


def handle_preset_css(task, step, state):
    css_path = FRONTEND_DIR / "assets" / "css" / "styles.css"
    css = _read(css_path)
    if "preset-bar" in css:
        print("    [skip] .preset-bar 스타일 이미 존재")
        return
    snippet = textwrap.dedent("""\

        /* ── 프리셋 바 ── */
        .preset-bar {
          padding: 16px;
          background: #f5f7fa;
          border-radius: 8px;
          margin-bottom: 24px;
        }
        .preset-bar__title {
          font-size: 0.9rem;
          color: #555;
          margin: 0 0 12px;
          font-weight: 600;
        }
        .preset-card-grid {
          display: flex;
          gap: 12px;
          flex-wrap: wrap;
        }
        .preset-card {
          background: #fff;
          border: 1px solid #e0e0e0;
          border-radius: 8px;
          padding: 14px 18px;
          cursor: pointer;
          min-width: 160px;
          flex: 1;
          transition: box-shadow 0.2s, border-color 0.2s;
        }
        .preset-card:hover {
          box-shadow: 0 4px 12px rgba(0,0,0,0.10);
          border-color: #4caf50;
        }
        .preset-card__icon { font-size: 1.4rem; display: block; margin-bottom: 6px; }
        .preset-card__label { font-size: 0.9rem; font-weight: 600; display: block; margin-bottom: 4px; }
        .preset-card__desc { font-size: 0.78rem; color: #777; margin: 0; }
    """)
    _write(css_path, css + snippet)


# ── 4. 모바일 반응형 CSS ──────────────────────────────────────────────────────

def handle_mobile_css(task, step, state):
    css_path = FRONTEND_DIR / "assets" / "css" / "styles.css"
    css = _read(css_path)
    if "@media" in css and "375px" in css:
        print("    [skip] 모바일 반응형 미디어쿼리 이미 존재")
        return
    snippet = textwrap.dedent("""\

        /* ── 모바일 반응형 ── */
        @media (max-width: 768px) {
          .dashboard-grid,
          .widget-grid {
            grid-template-columns: 1fr !important;
          }
          .preset-card-grid {
            flex-direction: column;
          }
          .preset-card {
            min-width: unset;
          }
        }

        @media (max-width: 375px) {
          canvas {
            width: 100% !important;
            height: auto !important;
          }
          .last-updated-bar {
            text-align: left;
            padding: 4px 8px;
          }
          nav ul {
            display: none;
            flex-direction: column;
            position: absolute;
            top: 56px;
            left: 0;
            right: 0;
            background: #fff;
            border-top: 1px solid #eee;
            padding: 8px 0;
          }
          nav ul.open {
            display: flex;
          }
          .nav-toggle {
            display: block !important;
          }
        }
    """)
    _write(css_path, css + snippet)


def handle_mobile_hamburger_js(task, step, state):
    candidates = [
        FRONTEND_DIR / "assets" / "js" / "common.js",
        FRONTEND_DIR / "assets" / "js" / "index.js",
    ]
    js_path = next((p for p in candidates if p.exists()), candidates[0])
    code = textwrap.dedent("""\
        // ── 햄버거 메뉴 (모바일) ─────────────────────────────────────────────
        function initHamburger() {
          const toggle = document.querySelector('.nav-toggle');
          const navUl = document.querySelector('nav ul');
          if (!toggle || !navUl) return;
          toggle.addEventListener('click', () => navUl.classList.toggle('open'));
        }
        document.addEventListener('DOMContentLoaded', initHamburger);
    """)
    _append_to_js(js_path, code)


def handle_chartjs_responsive(task, step, state):
    """charts.js에 responsive: true 옵션이 있는지 확인하고 없으면 추가."""
    charts_js = FRONTEND_DIR / "assets" / "js" / "charts.js"
    if not charts_js.exists():
        print("    [skip] charts.js 없음")
        return
    content = _read(charts_js)
    if "responsive" in content:
        print("    [skip] responsive 옵션 이미 존재")
        return
    # Chart() 생성자 options 객체에 responsive 추가 시도
    patched = re.sub(
        r"(options\s*:\s*\{)",
        r"\1\n        responsive: true,\n        maintainAspectRatio: false,",
        content,
        count=1,
    )
    if patched != content:
        _write(charts_js, patched)
    else:
        print("    [info] options 블록 미발견, 수동 확인 권장")


# ── 5. ETL 지수 백오프 ────────────────────────────────────────────────────────

def handle_etl_backoff(task, step, state):
    """etl.py에 retry_with_backoff 데코레이터 추가."""
    etl_path = ROOT / "etl.py"
    content = _read(etl_path)
    if "retry_with_backoff" in content:
        print("    [skip] retry_with_backoff 이미 존재")
        return
    backoff_code = textwrap.dedent("""\
        # ── 지수 백오프 재시도 데코레이터 (Hanness 자동 생성) ──────────────────
        import functools, time as _time, logging as _logging

        def retry_with_backoff(max_retries: int = 3, base_delay: float = 1.0):
            \"\"\"지수 백오프로 max_retries 회 재시도하는 데코레이터.\"\"\"
            def decorator(fn):
                @functools.wraps(fn)
                def wrapper(*args, **kwargs):
                    last_exc = None
                    for attempt in range(max_retries):
                        try:
                            return fn(*args, **kwargs)
                        except Exception as exc:
                            last_exc = exc
                            delay = base_delay * (2 ** attempt)
                            _logging.warning(
                                f"[retry] {fn.__name__} 실패 "
                                f"(시도 {attempt+1}/{max_retries}), {delay:.1f}초 후 재시도: {exc}"
                            )
                            _time.sleep(delay)
                    _logging.error(f"[retry] {fn.__name__} {max_retries}회 모두 실패: {last_exc}")
                    raise last_exc
                return wrapper
            return decorator

    """)
    _write(etl_path, backoff_code + content)


def handle_news_backoff(task, step, state):
    """crawler/news_pipeline.py의 fetch 함수에 @retry_with_backoff 적용."""
    news_path = CRAWLER_DIR / "news_pipeline.py"
    content = _read(news_path)
    if "retry_with_backoff" in content:
        print("    [skip] news_pipeline.py에 이미 적용됨")
        return
    # import 추가
    import_line = "from etl import retry_with_backoff\n"
    if "from etl import" not in content and import_line not in content:
        content = import_line + content
    # fetch 함수에 데코레이터 추가
    content = re.sub(
        r"(def fetch_news\b)",
        "@retry_with_backoff(max_retries=3)\n\\1",
        content, count=1
    )
    _write(news_path, content)


def handle_price_backoff(task, step, state):
    """crawler/at_price_trend.py의 fetch 함수에 @retry_with_backoff 적용."""
    price_path = CRAWLER_DIR / "at_price_trend.py"
    content = _read(price_path)
    if "retry_with_backoff" in content:
        print("    [skip] at_price_trend.py에 이미 적용됨")
        return
    import_line = "from etl import retry_with_backoff\n"
    if import_line not in content:
        content = import_line + content
    content = re.sub(
        r"(def fetch_price\b|def get_price\b|def collect\b)",
        "@retry_with_backoff(max_retries=3)\n\\1",
        content, count=1
    )
    _write(price_path, content)


# ── 6. 카테고리별 불용어 강화 ─────────────────────────────────────────────────

def handle_stopwords(task, step, state):
    """crawler/news_pipeline.py에 CATEGORY_STOPWORDS 추가."""
    news_path = CRAWLER_DIR / "news_pipeline.py"
    content = _read(news_path)
    if "CATEGORY_STOPWORDS" in content:
        print("    [skip] CATEGORY_STOPWORDS 이미 존재")
        return
    stopwords_block = textwrap.dedent("""\
        # ── 카테고리별 불용어 사전 (Hanness 자동 생성) ──────────────────────────
        COMMON_STOPWORDS = {
            "기자", "뉴스", "특파원", "보도", "연합", "뉴시스", "헤럴드",
            "오전", "오후", "오늘", "어제", "이번", "지난", "최근",
            "관련", "통해", "따라", "대해", "위해", "하지만", "그러나",
            "그런데", "따른", "이에", "이를", "이후", "이전", "및",
        }
        CATEGORY_STOPWORDS: dict[str, set[str]] = {
            "농산물": {"kg", "톤", "가격", "시세", "원산지", "수입산", "국내산"},
            "경제": {"증시", "코스피", "코스닥", "주가", "환율", "달러", "원화"},
            "사회": {"사건", "경찰", "검찰", "수사", "혐의", "피의자"},
            "날씨": {"강수량", "기온", "mm", "℃", "바람", "습도"},
        }

        def _filter_stopwords(words: list[str], category: str = "") -> list[str]:
            stops = COMMON_STOPWORDS | CATEGORY_STOPWORDS.get(category, set())
            return [w for w in words if w not in stops and len(w) > 1]

    """)
    _write(news_path, stopwords_block + content)


# ── API 엔드포인트 확인 (읽기 전용) ──────────────────────────────────────────

def handle_api_check(task, step, state):
    """backend 코드에서 API 엔드포인트 정의 존재 여부 확인."""
    endpoint_patterns = {
        "price": r'"/api/public/price|@.*router.*price"',
        "wordcloud": r'"/api/public/news/wordcloud|wordcloud"',
        "category": r'"/api/public/category"',
        "builder": r'"/api/builder|builder_controller"',
    }
    for name, pattern in endpoint_patterns.items():
        found = False
        for py_file in BACKEND_DIR.rglob("*.py"):
            content = _read(py_file)
            if re.search(pattern, content, re.IGNORECASE):
                print(f"    [ok] {name} 엔드포인트 확인됨: {py_file.relative_to(ROOT)}")
                found = True
                break
        if not found:
            print(f"    [warn] {name} 엔드포인트 미발견 — 백엔드 구현 필요")


# ═══════════════════════════════════════════════════════════════════════════════
# 핸들러 등록 테이블
# ═══════════════════════════════════════════════════════════════════════════════

# (keyword_in_step_description, handler_fn)
HANDLER_MAP: list[tuple[str, Callable]] = [
    # API 확인
    ("엔드포인트 응답 확인", handle_api_check),
    ("엔드포인트 포함 여부 확인", handle_api_check),

    # Last Updated
    ("last-updated-bar 요소", handle_last_updated_html),
    ("fetchlastupdated", handle_last_updated_js),
    ("kst 변환", handle_last_updated_js),
    (".last-updated-bar 스타일", handle_last_updated_css),

    # 데이터 상태 메시지
    ("data-status-msg 요소", handle_data_status_html),
    ("word_count", handle_data_status_js),
    ("진행 중 vs 완료", handle_data_status_js),
    (".data-status-msg 스타일", handle_data_status_css),

    # 템플릿 프리셋
    ("preset_templates 상수", handle_preset_constants),
    ("mypage.html에 #preset-bar", handle_preset_html),
    ("applypreset", handle_preset_apply_js),
    (".preset-card hover", handle_preset_css),

    # 모바일 반응형
    ("@media (max-width: 768", handle_mobile_css),
    ("grid-template-columns: 1fr", handle_mobile_css),
    ("햄버거 메뉴 토글", handle_mobile_hamburger_js),
    ("chart.js responsive", handle_chartjs_responsive),
    ("responsive: true", handle_chartjs_responsive),

    # ETL 백오프
    ("retry_with_backoff", handle_etl_backoff),
    ("news_pipeline.py의 fetch", handle_news_backoff),
    ("at_price_trend.py의 fetch", handle_price_backoff),
    ("기존 캐시 데이터 반환", handle_etl_backoff),

    # 불용어
    ("category_stopwords", handle_stopwords),
    ("카테고리 불용어 필터링", handle_stopwords),
    ("불용어 사전 추가", handle_stopwords),
]


def register_all_handlers(runner_module) -> None:
    """
    checkpoint_runner 모듈의 _STEP_HANDLERS dict에
    HANDLER_MAP의 모든 핸들러를 등록한다.
    """
    for keyword, fn in HANDLER_MAP:
        runner_module._STEP_HANDLERS[keyword.lower()] = fn
    print(f"  [builders] {len(HANDLER_MAP)}개 step 핸들러 등록 완료")
