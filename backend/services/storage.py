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
    """Production storage backed by Supabase.

    Schema: conversions(record_id, api_key_id, source_sportsbook,
                         target_sportsbook, booking_code, source_ticket_id,
                         parse_confidence, conversion_confidence,
                         convertible_count, unconvertible_count,
                         selection_count, has_splits, is_fully_converted,
                         raw_parse_result, raw_conversion, pulse_analysis,
                         created_at)
    """

    def __init__(self, supabase_client):
        self.supabase = supabase_client

    def save_conversion(self, record: ConversionRecord) -> Optional[str]:
        result = self.supabase.table("conversions").insert({
            "api_key_id": record.api_key,
            "source_sportsbook": record.source_platform,
            "target_sportsbook": record.target_platform,
            "booking_code": record.source_booking_code,
            "source_ticket_id": record.source_booking_code,
            "selection_count": record.selections_count,
            "convertible_count": record.converted_count,
            "unconvertible_count": record.skipped_count,
            "is_fully_converted": record.skipped_count == 0,
            "stake": record.stake,
            "potential_returns": record.potential_returns,
            "total_odds": record.total_odds,
            "risk_score": record.risk_score,
            "risk_level": record.risk_level,
            "parse_confidence": 1.0,
            "conversion_confidence": 1.0,
        }).execute()

        if result.data:
            return result.data[0].get("record_id")
        return None

    def get_conversions(self, api_key: str, limit: int = 50) -> list[ConversionRecord]:
        result = self.supabase.table("conversions").select("*").eq(
            "api_key_id", api_key
        ).order("created_at", desc=True).limit(limit).execute()

        # Map real schema columns back to ConversionRecord fields
        records = []
        for row in (result.data or []):
            records.append(ConversionRecord(
                api_key=row.get("api_key_id", ""),
                source_booking_code=row.get("booking_code", ""),
                source_platform=row.get("source_sportsbook", ""),
                target_platform=row.get("target_sportsbook", ""),
                selections_count=row.get("selection_count", 0),
                converted_count=row.get("convertible_count", 0),
                skipped_count=row.get("unconvertible_count", 0),
                stake=row.get("stake"),
                potential_returns=row.get("potential_returns"),
                total_odds=row.get("total_odds"),
                risk_score=row.get("risk_score"),
                risk_level=row.get("risk_level"),
                created_at=str(row.get("created_at", "")),
                id=str(row.get("record_id", "")),
            ))
        return records


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
