from fastapi.testclient import TestClient

from src.api.main import app


def test_health_and_cors_smoke():
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "healthy"
        assert body["scheduler"] is True
        assert body["ffmpeg"] is True
        assert body["ffprobe"] is True

        preflight = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert preflight.status_code == 200
        assert (
            preflight.headers["access-control-allow-origin"]
            == "http://localhost:5173"
        )
