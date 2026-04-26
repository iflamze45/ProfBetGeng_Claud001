import pytest
from fastapi.testclient import TestClient
from backend.main import create_app
from backend.models import ConvertedTicket, Bet9jaSelection, ResponseMeta
from backend.services.ticket_pulse import (
    MockTicketPulseService, _heuristic_score, RiskLevel
)
from backend.services.auth import MockAPIKeyService


def make_converted(selections: list[dict], skipped: int = 0) -> ConvertedTicket:
    sels = [Bet9jaSelection(**s) for s in selections]
    return ConvertedTicket(
        source_booking_code="TEST001",
        target_platform="bet9ja",
        selections=sels,
        converted_count=len(sels),
        skipped_count=skipped,
        meta=ResponseMeta()
    )


@pytest.fixture
def client(pulse):
    app = create_app()
    from backend.routes import get_pulse_service, get_auth_service, get_storage_service
    from backend.services.storage import MockStorageService
    app.dependency_overrides[get_pulse_service] = lambda: pulse
    app.dependency_overrides[get_auth_service] = lambda: MockAPIKeyService()
    app.dependency_overrides[get_storage_service] = lambda: MockStorageService()
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def pulse():
    return MockTicketPulseService()


class TestHeuristicScoring:

    def test_clean_single_selection(self):
        ticket = make_converted([{
            "event_id": "E1", "event_name": "Arsenal vs Chelsea",
            "market": "1X2", "pick": "Home", "odds": 1.85, "original_market": "1X2"
        }])
        report = _heuristic_score(ticket, "en")
        assert report.level == RiskLevel.LOW
        assert report.score < 35
        assert report.source == "heuristic"

    def test_high_accumulator_risk(self):
        sels = [
            {"event_id": f"E{i}", "event_name": f"Game {i}",
             "market": "1X2", "pick": "Home", "odds": 4.0, "original_market": "1X2"}
            for i in range(7)
        ]
        ticket = make_converted(sels)
        report = _heuristic_score(ticket, "en")
        assert report.level == RiskLevel.HIGH
        assert any(f.code == "ACCUMULATOR_RISK" for f in report.flags)

    def test_skipped_selections_flag(self):
        ticket = make_converted([{
            "event_id": "E1", "event_name": "Game",
            "market": "1X2", "pick": "Home", "odds": 1.5, "original_market": "1X2"
        }], skipped=2)
        report = _heuristic_score(ticket, "en")
        assert any(f.code == "SKIPPED_SELECTIONS" for f in report.flags)

    def test_high_odds_flag(self):
        ticket = make_converted([{
            "event_id": "E1", "event_name": "Game",
            "market": "Correct Score", "pick": "2-1", "odds": 8.5, "original_market": "Correct Score"
        }])
        report = _heuristic_score(ticket, "en")
        assert any(f.code == "HIGH_ODDS" for f in report.flags)

    def test_exotic_market_flag(self):
        ticket = make_converted([{
            "event_id": "E1", "event_name": "Game",
            "market": "Correct Score", "pick": "1-0", "odds": 6.0, "original_market": "Correct Score"
        }])
        report = _heuristic_score(ticket, "en")
        assert any(f.code == "EXOTIC_MARKETS" for f in report.flags)

    def test_score_capped_at_100(self):
        sels = [
            {"event_id": f"E{i}", "event_name": f"Game {i}",
             "market": "Correct Score", "pick": "3-2", "odds": 9.0, "original_market": "Correct Score"}
            for i in range(10)
        ]
        ticket = make_converted(sels, skipped=5)
        report = _heuristic_score(ticket, "en")
        assert report.score <= 100

    def test_pidgin_narrative(self):
        ticket = make_converted([{
            "event_id": "E1", "event_name": "Game",
            "market": "1X2", "pick": "Home", "odds": 1.5, "original_market": "1X2"
        }])
        report = _heuristic_score(ticket, "pid")
        assert report.language == "pid"
        assert any(word in report.narrative for word in ["Omo", "na", "dey", "dis"])

    def test_english_narrative(self):
        ticket = make_converted([{
            "event_id": "E1", "event_name": "Game",
            "market": "1X2", "pick": "Home", "odds": 1.5, "original_market": "1X2"
        }])
        report = _heuristic_score(ticket, "en")
        assert report.language == "en"
        assert "selection" in report.narrative.lower()


class TestMockTicketPulseService:

    @pytest.mark.asyncio
    async def test_returns_risk_report(self, pulse):
        ticket = make_converted([{
            "event_id": "E1", "event_name": "Game",
            "market": "1X2", "pick": "Home", "odds": 1.85, "original_market": "1X2"
        }])
        report = await pulse.analyse(ticket)
        assert report.score >= 0
        assert report.level in RiskLevel
        assert report.narrative

    @pytest.mark.asyncio
    async def test_pidgin_language_flag(self, pulse):
        ticket = make_converted([{
            "event_id": "E1", "event_name": "Game",
            "market": "1X2", "pick": "Home", "odds": 1.85, "original_market": "1X2"
        }])
        report = await pulse.analyse(ticket, language="pid")
        assert report.language == "pid"


class TestTicketPulseRoutes:

    def test_convert_with_analysis_en(self, client):
        r = client.post(
            "/api/v1/convert",
            json={
                "booking_code": "TEST",
                "selections": [{
                    "event_id": "E1", "event_name": "Arsenal vs Chelsea",
                    "market": "1X2", "pick": "1", "odds": 1.85
                }],
                "include_analysis": True,
                "language": "en"
            },
            headers={"X-API-Key": MockAPIKeyService.VALID_KEY}
        )
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert data["analysis"] is not None
        assert "pulse" in data["analysis"]
        assert "score" in data["analysis"]["pulse"]
        assert "narrative" in data["analysis"]["pulse"]

    def test_convert_with_analysis_pidgin(self, client):
        r = client.post(
            "/api/v1/convert",
            json={
                "booking_code": "TEST",
                "selections": [{
                    "event_id": "E1", "event_name": "Game",
                    "market": "1X2", "pick": "1", "odds": 1.85
                }],
                "include_analysis": True,
                "language": "pid"
            },
            headers={"X-API-Key": MockAPIKeyService.VALID_KEY}
        )
        assert r.status_code == 200
        assert r.json()["analysis"]["pulse"]["language"] == "pid"

    def test_convert_without_analysis(self, client):
        r = client.post(
            "/api/v1/convert",
            json={
                "booking_code": "TEST",
                "selections": [{
                    "event_id": "E1", "event_name": "Game",
                    "market": "1X2", "pick": "1", "odds": 1.85
                }],
                "include_analysis": False
            },
            headers={"X-API-Key": MockAPIKeyService.VALID_KEY}
        )
        assert r.status_code == 200
        assert r.json()["analysis"]["pulse"] is None


    def test_analyse_endpoint(self, client):
        r = client.post(
            "/api/v1/analyse",
            json={
                "converted": {
                    "source_booking_code": "TEST",
                    "target_platform": "bet9ja",
                    "selections": [{
                        "event_id": "E1", "event_name": "Game",
                        "market": "1X2", "pick": "Home", "odds": 1.85,
                        "original_market": "1X2"
                    }],
                    "converted_count": 1,
                    "skipped_count": 0,
                    "warnings": [],
                    "meta": {"parser_version": "1.0.0", "confidence_avg": 1.0}
                },
                "language": "en"
            },
            headers={"X-API-Key": MockAPIKeyService.VALID_KEY}
        )
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert data["analysis"]["score"] >= 0

    def test_analyse_no_auth(self, client):
        r = client.post("/api/v1/analyse", json={
            "converted": {
                "source_booking_code": "X", "target_platform": "bet9ja",
                "selections": [], "converted_count": 0, "skipped_count": 0,
                "warnings": [], "meta": {"parser_version": "1.0.0", "confidence_avg": 1.0}
            },
            "language": "en"
        })
        assert r.status_code == 401
