from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import APIKeyHeader
from typing import Optional
from pydantic import BaseModel

from .models import (
    ConvertedTicket, SportybetTicket, ConversionRecord,
    APIKeyCreate, APIKeyResponse, SportybetSelection,
    ConvertRequest, ConvertResponse,
)
from .services.sportybet_parser import SportybetAdapter
from .services.converter import Bet9jaConverter
from .services.auth import APIKeyService, MockAPIKeyService, require_api_key
from .services.storage import SupabaseStorageService, MockStorageService
from .services.ticket_pulse import TicketPulseService, MockTicketPulseService, RiskReport
from .services.supabase_client import get_supabase_client
from .config import get_settings

router = APIRouter()


def get_auth_service():
    client = get_supabase_client()
    return APIKeyService(client) if client else MockAPIKeyService()


def get_storage_service():
    client = get_supabase_client()
    return SupabaseStorageService(client) if client else MockStorageService()


def get_pulse_service():
    settings = get_settings()
    return TicketPulseService() if settings.anthropic_api_key else MockTicketPulseService()

parser = SportybetAdapter()
converter = Bet9jaConverter()


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
    return {"status": "ok", "app": settings.app_name, "version": settings.app_version, "auth_enabled": settings.auth_enabled}


@router.post("/api/v1/convert", response_model=ConvertResponse)
async def convert_ticket(
    request: ConvertRequest,
    api_key: str = Depends(require_api_key),
    auth_service=Depends(get_auth_service),
    storage_service=Depends(get_storage_service),
    pulse_service=Depends(get_pulse_service),
):
    settings = get_settings()
    if settings.auth_enabled and api_key != "dev_bypass":
        if not auth_service.validate_key(api_key):
            raise HTTPException(status_code=403, detail="Invalid or inactive API key")

    sportybet_ticket = SportybetTicket(booking_code=request.booking_code, selections=request.selections, stake=request.stake)
    internal_ticket, _ = parser.parse(sportybet_ticket)
    converted = converter.convert(internal_ticket)

    storage_service.save_conversion(ConversionRecord(
        api_key=api_key,
        source_booking_code=request.booking_code,
        source_platform="sportybet",
        target_platform="bet9ja",
        selections_count=len(request.selections),
        converted_count=converted.converted_count,
        skipped_count=converted.skipped_count,
    ))

    analysis = None
    if request.include_analysis:
        analysis = await pulse_service.analyse(converted, language=request.language)

    return ConvertResponse(success=True, converted=converted, analysis=analysis)


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
    auth_service=Depends(get_auth_service),
):
    result = auth_service.generate_key(label=payload.label, owner=payload.owner)
    return APIKeyResponse(**result)



# ─── Batch Conversion ────────────────────────────────────────────────────────

import asyncio
import uuid as _uuid
from .batch import BatchConvertRequest, BatchConvertResponse, BatchTicketResult, BatchSummary


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

            storage_service.save_conversion(ConversionRecord(
                api_key=api_key,
                source_booking_code=ticket.booking_code,
                source_platform="sportybet",
                target_platform="bet9ja",
                selections_count=len(ticket.selections),
                converted_count=converted.converted_count,
                skipped_count=converted.skipped_count,
            ))

            analysis = None
            if ticket.include_analysis:
                analysis = await pulse_service.analyse(converted, language=ticket.language)

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
