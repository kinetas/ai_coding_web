"""
수동 ETL 실행 스크립트 (자체 서버용).

크롤러 함수를 직접 호출해 ContentStore(SQLite/PostgreSQL)에 저장합니다.

사용법:
  python etl.py --wordcloud          # 워드클라우드만
  python etl.py --analysis           # 분석 스냅샷만
  python etl.py --all                # 전체
  python etl.py --all --dry-run      # 미리보기 (저장 안 함)
  python etl.py --category agri      # 특정 카테고리만
"""
from __future__ import annotations

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
  ("health", "kr"),
  ("traffic", "kr"),
  ("tour", "kr"),
  ("env", "kr"),
]

_ANALYSIS_PAGES: list[str] = [
  "analysis-1",
  "analysis-2",
  "analysis-3",
  "analysis-4",
  "analysis-5",
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
      store.set_wordcloud(cat, region, word_objs)
      print(f"  ✓ 저장 완료")

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


def main() -> None:
  _load_env()

  parser = argparse.ArgumentParser(description="ET 데이터 ETL 수동 실행")
  parser.add_argument("--wordcloud", action="store_true", help="워드클라우드 업데이트")
  parser.add_argument("--analysis", action="store_true", help="분석 스냅샷 업데이트")
  parser.add_argument("--all", dest="all_", action="store_true", help="전체 실행")
  parser.add_argument("--dry-run", action="store_true", help="저장하지 않고 미리보기만")
  parser.add_argument("--category", default=None, help="특정 카테고리만 (agri/health/traffic/tour/env)")
  args = parser.parse_args()

  if not (args.wordcloud or args.analysis or args.all_):
    parser.print_help()
    sys.exit(1)

  if args.dry_run:
    print("[dry-run 모드] 저장 없이 미리보기만 실행합니다.\n")

  if args.wordcloud or args.all_:
    run_wordcloud(dry_run=args.dry_run, category=args.category)

  if args.analysis or args.all_:
    run_analysis(dry_run=args.dry_run)

  print("\n완료.")


if __name__ == "__main__":
  main()
