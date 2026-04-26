import json
import httpx
from enum import Enum
from typing import Optional, AsyncGenerator
from pydantic import BaseModel, Field
from ..models import ConvertedTicket
from ..config import get_settings



class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class RiskFlag(BaseModel):
    code: str
    message: str
    severity: RiskLevel


class RiskReport(BaseModel):
    score: int = Field(..., ge=0, le=100)
    level: RiskLevel
    flags: list[RiskFlag] = Field(default_factory=list)
    narrative: str
    language: str = "en"
    source: str = Field(default="ai")
    model: Optional[str] = None


def _build_prompt(ticket: ConvertedTicket, language: str) -> str:
    selections_text = "\n".join([
        f"  - {json.dumps(s.event_name)} | {json.dumps(s.market)} | Pick: {json.dumps(s.pick)} | Odds: {s.odds}"
        for s in ticket.selections
    ])
    lang_instruction = (
        "Respond in Nigerian Pidgin English — natural, street-level tone."
        if language == "pid"
        else "Respond in clear, concise English."
    )
    # Using json.dumps to ensure user input is quoted and escaped within the prompt
    safe_booking_code = json.dumps(ticket.source_booking_code)
    
    return f"""You are Ticket Pulse — a sharp, no-nonsense sports betting risk analyst for Nigerian bettors.

Analyse this converted betting ticket and return ONLY a JSON object. No preamble, no markdown.

TICKET:
- Source booking code: {safe_booking_code}
- Platform: SportyBet → Bet9ja
- Selections ({ticket.converted_count} converted, {ticket.skipped_count} skipped):
{selections_text}
- Skipped markets: {ticket.skipped_count}
- Warnings: {len(ticket.warnings)}

INSTRUCTIONS:
{lang_instruction}

Return this exact JSON structure:
{{
  "score": <integer 0-100, where 100 = maximum risk>,
  "level": <"LOW" | "MEDIUM" | "HIGH">,
  "flags": [
    {{"code": "<FLAG_CODE>", "message": "<explanation>", "severity": <"LOW"|"MEDIUM"|"HIGH">}}
  ],
  "narrative": "<2-3 sentence assessment>"
}}

Flag codes: HIGH_ODDS, SKIPPED_SELECTIONS, ACCUMULATOR_RISK, EXOTIC_MARKETS, LOW_CONFIDENCE, CLEAN_TICKET"""


def _heuristic_score(ticket: ConvertedTicket, language: str) -> RiskReport:
    flags: list[RiskFlag] = []
    score = 20

    count = ticket.converted_count
    if count >= 6:
        score += 35
        flags.append(RiskFlag(code="ACCUMULATOR_RISK", message=f"{count} selections — high combo risk", severity=RiskLevel.HIGH))
    elif count >= 4:
        score += 20
        flags.append(RiskFlag(code="ACCUMULATOR_RISK", message=f"{count} selections — moderate combo risk", severity=RiskLevel.MEDIUM))

    if ticket.skipped_count > 0:
        score += ticket.skipped_count * 10
        flags.append(RiskFlag(
            code="SKIPPED_SELECTIONS",
            message=f"{ticket.skipped_count} market(s) could not convert to Bet9ja",
            severity=RiskLevel.MEDIUM
        ))

    if ticket.selections:
        avg_odds = sum(s.odds for s in ticket.selections) / len(ticket.selections)
        if avg_odds > 3.5:
            score += 20
            flags.append(RiskFlag(code="HIGH_ODDS", message=f"Average odds {avg_odds:.2f} — high variance", severity=RiskLevel.HIGH))
        elif avg_odds > 2.0:
            score += 10
            flags.append(RiskFlag(code="HIGH_ODDS", message=f"Average odds {avg_odds:.2f} — moderate variance", severity=RiskLevel.MEDIUM))

    exotic_markets = {"Correct Score", "Player to Score", "Asian Handicap"}
    exotic_count = sum(1 for s in ticket.selections if s.market in exotic_markets)
    if exotic_count > 0:
        score += exotic_count * 8
        flags.append(RiskFlag(code="EXOTIC_MARKETS", message=f"{exotic_count} exotic market(s) detected", severity=RiskLevel.MEDIUM))

    if not flags:
        flags.append(RiskFlag(code="CLEAN_TICKET", message="No major risk factors detected", severity=RiskLevel.LOW))

    score = min(score, 100)
    level = RiskLevel.HIGH if score >= 65 else RiskLevel.MEDIUM if score >= 35 else RiskLevel.LOW

    if language == "pid":
        narrative = (
            f"Omo, dis ticket get {count} selection{'s' if count != 1 else ''}. "
            f"Risk level na {level.value} — score {score}/100. "
            f"{'Shine your eye, the odds too high.' if level == RiskLevel.HIGH else 'E dey manageable but no sleep on am.' if level == RiskLevel.MEDIUM else 'Ticket clean, e get potential.'}"
        )
    else:
        narrative = (
            f"This ticket has {count} selection{'s' if count != 1 else ''} with a risk score of {score}/100 ({level.value}). "
            f"{'High variance — proceed with caution.' if level == RiskLevel.HIGH else 'Moderate risk — manageable but review carefully.' if level == RiskLevel.MEDIUM else 'Clean ticket with no major risk factors.'}"
        )

    return RiskReport(score=score, level=level, flags=flags, narrative=narrative, language=language, source="heuristic")


class TicketPulseService:
    MODEL = "claude-sonnet-4-20250514"
    TIMEOUT = 10.0

    async def analyse(self, ticket: ConvertedTicket, language: str = "en") -> RiskReport:
        settings = get_settings()
        if not settings.anthropic_api_key:
            return _heuristic_score(ticket, language)
        try:
            async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                response = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": settings.anthropic_api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json"
                    },
                    json={
                        "model": self.MODEL,
                        "max_tokens": 1024,
                        "messages": [{"role": "user", "content": _build_prompt(ticket, language)}]
                    }
                )
                response.raise_for_status()
                data = response.json()
                raw = data["content"][0]["text"].strip()
                if raw.startswith("```"):
                    raw = raw.split("```")[1]
                    if raw.startswith("json"):
                        raw = raw[4:]
                raw = raw.strip()
                parsed = json.loads(raw)
                return RiskReport(
                    score=parsed["score"],
                    level=RiskLevel(parsed["level"]),
                    flags=[RiskFlag(**f) for f in parsed.get("flags", [])],
                    narrative=parsed["narrative"],
                    language=language,
                    source="ai",
                    model=self.MODEL
                )
        except (httpx.TimeoutException, httpx.HTTPStatusError, json.JSONDecodeError, KeyError):
            report = _heuristic_score(ticket, language)
            report.source = "heuristic_fallback"
            return report

    async def analyse_stream(self, ticket: ConvertedTicket, language: str = "en") -> AsyncGenerator[str, None]:
        settings = get_settings()
        if not settings.anthropic_api_key:
            # Fallback to heuristic, yielded as a single JSON chunk then end
            report = _heuristic_score(ticket, language)
            yield f"data: {json.dumps({'text': json.dumps(report.model_dump())})}\n\n"
            yield "event: end\ndata: {}\n\n"
            return
            
        from .pbg_streaming_protocol import StreamingProtocol
        protocol = StreamingProtocol(api_key=settings.anthropic_api_key, model=self.MODEL, timeout=self.TIMEOUT)
        prompt = _build_prompt(ticket, language)
        async for chunk in protocol.stream_analysis(prompt):
            yield chunk


class MockTicketPulseService:
    async def analyse(self, ticket: ConvertedTicket, language: str = "en") -> RiskReport:
        return _heuristic_score(ticket, language)

    async def analyse_stream(self, ticket: ConvertedTicket, language: str = "en") -> AsyncGenerator[str, None]:
        report = _heuristic_score(ticket, language)
        # Yield the entirety of the mock response in a single SSE event
        yield f"data: {json.dumps({'text': json.dumps(report.model_dump())})}\n\n"
        yield "event: end\ndata: {}\n\n"

class MatchTelemetry(BaseModel):
    match_id: str
    home_score: int = 0
    away_score: int = 0
    minute: int = 0
    win_probability: float = 0.5 
    momentum_score: float = 0.0 # Positive for home dominance
    is_var_active: bool = False
    danger_strikes: int = 0

class MatchPulseIngester:
    """
    Phase 16: Sentient Settlement.
    Handles real-time match events to trigger cash-outs and hedges.
    """
    def __init__(self):
        self.active_telemetry: dict[str, MatchTelemetry] = {}

    def ingest_match_event(self, match_id: str, event_type: str, details: dict):
        tele = self.active_telemetry.get(match_id, MatchTelemetry(match_id=match_id))
        
        if event_type == "GOAL":
            is_home = details.get("team") == "home"
            if is_home: tele.home_score += 1
            else: tele.away_score += 1
            tele.win_probability = min(0.99, tele.win_probability + 0.3)
            tele.momentum_score += 5.0 if is_home else -5.0
            
        elif event_type == "DANGEROUS_ATTACK":
            is_home = details.get("team") == "home"
            tele.momentum_score += 0.5 if is_home else -0.5
            tele.danger_strikes += 1
            
        elif event_type == "VAR":
            tele.is_var_active = True

        tele.minute = details.get("minute", tele.minute)
        self.active_telemetry[match_id] = tele
        return tele

    def get_pulse_status(self) -> dict:
        return {
            "active_matches": len(self.active_telemetry),
            "telemetry": {k: v.dict() for k, v in self.active_telemetry.items()}
        }

# Global instance
match_pulse = MatchPulseIngester()
