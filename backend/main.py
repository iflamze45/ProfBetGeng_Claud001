"""
ProfBetGeng — FastAPI Entry Point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio

from .routes import router
from .config import get_settings
from .services.pbg_streaming_protocol import LiveOddsEngine, live_odds_manager
from .services.value_discovery import discovery_hub
from .services.data_ingestion import ingestion_engine

pulse_odds_engine = LiveOddsEngine(live_odds_manager)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    print(f"PBG {settings.app_version} starting — env: {settings.environment}")

    # Wire new value signals → WebSocket broadcast
    def _on_signal(signal):
        asyncio.create_task(live_odds_manager.broadcast_json({
            "type": "VALUE_SIGNAL",
            "match_id": signal.match_id,
            "teams": signal.teams,
            "market": signal.market,
            "local_odds": signal.local_odds,
            "global_odds": signal.global_odds,
            "value_score": signal.value_score,
            "signal_type": signal.signal_type,
            "timestamp": signal.timestamp.isoformat(),
        }))

    discovery_hub.on_new_signal(_on_signal)

    ingestion_task = asyncio.create_task(ingestion_engine.start_polling())
    odds_task = asyncio.create_task(pulse_odds_engine.start_stream())
    vdh_task = asyncio.create_task(discovery_hub.start_polling())
    yield
    print("PBG shutdown complete.")
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
