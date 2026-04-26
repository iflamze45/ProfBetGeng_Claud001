import pytest
from fastapi.testclient import TestClient
from backend.main import create_app
from backend.services.auth import require_api_key, MockAPIKeyService
from backend.services.storage import MockStorageService
from backend.models import ConversionRecord
from backend.routes import get_storage_service

@pytest.fixture
def storage():
    return MockStorageService()

@pytest.fixture
def client(storage):
    app = create_app()
    app.dependency_overrides[require_api_key] = lambda: "dev_bypass"
    app.dependency_overrides[get_storage_service] = lambda: storage
    yield TestClient(app)
    app.dependency_overrides.clear()

def test_convert_persists_financial_metrics(client, storage):
    """
    Ensures that conversion results (including stake, odds, potential returns) 
    are properly persisted to the storage layer during the /convert request.
    """
    payload = {
        "booking_code": "STAKE_TEST",
        "stake": 5000.0,
        "include_analysis": True,
        "selections": [
            {"event_id": "1", "event_name": "A vs B", "market": "1X2", "pick": "1", "odds": 2.5}
        ]
    }
    
    response = client.post("/api/v1/convert", json=payload)
    assert response.status_code == 200
    
    # Verify persistence in mock storage
    records = storage.get_conversions("dev_bypass")
    assert len(records) == 1
    record = records[0]
    
    assert record.source_booking_code == "STAKE_TEST"
    assert record.stake == 5000.0
    assert record.total_odds == 2.5
    assert record.potential_returns == 12500.0
    assert record.risk_score is not None
    assert record.risk_level is not None

def test_history_returns_financial_metrics(client, storage):
    """
    Ensures that the history endpoint returns the persisted financial metrics.
    """
    storage.save_conversion(ConversionRecord(
        api_key="dev_bypass",
        source_booking_code="HIST_001",
        source_platform="sportybet",
        target_platform="bet9ja",
        selections_count=1,
        converted_count=1,
        skipped_count=0,
        stake=2500.0,
        total_odds=3.0,
        potential_returns=7500.0,
        risk_score=45,
        risk_level="MEDIUM"
    ))
    
    response = client.get("/api/v1/history")
    assert response.status_code == 200
    data = response.json()
    
    assert data["count"] == 1
    record = data["records"][0]
    assert record["stake"] == 2500.0
    assert record["potential_returns"] == 7500.0
    assert record["total_odds"] == 3.0
    assert record["risk_score"] == 45
    assert record["risk_level"] == "MEDIUM"
