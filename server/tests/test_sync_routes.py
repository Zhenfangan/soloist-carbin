"""同步路由测试"""

from __future__ import annotations

from fastapi.testclient import TestClient

from server.main import app

client = TestClient(app)

VALID_TOKEN = "soloist-carbin-token"
VALID_HEADERS = {"Authorization": f"Bearer {VALID_TOKEN}"}


class TestSyncRoutes:
    def test_backup_requires_token(self) -> None:
        r = client.post("/api/v1/sync/backup", json={})
        assert r.status_code == 401

    def test_backup_with_valid_token(self) -> None:
        r = client.post("/api/v1/sync/backup", json={"data": {}}, headers=VALID_HEADERS)
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_restore_requires_token(self) -> None:
        r = client.get("/api/v1/sync/restore")
        assert r.status_code == 401

    def test_restore_with_valid_token(self) -> None:
        r = client.get("/api/v1/sync/restore", headers=VALID_HEADERS)
        assert r.status_code == 200
        assert "data" in r.json()

    def test_push_event_requires_token(self) -> None:
        r = client.post("/api/v1/sync/event", json={})
        assert r.status_code == 401

    def test_push_event_with_valid_token(self) -> None:
        r = client.post("/api/v1/sync/event", json={"type": "check_in"}, headers=VALID_HEADERS)
        assert r.status_code == 200


class TestReviewRoutes:
    def test_status_requires_token(self) -> None:
        r = client.get("/api/v1/review/status")
        assert r.status_code == 401

    def test_status_with_valid_token(self) -> None:
        r = client.get("/api/v1/review/status", headers=VALID_HEADERS)
        assert r.status_code == 200
        assert "date" in r.json()

    def test_history_requires_token(self) -> None:
        r = client.get("/api/v1/review/history")
        assert r.status_code == 401

    def test_history_with_valid_token(self) -> None:
        r = client.get("/api/v1/review/history", headers=VALID_HEADERS)
        assert r.status_code == 200
