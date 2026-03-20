"""
StorageService — M4 Step 2
Persists conversion records to Supabase.
Protocol-based for easy mock injection in tests.
"""
from typing import Optional, Protocol
from ..models import ConversionRecord


class StorageServiceProtocol(Protocol):
    def save_conversion(self, record: ConversionRecord) -> Optional[str]:
        ...

    def get_conversions(self, api_key: str, limit: int = 50) -> list[ConversionRecord]:
        ...


class SupabaseStorageService:
    """Production storage backed by Supabase."""

    def __init__(self, supabase_client):
        self.supabase = supabase_client

    def save_conversion(self, record: ConversionRecord) -> Optional[str]:
        result = self.supabase.table("conversions").insert({
            "api_key": record.api_key,
            "source_booking_code": record.source_booking_code,
            "source_platform": record.source_platform,
            "target_platform": record.target_platform,
            "selections_count": record.selections_count,
            "converted_count": record.converted_count,
            "skipped_count": record.skipped_count,
            "created_at": record.created_at
        }).execute()

        if result.data:
            return result.data[0].get("id")
        return None

    def get_conversions(self, api_key: str, limit: int = 50) -> list[ConversionRecord]:
        result = self.supabase.table("conversions").select("*").eq(
            "api_key", api_key
        ).order("created_at", desc=True).limit(limit).execute()

        return [ConversionRecord(**row) for row in (result.data or [])]


class MockStorageService:
    """In-memory mock for tests."""

    def __init__(self):
        self._store: list[ConversionRecord] = []

    def save_conversion(self, record: ConversionRecord) -> Optional[str]:
        record.id = f"mock_{len(self._store) + 1}"
        self._store.append(record)
        return record.id

    def get_conversions(self, api_key: str, limit: int = 50) -> list[ConversionRecord]:
        return [r for r in self._store if r.api_key == api_key][:limit]
