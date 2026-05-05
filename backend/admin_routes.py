"""
PBG Admin Routes — key management endpoints (v0.7.0).
All endpoints gated by X-Admin-Token header.
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

from .config import get_settings
from .services.admin_service import AdminService, MockAdminService
from .services.supabase_client import get_supabase_client

admin_router = APIRouter()
_logger = logging.getLogger(__name__)

_ADMIN_TOKEN_HEADER = APIKeyHeader(name="X-Admin-Token", auto_error=False)


def get_admin_service():
    client = get_supabase_client()
    if client is None:
        settings = get_settings()
        if settings.environment == "production":
            raise HTTPException(status_code=503, detail="Admin service unavailable — Supabase not configured")
        _logger.warning("AdminService: Supabase client unavailable — using in-memory mock (dev only)")
        return MockAdminService()
    return AdminService(client)


def _require_admin(
    token: Optional[str] = Security(_ADMIN_TOKEN_HEADER),
) -> None:
    settings = get_settings()
    if not token or token != settings.admin_token:
        raise HTTPException(status_code=403, detail="Invalid admin token")


class KeyPatchRequest(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None


@admin_router.get("/api/v1/admin/keys")
async def list_keys(
    _: None = Depends(_require_admin),
    admin_service=Depends(get_admin_service),
):
    keys = admin_service.list_keys()
    return {"keys": keys}


@admin_router.delete("/api/v1/admin/keys/{key_id}")
async def deactivate_key(
    key_id: str,
    _: None = Depends(_require_admin),
    admin_service=Depends(get_admin_service),
):
    success = admin_service.deactivate_key(key_id)
    if not success:
        raise HTTPException(status_code=404, detail="Key not found")
    return {"success": True, "key_id": key_id}


@admin_router.patch("/api/v1/admin/keys/{key_id}")
async def patch_key(
    key_id: str,
    payload: KeyPatchRequest,
    _: None = Depends(_require_admin),
    admin_service=Depends(get_admin_service),
):
    result = admin_service.patch_key(key_id, payload.name, payload.is_active)
    if result is None:
        raise HTTPException(status_code=404, detail="Key not found")
    return result
