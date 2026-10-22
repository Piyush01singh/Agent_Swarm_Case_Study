import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_models_endpoints():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Fetch available models (only fixed model gemini-3.1-flash-lite)
        res = await client.get("/api/models")
        assert res.status_code == 200
        data = res.json()
        assert "models" in data
        assert len(data["models"]) == 1
        assert data["models"][0]["id"] == "gemini-3.1-flash-lite"
        
        # Verify models display remaining RPM and status
        for m in data["models"]:
            assert "id" in m
            assert "name" in m
            assert "rpm_limit" in m
            assert "rpm_used" in m
            assert "rpm_left" in m
            assert "status" in m
            assert m["rpm_left"] >= 0
        
        # 2. Select fixed model
        select_res = await client.post("/api/models/select", json={"model": "gemini-3.1-flash-lite"})
        assert select_res.status_code == 200
        assert select_res.json()["success"] is True
        assert select_res.json()["current_model"] == "gemini-3.1-flash-lite"
