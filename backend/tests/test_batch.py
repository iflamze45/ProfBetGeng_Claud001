"""
ProfBetGeng — Batch Conversion Tests
M4 Step 4 | Gates G-1 through G-7
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

from ..main import create_app
from ..batch import BatchConvertResponse, BatchTicketResult
from ..models import ConvertedTicket, Bet9jaSelection
from ..services.auth import require_api_key
from ..routes import get_storage_service, get_pulse_service


# ── Shared fixtures ───────────────────────────────────────────────────────────

SAMPLE_TICKET = {
    "booking_code": "SB001",
    "stake": 1000,
    "include_analysis": False,
    "language": "en",
    "selections": [
        {"event_id": "sr:match:1001", "event_name": "Arsenal vs Chelsea", "market": "1X2", "pick": "1", "odds": 2.10}
    ],
}


def fake_settings(batch_enabled=True, auth_enabled=False):
    s = MagicMock()
    s.batch_enabled = batch_enabled
    s.auth_enabled = auth_enabled
    return s


def fake_converted():
    return ConvertedTicket(
        source_booking_code="SB001",
        target_platform="bet9ja",
        selections=[Bet9jaSelection(
            event_id="sr:match:1001",
            event_name="Arsenal vs Chelsea",
            market="1X2",
            pick="1",
            odds=2.10,
            original_market="1X2",
        )],
        converted_count=1,
        skipped_count=0,
    )


@pytest.fixture
def client():
    app = create_app()
    app.dependency_overrides[require_api_key] = lambda: "dev_bypass"
    # Provide safe mock overrides for external services
    app.dependency_overrides[get_storage_service] = lambda: MagicMock()
    app.dependency_overrides[get_pulse_service] = lambda: AsyncMock() if hasattr(AsyncMock, '__call__') else MagicMock() # Will use a real async mock later if needed, but for now simple mocked routes are fine
    
    yield TestClient(app)
    app.dependency_overrides.clear()


# ── G-1: 10 tickets processed independently ───────────────────────────────────

def test_batch_accepts_ten_tickets(client):
    tickets = [SAMPLE_TICKET.copy() for _ in range(10)]
    with patch("backend.routes.get_settings", return_value=fake_settings()), \
         patch("backend.routes.parser") as mp, \
         patch("backend.routes.converter") as mc, \
         patch("backend.routes.get_storage_service", return_value=MagicMock()), \
         patch("backend.routes.get_pulse_service", return_value=MagicMock()):
        mp.parse.return_value = (MagicMock(), None)
        mc.convert.return_value = fake_converted()
        response = client.post("/api/v1/convert-batch", json={"tickets": tickets})
    assert response.status_code == 200
    data = response.json()
    assert data["summary"]["total"] == 10
    assert len(data["results"]) == 10


# ── G-2: One failure doesn't abort others ─────────────────────────────────────

def test_batch_one_failure_rest_succeed(client):
    tickets = [SAMPLE_TICKET.copy() for _ in range(3)]
    call_count = 0

    def selective_parse(ticket):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise ValueError("Simulated parse failure")
        return (MagicMock(), None)

    with patch("backend.routes.get_settings", return_value=fake_settings()), \
         patch("backend.routes.parser") as mp, \
         patch("backend.routes.converter") as mc, \
         patch("backend.routes.get_storage_service", return_value=MagicMock()), \
         patch("backend.routes.get_pulse_service", return_value=MagicMock()):
        mp.parse.side_effect = selective_parse
        mc.convert.return_value = fake_converted()
        response = client.post("/api/v1/convert-batch", json={"tickets": tickets})

    assert response.status_code == 200
    data = response.json()
    assert data["summary"]["succeeded"] == 2
    assert data["summary"]["failed"] == 1
    assert data["results"][0]["status"] == "success"
    assert data["results"][1]["status"] == "error"
    assert data["results"][2]["status"] == "success"


# ── G-3: Each success persists to Supabase ────────────────────────────────────

def test_batch_persists_successful_conversions(client):
    tickets = [SAMPLE_TICKET.copy() for _ in range(2)]
    mock_storage = MagicMock()

    # Override FastAPI dependency to inject our mock storage
    client.app.dependency_overrides[get_storage_service] = lambda: mock_storage

    with patch("backend.routes.get_settings", return_value=fake_settings()), \
         patch("backend.routes.parser") as mp, \
         patch("backend.routes.converter") as mc:
        mp.parse.return_value = (MagicMock(), None)
        mc.convert.return_value = fake_converted()
        response = client.post("/api/v1/convert-batch", json={"tickets": tickets})

    # Clean up the override
    del client.app.dependency_overrides[get_storage_service]

    assert response.status_code == 200
    assert mock_storage.save_conversion.call_count == 2


# ── G-4: Response shape ───────────────────────────────────────────────────────

def test_batch_response_shape(client):
    tickets = [SAMPLE_TICKET.copy()]
    with patch("backend.routes.get_settings", return_value=fake_settings()), \
         patch("backend.routes.parser") as mp, \
         patch("backend.routes.converter") as mc, \
         patch("backend.routes.get_storage_service", return_value=MagicMock()), \
         patch("backend.routes.get_pulse_service", return_value=MagicMock()):
        mp.parse.return_value = (MagicMock(), None)
        mc.convert.return_value = fake_converted()
        response = client.post("/api/v1/convert-batch", json={"tickets": tickets})

    data = response.json()
    assert "batch_id" in data
    assert "summary" in data
    assert "results" in data
    assert len(data["batch_id"]) == 36  # UUID4 format


# ── G-5: 11th ticket returns 422 ─────────────────────────────────────────────

def test_batch_rejects_eleven_tickets(client):
    tickets = [SAMPLE_TICKET.copy() for _ in range(11)]
    with patch("backend.routes.get_settings", return_value=fake_settings()):
        response = client.post("/api/v1/convert-batch", json={"tickets": tickets})
    assert response.status_code == 422


# ── G-6: batch_enabled=False returns 404 ─────────────────────────────────────

def test_batch_disabled_returns_404(client):
    tickets = [SAMPLE_TICKET.copy()]
    with patch("backend.routes.get_settings", return_value=fake_settings(batch_enabled=False)):
        response = client.post("/api/v1/convert-batch", json={"tickets": tickets})
    assert response.status_code == 404


# ── G-7: Empty list rejected ──────────────────────────────────────────────────

def test_batch_empty_list_rejected(client):
    with patch("backend.routes.get_settings", return_value=fake_settings()):
        response = client.post("/api/v1/convert-batch", json={"tickets": []})
    assert response.status_code == 422
