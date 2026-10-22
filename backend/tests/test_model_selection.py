import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_models_endpoints():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Fetch available models
        res = await client.get("/api/models")
        assert res.status_code == 200
        data = res.json()
        assert "models" in data
        assert len(data["models"]) >= 5
        
        # Verify models display remaining RPM and status
        for m in data["models"]:
            assert "id" in m
            assert "name" in m
            assert "rpm_limit" in m
            assert "rpm_used" in m
            assert "rpm_left" in m
            assert "status" in m
            assert m["rpm_left"] >= 0
        
        # 2. Select an available unexhausted model
        select_res = await client.post("/api/models/select", json={"model": "gemini-2.5-flash"})
        assert select_res.status_code == 200
        assert select_res.json()["success"] is True
        assert select_res.json()["current_model"] == "gemini-2.5-flash"
