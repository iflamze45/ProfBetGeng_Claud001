"""
APIKeyService — M4 Step 1
Handles API key generation, validation, and rate limiting.
Supports auth_enabled flag for dev bypass.
"""
import secrets
import hashlib
from typing import Optional, Protocol
from datetime import datetime
from fastapi import HTTPException, Security, Depends
from fastapi.security import APIKeyHeader
from ..config import get_settings

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


class APIKeyServiceProtocol(Protocol):
    def generate_key(self, label: str, owner: Optional[str] = None) -> dict:
        ...

    def validate_key(self, key: str) -> bool:
        ...


class APIKeyService:
    """Production API key service backed by Supabase.

    Schema: api_keys(key_id, key_hash, key_prefix, name, is_active,
                      rate_limit, request_count, created_at, last_used_at)
    """

    def __init__(self, supabase_client):
        self.supabase = supabase_client

    def generate_key(self, label: str, owner: Optional[str] = None) -> dict:
        raw_key = f"pbg_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        key_prefix = raw_key[:12]           # e.g. "pbg_abc12345"
        created_at = datetime.utcnow().isoformat()

        self.supabase.table("api_keys").insert({
            "key_hash": key_hash,
            "key_prefix": key_prefix,
            "name": label,                  # schema uses 'name' not 'label'
            "is_active": True,
        }).execute()

        return {
            "key": raw_key,
            "label": label,
            "owner": owner,
            "created_at": created_at,
        }

    def validate_key(self, key: str) -> bool:
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        result = self.supabase.table("api_keys").select("is_active").eq(
            "key_hash", key_hash
        ).maybe_single().execute()
        return bool(result.data and result.data.get("is_active"))


class MockAPIKeyService:
    """Mock for tests — always valid unless key == 'invalid'."""

    VALID_KEY = "pbg_test_key_valid"

    def generate_key(self, label: str, owner: Optional[str] = None) -> dict:
        return {
            "key": self.VALID_KEY,
            "label": label,
            "owner": owner,
            "created_at": datetime.utcnow().isoformat()
        }

    def validate_key(self, key: str) -> bool:
        return key != "invalid"


def require_api_key(
    api_key: Optional[str] = Security(API_KEY_HEADER),
) -> str:
    settings = get_settings()
    if not settings.auth_enabled:
        return "dev_bypass"
    if not api_key:
        raise HTTPException(status_code=401, detail="API key required")
    # Key validation happens at route level with injected service
    return api_key
