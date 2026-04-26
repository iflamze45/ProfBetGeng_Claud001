"""
ProfBetGeng — FastAPI Entry Point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio

from .routes import router
from .config import get_settings

# Optional live-engine services — only available locally, not required on fresh clone
try:
    from .services.pbg_streaming_protocol import LiveOddsEngine, live_odds_manager
    from .services.value_discovery import discovery_hub
    from .services.data_ingestion import ingestion_engine
    pulse_odds_engine = LiveOddsEngine(live_odds_manager)
    _LIVE_ENGINES = True
except ImportError:
    _LIVE_ENGINES = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    print(f"PBG {settings.app_version} starting — env: {settings.environment}")
    if _LIVE_ENGINES:
        ingestion_task = asyncio.create_task(ingestion_engine.start_polling())
        odds_task = asyncio.create_task(pulse_odds_engine.start_stream())
        vdh_task = asyncio.create_task(discovery_hub.start_polling())
    yield
    print("PBG shutdown complete.")
    if _LIVE_ENGINES:
        ingestion_engine.stop()
        pulse_odds_engine.stop_stream()
        discovery_hub.stop()
        await asyncio.gather(ingestion_task, odds_task, vdh_task, return_exceptions=True)



def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan
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
