"""
SportybetParser — M1/M2
Parses raw SportyBet selections into normalized InternalTicket.
Returns (InternalTicket, list[StructuredWarning]) — never raises on soft failures.
"""
import re
from typing import Protocol
from ..models import (
    SportybetTicket, InternalTicket, NormalizedSelection,
    StructuredWarning, UnresolvedSummary, ResponseMeta, MarketType
)


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


def _resolve_ah_line(pick: str) -> tuple[str, list[str]]:
    """Splits quarter-ball AH into two standard lines."""
    match = AH_QUARTER_PATTERN.match(pick.strip())
    if not match:
        return pick, []
    value = float(pick)
    if value > 0:
        leg1 = f"+{value - 0.25:.2f}".rstrip("0").rstrip(".")
        leg2 = f"+{value + 0.25:.2f}".rstrip("0").rstrip(".")
    else:
        leg1 = f"{value - 0.25:.2f}".rstrip("0").rstrip(".")
        leg2 = f"{value + 0.25:.2f}".rstrip("0").rstrip(".")
    return pick, [leg1, leg2]


class SportsbookAdapter(Protocol):
    def parse(self, ticket: SportybetTicket) -> tuple[InternalTicket, list[StructuredWarning]]:
        ...


class SportybetAdapter:
    PARSER_VERSION = "1.0.0"

    def parse(self, ticket: SportybetTicket) -> tuple[InternalTicket, list[StructuredWarning]]:
        selections: list[NormalizedSelection] = []
        warnings: list[StructuredWarning] = []
        confidence_sum = 0.0

        for idx, sel in enumerate(ticket.selections):
            market_type, confidence = _resolve_market(sel.market)

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
            except (ValueError, TypeError):
                odds = 1.0
                warnings.append(StructuredWarning(
                    code="INVALID_ODDS",
                    message=f"Could not parse odds '{sel.odds}', defaulted to 1.0",
                    selection_index=idx
                ))

            confidence_sum += confidence
            selections.append(NormalizedSelection(
                event_id=sel.event_id,
                event_name=sel.event_name,
                market_type=market_type,
                raw_market=sel.market,
                pick=sel.pick,
                odds=odds,
                confidence=confidence,
                kick_off=sel.kick_off,
                metadata=metadata
            ))

        total = len(selections)
        unresolved = sum(1 for s in selections if s.market_type == MarketType.UNSUPPORTED)
        avg_confidence = confidence_sum / total if total > 0 else 0.0

        return InternalTicket(
            source_booking_code=ticket.booking_code,
            selections=selections,
            total_odds=ticket.total_odds,
            stake=ticket.stake,
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
