"""
ProfBetGeng API Routes — v1
POST /api/v1/convert   — Convert SportyBet ticket to Bet9ja (authenticated)
GET  /api/v1/history   — Get conversion history for API key (authenticated)
POST /api/v1/keys      — Generate new API key (admin)
GET  /health           — Health check (public)
"""
from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi.security import APIKeyHeader
from typing import Optional

from .models import (
    ConvertRequest, ConvertResponse, ConvertedTicket,
    SportybetTicket, ConversionRecord, APIKeyCreate, APIKeyResponse
)
from .services.sportybet_parser import SportybetAdapter
from .services.converter import Bet9jaConverter
from .services.auth import MockAPIKeyService, require_api_key
from .services.storage import MockStorageService
from .config import get_settings

router = APIRouter()

# ── Dependency Providers (swap for production instances) ──────────────────

def get_auth_service():
    return MockAPIKeyService()

def get_storage_service():
    return MockStorageService()

parser = SportybetAdapter()
converter = Bet9jaConverter()

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


# ── Health ─────────────────────────────────────────────────────────────────

@router.get("/health")
async def health():
    settings = get_settings()
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "auth_enabled": settings.auth_enabled
    }


# ── Convert ────────────────────────────────────────────────────────────────

@router.post("/api/v1/convert", response_model=ConvertResponse)
async def convert_ticket(
    request: ConvertRequest,
    api_key: str = Depends(require_api_key),
    auth_service=Depends(get_auth_service),
    storage_service=Depends(get_storage_service),
):
    settings = get_settings()

    # Validate key against service (skip in dev bypass)
    if settings.auth_enabled and api_key != "dev_bypass":
        if not auth_service.validate_key(api_key):
            raise HTTPException(status_code=403, detail="Invalid or inactive API key")

    # Parse
    sportybet_ticket = SportybetTicket(
        booking_code=request.booking_code,
        selections=request.selections,
        stake=request.stake
    )
    internal_ticket, parse_warnings = parser.parse(sportybet_ticket)

    # Convert
    converted = converter.convert(internal_ticket)

    # Persist
    record = ConversionRecord(
        api_key=api_key,
        source_booking_code=request.booking_code,
        source_platform="sportybet",
        target_platform="bet9ja",
        selections_count=len(request.selections),
        converted_count=converted.converted_count,
        skipped_count=converted.skipped_count,
    )
    storage_service.save_conversion(record)

    return ConvertResponse(success=True, converted=converted)


# ── History ────────────────────────────────────────────────────────────────

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


# ── Key Generation ─────────────────────────────────────────────────────────

@router.post("/api/v1/keys", response_model=APIKeyResponse)
async def create_api_key(
    payload: APIKeyCreate,
    auth_service=Depends(get_auth_service),
):
    result = auth_service.generate_key(label=payload.label, owner=payload.owner)
    return APIKeyResponse(**result)
