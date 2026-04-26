"""
Bet9jaConverter — M3
Converts InternalTicket to Bet9ja ConvertedTicket.
Handles market translation, pick normalization, AH quarter-ball split legs.
"""
from typing import Protocol
from ..models import (
    InternalTicket, ConvertedTicket, Bet9jaSelection,
    StructuredWarning, ResponseMeta, MarketType, NormalizedSelection
)


# ── Market Translation Registry ───────────────────────────────────────────

MARKET_REGISTRY: dict[MarketType, str] = {
    MarketType.MATCH_WINNER: "1X2",
    MarketType.OVER_UNDER: "Goals Over/Under",
    MarketType.BOTH_TEAMS_SCORE: "Both Teams to Score",
    MarketType.BTTS_HT: "Both Teams to Score - 1st Half",
    MarketType.ASIAN_HANDICAP: "Asian Handicap",
    MarketType.EUROPEAN_HANDICAP: "Handicap",
    MarketType.DOUBLE_CHANCE: "Double Chance",
    MarketType.CORRECT_SCORE: "Correct Score",
    MarketType.PLAYER_PROP: "Player to Score",
}

# ── Pick Normalization Table ───────────────────────────────────────────────

PICK_MAP: dict[str, str] = {
    "1": "Home",
    "2": "Away",
    "x": "Draw",
    "X": "Draw",
    "home": "Home",
    "away": "Away",
    "draw": "Draw",
    "yes": "Yes",
    "no": "No",
    "gg": "Yes",
    "ng": "No",
    "o": "Over",
    "u": "Under"
}

UNSUPPORTED_MARKETS = {MarketType.UNSUPPORTED}


class ConversionAdapter(Protocol):
    def convert(self, ticket: InternalTicket) -> ConvertedTicket:
        ...


class Bet9jaConverter:
    CONVERTER_VERSION = "1.0.0"

    def convert(self, ticket: InternalTicket) -> ConvertedTicket:
        converted: list[Bet9jaSelection] = []
        warnings: list[StructuredWarning] = list(ticket.unresolved.warnings)
        skipped = 0

        for idx, sel in enumerate(ticket.selections):
            if sel.market_type in UNSUPPORTED_MARKETS:
                skipped += 1
                warnings.append(StructuredWarning(
                    code="SKIPPED_UNSUPPORTED",
                    message=f"Market '{sel.raw_market}' not supported on Bet9ja — selection skipped",
                    selection_index=idx
                ))
                continue

            bet9ja_market = MARKET_REGISTRY.get(sel.market_type, sel.raw_market)
            bet9ja_pick = self._normalize_pick(sel)

            # AH quarter-ball: generate split leg notation
            if sel.market_type == MarketType.ASIAN_HANDICAP and sel.metadata.get("ah_legs"):
                legs = sel.metadata["ah_legs"]
                bet9ja_pick = f"{bet9ja_pick} ({legs[0]}/{legs[1]})"

            converted.append(Bet9jaSelection(
                event_id=sel.event_id,
                event_name=sel.event_name,
                market=bet9ja_market,
                pick=bet9ja_pick,
                odds=sel.odds,
                original_market=sel.raw_market
            ))

        total_odds = None
        if converted:
            prod = 1.0
            for s in converted:
                prod *= (s.odds or 1.0)
            total_odds = round(prod, 2)

        return ConvertedTicket(
            source_booking_code=ticket.source_booking_code,
            target_platform="bet9ja",
            selections=converted,
            converted_count=len(converted),
            skipped_count=skipped,
            total_odds=total_odds,
            warnings=warnings,
            meta=ResponseMeta(parser_version=self.CONVERTER_VERSION)
        )

    def _normalize_pick(self, sel: NormalizedSelection) -> str:
        pick = sel.pick.strip()
        bet9ja_pick = PICK_MAP.get(pick, PICK_MAP.get(pick.lower(), pick))
        
        # Merge the normalized 'Line' back in for the target platform reconstruction
        if sel.line is not None:
            if sel.market_type == MarketType.OVER_UNDER:
                action = "Over" if pick.lower() in ["o", "over"] else "Under"
                return f"{action} {sel.line}"
            elif sel.market_type == MarketType.PLAYER_PROP:
                line_str = f" {sel.line}" if sel.line else ""
                return f"{sel.pick}{line_str}"
            elif sel.market_type in (MarketType.ASIAN_HANDICAP, MarketType.EUROPEAN_HANDICAP):
                return f"{bet9ja_pick} ({sel.line})"
            else:
                return f"{bet9ja_pick} {sel.line}"
                
        return bet9ja_pick
