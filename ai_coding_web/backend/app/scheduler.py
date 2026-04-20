"""
APScheduler ETL jobs.

- Wordcloud: daily 00:00 Asia/Seoul (news RSS -> wordcloud_terms)
- Analysis snapshots: Monday 00:00 (news pipeline -> analysis_snapshots)
- Agri prices: daily 00:30 (public API -> agri_price_*; skips if env keys missing)

Calls crawler functions in-process (no HTTP).
"""
from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

_scheduler = BackgroundScheduler(timezone="Asia/Seoul")

_WORDCLOUD_TARGETS: list[tuple[str, str]] = [
  ("agri", "kr"),
]

_ANALYSIS_PAGES: list[str] = [
  "analysis-1",
]

_CROP_TARGETS: list[str] = [
  "배추", "무", "사과", "대파", "양파", "감자", "고추", "쌀", "토마토", "오이",
]


def run_wordcloud_etl() -> None:
  """Daily 00:00 — RSS crawl -> wordcloud_terms."""
  from crawler.news_pipeline import pipeline_wordcloud
  from backend.app.db import SessionLocal
  from backend.app.repositories.memory_store import ContentStore

  logger.info("[ETL] Wordcloud update started")
  store = ContentStore(SessionLocal)
  errors: list[str] = []

  for category, region in _WORDCLOUD_TARGETS:
    try:
      words = pipeline_wordcloud(category, region)
      from backend.app.models.wordcloud import Word
      word_objs = [Word(text=w["text"], weight=float(w["weight"])) for w in words]
      store.set_wordcloud(category, region, word_objs)
      logger.info("[ETL] Wordcloud OK: %s/%s (%d terms)", category, region, len(word_objs))
    except Exception as exc:
      logger.error("[ETL] Wordcloud failed: %s/%s — %s", category, region, exc)
      errors.append(f"{category}/{region}: {exc}")

  status = "success" if not errors else "partial_error"
  details = "; ".join(errors) if errors else ""
  store.record_etl_run("news_rss_wordcloud", status, details)
  logger.info("[ETL] Wordcloud finished (status=%s)", status)


def run_analysis_etl() -> None:
  """Monday 00:00 — analysis snapshots."""
  from crawler.news_pipeline import pipeline_analysis
  from backend.app.db import SessionLocal
  from backend.app.repositories.memory_store import ContentStore

  logger.info("[ETL] Analysis snapshots update started")
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
      logger.info("[ETL] Analysis OK: %s", page)
    except Exception as exc:
      logger.error("[ETL] Analysis failed: %s — %s", page, exc)
      errors.append(f"{page}: {exc}")

  status = "success" if not errors else "partial_error"
  details = "; ".join(errors) if errors else ""
  store.record_etl_run("news_analysis", status, details)
  logger.info("[ETL] Analysis snapshots finished (status=%s)", status)


def run_agri_price_etl() -> None:
  """Daily 00:30 — agri public API -> agri_price_* (no-op if env unset)."""
  from crawler.at_price_trend import fetch_full_agri_from_env
  from backend.app.db import SessionLocal
  from backend.app.repositories.agri_etl import upsert_agri_price_from_full_package
  from backend.app.repositories.memory_store import ContentStore

  logger.info("[ETL] Agri price update started")
  full = fetch_full_agri_from_env()
  if not full:
    logger.warning("[ETL] Agri price skipped: DATA_GO_KR_SERVICE_KEY / AT_PRICE_API_PATH not set")
    return

  raw_db_row = full.get("raw_db_row") or {}
  items = raw_db_row.get("items") or []
  try:
    n_ok, n_skip = upsert_agri_price_from_full_package(full, SessionLocal)
    store = ContentStore(SessionLocal)
    store.record_etl_run("agri_price_data_go_kr", "success", f"items={len(items)},history={n_ok},skip={n_skip}")
    logger.info("[ETL] Agri price OK: items=%d, history_rows=%d, skipped=%d", len(items), n_ok, n_skip)
  except Exception as exc:
    logger.exception("[ETL] Agri price failed: %s", exc)
    store = ContentStore(SessionLocal)
    store.record_etl_run("agri_price_data_go_kr", "error", str(exc)[:500])


def run_crop_keywords_etl() -> None:
  """Daily 01:00 — 품목별 뉴스 키워드 수집 (가격-뉴스 상관 분석용)."""
  from crawler.news_pipeline import pipeline_crop_keywords
  from backend.app.db import SessionLocal
  from backend.app.repositories.memory_store import ContentStore
  from backend.app.models.wordcloud import Word

  logger.info("[ETL] Crop keywords update started")
  store = ContentStore(SessionLocal)
  errors: list[str] = []

  for crop in _CROP_TARGETS:
    try:
      words = pipeline_crop_keywords(crop, "kr")
      word_objs = [Word(text=w["text"], weight=float(w["weight"])) for w in words]
      store.set_wordcloud(f"crop_{crop}", "kr", word_objs, min_words=5)
      logger.info("[ETL] Crop keywords OK: %s (%d terms)", crop, len(word_objs))
    except Exception as exc:
      logger.error("[ETL] Crop keywords failed: %s — %s", crop, exc)
      errors.append(f"{crop}: {exc}")

  status = "success" if not errors else "partial_error"
  store.record_etl_run("crop_keywords", status, "; ".join(errors))
  logger.info("[ETL] Crop keywords finished (status=%s)", status)


_KST = "Asia/Seoul"


def start_scheduler() -> None:
  _scheduler.add_job(run_wordcloud_etl, CronTrigger(hour=0, minute=0, timezone=_KST), id="wordcloud_daily")
  _scheduler.add_job(run_agri_price_etl, CronTrigger(hour=0, minute=30, timezone=_KST), id="agri_price_daily")
  _scheduler.add_job(run_crop_keywords_etl, CronTrigger(hour=1, minute=0, timezone=_KST), id="crop_keywords_daily")
  _scheduler.add_job(run_analysis_etl, CronTrigger(day_of_week="mon", hour=0, minute=0, timezone=_KST), id="analysis_weekly")
  _scheduler.start()
  logger.info("[Scheduler] Started — wordcloud 00:00 / agri 00:30 / crops 01:00 / analysis Mon 00:00 (Asia/Seoul)")


def stop_scheduler() -> None:
  if _scheduler.running:
    _scheduler.shutdown(wait=False)
    logger.info("[Scheduler] Stopped")
