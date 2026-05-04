"""
SportybetParser — M1/M2
Parses raw SportyBet selections into normalized InternalTicket.
Returns (InternalTicket, list[StructuredWarning]) — never raises on soft failures.
"""
import re
import logging
from typing import Protocol, Optional

logger = logging.getLogger(__name__)
from ..models import (
    SportybetTicket, InternalTicket, NormalizedSelection,
    StructuredWarning, UnresolvedSummary, ResponseMeta, MarketType
)


from enum import Enum
from typing import Protocol, Optional, Dict

class ProxyType(str, Enum):
    RESIDENTIAL = "RESIDENTIAL"
    MOBILE_LTE = "MOBILE_LTE"
    DATACENTER = "DATACENTER"

class ProxyController:
    """
    Phase 15: The Veil.
    Manages dynamic proxy rotation to evade detection.
    """
    def __init__(self):
        self.suspicion_score: float = 0.0 # 1.0 triggers rotation
        self.active_type: ProxyType = ProxyType.DATACENTER

    def rotate_mesh(self):
        """Rotates to high-integrity mobile/residential if suspicion is high."""
        if self.suspicion_score > 0.7:
            self.active_type = ProxyType.MOBILE_LTE
            logger.warning("THE_VEIL: Rotating to MOBILE_LTE mesh. High suspicion detected.")
        elif self.suspicion_score > 0.3:
            self.active_type = ProxyType.RESIDENTIAL
        else:
            self.active_type = ProxyType.DATACENTER
        
        self.suspicion_score = 0.0 # Reset after rotation

MARKET_MAP: dict[str, MarketType] = {
    # 1X2
    "1x2": MarketType.MATCH_WINNER,
    "match winner": MarketType.MATCH_WINNER,
    "full time result": MarketType.MATCH_WINNER,
    # Over/Under
    "over/under": MarketType.OVER_UNDER,
    "total goals": MarketType.OVER_UNDER,
    "goals over/under": MarketType.OVER_UNDER,
    # BTTS
    "both teams to score": MarketType.BOTH_TEAMS_SCORE,
    "btts": MarketType.BOTH_TEAMS_SCORE,
    "gg/ng": MarketType.BOTH_TEAMS_SCORE,
    # BTTS HT
    "both teams to score - 1st half": MarketType.BTTS_HT,
    "btts ht": MarketType.BTTS_HT,
    # Asian Handicap
    "asian handicap": MarketType.ASIAN_HANDICAP,
    "ah": MarketType.ASIAN_HANDICAP,
    # European Handicap
    "european handicap": MarketType.EUROPEAN_HANDICAP,
    "handicap": MarketType.EUROPEAN_HANDICAP,
    # Double Chance
    "double chance": MarketType.DOUBLE_CHANCE,
    # Correct Score
    "correct score": MarketType.CORRECT_SCORE,
    # Player Props
    "player to score": MarketType.PLAYER_PROP,
    "anytime scorer": MarketType.PLAYER_PROP,
    "first goal scorer": MarketType.PLAYER_PROP,
}

AH_QUARTER_PATTERN = re.compile(r"^([+-]?\d+\.25|[+-]?\d+\.75)$")
CORRECT_SCORE_PATTERN = re.compile(r"^\d+[-:]\d+$")


def _resolve_market(raw: str) -> tuple[MarketType, float]:
    """Returns (MarketType, confidence)"""
    normalized = raw.strip().lower()
    if normalized in MARKET_MAP:
        return MARKET_MAP[normalized], 1.0
    # Partial match
    for key, market in MARKET_MAP.items():
        if key in normalized:
            return market, 0.85
    return MarketType.UNSUPPORTED, 0.0


def _format_ah_leg(value: float) -> str:
    """Format an AH line value keeping exactly one decimal place."""
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.1f}"


def _resolve_ah_line(pick: str) -> tuple[str, list[str]]:
    """Splits quarter-ball AH into two standard lines."""
    match = AH_QUARTER_PATTERN.match(pick.strip())
    if not match:
        return pick, []
    value = float(pick)
    leg1 = _format_ah_leg(value - 0.25)
    leg2 = _format_ah_leg(value + 0.25)
    return pick, [leg1, leg2]


def _normalize_pick_and_line(market_type: MarketType, raw_pick: str) -> tuple[str, Optional[str]]:
    """Separates the generic pick string from its numeric line value."""
    pick = raw_pick.strip()
    upper_pick = pick.upper()
    line = None
    
    if market_type == MarketType.OVER_UNDER:
        match = re.search(r'(OVER|UNDER|O|U)[^\d]*(\d+\.?\d*)', upper_pick)
        if match:
            pick = "O" if match.group(1).startswith("O") else "U"
            line = match.group(2)
            
    elif market_type in (MarketType.ASIAN_HANDICAP, MarketType.EUROPEAN_HANDICAP):
        match = re.search(r'([A-Z1X2\s]+)?\s*[\(]?([+-]?\d+\.?\d*)[\)]?', upper_pick)
        if match:
            extracted_pick = match.group(1).strip() if match.group(1) else "AH"
            if extracted_pick:
                pick = extracted_pick
            line = match.group(2)
            
    elif market_type in (MarketType.BOTH_TEAMS_SCORE, MarketType.BTTS_HT):
        if upper_pick in ["YES", "GG", "GG/NG", "BOTH TEAMS TO SCORE"]:
            pick = "GG"
        elif upper_pick in ["NO", "NG"]:
            pick = "NG"
            
    return pick, line


class SportsbookAdapter(Protocol):
    def parse(self, ticket: SportybetTicket) -> tuple[InternalTicket, list[StructuredWarning]]:
        ...


class SportybetAdapter:
    PARSER_VERSION = "1.1.0" # Phase 15 Upgrade

    def __init__(self):
        self.veil = ProxyController()

    def parse(self, ticket: SportybetTicket) -> tuple[InternalTicket, list[StructuredWarning]]:
        selections: list[NormalizedSelection] = []
        warnings: list[StructuredWarning] = []
        confidence_sum = 0.0

        # Detection Simulation: Logic that flags suspicious parsing patterns
        if len(ticket.selections) > 10:
            self.veil.suspicion_score += 0.2
            if self.veil.suspicion_score > 0.5:
                self.veil.rotate_mesh()

        for idx, sel in enumerate(ticket.selections):
            market_type, confidence = _resolve_market(sel.market)
            
            normalized_pick, line = _normalize_pick_and_line(market_type, sel.pick)

            metadata: dict = {}

            if market_type == MarketType.ASIAN_HANDICAP:
                _, legs = _resolve_ah_line(sel.pick)
                if legs:
                    metadata["ah_legs"] = legs

            if market_type == MarketType.PLAYER_PROP:
                metadata["player_prop"] = True
                metadata["raw_pick"] = sel.pick

            if CORRECT_SCORE_PATTERN.match(sel.pick.strip()):
                metadata["correct_score"] = True

            if market_type == MarketType.UNSUPPORTED:
                warnings.append(StructuredWarning(
                    code="UNRESOLVED_MARKET",
                    message=f"Could not resolve market '{sel.market}'",
                    selection_index=idx
                ))

            try:
                odds = float(sel.odds)
                if odds < 1.0:
                    raise ValueError("Odds cannot be less than 1.0")
            except (ValueError, TypeError):
                odds = 1.0
                warnings.append(StructuredWarning(
                    code="INVALID_ODDS",
                    message=f"Invalid odds '{sel.odds}' (must be >= 1.0), defaulted to 1.0",
                    selection_index=idx
                ))

            confidence_sum += confidence
            selections.append(NormalizedSelection(
                event_id=sel.event_id,
                event_name=sel.event_name,
                market_type=market_type,
                raw_market=sel.market,
                pick=normalized_pick,
                line=line,
                odds=odds,
                confidence=confidence,
                kick_off=sel.kick_off,
                correlation_group=sel.event_id, # Intelligence: track legs per match
                metadata=metadata
            ))

        total = len(selections)
        unresolved = sum(1 for s in selections if s.market_type == MarketType.UNSUPPORTED)
        avg_confidence = confidence_sum / total if total > 0 else 0.0

        if ticket.total_odds:
            total_odds = ticket.total_odds
        elif selections:
            total_odds = 1.0
            for s in selections:
                total_odds *= s.odds
        else:
            total_odds = 1.0
        potential_returns = (ticket.stake * total_odds) if ticket.stake and total_odds else None

        return InternalTicket(
            source_booking_code=ticket.booking_code,
            selections=selections,
            total_odds=total_odds,
            stake=ticket.stake,
            potential_returns=potential_returns,
            unresolved=UnresolvedSummary(
                total=total,
                unresolved_count=unresolved,
                warnings=warnings
            ),
            meta=ResponseMeta(
                parser_version=self.PARSER_VERSION,
                confidence_avg=round(avg_confidence, 3)
            )
        ), warnings
