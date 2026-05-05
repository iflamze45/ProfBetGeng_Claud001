"""
AdminService — key management and analytics operations for admin endpoints.
Follows the Protocol + Mock pair pattern used throughout PBG.
"""
from collections import defaultdict
from typing import Optional, Protocol


class AdminServiceProtocol(Protocol):
    def list_keys(self) -> list[dict]: ...
    def deactivate_key(self, key_id: str) -> bool: ...
    def patch_key(self, key_id: str, name: Optional[str], is_active: Optional[bool]) -> Optional[dict]: ...
    def get_analytics(self) -> dict: ...


class AdminService:
    """Production implementation backed by Supabase.

    Columns returned from api_keys: key_id, key_prefix, name, is_active,
        request_count, created_at, last_used_at (key_hash never returned).
    Analytics aggregation is done Python-side to avoid .rpc() free-tier limits.
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

    def get_analytics(self) -> dict:
        result = self.supabase.table("conversions").select(
            "api_key, is_fully_converted, created_at"
        ).execute()
        return _aggregate_conversions(result.data or [])


class MockAdminService:
    """In-memory mock for tests.

    Accepts optional seed_keys and seed_conversions lists.
    """

    def __init__(
        self,
        seed_keys: Optional[list[dict]] = None,
        seed_conversions: Optional[list[dict]] = None,
    ):
        self._keys: list[dict] = [dict(k) for k in (seed_keys or [])]
        self._conversions: list[dict] = list(seed_conversions or [])

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

    def get_analytics(self) -> dict:
        return _aggregate_conversions(self._conversions)


def _aggregate_conversions(rows: list[dict]) -> dict:
    """Shared aggregation logic for both production and mock."""
    total = len(rows)
    if total == 0:
        return {
            "total_conversions": 0,
            "conversions_per_key": [],
            "daily_trend": [],
            "success_rate": 0.0,
        }

    per_key: dict[str, int] = defaultdict(int)
    daily: dict[str, int] = defaultdict(int)
    success_count = 0

    for row in rows:
        api_key = row.get("api_key") or "unknown"
        created_at = row.get("created_at") or ""
        date = created_at[:10] if len(created_at) >= 10 else "unknown"

        per_key[api_key] += 1
        daily[date] += 1
        if row.get("is_fully_converted"):
            success_count += 1

    return {
        "total_conversions": total,
        "conversions_per_key": [
            {"api_key": k, "count": v} for k, v in sorted(per_key.items())
        ],
        "daily_trend": [
            {"date": d, "count": c} for d, c in sorted(daily.items())
        ],
        "success_rate": round(success_count / total, 4),
    }
