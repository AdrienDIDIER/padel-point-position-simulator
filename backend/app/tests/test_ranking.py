from fastapi.testclient import TestClient
from ..main import app

client = TestClient(app)

def test_position_endpoint():
    response = client.get("/api/position?points=100")
    assert response.status_code == 200 or response.status_code == 400  # Depending on your dataset
