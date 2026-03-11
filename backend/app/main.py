from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.controllers.analysis_controller import build_router as build_analysis_router
from backend.app.controllers.builder_controller import build_router as build_builder_router
from backend.app.controllers.health_controller import router as health_router
from backend.app.controllers.wordcloud_controller import build_router as build_wordcloud_router
from backend.app.repositories.builder_store import BuilderStore
from backend.app.repositories.memory_store import InMemoryStore
from backend.app.services.analysis_service import AnalysisService
from backend.app.services.builder_service import BuilderService
from backend.app.services.wordcloud_service import WordcloudService


def create_app() -> FastAPI:
  app = FastAPI(title="Et Demo API", version="0.1.0")

  app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
  )

  store = InMemoryStore()
  builder_store = BuilderStore()
  wordcloud_service = WordcloudService(store)
  analysis_service = AnalysisService(store)
  builder_service = BuilderService(builder_store)

  app.include_router(health_router, prefix="/api")
  app.include_router(build_wordcloud_router(wordcloud_service), prefix="/api")
  app.include_router(build_analysis_router(analysis_service), prefix="/api")
  app.include_router(build_builder_router(builder_service), prefix="/api")
  return app


app = create_app()

