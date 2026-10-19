import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_health_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "healthy"
        assert "gemini_model" in data

@pytest.mark.asyncio
async def test_profile_adaptability_three_profiles():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Profile 1: Rahul (CS, 8.2 CGPA, Master's)
        p1 = {
            "full_name": "Rahul Sharma",
            "current_degree": "B.Tech Computer Science",
            "cgpa": 8.2,
            "target_degree": "Master's",
            "target_field": "Computer Science",
            "target_countries": ["Canada", "Germany", "Singapore"]
        }
        res1 = await client.post("/api/research/start", json=p1)
        assert res1.status_code == 200
        run1 = res1.json()
        assert run1["student_profile"]["cgpa"] == 8.2

        # Profile 2: Profile B (Biotechnology, 6.8 CGPA, lower grades)
        p2 = {
            "full_name": "Student B",
            "current_degree": "B.Sc Biotechnology",
            "cgpa": 6.8,
            "target_degree": "Master's",
            "target_field": "Bioinformatics",
            "target_countries": ["Germany"]
        }
        res2 = await client.post("/api/research/start", json=p2)
        assert res2.status_code == 200
        run2 = res2.json()
        assert run2["student_profile"]["cgpa"] == 6.8

        # Profile 3: Profile C (Seeking PhD, missing language test)
        p3 = {
            "full_name": "Student C",
            "current_degree": "M.Sc Mathematics",
            "cgpa": 8.5,
            "target_degree": "PhD",
            "target_field": "Data Science",
            "target_countries": ["Singapore"]
        }
        res3 = await client.post("/api/research/start", json=p3)
        assert res3.status_code == 200
        run3 = res3.json()
        assert run3["student_profile"]["target_degree"] == "PhD"

@pytest.mark.asyncio
async def test_reset_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/api/opportunities/reset")
        assert res.status_code == 200
        assert res.json()["success"] is True
