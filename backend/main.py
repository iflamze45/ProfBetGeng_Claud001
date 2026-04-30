"""
ProfBetGeng — FastAPI Entry Point
"""
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import router
from .config import get_settings
from .services.pbg_streaming_protocol import LiveOddsEngine, live_odds_manager

logger = logging.getLogger(__name__)

pulse_odds_engine = LiveOddsEngine(live_odds_manager)


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    logger.info(f"PBG {settings.app_version} starting — env: {settings.environment}")
    print(f"PBG {settings.app_version} starting — env: {settings.environment}")
    odds_task = asyncio.create_task(pulse_odds_engine.start_stream())
    yield
    pulse_odds_engine.stop_stream()
    await asyncio.gather(odds_task, return_exceptions=True)
    logger.info("PBG shutdown complete.")
    print("PBG shutdown complete.")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://localhost:5174",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:5174",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
