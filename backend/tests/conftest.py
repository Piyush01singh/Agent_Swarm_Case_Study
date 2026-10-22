"""
Root test configuration and offline safety fixtures for ScholarSwarm backend.
Ensures zero external network calls or personal API quota consumption across
the entire test suite.
"""

import pytest
from unittest.mock import AsyncMock
import app.services.gemini_service as gs_mod
from tests.fixtures.opportunities import get_mock_discovery_response, get_mock_url_analysis_response


@pytest.fixture(autouse=True)
def mock_gemini_suite_offline(monkeypatch):
    """
    Autouse fixture that strictly mocks all Gemini external calls:
    - search_grounded_discovery
    - analyze_url_and_extract_criteria
    - review_evidence_and_claims
    - review_opportunity_claims
    - generate_sop_draft
    - check_connection
    so the entire test suite runs offline without burning quota or hanging on network.
    """
    async def _mock_discovery(query: str, context_prompt: str = ""):
        countries = [c for c in ["Canada", "Germany", "Singapore"] if c.lower() in query.lower()]
        return get_mock_discovery_response(countries=countries or None)

    async def _mock_extract(urls, program_name="", university="", student_profile_summary=""):
        url = urls[0] if urls else ""
        return get_mock_url_analysis_response(url)

    async def _mock_review(opportunity_data, student_data):
        return {
            "success": True,
            "data": {
                "approved": True,
                "confidence_rating": "HIGH",
                "issues_detected": [],
                "reviewer_notes": "Official university sources and evidence verified by mock reviewer."
            }
        }

    async def _mock_sop(student_profile_dict, opportunity_dict, user_notes=None):
        return {
            "success": True,
            "data": {
                "title": f"Statement of Purpose - {opportunity_dict.get('program_name')}",
                "sop_content": f"Statement of Purpose for {student_profile_dict.get('full_name')} at {opportunity_dict.get('university')}.",
                "key_alignments": ["Academics", "Research"],
                "unconfirmed_claims": [],
                "word_count": 300,
                "model_used": "gemini-2.5-flash-mock"
            }
        }

    async def _mock_check_connection():
        return {
            "authenticated": True,
            "status": "AUTHENTICATED",
            "message": "Successfully authenticated with Google Gen AI API (mocked offline).",
            "model": "gemini-2.5-flash",
            "response_sample": "pong"
        }

    monkeypatch.setattr(gs_mod.gemini_service, "search_grounded_discovery", _mock_discovery)
    monkeypatch.setattr(gs_mod.gemini_service, "analyze_url_and_extract_criteria", _mock_extract)
    monkeypatch.setattr(gs_mod.gemini_service, "review_evidence_and_claims", _mock_review)
    monkeypatch.setattr(gs_mod.gemini_service, "review_opportunity_claims", _mock_review)
    monkeypatch.setattr(gs_mod.gemini_service, "generate_sop_draft", _mock_sop)
    monkeypatch.setattr(gs_mod.gemini_service, "check_connection", _mock_check_connection)
    monkeypatch.setattr(gs_mod.gemini_service, "validate_connection", _mock_check_connection)
