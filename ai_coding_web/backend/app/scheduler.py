"""
APScheduler 기반 자동 ETL 스케줄러.

- 워드클라우드: 매일 00:00 (뉴스 RSS 크롤 → wordcloud_terms 갱신)
- 분석 스냅샷:  매주 월요일 00:00 (뉴스 분석 데이터 → analysis_snapshots 갱신)
- 농가격: 매일 00:30 (공공데이터 API → agri_price_* , env 미설정 시 로그만)

크롤러 함수를 직접 호출하므로 HTTP 오버헤드 없음.
"""
from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

_scheduler = BackgroundScheduler(timezone="Asia/Seoul")

# 카테고리 × 지역 조합
_WORDCLOUD_TARGETS: list[tuple[str, str]] = [
  ("agri", "kr"),
  ("health", "kr"),
  ("traffic", "kr"),
  ("tour", "kr"),
  ("env", "kr"),
]

# 분석 페이지 목록
_ANALYSIS_PAGES: list[str] = [
  "analysis-1",
  "analysis-2",
  "analysis-3",
  "analysis-4",
  "analysis-5",
]


def run_wordcloud_etl() -> None:
  """매일 00:00 — 뉴스 RSS 크롤 후 wordcloud_terms 갱신."""
  from crawler.news_pipeline import pipeline_wordcloud
  from backend.app.db import SessionLocal
  from backend.app.repositories.memory_store import ContentStore

  logger.info("[ETL] 워드클라우드 업데이트 시작")
  store = ContentStore(SessionLocal)
  errors: list[str] = []

  for category, region in _WORDCLOUD_TARGETS:
    try:
      words = pipeline_wordcloud(category, region)
      from backend.app.models.wordcloud import Word
      word_objs = [Word(text=w["text"], weight=float(w["weight"])) for w in words]
      store.set_wordcloud(category, region, word_objs)
      logger.info("[ETL] 워드클라우드 완료: %s/%s (%d개)", category, region, len(word_objs))
    except Exception as exc:
      logger.error("[ETL] 워드클라우드 실패: %s/%s — %s", category, region, exc)
      errors.append(f"{category}/{region}: {exc}")

  status = "success" if not errors else "partial_error"
  details = "; ".join(errors) if errors else ""
  store.record_etl_run("news_rss_wordcloud", status, details)
  logger.info("[ETL] 워드클라우드 완료 (status=%s)", status)


def run_analysis_etl() -> None:
  """매주 월요일 00:00 — 뉴스 분석 데이터로 analysis_snapshots 갱신."""
  from crawler.news_pipeline import pipeline_analysis
  from backend.app.db import SessionLocal
  from backend.app.repositories.memory_store import ContentStore

  logger.info("[ETL] 분석 스냅샷 업데이트 시작")
  store = ContentStore(SessionLocal)
  errors: list[str] = []

  for page in _ANALYSIS_PAGES:
    try:
      payload = pipeline_analysis(page, region_kr=True)
      store.set_analysis(
        page=page,
        line=payload.get("line", []),
        bar=payload.get("bar", []),
        donut=payload.get("donut", []),
        accents=payload.get("accents"),
      )
      logger.info("[ETL] 분석 완료: %s", page)
    except Exception as exc:
      logger.error("[ETL] 분석 실패: %s — %s", page, exc)
      errors.append(f"{page}: {exc}")

  status = "success" if not errors else "partial_error"
  details = "; ".join(errors) if errors else ""
  store.record_etl_run("news_analysis", status, details)
  logger.info("[ETL] 분석 스냅샷 완료 (status=%s)", status)


def run_agri_price_etl() -> None:
  """매일 00:30 — 공공데이터 농가격 API → agri_price_* (키·경로 없으면 건너뜀)."""
  from crawler.at_price_trend import fetch_full_agri_from_env
  from backend.app.db import SessionLocal
  from backend.app.repositories.agri_etl import upsert_agri_price_from_full_package
  from backend.app.repositories.memory_store import ContentStore

  logger.info("[ETL] 농가격(공공데이터) 업데이트 시작")
  full = fetch_full_agri_from_env()
  if not full:
    logger.warning("[ETL] 농가격 건너뜀: DATA_GO_KR_SERVICE_KEY·AT_PRICE_API_PATH 미설정")
    return

  raw_db_row = full.get("raw_db_row") or {}
  items = raw_db_row.get("items") or []
  try:
    n_ok, n_skip = upsert_agri_price_from_full_package(full, SessionLocal)
    store = ContentStore(SessionLocal)
    store.record_etl_run("agri_price_data_go_kr", "success", f"items={len(items)},history={n_ok},skip={n_skip}")
    logger.info("[ETL] 농가격 완료: item %d건, 이력 %d건 (스킵 %d)", len(items), n_ok, n_skip)
  except Exception as exc:
    logger.exception("[ETL] 농가격 실패: %s", exc)
    store = ContentStore(SessionLocal)
    store.record_etl_run("agri_price_data_go_kr", "error", str(exc)[:500])


def start_scheduler() -> None:
  _scheduler.add_job(run_wordcloud_etl, CronTrigger(hour=0, minute=0), id="wordcloud_daily")
  _scheduler.add_job(run_agri_price_etl, CronTrigger(hour=0, minute=30), id="agri_price_daily")
  _scheduler.add_job(run_analysis_etl, CronTrigger(day_of_week="mon", hour=0, minute=0), id="analysis_weekly")
  _scheduler.start()
  logger.info("[Scheduler] 시작 — 워드클라우드 매일 00:00 / 농가격 00:30 / 분석 매주 월 00:00")


def stop_scheduler() -> None:
  if _scheduler.running:
    _scheduler.shutdown(wait=False)
    logger.info("[Scheduler] 종료")
