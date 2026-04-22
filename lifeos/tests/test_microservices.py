"""Tests for all 5 microservices"""

import pytest
from fastapi.testclient import TestClient
from lifeos.env_services.echo_app import app as echo_app
from lifeos.env_services.coding_app import app as coding_app
from lifeos.env_services.chess_app import app as chess_app
from lifeos.env_services.carla_app import app as carla_app
from lifeos.env_services.julia_app import app as julia_app


# === ECHO SERVICE TESTS ===
class TestEchoService:
    def test_health(self):
        client = TestClient(echo_app)
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
        assert resp.json()["env"] == "echo_env"

    def test_echo_post(self):
        client = TestClient(echo_app)
        resp = client.post("/echo", json={"message": "hello", "payload": {"x": 1}})
        assert resp.status_code == 200
        data = resp.json()
        assert data["received"]["message"] == "hello"
        assert data["env"] == "echo_env"


# === CODING SERVICE TESTS ===
class TestCodingService:
    def test_health(self):
        client = TestClient(coding_app)
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
        assert resp.json()["env"] == "coding_env"

    def test_python_exec_simple(self):
        client = TestClient(coding_app)
        resp = client.post("/exec/python", json={"code": "print(2+3)", "timeout_seconds": 5})
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["language"] == "python"
        assert "5" in data["stdout"]
        assert data["exit_code"] == 0

    def test_python_exec_error(self):
        client = TestClient(coding_app)
        resp = client.post("/exec/python", json={"code": "1/0", "timeout_seconds": 5})
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is False
        assert data["language"] == "python"
        assert "error" in data["stderr"].lower() or data["exit_code"] != 0

    def test_python_exec_timeout(self):
        client = TestClient(coding_app)
        resp = client.post("/exec/python", json={"code": "import time; time.sleep(10)", "timeout_seconds": 1})
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is False
        assert "Timeout" in data["stderr"] or data["exit_code"] == -1


# === CHESS SERVICE TESTS ===
class TestChessService:
    def test_health(self):
        client = TestClient(chess_app)
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
        assert resp.json()["env"] == "chess_env"

    def test_valid_move_e2e4(self):
        client = TestClient(chess_app)
        resp = client.post("/validate-move", json={"move": "e2e4", "turn": "white"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is True
        assert data["move"] == "e2e4"
        assert data["env"] == "chess_env"

    def test_valid_move_with_promotion(self):
        client = TestClient(chess_app)
        resp = client.post("/validate-move", json={"move": "d7d8q", "turn": "black"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is True

    def test_invalid_move_format(self):
        client = TestClient(chess_app)
        resp = client.post("/validate-move", json={"move": "invalid", "turn": "white"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is False

    def test_invalid_move_out_of_board(self):
        client = TestClient(chess_app)
        resp = client.post("/validate-move", json={"move": "i9j9", "turn": "white"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is False


# === CARLA SERVICE TESTS ===
class TestCarlaService:
    def test_health(self):
        client = TestClient(carla_app)
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
        assert resp.json()["env"] == "carla_env"

    def test_step_acceleration(self):
        client = TestClient(carla_app)
        resp = client.post("/step", json={"throttle": 1.0, "steer": 0.0, "brake": 0.0})
        assert resp.status_code == 200
        data = resp.json()
        state = data["state"]
        assert state["speed_kmh"] > 0
        assert state["lane_offset"] == 0.0
        assert data["env"] == "carla_env"

    def test_step_steering(self):
        client = TestClient(carla_app)
        resp = client.post("/step", json={"throttle": 0.5, "steer": 1.0, "brake": 0.0})
        assert resp.status_code == 200
        data = resp.json()
        state = data["state"]
        assert state["lane_offset"] > 0.0  # Steering right

    def test_step_braking(self):
        client = TestClient(carla_app)
        resp = client.post("/step", json={"throttle": 0.0, "steer": 0.0, "brake": 1.0})
        assert resp.status_code == 200
        data = resp.json()
        state = data["state"]
        assert state["speed_kmh"] == 0.0


# === JULIA SERVICE TESTS ===
class TestJuliaService:
    def test_health(self):
        client = TestClient(julia_app)
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
        assert resp.json()["env"] == "julia_env"

    def test_julia_exec_missing_binary(self):
        """Julia may not be installed - test graceful handling"""
        client = TestClient(julia_app)
        resp = client.post("/exec/julia", json={"code": "println(2+3)", "timeout_seconds": 5})
        assert resp.status_code == 200
        data = resp.json()
        assert data["language"] == "julia"
        # If Julia is not installed, we expect ok=False with appropriate error
        if not data["ok"]:
            assert "julia" in data["stderr"].lower() or "not found" in data["stderr"].lower()
