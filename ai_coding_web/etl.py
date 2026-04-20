from __future__ import annotations

# ── 지수 백오프 재시도 데코레이터 (Hanness 자동 생성) ──────────────────
import functools, time as _time, logging as _logging

def retry_with_backoff(max_retries: int = 3, base_delay: float = 1.0):
    """지수 백오프로 max_retries 회 재시도하는 데코레이터."""
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

"""
수동 ETL 실행 스크립트 (자체 서버용).

크롤러 함수를 직접 호출해 ContentStore(SQLite/PostgreSQL)에 저장합니다.

사용법:
  python etl.py --wordcloud          # 워드클라우드만
  python etl.py --analysis           # 분석 스냅샷만
  python etl.py --agri               # 농가격(공공데이터 API → agri_price_*)
  python etl.py --all                # 워드클라우드 + 분석 + 농가격
  python etl.py --all --dry-run      # 미리보기 (저장 안 함)
  python etl.py --category agri      # 특정 카테고리만 (워드클라우드)

농가격: .env 에 DATA_GO_KR_SERVICE_KEY(또는 PUBLIC_DATA_SERVICE_KEY), AT_PRICE_API_PATH 필수.
"""

import argparse
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).resolve().parent))


def _load_env() -> None:
  try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env", override=True)
  except ImportError:
    pass


_WORDCLOUD_TARGETS: list[tuple[str, str]] = [
  ("agri", "kr"),
]

_ANALYSIS_PAGES: list[str] = [
  "analysis-1",
]

_CROP_TARGETS: list[str] = [
  "배추", "무", "사과", "대파", "양파", "감자", "고추", "쌀", "토마토", "오이",
]


def run_wordcloud(*, dry_run: bool = False, category: str | None = None) -> None:
  from crawler.news_pipeline import pipeline_wordcloud
  from backend.app.db import SessionLocal
  from backend.app.repositories.memory_store import ContentStore
  from backend.app.models.wordcloud import Word

  store = ContentStore(SessionLocal)
  targets = [(c, r) for c, r in _WORDCLOUD_TARGETS if category is None or c == category]

  for cat, region in targets:
    print(f"[wordcloud] {cat}/{region} 크롤링 중...")
    words = pipeline_wordcloud(cat, region)
    print(f"  → {len(words)}개 단어 수집")
    if dry_run:
      for w in words[:5]:
        print(f"     {w['text']}: {w['weight']:.1f}")
      if len(words) > 5:
        print(f"     ... 외 {len(words) - 5}개")
    else:
      word_objs = [Word(text=w["text"], weight=float(w["weight"])) for w in words]
      saved = store.set_wordcloud(cat, region, word_objs)
      if saved:
        print(f"  ✓ 저장 완료 ({saved}개)")
      else:
        print(f"  ⚠ 수집 단어 부족({len(words)}개) — 기존 데이터 유지")

  if not dry_run:
    store.record_etl_run("news_rss_wordcloud", "success")


def run_analysis(*, dry_run: bool = False) -> None:
  from crawler.news_pipeline import pipeline_analysis
  from backend.app.db import SessionLocal
  from backend.app.repositories.memory_store import ContentStore

  store = ContentStore(SessionLocal)

  for page in _ANALYSIS_PAGES:
    print(f"[analysis] {page} 분석 중...")
    payload = pipeline_analysis(page, region_kr=True)
    print(f"  line={payload.get('line', [])[:3]}... bar={payload.get('bar', [])[:3]}...")
    if not dry_run:
      store.set_analysis(
        page=page,
        line=payload.get("line", []),
        bar=payload.get("bar", []),
        donut=payload.get("donut", []),
        accents=payload.get("accents"),
      )
      print(f"  ✓ 저장 완료")

  if not dry_run:
    store.record_etl_run("news_analysis", "success")


def run_crop_keywords(*, dry_run: bool = False, crop: str | None = None) -> None:
  """품목별 뉴스 키워드 수집 — 가격-뉴스 상관 분석용."""
  from crawler.news_pipeline import pipeline_crop_keywords
  from backend.app.db import SessionLocal
  from backend.app.repositories.memory_store import ContentStore
  from backend.app.models.wordcloud import Word

  store = ContentStore(SessionLocal)
  targets = [c for c in _CROP_TARGETS if crop is None or c == crop]

  for crop_name in targets:
    print(f"[crops] {crop_name} 뉴스 키워드 수집 중...")
    words = pipeline_crop_keywords(crop_name, "kr")
    print(f"  → {len(words)}개 단어 수집")
    if dry_run:
      for w in words[:5]:
        print(f"     {w['text']}: {w['weight']:.1f}")
    else:
      word_objs = [Word(text=w["text"], weight=float(w["weight"])) for w in words]
      saved = store.set_wordcloud(f"crop_{crop_name}", "kr", word_objs, min_words=5)
      if saved:
        print(f"  ✓ 저장 완료 ({saved}개)")
      else:
        print(f"  ⚠ 수집 단어 부족({len(words)}개) — 기존 데이터 유지")

  if not dry_run:
    store.record_etl_run("crop_keywords", "success")


def run_agri_price(*, dry_run: bool = False) -> None:
  """공공데이터포털 농가격 API → agri_price_analytics / agri_price_raw / agri_price_history."""
  from crawler.at_price_trend import fetch_full_agri_from_env
  from backend.app.db import SessionLocal
  from backend.app.repositories.agri_etl import upsert_agri_price_from_full_package
  from backend.app.repositories.memory_store import ContentStore

  print("[agri] 공공데이터 농가격 API 조회 중...")
  fetch_with_retry = retry_with_backoff(max_retries=3, base_delay=2.0)(fetch_full_agri_from_env)
  try:
    full = fetch_with_retry()
  except Exception as exc:
    print(f"  ✗ 농가격 API 조회 최종 실패: {exc}")
    return
  if not full:
    print("  ⚠ 건너뜀: DATA_GO_KR_SERVICE_KEY(또는 PUBLIC_DATA_SERVICE_KEY)와 AT_PRICE_API_PATH가 설정되어 있어야 합니다.")
    return

  raw_db_row = full.get("raw_db_row") or {}
  items = raw_db_row.get("items") or []
  print(f"  → {len(items)}건 item 수집")

  if dry_run:
    print("  [dry-run] DB 저장 생략")
    return

  n_ok, n_skip = upsert_agri_price_from_full_package(full, SessionLocal)
  print(f"  ✓ agri_price 저장 완료 (이력 {n_ok}건, 스킵 {n_skip}건)")

  store = ContentStore(SessionLocal)
  store.record_etl_run("agri_price_data_go_kr", "success", f"items={len(items)},history={n_ok}")


def main() -> None:
  _load_env()

  parser = argparse.ArgumentParser(description="ET 데이터 ETL 수동 실행")
  parser.add_argument("--wordcloud", action="store_true", help="농산물 워드클라우드 업데이트")
  parser.add_argument("--analysis", action="store_true", help="분석 스냅샷 업데이트")
  parser.add_argument("--agri", action="store_true", help="농가격(공공데이터 API → agri_price_*)")
  parser.add_argument("--crops", action="store_true", help="품목별 뉴스 키워드 수집 (가격-뉴스 상관 분석용)")
  parser.add_argument("--all", dest="all_", action="store_true", help="워드클라우드+분석+농가격+품목키워드")
  parser.add_argument("--dry-run", action="store_true", help="저장하지 않고 미리보기만")
  parser.add_argument("--category", default=None, help="특정 카테고리만 (agri)")
  parser.add_argument("--crop", default=None, help="특정 품목만 (배추/무/사과 등, --crops와 함께)")
  args = parser.parse_args()

  if not (args.wordcloud or args.analysis or args.agri or args.crops or args.all_):
    parser.print_help()
    sys.exit(1)

  if args.dry_run:
    print("[dry-run 모드] 저장 없이 미리보기만 실행합니다.\n")

  if args.wordcloud or args.all_:
    run_wordcloud(dry_run=args.dry_run, category=args.category)

  if args.analysis or args.all_:
    run_analysis(dry_run=args.dry_run)

  if args.agri or args.all_:
    run_agri_price(dry_run=args.dry_run)

  if args.crops or args.all_:
    run_crop_keywords(dry_run=args.dry_run, crop=args.crop)

  print("\n완료.")


if __name__ == "__main__":
  main()
