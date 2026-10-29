from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from sqlalchemy import Engine

from ad_automation.config import Settings
from ad_automation.db import create_database_engine, initialize_database
from ad_automation.api.assets import router as assets_router
from ad_automation.api.jobs import router as jobs_router


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or Settings.from_env()
    engine = create_database_engine(app_settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        initialize_database(engine)
        yield
        engine.dispose()

    app = FastAPI(title="广告素材自动化处理系统", lifespan=lifespan)
    app.state.settings = app_settings
    app.state.database_engine = engine
    app.include_router(assets_router)
    app.include_router(jobs_router)

    @app.get("/api/health")
    def health() -> dict[str, bool | str]:
        ffmpeg_ready = bool(app_settings.ffmpeg_path and app_settings.ffprobe_path)
        return {
            "ready": True,
            "database": "ok" if app_settings.database_path.is_file() else "error",
            "ffmpeg": ffmpeg_ready,
        }

    return app


app = create_app()
