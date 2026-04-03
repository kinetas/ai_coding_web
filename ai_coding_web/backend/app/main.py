from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.bootstrap import init_database
from backend.app.config import get_settings
from backend.app.controllers.analysis_controller import build_router as build_analysis_router
from backend.app.controllers.auth_controller import router as auth_router
from backend.app.controllers.builder_controller import build_router as build_builder_router
from backend.app.controllers.health_controller import router as health_router
from backend.app.controllers.agri_analytics_controller import build_router as build_agri_analytics_router
from backend.app.controllers.public_category_controller import build_router as build_public_category_router
from backend.app.controllers.wordcloud_controller import build_router as build_wordcloud_router
from backend.app.db import SessionLocal
from backend.app.repositories.builder_store import BuilderStore
from backend.app.repositories.memory_store import ContentStore
from backend.app.repositories.supabase_content_store import SupabaseContentStore
from backend.app.services.agri_analytics_service import AgriAnalyticsService
from backend.app.services.public_category_service import PublicCategoryService
from backend.app.services.analysis_service import AnalysisService
from backend.app.services.builder_service import BuilderService
from backend.app.services.wordcloud_service import WordcloudService


def create_app() -> FastAPI:
  settings = get_settings()
  init_database()

  app = FastAPI(title=settings.app_name, version=settings.app_version)

  app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins or ["http://127.0.0.1:5500"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
  )

  if settings.content_source == "supabase":
    if not settings.supabase_url:
      raise RuntimeError("CONTENT_SOURCE=supabase 일 때 SUPABASE_URL 이 필요합니다.")
    store: ContentStore | SupabaseContentStore = SupabaseContentStore(settings)
  else:
    store = ContentStore(SessionLocal)

  builder_store = BuilderStore(SessionLocal)
  wordcloud_service = WordcloudService(store)
  analysis_service = AnalysisService(store)
  builder_service = BuilderService(builder_store)
  agri_analytics_service = AgriAnalyticsService(settings)
  public_category_service = PublicCategoryService(settings)

  app.include_router(health_router, prefix="/api")
  app.include_router(auth_router, prefix="/api")
  app.include_router(build_wordcloud_router(wordcloud_service), prefix="/api")
  app.include_router(build_analysis_router(analysis_service), prefix="/api")
  app.include_router(build_builder_router(builder_service), prefix="/api")
  app.include_router(build_agri_analytics_router(agri_analytics_service), prefix="/api")
  app.include_router(build_public_category_router(public_category_service), prefix="/api")
  return app


app = create_app()

