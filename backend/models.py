from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime


# ── Enums ──────────────────────────────────────────────────────────────────

class MarketType(str, Enum):
    MATCH_WINNER = "1X2"
    OVER_UNDER = "OVER_UNDER"
    BOTH_TEAMS_SCORE = "BTTS"
    ASIAN_HANDICAP = "ASIAN_HANDICAP"
    DOUBLE_CHANCE = "DOUBLE_CHANCE"
    CORRECT_SCORE = "CORRECT_SCORE"
    BTTS_HT = "BTTS_HT"
    EUROPEAN_HANDICAP = "EUROPEAN_HANDICAP"
    PLAYER_PROP = "PLAYER_PROP"
    UNSUPPORTED = "UNSUPPORTED"


class TicketStatus(str, Enum):
    PENDING = "pending"
    WON = "won"
    LOST = "lost"
    VOID = "void"


# ── SportyBet Input Schemas ────────────────────────────────────────────────

class SportybetSelection(BaseModel):
    event_id: str
    event_name: str
    market: str
    pick: str
    odds: float
    kick_off: Optional[str] = None


class SportybetTicket(BaseModel):
    booking_code: str
    selections: list[SportybetSelection]
    total_odds: Optional[float] = None
    stake: Optional[float] = None


# ── Internal Normalized Schemas ────────────────────────────────────────────

class NormalizedSelection(BaseModel):
    event_id: str
    event_name: str
    market_type: MarketType
    raw_market: str
    pick: str
    odds: float
    confidence: float = 1.0
    kick_off: Optional[str] = None
    metadata: dict = Field(default_factory=dict)


class StructuredWarning(BaseModel):
    code: str
    message: str
    selection_index: Optional[int] = None


class UnresolvedSummary(BaseModel):
    total: int
    unresolved_count: int
    warnings: list[StructuredWarning] = Field(default_factory=list)


class ResponseMeta(BaseModel):
    parser_version: str = "1.0.0"
    processed_at: str = Field(default_factory=lambda: datetime.now(datetime.UTC).isoformat())
    confidence_avg: float = 1.0


class InternalTicket(BaseModel):
    source_booking_code: str
    selections: list[NormalizedSelection]
    total_odds: Optional[float] = None
    stake: Optional[float] = None
    unresolved: UnresolvedSummary = Field(default_factory=lambda: UnresolvedSummary(total=0, unresolved_count=0))
    meta: ResponseMeta = Field(default_factory=ResponseMeta)


# ── Bet9ja Output Schemas ──────────────────────────────────────────────────

class Bet9jaSelection(BaseModel):
    event_id: str
    event_name: str
    market: str
    pick: str
    odds: float
    original_market: str


class ConvertedTicket(BaseModel):
    source_booking_code: str
    target_platform: str = "bet9ja"
    selections: list[Bet9jaSelection]
    converted_count: int
    skipped_count: int
    total_odds: Optional[float] = None
    warnings: list[StructuredWarning] = Field(default_factory=list)
    meta: ResponseMeta = Field(default_factory=ResponseMeta)


# ── Auth & Storage ─────────────────────────────────────────────────────────

class APIKeyCreate(BaseModel):
    label: str
    owner: Optional[str] = None


class APIKeyResponse(BaseModel):
    key: str
    label: str
    owner: Optional[str] = None
    created_at: str


@dataclass
class ConversionRecord:
    api_key: str
    source_booking_code: str
    source_platform: str
    target_platform: str
    selections_count: int
    converted_count: int
    skipped_count: int
    created_at: str = field(default_factory=lambda: datetime.now(datetime.UTC).isoformat())
    id: Optional[str] = None


# ── API Request/Response ───────────────────────────────────────────────────

class ConvertRequest(BaseModel):
    booking_code: str
    selections: list[SportybetSelection]
    stake: Optional[float] = None


class ConvertResponse(BaseModel):
    success: bool
    converted: Optional[ConvertedTicket] = None
    error: Optional[str] = None
