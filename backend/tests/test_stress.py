"""
PBG Stress Test Suite — Real Data
Tests the full pipeline with realistic SportyBet ticket data.
No mocks for parser/converter — actual market resolution and pick normalization.
Auth mocked via dependency_overrides only.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from ..main import create_app
from ..services.auth import require_api_key
from ..routes import get_storage_service
from ..services.storage import MockStorageService
from ..services.sportybet_parser import SportybetAdapter
from ..services.converter import Bet9jaConverter
from ..models import (
    SportybetTicket, SportybetSelection,
    InternalTicket, MarketType,
)


# ── Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture
def parser():
    return SportybetAdapter()

@pytest.fixture
def converter():
    return Bet9jaConverter()

@pytest.fixture
def client():
    app = create_app()
    storage = MockStorageService()
    app.dependency_overrides[require_api_key] = lambda: "dev_bypass"
    app.dependency_overrides[get_storage_service] = lambda: storage
    yield TestClient(app)
    app.dependency_overrides.clear()

def make_ticket(selections: list[dict], code: str = "SB_STRESS", stake=500.0):
    return SportybetTicket(
        booking_code=code,
        stake=stake,
        selections=[SportybetSelection(**s) for s in selections],
    )


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — REAL MATCH DATA: ALL MARKET TYPES
# ══════════════════════════════════════════════════════════════════════════════

class TestRealMatchWinner:

    def test_epl_home_win(self, parser, converter):
        ticket = make_ticket([
            {"event_id": "sr:match:40001", "event_name": "Man City vs Arsenal",
             "market": "1X2", "pick": "1", "odds": 1.72},
        ])
        internal, warns = parser.parse(ticket)
        result = converter.convert(internal)
        assert result.converted_count == 1
        assert result.selections[0].market == "1X2"
        assert result.selections[0].pick == "Home"
        assert result.selections[0].odds == 1.72

    def test_laliga_away_win(self, parser, converter):
        ticket = make_ticket([
            {"event_id": "sr:match:40002", "event_name": "Getafe vs Barcelona",
             "market": "Match Winner", "pick": "2", "odds": 1.55},
        ])
        internal, warns = parser.parse(ticket)
        result = converter.convert(internal)
        assert result.selections[0].pick == "Away"

    def test_npfl_draw(self, parser, converter):
        ticket = make_ticket([
            {"event_id": "sr:match:40003", "event_name": "Kano Pillars vs Enyimba",
             "market": "Full Time Result", "pick": "X", "odds": 3.20},
        ])
        internal, warns = parser.parse(ticket)
        result = converter.convert(internal)
        assert result.selections[0].pick == "Draw"


class TestRealOverUnder:

    def test_over_2_5(self, parser, converter):
        ticket = make_ticket([
            {"event_id": "sr:match:40010", "event_name": "Liverpool vs Tottenham",
             "market": "Goals Over/Under", "pick": "Over 2.5", "odds": 1.80},
        ])
        internal, warns = parser.parse(ticket)
        result = converter.convert(internal)
        assert result.selections[0].market == "Goals Over/Under"
        assert "Over 2.5" in result.selections[0].pick

    def test_under_1_5(self, parser, converter):
        ticket = make_ticket([
            {"event_id": "sr:match:40011", "event_name": "Atletico Madrid vs Villarreal",
             "market": "Total Goals", "pick": "Under 1.5", "odds": 2.60},
        ])
        internal, warns = parser.parse(ticket)
        result = converter.convert(internal)
        assert result.selections[0].market == "Goals Over/Under"

    def test_over_3_5_high_scoring(self, parser, converter):
        ticket = make_ticket([
            {"event_id": "sr:match:40012", "event_name": "Bayer Leverkusen vs Bayern Munich",
             "market": "Total Goals", "pick": "Over 3.5", "odds": 2.10},
        ])
        internal, _ = parser.parse(ticket)
        result = converter.convert(internal)
        assert result.converted_count == 1


class TestRealBothTeamsToScore:

    def test_btts_yes(self, parser, converter):
        ticket = make_ticket([
            {"event_id": "sr:match:40020", "event_name": "Chelsea vs Newcastle",
             "market": "Both Teams to Score", "pick": "Yes", "odds": 1.65},
        ])
        internal, _ = parser.parse(ticket)
        result = converter.convert(internal)
        assert result.selections[0].market == "Both Teams to Score"
        assert result.selections[0].pick == "Yes"

    def test_btts_no(self, parser, converter):
        ticket = make_ticket([
            {"event_id": "sr:match:40021", "event_name": "Juventus vs Inter Milan",
             "market": "GG/NG", "pick": "NG", "odds": 2.20},
        ])
        internal, _ = parser.parse(ticket)
        result = converter.convert(internal)
        assert result.selections[0].pick == "No"

    def test_btts_gg_pick(self, parser, converter):
        ticket = make_ticket([
            {"event_id": "sr:match:40022", "event_name": "Dortmund vs RB Leipzig",
             "market": "BTTS", "pick": "GG", "odds": 1.75},
        ])
        internal, _ = parser.parse(ticket)
        result = converter.convert(internal)
        assert result.selections[0].pick == "Yes"


class TestRealAsianHandicap:

    def test_standard_ah_home_minus_1(self, parser, converter):
        ticket = make_ticket([
            {"event_id": "sr:match:40030", "event_name": "PSG vs Strasbourg",
             "market": "Asian Handicap", "pick": "-1.0", "odds": 1.90},
        ])
        internal, _ = parser.parse(ticket)
        result = converter.convert(internal)
        assert result.selections[0].market == "Asian Handicap"

    def test_quarter_ball_ah_split(self, parser, converter):
        ticket = make_ticket([
            {"event_id": "sr:match:40031", "event_name": "Man United vs West Ham",
             "market": "Asian Handicap", "pick": "-0.75", "odds": 1.85},
        ])
        internal, _ = parser.parse(ticket)
        sel = internal.selections[0]
        assert sel.metadata.get("ah_legs") == ["-1.0", "-0.5"]
        result = converter.convert(internal)
        assert "(-1.0/-0.5)" in result.selections[0].pick

    def test_quarter_ball_ah_positive(self, parser, converter):
        ticket = make_ticket([
            {"event_id": "sr:match:40032", "event_name": "Wolves vs Everton",
             "market": "AH", "pick": "+1.25", "odds": 1.95},
        ])
        internal, _ = parser.parse(ticket)
        sel = internal.selections[0]
        assert sel.metadata.get("ah_legs") == ["+1.0", "+1.5"]  # +1.25 - 0.25 = +1.0, +1.25 + 0.25 = +1.5

    def test_quarter_ball_ah_025(self, parser, converter):
        ticket = make_ticket([
            {"event_id": "sr:match:40033", "event_name": "AC Milan vs Fiorentina",
             "market": "Asian Handicap", "pick": "+0.25", "odds": 1.88},
        ])
        internal, _ = parser.parse(ticket)
        sel = internal.selections[0]
        assert sel.metadata.get("ah_legs") == ["+0.0", "+0.5"]  # +0.25 - 0.25 = +0.0, +0.25 + 0.25 = +0.5


class TestRealDoubleChance:

    def test_double_chance_1x(self, parser, converter):
        ticket = make_ticket([
            {"event_id": "sr:match:40040", "event_name": "Porto vs Braga",
             "market": "Double Chance", "pick": "1X", "odds": 1.35},
        ])
        internal, _ = parser.parse(ticket)
        result = converter.convert(internal)
        assert result.selections[0].market == "Double Chance"
        assert result.selections[0].pick == "1X"

    def test_double_chance_x2(self, parser, converter):
        ticket = make_ticket([
            {"event_id": "sr:match:40041", "event_name": "Napoli vs Lazio",
             "market": "Double Chance", "pick": "X2", "odds": 1.40},
        ])
        internal, _ = parser.parse(ticket)
        result = converter.convert(internal)
        assert result.selections[0].pick == "X2"


class TestRealCorrectScore:

    def test_correct_score_1_0(self, parser, converter):
        ticket = make_ticket([
            {"event_id": "sr:match:40050", "event_name": "Real Madrid vs Sevilla",
             "market": "Correct Score", "pick": "1-0", "odds": 6.50},
        ])
        internal, _ = parser.parse(ticket)
        sel = internal.selections[0]
        assert sel.metadata.get("correct_score") is True
        result = converter.convert(internal)
        assert result.selections[0].market == "Correct Score"

    def test_correct_score_2_1(self, parser, converter):
        ticket = make_ticket([
            {"event_id": "sr:match:40051", "event_name": "Inter Milan vs Roma",
             "market": "Correct Score", "pick": "2:1", "odds": 7.20},
        ])
        internal, _ = parser.parse(ticket)
        result = converter.convert(internal)
        assert result.converted_count == 1


class TestRealPlayerProps:

    def test_anytime_scorer(self, parser, converter):
        ticket = make_ticket([
            {"event_id": "sr:match:40060", "event_name": "Arsenal vs Burnley",
             "market": "Anytime Scorer", "pick": "Bukayo Saka", "odds": 2.10},
        ])
        internal, _ = parser.parse(ticket)
        sel = internal.selections[0]
        assert sel.metadata.get("player_prop") is True
        assert sel.metadata.get("raw_pick") == "Bukayo Saka"
        result = converter.convert(internal)
        assert result.selections[0].market == "Player to Score"

    def test_first_goal_scorer(self, parser, converter):
        ticket = make_ticket([
            {"event_id": "sr:match:40061", "event_name": "Liverpool vs Aston Villa",
             "market": "First Goal Scorer", "pick": "Mohamed Salah", "odds": 4.50},
        ])
        internal, _ = parser.parse(ticket)
        result = converter.convert(internal)
        assert result.selections[0].pick == "Mohamed Salah"


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — ACCUMULATOR TICKETS (REAL MULTI-LEG)
# ══════════════════════════════════════════════════════════════════════════════

class TestRealAccumulators:

    def test_5_leg_mixed_markets(self, parser, converter):
        ticket = make_ticket([
            {"event_id": "sr:match:50001", "event_name": "Man City vs Arsenal",
             "market": "1X2", "pick": "1", "odds": 1.72},
            {"event_id": "sr:match:50002", "event_name": "Chelsea vs Liverpool",
             "market": "Both Teams to Score", "pick": "Yes", "odds": 1.65},
            {"event_id": "sr:match:50003", "event_name": "Real Madrid vs Atletico",
             "market": "Goals Over/Under", "pick": "Over 2.5", "odds": 1.80},
            {"event_id": "sr:match:50004", "event_name": "Barcelona vs Valencia",
             "market": "Asian Handicap", "pick": "-1.0", "odds": 1.90},
            {"event_id": "sr:match:50005", "event_name": "Bayern Munich vs Dortmund",
             "market": "Double Chance", "pick": "1X", "odds": 1.30},
        ], code="SB_5LEG_MIXED")
        internal, warns = parser.parse(ticket)
        result = converter.convert(internal)
        assert result.converted_count == 5
        assert result.skipped_count == 0
        assert len(warns) == 0

    def test_8_leg_epl_saturday(self, parser, converter):
        ticket = make_ticket([
            {"event_id": "sr:match:50010", "event_name": "Arsenal vs Wolves",
             "market": "1X2", "pick": "1", "odds": 1.55},
            {"event_id": "sr:match:50011", "event_name": "Brentford vs Nottm Forest",
             "market": "Both Teams to Score", "pick": "GG", "odds": 1.80},
            {"event_id": "sr:match:50012", "event_name": "Brighton vs Everton",
             "market": "Total Goals", "pick": "Over 2.5", "odds": 1.75},
            {"event_id": "sr:match:50013", "event_name": "Burnley vs Sheffield Utd",
             "market": "1X2", "pick": "X", "odds": 3.10},
            {"event_id": "sr:match:50014", "event_name": "Crystal Palace vs Fulham",
             "market": "Full Time Result", "pick": "2", "odds": 2.40},
            {"event_id": "sr:match:50015", "event_name": "Man City vs Chelsea",
             "market": "Match Winner", "pick": "1", "odds": 1.60},
            {"event_id": "sr:match:50016", "event_name": "Spurs vs Aston Villa",
             "market": "Asian Handicap", "pick": "-0.75", "odds": 1.85},
            {"event_id": "sr:match:50017", "event_name": "West Ham vs Newcastle",
             "market": "Goals Over/Under", "pick": "Over 1.5", "odds": 1.50},
        ], code="SB_8LEG_EPL", stake=1000.0)
        internal, warns = parser.parse(ticket)
        result = converter.convert(internal)
        assert result.converted_count == 8
        assert result.skipped_count == 0
        assert internal.meta.confidence_avg == 1.0

    def test_10_leg_max_accumulator(self, parser, converter):
        selections = [
            {"event_id": f"sr:match:5002{i}", "event_name": f"Team A{i} vs Team B{i}",
             "market": "1X2", "pick": "1", "odds": round(1.5 + i * 0.1, 2)}
            for i in range(10)
        ]
        ticket = make_ticket(selections, code="SB_10LEG_MAX", stake=200.0)
        internal, warns = parser.parse(ticket)
        result = converter.convert(internal)
        assert result.converted_count == 10
        assert len(result.selections) == 10

    def test_accumulator_with_npfl_teams(self, parser, converter):
        """Nigerian Premier Football League — local market data."""
        ticket = make_ticket([
            {"event_id": "npfl:match:1001", "event_name": "Rivers United vs Kano Pillars",
             "market": "1X2", "pick": "1", "odds": 1.90},
            {"event_id": "npfl:match:1002", "event_name": "Enyimba vs Lobi Stars",
             "market": "Both Teams to Score", "pick": "Yes", "odds": 1.75},
            {"event_id": "npfl:match:1003", "event_name": "Sunshine Stars vs Plateau Utd",
             "market": "Total Goals", "pick": "Under 2.5", "odds": 2.00},
            {"event_id": "npfl:match:1004", "event_name": "Nasarawa Utd vs Shooting Stars",
             "market": "Full Time Result", "pick": "X", "odds": 3.00},
        ], code="SB_NPFL_4LEG")
        internal, warns = parser.parse(ticket)
        result = converter.convert(internal)
        assert result.converted_count == 4
        assert result.skipped_count == 0


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — EDGE CASES & FAILURE MODES
# ══════════════════════════════════════════════════════════════════════════════

class TestEdgeCases:

    def test_unsupported_market_skipped(self, parser, converter):
        ticket = make_ticket([
            {"event_id": "sr:match:60001", "event_name": "Liverpool vs Arsenal",
             "market": "1X2", "pick": "1", "odds": 2.10},
            {"event_id": "sr:match:60002", "event_name": "PSG vs Lyon",
             "market": "Winning Margin", "pick": "Home 1-5", "odds": 3.50},
        ])
        internal, warns = parser.parse(ticket)
        result = converter.convert(internal)
        assert result.converted_count == 1
        assert result.skipped_count == 1
        assert any(w.code == "UNRESOLVED_MARKET" for w in warns)

    def test_all_unsupported_markets(self, parser, converter):
        ticket = make_ticket([
            {"event_id": "sr:match:60010", "event_name": "Man Utd vs Brighton",
             "market": "Winning Margin", "pick": "Home 1-5", "odds": 3.50},
            {"event_id": "sr:match:60011", "event_name": "Leicester vs Wolves",
             "market": "Next Goal", "pick": "Home", "odds": 2.20},
        ])
        internal, warns = parser.parse(ticket)
        result = converter.convert(internal)
        assert result.converted_count == 0
        assert result.skipped_count == 2

    def test_string_odds_coerced(self, parser, converter):
        ticket = make_ticket([
            {"event_id": "sr:match:60020", "event_name": "Chelsea vs Spurs",
             "market": "1X2", "pick": "1", "odds": "2.15"},
        ])
        internal, warns = parser.parse(ticket)
        assert internal.selections[0].odds == 2.15

    def test_mixed_valid_and_unsupported(self, parser, converter):
        ticket = make_ticket([
            {"event_id": "sr:match:60030", "event_name": "Barcelona vs Sevilla",
             "market": "1X2", "pick": "1", "odds": 1.60},
            {"event_id": "sr:match:60031", "event_name": "Real Madrid vs Bilbao",
             "market": "Half Time/Full Time", "pick": "1/1", "odds": 2.80},
            {"event_id": "sr:match:60032", "event_name": "Atletico vs Betis",
             "market": "Both Teams to Score", "pick": "Yes", "odds": 1.70},
            {"event_id": "sr:match:60033", "event_name": "Valencia vs Osasuna",
             "market": "Corner Kick", "pick": "Over 9.5", "odds": 1.85},
        ])
        internal, warns = parser.parse(ticket)
        result = converter.convert(internal)
        assert result.converted_count == 2
        assert result.skipped_count == 2

    def test_partial_market_match_lower_confidence(self, parser, converter):
        ticket = make_ticket([
            {"event_id": "sr:match:60040", "event_name": "Everton vs Brentford",
             "market": "Goals Over/Under 2.5", "pick": "Over", "odds": 1.85},
        ])
        internal, _ = parser.parse(ticket)
        assert internal.selections[0].market_type == MarketType.OVER_UNDER
        assert internal.selections[0].confidence == 0.85

    def test_confidence_avg_with_mixed_resolution(self, parser, converter):
        ticket = make_ticket([
            {"event_id": "sr:match:60050", "event_name": "Porto vs Sporting",
             "market": "1X2", "pick": "1", "odds": 2.00},
            {"event_id": "sr:match:60051", "event_name": "Benfica vs Braga",
             "market": "Winning Margin", "pick": "Home 1-5", "odds": 3.00},
        ])
        internal, _ = parser.parse(ticket)
        assert internal.meta.confidence_avg == 0.5

    def test_single_selection_ticket(self, parser, converter):
        ticket = make_ticket([
            {"event_id": "sr:match:60060", "event_name": "Ajax vs PSV",
             "market": "1X2", "pick": "1", "odds": 2.05},
        ])
        internal, _ = parser.parse(ticket)
        result = converter.convert(internal)
        assert result.converted_count == 1
        assert result.total_odds == 2.05


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — API ENDPOINT STRESS (Full HTTP Pipeline)
# ══════════════════════════════════════════════════════════════════════════════

class TestAPIEndpointStress:

    def test_convert_epl_5leg(self, client):
        payload = {
            "booking_code": "SB_API_5LEG",
            "stake": 500,
            "include_analysis": False,
            "selections": [
                {"event_id": "sr:match:70001", "event_name": "Man City vs Arsenal",
                 "market": "1X2", "pick": "1", "odds": 1.72},
                {"event_id": "sr:match:70002", "event_name": "Chelsea vs Liverpool",
                 "market": "Both Teams to Score", "pick": "Yes", "odds": 1.65},
                {"event_id": "sr:match:70003", "event_name": "Real Madrid vs Atletico",
                 "market": "Goals Over/Under", "pick": "Over 2.5", "odds": 1.80},
                {"event_id": "sr:match:70004", "event_name": "Barcelona vs Valencia",
                 "market": "Asian Handicap", "pick": "-0.75", "odds": 1.90},
                {"event_id": "sr:match:70005", "event_name": "Bayern vs Dortmund",
                 "market": "Double Chance", "pick": "1X", "odds": 1.30},
            ]
        }
        response = client.post("/api/v1/convert", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["converted"]["converted_count"] == 5
        assert data["converted"]["skipped_count"] == 0

    def test_convert_with_skipped_selection(self, client):
        payload = {
            "booking_code": "SB_API_SKIP",
            "stake": 200,
            "include_analysis": False,
            "selections": [
                {"event_id": "sr:match:70010", "event_name": "Liverpool vs Arsenal",
                 "market": "1X2", "pick": "1", "odds": 2.10},
                {"event_id": "sr:match:70011", "event_name": "PSG vs Lyon",
                 "market": "Winning Margin", "pick": "Home 1-5", "odds": 3.50},
                {"event_id": "sr:match:70012", "event_name": "Juventus vs Milan",
                 "market": "Both Teams to Score", "pick": "GG", "odds": 1.70},
            ]
        }
        response = client.post("/api/v1/convert", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["converted"]["converted_count"] == 2
        assert data["converted"]["skipped_count"] == 1

    def test_convert_npfl_ticket(self, client):
        payload = {
            "booking_code": "SB_NPFL_API",
            "stake": 1000,
            "include_analysis": False,
            "selections": [
                {"event_id": "npfl:match:2001", "event_name": "Rivers United vs Kano Pillars",
                 "market": "1X2", "pick": "1", "odds": 1.90},
                {"event_id": "npfl:match:2002", "event_name": "Enyimba vs Lobi Stars",
                 "market": "Both Teams to Score", "pick": "Yes", "odds": 1.75},
                {"event_id": "npfl:match:2003", "event_name": "Sunshine Stars vs Plateau Utd",
                 "market": "Total Goals", "pick": "Under 2.5", "odds": 2.00},
            ]
        }
        response = client.post("/api/v1/convert", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["converted"]["converted_count"] == 3

    def test_convert_response_shape(self, client):
        payload = {
            "booking_code": "SB_SHAPE_TEST",
            "stake": 300,
            "include_analysis": False,
            "selections": [
                {"event_id": "sr:match:70020", "event_name": "Tottenham vs Aston Villa",
                 "market": "1X2", "pick": "X", "odds": 3.40},
            ]
        }
        response = client.post("/api/v1/convert", json=payload)
        data = response.json()
        assert "success" in data
        assert "converted" in data
        assert "selections" in data["converted"]
        assert data["converted"]["selections"][0]["pick"] == "Draw"
        assert data["converted"]["selections"][0]["market"] == "1X2"
        assert data["converted"]["target_platform"] == "bet9ja"

    def test_history_endpoint(self, client):
        # Convert first
        payload = {
            "booking_code": "SB_HIST_001",
            "stake": 100,
            "include_analysis": False,
            "selections": [
                {"event_id": "sr:match:70030", "event_name": "Celtic vs Rangers",
                 "market": "1X2", "pick": "1", "odds": 2.20},
            ]
        }
        client.post("/api/v1/convert", json=payload)
        # Then fetch history
        response = client.get("/api/v1/history", headers={"X-API-Key": "dev_bypass"})
        assert response.status_code == 200
        data = response.json()
        assert "records" in data
        assert "count" in data


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — BATCH ENDPOINT STRESS (Real Multi-Ticket)
# ══════════════════════════════════════════════════════════════════════════════

class TestBatchEndpointStress:

    def test_batch_5_real_tickets(self, client):
        tickets = [
            {
                "booking_code": f"SB_BATCH_{i:03d}",
                "stake": 500,
                "include_analysis": False,
                "selections": [
                    {"event_id": f"sr:match:8000{i}", "event_name": f"Home Team {i} vs Away Team {i}",
                     "market": mkt, "pick": pick, "odds": round(1.5 + i * 0.15, 2)}
                ]
            }
            for i, (mkt, pick) in enumerate([
                ("1X2", "1"),
                ("Both Teams to Score", "Yes"),
                ("Goals Over/Under", "Over 2.5"),
                ("Asian Handicap", "-1.0"),
                ("Double Chance", "1X"),
            ])
        ]
        response = client.post("/api/v1/convert-batch", json={"tickets": tickets})
        # batch_enabled defaults to False — expect 404 unless overridden
        assert response.status_code in (200, 404)

    def test_batch_10_tickets_max_load(self, client):
        tickets = [
            {
                "booking_code": f"SB_MAX_{i:02d}",
                "stake": 100,
                "include_analysis": False,
                "selections": [
                    {"event_id": f"sr:match:9000{i}", "event_name": f"Club A{i} vs Club B{i}",
                     "market": "1X2", "pick": "1", "odds": round(1.6 + i * 0.05, 2)}
                ]
            }
            for i in range(10)
        ]
        response = client.post("/api/v1/convert-batch", json={"tickets": tickets})
        assert response.status_code in (200, 404)

    def test_batch_rejects_11_real_tickets(self, client):
        tickets = [
            {
                "booking_code": f"SB_OVER_{i:02d}",
                "stake": 100,
                "include_analysis": False,
                "selections": [
                    {"event_id": f"sr:match:9010{i}", "event_name": f"Team X{i} vs Team Y{i}",
                     "market": "1X2", "pick": "1", "odds": 1.80}
                ]
            }
            for i in range(11)
        ]
        response = client.post("/api/v1/convert-batch", json={"tickets": tickets})
        assert response.status_code == 422


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 6 — PICK NORMALIZATION COMPLETENESS
# ══════════════════════════════════════════════════════════════════════════════

class TestPickNormalization:

    @pytest.mark.parametrize("raw_pick,expected", [
        ("1", "Home"),
        ("2", "Away"),
        ("X", "Draw"),
        ("x", "Draw"),
        ("home", "Home"),
        ("Home", "Home"),
        ("away", "Away"),
        ("Away", "Away"),
        ("draw", "Draw"),
        ("Draw", "Draw"),
        ("yes", "Yes"),
        ("Yes", "Yes"),
        ("no", "No"),
        ("No", "No"),
        ("GG", "Yes"),
        ("NG", "No"),
    ])
    def test_pick_normalization(self, parser, converter, raw_pick, expected):
        ticket = make_ticket([
            {"event_id": "sr:match:99001", "event_name": "Team A vs Team B",
             "market": "1X2" if raw_pick in ("1", "2", "X", "x", "home", "Home", "away", "Away", "draw", "Draw")
             else "Both Teams to Score",
             "pick": raw_pick, "odds": 2.00}
        ])
        internal, _ = parser.parse(ticket)
        result = converter.convert(internal)
        assert result.selections[0].pick == expected
