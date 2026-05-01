import pytest
from fastapi.testclient import TestClient
from backend.main import create_app

@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)

def test_market_signals_route(client):
    """Verifies that the market signals route exists and handles auth."""
    # Test unauthorized
    response = client.get("/api/v1/market/signals")
    assert response.status_code == 401 
    
    # Test valid key (assuming 'pbg-web-user' is a valid mock key)
    response = client.get("/api/v1/market/signals", headers={"X-API-Key": "pbg-web-user"})
    assert response.status_code == 200
    assert "signals" in response.json()
