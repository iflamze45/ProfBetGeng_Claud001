import re
from pydantic import BaseModel, Field, field_validator
from typing import Any, Optional
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timezone


# ── Helpers ────────────────────────────────────────────────────────────────

def sanitize_html(text: str) -> str:
    if not text:
        return text
    # Strip common HTML tags
    return re.sub(r'<[^>]*>', '', text)


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

    @field_validator("event_name", "market", "pick")
    @classmethod
    def clean_text(cls, v: str) -> str:
        return sanitize_html(v)


class SportybetTicket(BaseModel):
    booking_code: str
    selections: list[SportybetSelection]
    total_odds: Optional[float] = None
    stake: Optional[float] = None

    @field_validator("booking_code")
    @classmethod
    def clean_code(cls, v: str) -> str:
        return sanitize_html(v)


# ── Internal Normalized Schemas ────────────────────────────────────────────

class NormalizedSelection(BaseModel):
    event_id: str
    event_name: str
    market_type: MarketType
    raw_market: str
    pick: str
    line: Optional[str] = None
    odds: float
    confidence: float = 1.0
    kick_off: Optional[str] = None
    correlation_group: Optional[str] = None # Grouping matches to detect overexposure
    val_gap_score: float = 0.0 # (Local Odds / Global Fair) - 1
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
    processed_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    confidence_avg: float = 1.0


class InternalTicket(BaseModel):
    source_booking_code: str
    selections: list[NormalizedSelection]
    total_odds: Optional[float] = None
    stake: Optional[float] = None
    potential_returns: Optional[float] = None
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
    stake: Optional[float] = None
    potential_returns: Optional[float] = None
    total_odds: Optional[float] = None
    risk_score: Optional[int] = None
    risk_level: Optional[str] = None
    net_roi: Optional[float] = None # Tracked after result
    is_settled: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    id: Optional[str] = None

@dataclass
class ExecutionResult:
    """The 'Finality' object—locking the outcome of a ticket."""
    ticket_id: str
    status: TicketStatus
    payout_actual: float
    roi_actual: float
    settled_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    consensus_clv: float = 0.0 # Closing Line Value at time of settlement


# ── API Request/Response ───────────────────────────────────────────────────

class ParseTicketRequest(BaseModel):
    raw_text: str


class ParseTicketResponse(BaseModel):
    success: bool
    ticket: Optional[SportybetTicket] = None
    error: Optional[str] = None


class SocialTicket(BaseModel):
    ticket_id: str
    username: str = "Anonymous Sovereign"
    selections_summary: str
    total_odds: float
    verified_roi: float = 0.0
    sentiment_score: float
    published_at: datetime = datetime.now()
    mirrors_count: int = 0
    reputation_score: int = 100 # 0-1000

class MirrorAction(BaseModel):
    target_ticket_id: str
    source_username: str
    applied_multiplier: float = 1.0 # fractional kelly adjustment

class KellyStakeRequest(BaseModel):
    local_odds: float
    global_odds: float
    social_spike: float = 1.0
    bankroll: Optional[float] = 1000.0 # Default fallback

class KellyStakeResponse(BaseModel):
    optimal_stake: float
    fraction: float
    confidence: str
    risk_ruin: float

class ConvertRequest(BaseModel):
    booking_code: str
    selections: list[SportybetSelection]
    stake: Optional[float] = None
    include_analysis: bool = False
    language: str = "en"


class CompositeAnalysis(BaseModel):
    """Triad of analysis signals returned with every converted ticket."""
    model_config = {"arbitrary_types_allowed": True}

    pulse: Optional[Any] = None      # RiskReport from TicketPulseService
    metrics: Optional[Any] = None    # RiskMetrics from RiskEngine
    sentiment: Optional[Any] = None  # SentimentReport from SentimentAnalysisService


class ConvertResponse(BaseModel):
    model_config = {"arbitrary_types_allowed": True}

    success: bool
    converted: Optional[ConvertedTicket] = None
    analysis: Optional[CompositeAnalysis] = None
    sentiment: Optional[dict] = None
    error: Optional[str] = None
