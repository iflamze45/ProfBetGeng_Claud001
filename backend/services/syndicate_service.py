"""
SyndicateService — syndicate CRUD for group ticket sharing.
Follows the Protocol + Mock pair pattern used throughout PBG.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, Protocol


class SyndicateServiceProtocol(Protocol):
    def create_syndicate(self, name: str, owner: str) -> dict: ...
    def list_syndicates(self, owner: str) -> list[dict]: ...
    def delete_syndicate(self, syndicate_id: str, owner: str) -> bool: ...
    def add_member(self, syndicate_id: str, api_key: str) -> Optional[dict]: ...
    def remove_member(self, syndicate_id: str, api_key: str) -> bool: ...
    def add_ticket(self, syndicate_id: str, booking_code: str, added_by: str) -> Optional[dict]: ...


class SyndicateService:
    """Production implementation backed by Supabase.

    Tables: syndicates, syndicate_members, syndicate_tickets
    (schema: supabase/migrations/005_syndicates.sql)
    """

    def __init__(self, supabase_client):
        self.supabase = supabase_client

    def create_syndicate(self, name: str, owner: str) -> dict:
        result = self.supabase.table("syndicates").insert({
            "name": name,
            "owner_api_key": owner,
        }).select("id, name, owner_api_key, created_at").execute()
        return result.data[0]

    def list_syndicates(self, owner: str) -> list[dict]:
        result = self.supabase.table("syndicates").select(
            "id, name, owner_api_key, created_at"
        ).eq("owner_api_key", owner).order("created_at", desc=True).execute()
        return result.data or []

    def delete_syndicate(self, syndicate_id: str, owner: str) -> bool:
        result = self.supabase.table("syndicates").delete().eq(
            "id", syndicate_id
        ).eq("owner_api_key", owner).select("id").execute()
        return bool(result.data)

    def add_member(self, syndicate_id: str, api_key: str) -> Optional[dict]:
        exists = self.supabase.table("syndicates").select("id").eq(
            "id", syndicate_id
        ).maybe_single().execute()
        if not exists.data:
            return None
        result = self.supabase.table("syndicate_members").insert({
            "syndicate_id": syndicate_id,
            "api_key": api_key,
        }).select("id, syndicate_id, api_key, joined_at").execute()
        return result.data[0] if result.data else None

    def remove_member(self, syndicate_id: str, api_key: str) -> bool:
        result = self.supabase.table("syndicate_members").delete().eq(
            "syndicate_id", syndicate_id
        ).eq("api_key", api_key).select("id").execute()
        return bool(result.data)

    def add_ticket(self, syndicate_id: str, booking_code: str, added_by: str) -> Optional[dict]:
        exists = self.supabase.table("syndicates").select("id").eq(
            "id", syndicate_id
        ).maybe_single().execute()
        if not exists.data:
            return None
        result = self.supabase.table("syndicate_tickets").insert({
            "syndicate_id": syndicate_id,
            "booking_code": booking_code,
            "added_by": added_by,
        }).select("id, syndicate_id, booking_code, added_by, added_at").execute()
        return result.data[0] if result.data else None


class MockSyndicateService:
    """In-memory mock for tests."""

    def __init__(self):
        self._syndicates: dict[str, dict] = {}
        self._members: list[dict] = []
        self._tickets: list[dict] = []

    def create_syndicate(self, name: str, owner: str) -> dict:
        sid = str(uuid.uuid4())
        record = {
            "id": sid,
            "name": name,
            "owner_api_key": owner,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._syndicates[sid] = record
        return dict(record)

    def list_syndicates(self, owner: str) -> list[dict]:
        return [dict(s) for s in self._syndicates.values() if s["owner_api_key"] == owner]

    def delete_syndicate(self, syndicate_id: str, owner: str) -> bool:
        s = self._syndicates.get(syndicate_id)
        if not s or s["owner_api_key"] != owner:
            return False
        del self._syndicates[syndicate_id]
        self._members = [m for m in self._members if m["syndicate_id"] != syndicate_id]
        self._tickets = [t for t in self._tickets if t["syndicate_id"] != syndicate_id]
        return True

    def add_member(self, syndicate_id: str, api_key: str) -> Optional[dict]:
        if syndicate_id not in self._syndicates:
            return None
        record = {
            "id": str(uuid.uuid4()),
            "syndicate_id": syndicate_id,
            "api_key": api_key,
            "joined_at": datetime.now(timezone.utc).isoformat(),
        }
        self._members.append(record)
        return dict(record)

    def remove_member(self, syndicate_id: str, api_key: str) -> bool:
        before = len(self._members)
        self._members = [
            m for m in self._members
            if not (m["syndicate_id"] == syndicate_id and m["api_key"] == api_key)
        ]
        return len(self._members) < before

    def add_ticket(self, syndicate_id: str, booking_code: str, added_by: str) -> Optional[dict]:
        if syndicate_id not in self._syndicates:
            return None
        record = {
            "id": str(uuid.uuid4()),
            "syndicate_id": syndicate_id,
            "booking_code": booking_code,
            "added_by": added_by,
            "added_at": datetime.now(timezone.utc).isoformat(),
        }
        self._tickets.append(record)
        return dict(record)
