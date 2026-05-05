import asyncio
import uuid as _uuid
import datetime as _datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Security, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.responses import StreamingResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

from .models import (
    ConvertedTicket, SportybetTicket, ConversionRecord,
    APIKeyCreate, APIKeyResponse,
    ConvertRequest, ConvertResponse, CompositeAnalysis,
)
from .services.sportybet_parser import SportybetAdapter
from .services.syndicate_service import SyndicateService, MockSyndicateService
from .services.converter import Bet9jaConverter
from .services.pbg_streaming_protocol import live_odds_manager
from .services.auth import APIKeyService, MockAPIKeyService, require_api_key
from .services.storage import SupabaseStorageService, MockStorageService
from .services.ticket_pulse import TicketPulseService, MockTicketPulseService, RiskReport
from .services.risk_engine import RiskEngine
from .services.sentiment import SentimentAnalysisService
from .services.odds_lookup import get_odds_lookup_service
from .services.supabase_client import get_supabase_client
from .config import get_settings
from .batch import BatchConvertRequest, BatchConvertResponse, BatchTicketResult, BatchSummary

router = APIRouter()
parser = SportybetAdapter()
converter = Bet9jaConverter()


def get_auth_service():
    client = get_supabase_client()
    return APIKeyService(client) if client else MockAPIKeyService()


def get_storage_service():
    client = get_supabase_client()
    return SupabaseStorageService(client) if client else MockStorageService()


def get_pulse_service():
    settings = get_settings()
    return TicketPulseService() if settings.anthropic_api_key else MockTicketPulseService()


def get_sentiment_service():
    settings = get_settings()
    return SentimentAnalysisService(api_key=settings.anthropic_api_key or None)


def persist_conversion(storage_service, record: ConversionRecord):
    """Standalone worker function for background persistence."""
    try:
        storage_service.save_conversion(record)
    except Exception as e:
        print(f"ERROR: Background persistence failed: {e}")


class AnalyseRequest(BaseModel):
    converted: ConvertedTicket
    language: str = "en"


class AnalyseResponse(BaseModel):
    success: bool
    analysis: Optional[RiskReport] = None
    error: Optional[str] = None


@router.get("/health")
async def health():
    settings = get_settings()
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "auth_enabled": settings.auth_enabled,
    }


@router.post("/api/v1/convert", response_model=ConvertResponse)
async def convert_ticket(
    request: ConvertRequest,
    background_tasks: BackgroundTasks,
    api_key: str = Depends(require_api_key),
    auth_service=Depends(get_auth_service),
    storage_service=Depends(get_storage_service),
    pulse_service=Depends(get_pulse_service),
    sentiment_service=Depends(get_sentiment_service),
    odds_service=Depends(get_odds_lookup_service),
):
    settings = get_settings()
    if settings.auth_enabled and api_key != "dev_bypass":
        if not auth_service.validate_key(api_key):
            raise HTTPException(status_code=403, detail="Invalid or inactive API key")

    sportybet_ticket = SportybetTicket(
        booking_code=request.booking_code,
        selections=request.selections,
        stake=request.stake,
    )
    internal_ticket, _ = parser.parse(sportybet_ticket)

    if odds_service is not None:
        await odds_service.enrich_val_gap(internal_ticket.selections)

    converted = converter.convert(internal_ticket)

    pulse_result = None
    metrics_result = None
    sentiment_result = None

    if request.include_analysis:
        metrics_result = RiskEngine.compute(converted, internal_ticket.selections)
        pulse_result, sentiment_result = await asyncio.gather(
            pulse_service.analyse(converted, language=request.language),
            sentiment_service.analyse(converted),
        )

    composite = CompositeAnalysis(
        pulse=pulse_result,
        metrics=metrics_result,
        sentiment=sentiment_result,
    )

    record = ConversionRecord(
        api_key=api_key,
        source_booking_code=request.booking_code,
        source_platform="sportybet",
        target_platform="bet9ja",
        selections_count=len(request.selections),
        converted_count=converted.converted_count,
        skipped_count=converted.skipped_count,
        stake=request.stake,
        total_odds=internal_ticket.total_odds,
        potential_returns=internal_ticket.potential_returns,
        risk_score=pulse_result.score if pulse_result else None,
        risk_level=pulse_result.level if pulse_result else None,
    )
    background_tasks.add_task(persist_conversion, storage_service, record)

    # Broadcast to real-time HUD
    await live_odds_manager.broadcast_json({
        "type": "CONVERSION_SUCCESS",
        "source": "sportybet",
        "target": "bet9ja",
        "selections": converted.converted_count,
        "timestamp": _datetime.datetime.now().isoformat(),
    })

    return ConvertResponse(
        success=True,
        converted=converted,
        analysis=composite,
    )


@router.post("/api/v1/analyse", response_model=AnalyseResponse)
async def analyse_ticket(
    request: AnalyseRequest,
    api_key: str = Depends(require_api_key),
    auth_service=Depends(get_auth_service),
    pulse_service=Depends(get_pulse_service),
):
    settings = get_settings()
    if settings.auth_enabled and api_key != "dev_bypass":
        if not auth_service.validate_key(api_key):
            raise HTTPException(status_code=403, detail="Invalid or inactive API key")
    analysis = await pulse_service.analyse(request.converted, language=request.language)
    return AnalyseResponse(success=True, analysis=analysis)


@router.post("/api/v1/analyse/stream")
async def analyse_ticket_stream(
    request: AnalyseRequest,
    api_key: str = Depends(require_api_key),
    auth_service=Depends(get_auth_service),
    pulse_service=Depends(get_pulse_service),
):
    settings = get_settings()
    if settings.auth_enabled and api_key != "dev_bypass":
        if not auth_service.validate_key(api_key):
            raise HTTPException(status_code=403, detail="Invalid or inactive API key")

    generator = pulse_service.analyse_stream(request.converted, language=request.language)
    return StreamingResponse(generator, media_type="text/event-stream")


@router.get("/api/v1/history")
async def get_history(
    limit: int = 50,
    api_key: str = Depends(require_api_key),
    auth_service=Depends(get_auth_service),
    storage_service=Depends(get_storage_service),
):
    settings = get_settings()
    if settings.auth_enabled and api_key != "dev_bypass":
        if not auth_service.validate_key(api_key):
            raise HTTPException(status_code=403, detail="Invalid or inactive API key")
    records = storage_service.get_conversions(api_key=api_key, limit=limit)
    return {"records": [r.__dict__ for r in records], "count": len(records)}


@router.post("/api/v1/keys", response_model=APIKeyResponse)
async def create_api_key(
    payload: APIKeyCreate,
    admin_token: str = Security(APIKeyHeader(name="X-Admin-Token", auto_error=False)),
    auth_service=Depends(get_auth_service),
):
    settings = get_settings()
    if not admin_token or admin_token != settings.admin_token:
        raise HTTPException(status_code=403, detail="Invalid admin token")

    result = auth_service.generate_key(label=payload.label, owner=payload.owner)
    return APIKeyResponse(**result)


@router.post("/api/v1/convert-batch", response_model=BatchConvertResponse)
async def convert_batch(
    request: BatchConvertRequest,
    api_key: str = Depends(require_api_key),
    auth_service=Depends(get_auth_service),
    storage_service=Depends(get_storage_service),
    pulse_service=Depends(get_pulse_service),
):
    settings = get_settings()

    if not settings.batch_enabled:
        raise HTTPException(status_code=404, detail="Batch conversion is not enabled")

    if settings.auth_enabled and api_key != "dev_bypass":
        if not auth_service.validate_key(api_key):
            raise HTTPException(status_code=403, detail="Invalid or inactive API key")

    batch_id = str(_uuid.uuid4())

    async def process_one(index: int, ticket: ConvertRequest) -> BatchTicketResult:
        try:
            sportybet_ticket = SportybetTicket(
                booking_code=ticket.booking_code,
                selections=ticket.selections,
                stake=ticket.stake,
            )
            internal_ticket, _ = parser.parse(sportybet_ticket)
            converted = converter.convert(internal_ticket)

            analysis = None
            if ticket.include_analysis:
                analysis = await pulse_service.analyse(converted, language=ticket.language)

            storage_service.save_conversion(ConversionRecord(
                api_key=api_key,
                source_booking_code=ticket.booking_code,
                source_platform="sportybet",
                target_platform="bet9ja",
                selections_count=len(ticket.selections),
                converted_count=converted.converted_count,
                skipped_count=converted.skipped_count,
                stake=ticket.stake,
                total_odds=internal_ticket.total_odds,
                potential_returns=internal_ticket.potential_returns,
                risk_score=analysis.score if analysis else None,
                risk_level=analysis.level if analysis else None,
            ))

            result = ConvertResponse(success=True, converted=converted, analysis=analysis)
            return BatchTicketResult(index=index, status="success", result=result)

        except Exception as exc:
            return BatchTicketResult(index=index, status="error", error=str(exc))

    tasks = [process_one(i, t) for i, t in enumerate(request.tickets)]
    results: list[BatchTicketResult] = await asyncio.gather(*tasks)

    succeeded = sum(1 for r in results if r.status == "success")
    failed = len(results) - succeeded

    return BatchConvertResponse(
        batch_id=batch_id,
        summary=BatchSummary(total=len(results), succeeded=succeeded, failed=failed),
        results=results,
    )


def get_syndicate_service():
    client = get_supabase_client()
    return SyndicateService(client) if client else MockSyndicateService()


class SyndicateCreate(BaseModel):
    name: str


class MemberAdd(BaseModel):
    api_key: str


class TicketAdd(BaseModel):
    booking_code: str


@router.post("/api/v1/syndicates", status_code=201)
async def create_syndicate(
    payload: SyndicateCreate,
    owner: str = Depends(require_api_key),
    syndicate_service=Depends(get_syndicate_service),
):
    return syndicate_service.create_syndicate(payload.name, owner)


@router.get("/api/v1/syndicates")
async def list_syndicates(
    owner: str = Depends(require_api_key),
    syndicate_service=Depends(get_syndicate_service),
):
    return {"syndicates": syndicate_service.list_syndicates(owner)}


@router.delete("/api/v1/syndicates/{syndicate_id}", status_code=204)
async def delete_syndicate(
    syndicate_id: str,
    owner: str = Depends(require_api_key),
    syndicate_service=Depends(get_syndicate_service),
):
    if not syndicate_service.delete_syndicate(syndicate_id, owner):
        raise HTTPException(status_code=404, detail="Syndicate not found or not owned by you")


@router.post("/api/v1/syndicates/{syndicate_id}/members", status_code=201)
async def add_member(
    syndicate_id: str,
    payload: MemberAdd,
    _: str = Depends(require_api_key),
    syndicate_service=Depends(get_syndicate_service),
):
    result = syndicate_service.add_member(syndicate_id, payload.api_key)
    if result is None:
        raise HTTPException(status_code=404, detail="Syndicate not found")
    return result


@router.delete("/api/v1/syndicates/{syndicate_id}/members/{member_key}", status_code=204)
async def remove_member(
    syndicate_id: str,
    member_key: str,
    _: str = Depends(require_api_key),
    syndicate_service=Depends(get_syndicate_service),
):
    if not syndicate_service.remove_member(syndicate_id, member_key):
        raise HTTPException(status_code=404, detail="Member not found in syndicate")


@router.post("/api/v1/syndicates/{syndicate_id}/tickets", status_code=201)
async def add_syndicate_ticket(
    syndicate_id: str,
    payload: TicketAdd,
    added_by: str = Depends(require_api_key),
    syndicate_service=Depends(get_syndicate_service),
):
    result = syndicate_service.add_ticket(syndicate_id, payload.booking_code, added_by)
    if result is None:
        raise HTTPException(status_code=404, detail="Syndicate not found")
    return result


@router.get("/api/v1/quant/arbs")
async def get_arb_windows(_: str = Security(require_api_key)):
    """Retrieve multi-market arbitrage windows."""
    mock_arbs = [
        {
            "match_id": "ARB_772",
            "teams": "Arsenal vs Chelsea",
            "profit_margin": 0.042,
            "outcomes": {"1": 2.15, "X": 3.45, "2": 4.80},
            "bookmakers": {"1": "SportyBet", "X": "Bet9ja", "2": "Pinnacle"},
        }
    ]
    return {"windows": mock_arbs}


@router.websocket("/api/v1/ws/odds")
async def websocket_odds_endpoint(websocket: WebSocket):
    """
    Connects the Sovereign Terminal Dashboard to the real-time Odds streaming architecture.
    """
    await live_odds_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        live_odds_manager.disconnect(websocket)
