"""
Root test configuration and offline safety fixtures for ScholarSwarm backend.
Ensures zero external network calls or personal API quota consumption across
the entire test suite.
"""

import pytest
from unittest.mock import AsyncMock
import app.services.gemini_service as gs_mod
import app.services.tavily_service as ts_mod
import app.services.safe_retriever as sr_mod
from tests.fixtures.opportunities import (
    get_mock_discovery_response,
    get_mock_url_analysis_response,
    get_fixture_raw_opportunities,
    CANONICAL_FIXTURE_OPPORTUNITIES
)


@pytest.fixture(autouse=True)
def mock_gemini_suite_offline(monkeypatch):
    """
    Autouse fixture that strictly mocks all Gemini & Tavily external calls:
    - tavily_service.search
    - safe_page_retriever.retrieve_page
    - gemini_service.search_grounded_discovery
    - gemini_service.analyze_url_and_extract_criteria
    - gemini_service.review_evidence_and_claims
    - gemini_service.review_opportunity_claims
    - gemini_service.generate_sop_draft
    - gemini_service.check_connection
    so the entire test suite runs offline without burning quota or hanging on network.
    """
    async def _mock_tavily_search(query: str, search_depth="basic", max_results=5, include_raw_content=False, country=None):
        countries = [c for c in ["Canada", "Germany", "Singapore"] if c.lower() in query.lower()]
        fixtures = get_fixture_raw_opportunities(countries or ([country] if country else None))
        results = [
            {
                "title": f["title"],
                "url": f["canonical_url"],
                "content": f["funding"].get("coverage_description", ""),
                "score": 0.95
            }
            for f in fixtures
        ]
        return {
            "success": True,
            "status": "SUCCESS",
            "results": results,
            "query": query,
            "country": country,
            "cached": False
        }

    async def _mock_retrieve(url: str, max_chars: int = 15000):
        matched = None
        for f in CANONICAL_FIXTURE_OPPORTUNITIES:
            if f["canonical_url"] == url or url in f.get("official_source_urls", []):
                matched = f
                break
        desc = matched["funding"].get("coverage_description", "") if matched else "Official degree and scholarship guidelines"
        return {
            "success": True,
            "status": "URL_RETRIEVAL_STATUS_SUCCESS",
            "error": None,
            "text": f"Official university regulations and admissions criteria for {url}. {desc}",
            "url": url
        }

    async def _mock_discovery(query: str, context_prompt: str = ""):
        countries = [c for c in ["Canada", "Germany", "Singapore"] if c.lower() in query.lower()]
        return get_mock_discovery_response(countries=countries or None)

    async def _mock_extract(urls, program_name="", university="", student_profile_summary="", **kwargs):
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

    # Tavily service mocking
    monkeypatch.setattr(ts_mod.tavily_service, "api_key", "tvly-mock-offline-key")
    monkeypatch.setattr(ts_mod.tavily_service, "search", _mock_tavily_search)

    # Safe page retriever mocking
    monkeypatch.setattr(sr_mod.safe_page_retriever, "retrieve_page", _mock_retrieve)

    # Gemini service mocking
    monkeypatch.setattr(gs_mod.gemini_service, "search_grounded_discovery", _mock_discovery)
    monkeypatch.setattr(gs_mod.gemini_service, "analyze_url_and_extract_criteria", _mock_extract)
    monkeypatch.setattr(gs_mod.gemini_service, "review_evidence_and_claims", _mock_review)
    monkeypatch.setattr(gs_mod.gemini_service, "review_opportunity_claims", _mock_review)
    monkeypatch.setattr(gs_mod.gemini_service, "generate_sop_draft", _mock_sop)
    monkeypatch.setattr(gs_mod.gemini_service, "check_connection", _mock_check_connection)
    monkeypatch.setattr(gs_mod.gemini_service, "validate_connection", _mock_check_connection)
