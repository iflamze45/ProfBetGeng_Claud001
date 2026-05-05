"""
AdminService — key management operations for admin endpoints.
Follows the Protocol + Mock pair pattern used throughout PBG.
"""
from typing import Optional, Protocol


class AdminServiceProtocol(Protocol):
    def list_keys(self) -> list[dict]: ...
    def deactivate_key(self, key_id: str) -> bool: ...
    def patch_key(self, key_id: str, name: Optional[str], is_active: Optional[bool]) -> Optional[dict]: ...


class AdminService:
    """Production implementation backed by Supabase.

    Columns returned: key_id, key_prefix, name, is_active, request_count, created_at, last_used_at
    key_hash is never returned (security).
    """

    def __init__(self, supabase_client):
        self.supabase = supabase_client

    def list_keys(self) -> list[dict]:
        result = self.supabase.table("api_keys").select(
            "key_id, key_prefix, name, is_active, request_count, created_at, last_used_at"
        ).order("created_at", desc=True).execute()
        return result.data or []

    def deactivate_key(self, key_id: str) -> bool:
        result = self.supabase.table("api_keys").update(
            {"is_active": False}
        ).eq("key_id", key_id).select("key_id").execute()
        return bool(result.data)

    def patch_key(self, key_id: str, name: Optional[str], is_active: Optional[bool]) -> Optional[dict]:
        result = self.supabase.table("api_keys").select(
            "key_id, key_prefix, name, is_active, request_count, created_at, last_used_at"
        ).eq("key_id", key_id).maybe_single().execute()
        if not result.data:
            return None
        updates: dict = {}
        if name is not None:
            updates["name"] = name
        if is_active is not None:
            updates["is_active"] = is_active
        if updates:
            updated = self.supabase.table("api_keys").update(updates).eq(
                "key_id", key_id
            ).select(
                "key_id, key_prefix, name, is_active, request_count, created_at, last_used_at"
            ).execute()
            return updated.data[0] if updated.data else result.data
        return result.data


class MockAdminService:
    """In-memory mock for tests. Accepts optional seed_keys list."""

    def __init__(self, seed_keys: Optional[list[dict]] = None):
        self._keys: list[dict] = [dict(k) for k in (seed_keys or [])]

    def list_keys(self) -> list[dict]:
        return list(self._keys)

    def deactivate_key(self, key_id: str) -> bool:
        for key in self._keys:
            if key["key_id"] == key_id:
                key["is_active"] = False
                return True
        return False

    def patch_key(self, key_id: str, name: Optional[str], is_active: Optional[bool]) -> Optional[dict]:
        for key in self._keys:
            if key["key_id"] == key_id:
                if name is not None:
                    key["name"] = name
                if is_active is not None:
                    key["is_active"] = is_active
                return dict(key)
        return None
