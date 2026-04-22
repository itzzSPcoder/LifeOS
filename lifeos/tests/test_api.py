from fastapi.testclient import TestClient

from lifeos.api.main import app


def test_scenarios_endpoint() -> None:
    client = TestClient(app)
    response = client.get("/scenarios")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
