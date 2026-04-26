"""
ProfBetGeng — Full Test Suite
Covers: parser, converter, auth, storage, routes
"""
import pytest
from fastapi.testclient import TestClient
from ..main import create_app
from ..models import (
    SportybetTicket, SportybetSelection, MarketType, ConversionRecord
)
from ..services.sportybet_parser import SportybetAdapter
from ..services.converter import Bet9jaConverter
from ..services.auth import MockAPIKeyService
from ..services.storage import MockStorageService


# ── Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture
def parser():
    return SportybetAdapter()

@pytest.fixture
def converter():
    return Bet9jaConverter()

@pytest.fixture
def auth_service():
    return MockAPIKeyService()

@pytest.fixture
def storage_service():
    return MockStorageService()

@pytest.fixture
def client(auth_service, storage_service):
    app = create_app()
    from ..routes import get_auth_service, get_storage_service
    app.dependency_overrides[get_auth_service] = lambda: auth_service
    app.dependency_overrides[get_storage_service] = lambda: storage_service
    yield TestClient(app)
    app.dependency_overrides.clear()

def make_ticket(selections: list[dict], code: str = "TEST001") -> SportybetTicket:
    return SportybetTicket(
        booking_code=code,
        selections=[SportybetSelection(**s) for s in selections]
    )


# ── Parser Tests ───────────────────────────────────────────────────────────

class TestSpotybetParser:

    def test_parse_1x2(self, parser):
        ticket = make_ticket([{
            "event_id": "E1", "event_name": "Arsenal vs Chelsea",
            "market": "1X2", "pick": "1", "odds": 1.85
        }])
        internal, warnings = parser.parse(ticket)
        assert internal.selections[0].market_type == MarketType.MATCH_WINNER
        assert internal.selections[0].confidence == 1.0
        assert len(warnings) == 0

    def test_parse_over_under(self, parser):
        ticket = make_ticket([{
            "event_id": "E2", "event_name": "Man City vs Liverpool",
            "market": "Over/Under", "pick": "Over 2.5", "odds": 1.75
        }])
        internal, warnings = parser.parse(ticket)
        assert internal.selections[0].market_type == MarketType.OVER_UNDER

    def test_parse_btts(self, parser):
        ticket = make_ticket([{
            "event_id": "E3", "event_name": "Real Madrid vs Barcelona",
            "market": "Both Teams to Score", "pick": "Yes", "odds": 1.65
        }])
        internal, _ = parser.parse(ticket)
        assert internal.selections[0].market_type == MarketType.BOTH_TEAMS_SCORE

    def test_parse_asian_handicap_quarter_ball(self, parser):
        ticket = make_ticket([{
            "event_id": "E4", "event_name": "PSG vs Lyon",
            "market": "Asian Handicap", "pick": "-0.75", "odds": 1.90
        }])
        internal, _ = parser.parse(ticket)
        sel = internal.selections[0]
        assert sel.market_type == MarketType.ASIAN_HANDICAP
        assert "ah_legs" in sel.metadata

    def test_parse_unsupported_market(self, parser):
        ticket = make_ticket([{
            "event_id": "E5", "event_name": "Team A vs Team B",
            "market": "Some Exotic Market XYZ", "pick": "Yes", "odds": 2.0
        }])
        internal, warnings = parser.parse(ticket)
        assert internal.selections[0].market_type == MarketType.UNSUPPORTED
        assert internal.unresolved.unresolved_count == 1
        assert any(w.code == "UNRESOLVED_MARKET" for w in warnings)

    def test_parse_accumulator(self, parser):
        ticket = make_ticket([
            {"event_id": "E1", "event_name": "Game 1", "market": "1X2", "pick": "1", "odds": 1.5},
            {"event_id": "E2", "event_name": "Game 2", "market": "Over/Under", "pick": "Over 2.5", "odds": 1.8},
            {"event_id": "E3", "event_name": "Game 3", "market": "Both Teams to Score", "pick": "Yes", "odds": 1.6},
        ])
        internal, warnings = parser.parse(ticket)
        assert len(internal.selections) == 3
        assert internal.unresolved.total == 3
        assert internal.unresolved.unresolved_count == 0

    def test_parse_string_coerced_odds(self, parser):
        ticket = make_ticket([{
            "event_id": "E6", "event_name": "Game X",
            "market": "1X2", "pick": "2", "odds": "2.10"
        }])
        internal, warnings = parser.parse(ticket)
        assert internal.selections[0].odds == 2.10

    def test_parse_correct_score_metadata(self, parser):
        ticket = make_ticket([{
            "event_id": "E7", "event_name": "Game Y",
            "market": "Correct Score", "pick": "2-1", "odds": 7.5
        }])
        internal, _ = parser.parse(ticket)
        assert internal.selections[0].metadata.get("correct_score") is True

    def test_parse_player_prop_metadata(self, parser):
        ticket = make_ticket([{
            "event_id": "E8", "event_name": "Game Z",
            "market": "Player to Score", "pick": "Mbappe", "odds": 2.2
        }])
        internal, _ = parser.parse(ticket)
        sel = internal.selections[0]
        assert sel.market_type == MarketType.PLAYER_PROP
        assert sel.metadata.get("player_prop") is True

    def test_meta_confidence_avg(self, parser):
        ticket = make_ticket([
            {"event_id": "E1", "event_name": "G1", "market": "1X2", "pick": "1", "odds": 1.5},
            {"event_id": "E2", "event_name": "G2", "market": "Unknown Market", "pick": "X", "odds": 2.0},
        ])
        internal, _ = parser.parse(ticket)
        assert 0.0 <= internal.meta.confidence_avg <= 1.0


# ── Converter Tests ────────────────────────────────────────────────────────

class TestBet9jaConverter:

    def _parse_and_convert(self, parser, converter, selections):
        ticket = make_ticket(selections)
        internal, _ = parser.parse(ticket)
        return converter.convert(internal)

    def test_convert_1x2(self, parser, converter):
        result = self._parse_and_convert(parser, converter, [{
            "event_id": "E1", "event_name": "Arsenal vs Chelsea",
            "market": "1X2", "pick": "1", "odds": 1.85
        }])
        assert result.converted_count == 1
        assert result.selections[0].market == "1X2"
        assert result.selections[0].pick == "Home"

    def test_convert_pick_normalization(self, parser, converter):
        result = self._parse_and_convert(parser, converter, [{
            "event_id": "E1", "event_name": "Game",
            "market": "1X2", "pick": "2", "odds": 2.0
        }])
        assert result.selections[0].pick == "Away"

    def test_convert_skips_unsupported(self, parser, converter):
        result = self._parse_and_convert(parser, converter, [
            {"event_id": "E1", "event_name": "G1", "market": "1X2", "pick": "1", "odds": 1.5},
            {"event_id": "E2", "event_name": "G2", "market": "Unknown XYZ", "pick": "Yes", "odds": 2.0},
        ])
        assert result.converted_count == 1
        assert result.skipped_count == 1
        assert any(w.code == "SKIPPED_UNSUPPORTED" for w in result.warnings)

    def test_convert_ah_quarter_ball(self, parser, converter):
        result = self._parse_and_convert(parser, converter, [{
            "event_id": "E1", "event_name": "PSG vs Lyon",
            "market": "Asian Handicap", "pick": "-0.75", "odds": 1.90
        }])
        assert result.converted_count == 1
        assert "/" in result.selections[0].pick

    def test_convert_btts(self, parser, converter):
        result = self._parse_and_convert(parser, converter, [{
            "event_id": "E1", "event_name": "Game",
            "market": "Both Teams to Score", "pick": "Yes", "odds": 1.65
        }])
        assert result.selections[0].market == "Both Teams to Score"

    def test_convert_full_accumulator(self, parser, converter):
        result = self._parse_and_convert(parser, converter, [
            {"event_id": "E1", "event_name": "G1", "market": "1X2", "pick": "1", "odds": 1.5},
            {"event_id": "E2", "event_name": "G2", "market": "Over/Under", "pick": "Over 2.5", "odds": 1.8},
            {"event_id": "E3", "event_name": "G3", "market": "Both Teams to Score", "pick": "Yes", "odds": 1.6},
        ])
        assert result.converted_count == 3
        assert result.skipped_count == 0


# ── Auth Tests ─────────────────────────────────────────────────────────────

class TestMockAuthService:

    def test_generate_key(self, auth_service):
        result = auth_service.generate_key(label="test", owner="commander")
        assert result["key"] == MockAPIKeyService.VALID_KEY
        assert result["label"] == "test"

    def test_validate_valid_key(self, auth_service):
        assert auth_service.validate_key(MockAPIKeyService.VALID_KEY) is True

    def test_validate_invalid_key(self, auth_service):
        assert auth_service.validate_key("invalid") is False

    def test_validate_random_key(self, auth_service):
        assert auth_service.validate_key("pbg_some_random_key") is True


# ── Storage Tests ──────────────────────────────────────────────────────────

class TestMockStorageService:

    def _make_record(self, key="pbg_test"):
        return ConversionRecord(
            api_key=key,
            source_booking_code="ABC123",
            source_platform="sportybet",
            target_platform="bet9ja",
            selections_count=3,
            converted_count=3,
            skipped_count=0
        )

    def test_save_returns_id(self, storage_service):
        record = self._make_record()
        record_id = storage_service.save_conversion(record)
        assert record_id is not None

    def test_get_conversions(self, storage_service):
        record = self._make_record()
        storage_service.save_conversion(record)
        results = storage_service.get_conversions("pbg_test")
        assert len(results) == 1
        assert results[0].source_booking_code == "ABC123"

    def test_get_conversions_filters_by_key(self, storage_service):
        storage_service.save_conversion(self._make_record("key_a"))
        storage_service.save_conversion(self._make_record("key_b"))
        results = storage_service.get_conversions("key_a")
        assert len(results) == 1

    def test_save_multiple(self, storage_service):
        for i in range(5):
            r = self._make_record()
            r.source_booking_code = f"CODE{i}"
            storage_service.save_conversion(r)
        results = storage_service.get_conversions("pbg_test")
        assert len(results) == 5


# ── Route Tests ────────────────────────────────────────────────────────────

class TestRoutes:

    def test_health(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_convert_no_auth(self, client):
        r = client.post("/api/v1/convert", json={
            "booking_code": "TEST",
            "selections": [{
                "event_id": "E1", "event_name": "Game",
                "market": "1X2", "pick": "1", "odds": 1.85
            }]
        })
        # Auth enabled by default — expect 401
        assert r.status_code == 401

    def test_convert_with_valid_key(self, client):
        r = client.post(
            "/api/v1/convert",
            json={
                "booking_code": "TEST",
                "selections": [{
                    "event_id": "E1", "event_name": "Arsenal vs Chelsea",
                    "market": "1X2", "pick": "1", "odds": 1.85
                }]
            },
            headers={"X-API-Key": MockAPIKeyService.VALID_KEY}
        )
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert data["converted"]["converted_count"] == 1

    def test_convert_with_invalid_key(self, client):
        r = client.post(
            "/api/v1/convert",
            json={
                "booking_code": "TEST",
                "selections": [{
                    "event_id": "E1", "event_name": "Game",
                    "market": "1X2", "pick": "1", "odds": 1.85
                }]
            },
            headers={"X-API-Key": "invalid"}
        )
        assert r.status_code == 403

    def test_history_with_valid_key(self, client):
        r = client.get(
            "/api/v1/history",
            headers={"X-API-Key": MockAPIKeyService.VALID_KEY}
        )
        assert r.status_code == 200
        assert "records" in r.json()

    def test_create_api_key(self, client):
        r = client.post(
            "/api/v1/keys", 
            json={"label": "test-key", "owner": "commander"},
            headers={"X-Admin-Token": "pbg_admin_secret"}
        )
        assert r.status_code == 200
        assert "key" in r.json()

    def test_create_api_key_invalid_token(self, client):
        r = client.post(
            "/api/v1/keys", 
            json={"label": "test-key", "owner": "commander"},
            headers={"X-Admin-Token": "wrong_secret"}
        )
        assert r.status_code == 403
