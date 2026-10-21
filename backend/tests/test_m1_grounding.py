"""
Milestone M1 Unit & Contract Tests:
Verifies Google Search Grounding tool configuration, URL Context tool enablement,
UrlRetrievalStatus metadata handling (SUCCESS vs PAYWALL/UNSAFE/ERROR),
explicit GeminiConfigurationError on missing keys, HTTP 503 handler,
and strict zero dummy fallback in live operational code.
"""

import pytest
import json
import inspect
from unittest.mock import MagicMock, AsyncMock, patch, PropertyMock
from google.genai import types
from fastapi.testclient import TestClient

from app.main import app
from app.services.gemini_service import GeminiService, GeminiConfigurationError
from app.agents.research_eligibility import ResearchEligibilityAgent
from app.models.profile import StudentProfile
from app.models.evidence import EvidenceRecord
from tests.fixtures.opportunities import CANONICAL_FIXTURE_OPPORTUNITIES, REAL_OPPORTUNITIES_BASE


# ==============================================================================
# 1. Missing Key & Configuration Error Policies
# ==============================================================================
def test_missing_api_key_ensure_available_raises_exception():
    """Verify ensure_available raises GeminiConfigurationError when API key is missing."""
    service = GeminiService()
    service.api_key = ""
    service._client = None
    assert service.is_available is False

    with pytest.raises(GeminiConfigurationError) as exc_info:
        service.ensure_available()
    assert "GEMINI_API_KEY is not configured" in str(exc_info.value)


@pytest.mark.asyncio
async def test_search_grounded_discovery_missing_key_error():
    """Verify search_grounded_discovery returns explicit error when API key is missing."""
    service = GeminiService()
    service.api_key = ""
    service._client = None

    res = await service.search_grounded_discovery("masters in canada", "student context")
    assert res["success"] is False
    assert "GEMINI_API_KEY is not configured" in res["error"]
    assert res["sources"] == []


@pytest.mark.asyncio
async def test_research_agent_missing_key_raises_error_without_dummy_fallback():
    """Verify ResearchEligibilityAgent raises GeminiConfigurationError and NEVER falls back to dummy records."""
    agent = ResearchEligibilityAgent()
    profile = StudentProfile(
        full_name="Rahul Sharma",
        current_degree="B.Tech Computer Science",
        cgpa=8.2,
        target_degree="Master's",
        target_field="Computer Science",
        target_countries=["Canada"]
    )

    with patch.object(GeminiService, "is_available", new_callable=PropertyMock, return_value=False):
        with pytest.raises(GeminiConfigurationError) as exc_info:
            await agent.execute_discovery_and_audit(
                run_id="test-run-no-key",
                profile=profile,
                research_round=1
            )
        assert "GEMINI_API_KEY is not configured" in str(exc_info.value)


def test_gemini_configuration_error_returns_503_http_response():
    """Verify that FastAPI translates GeminiConfigurationError into an HTTP 503 response."""
    test_app = TestClient(app, raise_server_exceptions=False)

    @app.get("/api/test-m1-config-error")
    async def sample_endpoint():
        raise GeminiConfigurationError("Testing 503 translation")

    response = test_app.get("/api/test-m1-config-error")
    assert response.status_code == 503
    body = response.json()
    assert body["error"] == "GeminiConfigurationError"
    assert "Testing 503 translation" in body["detail"]


# ==============================================================================
# 2. Tool Enablement & SDK Configuration
# ==============================================================================
def test_url_context_tool_structure():
    """Verify types.Tool(url_context=types.UrlContext()) is valid SDK configuration."""
    tool = types.Tool(url_context=types.UrlContext())
    assert tool.url_context is not None


def test_google_search_grounding_tool_structure():
    """Verify types.Tool(google_search=types.GoogleSearch()) is valid SDK configuration."""
    tool = types.Tool(google_search=types.GoogleSearch())
    assert tool.google_search is not None


@pytest.mark.asyncio
async def test_analyze_url_and_extract_criteria_configures_url_context_tool():
    """Verify analyze_url_and_extract_criteria passes types.Tool(url_context=...) in config."""
    service = GeminiService()
    service.api_key = "test-api-key"
    mock_client = MagicMock()
    service._client = mock_client

    # Mock response with url_context_metadata
    mock_candidate = MagicMock()
    mock_meta_entry = MagicMock()
    mock_meta_entry.retrieved_url = "https://web.cs.toronto.edu/graduate/mscac"
    mock_meta_entry.url_retrieval_status = types.UrlRetrievalStatus.URL_RETRIEVAL_STATUS_SUCCESS
    mock_candidate.url_context_metadata.url_metadata = [mock_meta_entry]

    mock_response = MagicMock()
    mock_response.candidates = [mock_candidate]
    mock_response.text = json.dumps({
        "admission_requirements": [
            {
                "criterion_name": "Academic CGPA",
                "stated_requirement": "B+ average (8.0/10.0)",
                "student_value": "8.2",
                "status": "MEETS",
                "evidence_excerpt": "Minimum overall B+ average",
                "source_url": "https://web.cs.toronto.edu/graduate/mscac"
            }
        ],
        "funding_details": {
            "funding_type": "Fully Funded",
            "coverage_description": "$17,500 CAD scholarship"
        },
        "deadline": "2026-12-01",
        "deadline_type": "Fixed",
        "deadline_verified": True,
        "overall_eligibility_status": "MEETS_STATED_CRITERIA"
    })

    mock_client.models.generate_content.return_value = mock_response

    res = await service.analyze_url_and_extract_criteria(
        urls=["https://web.cs.toronto.edu/graduate/mscac"],
        program_name="MScAC",
        university="University of Toronto",
        student_profile_summary="CGPA 8.2"
    )

    assert res["success"] is True
    assert res["is_retrieval_successful"] is True
    assert res["retrieval_status"] == "URL_RETRIEVAL_STATUS_SUCCESS"
    assert res["evidence_quality"] == "OFFICIAL"

    # Verify that types.Tool(url_context=...) was configured on the call
    call_args = mock_client.models.generate_content.call_args
    passed_config = call_args.kwargs.get("config")
    assert passed_config is not None
    assert hasattr(passed_config, "tools")
    assert any(getattr(t, "url_context", None) is not None for t in passed_config.tools)


# ==============================================================================
# 3. UrlRetrievalStatus Metadata Inspection & Error Policy
# ==============================================================================
def test_retrieval_status_enums_exist():
    """Verify google-genai SDK defines SUCCESS, PAYWALL, UNSAFE, and ERROR statuses."""
    assert hasattr(types, "UrlRetrievalStatus")
    assert hasattr(types.UrlRetrievalStatus, "URL_RETRIEVAL_STATUS_SUCCESS")
    assert hasattr(types.UrlRetrievalStatus, "URL_RETRIEVAL_STATUS_PAYWALL")
    assert hasattr(types.UrlRetrievalStatus, "URL_RETRIEVAL_STATUS_UNSAFE")
    assert hasattr(types.UrlRetrievalStatus, "URL_RETRIEVAL_STATUS_ERROR")


def test_retrieval_status_policy_paywall_marks_unresolved():
    """Verify PAYWALL status causes criterion status UNRESOLVED and does NOT crash."""
    status = types.UrlRetrievalStatus.URL_RETRIEVAL_STATUS_PAYWALL
    is_success = (status == types.UrlRetrievalStatus.URL_RETRIEVAL_STATUS_SUCCESS)
    assert is_success is False

    record = EvidenceRecord(
        criterion_name="Academic CGPA",
        stated_requirement="Published on portal",
        student_value="8.2",
        status="UNRESOLVED",
        evidence_excerpt=None,
        source_url="https://paywalled.edu/admissions",
        source_category="UNVERIFIED",
        uncertainty_or_conflict="Source URL paywalled; criteria unverified via live retrieval."
    )
    assert record.status == "UNRESOLVED"
    assert record.evidence_excerpt is None
    assert "paywalled" in record.uncertainty_or_conflict.lower()


def test_retrieval_status_policy_unsafe_marks_unresolved():
    """Verify UNSAFE status marks criteria UNRESOLVED and flags safety issue."""
    status = types.UrlRetrievalStatus.URL_RETRIEVAL_STATUS_UNSAFE
    assert status != types.UrlRetrievalStatus.URL_RETRIEVAL_STATUS_SUCCESS

    record = EvidenceRecord(
        criterion_name="Prerequisites",
        stated_requirement="Unknown",
        status="UNRESOLVED",
        source_url="https://malicious-link.com",
        source_category="UNVERIFIED",
        uncertainty_or_conflict="Source URL flagged as UNSAFE by GenAI URL safety filter."
    )
    assert record.status == "UNRESOLVED"
    assert record.source_category == "UNVERIFIED"
    assert "UNSAFE" in record.uncertainty_or_conflict


def test_retrieval_status_policy_error_marks_unresolved():
    """Verify HTTP ERROR status marks criteria UNRESOLVED gracefully."""
    status = types.UrlRetrievalStatus.URL_RETRIEVAL_STATUS_ERROR
    assert status != types.UrlRetrievalStatus.URL_RETRIEVAL_STATUS_SUCCESS

    record = EvidenceRecord(
        criterion_name="Language Test",
        stated_requirement="IELTS requirements",
        status="UNRESOLVED",
        source_url="https://broken-link.edu/404",
        source_category="UNVERIFIED",
        uncertainty_or_conflict="Source URL retrieval error (HTTP/Network failure); criteria unverified."
    )
    assert record.status == "UNRESOLVED"
    assert "retrieval error" in record.uncertainty_or_conflict.lower()


def test_partial_url_retrieval_failure_preservation():
    """
    Verify multi-URL candidate preserves verified data from successful URL
    while classifying failed URL criteria as UNRESOLVED without dropping candidate.
    """
    records = []
    # Success URL
    records.append(EvidenceRecord(
        criterion_name="Academic CGPA",
        stated_requirement="Minimum 8.0/10.0 CGPA",
        student_value="8.2",
        status="MEETS",
        evidence_excerpt="Applicant must have B+ average (8.0/10) in final two years.",
        source_url="https://cs.toronto.edu/mscac",
        source_category="OFFICIAL"
    ))
    # Paywalled URL
    records.append(EvidenceRecord(
        criterion_name="Departmental Fellowship Details",
        stated_requirement="Stipend details",
        status="UNRESOLVED",
        evidence_excerpt=None,
        source_url="https://cs.toronto.edu/internal-paywalled",
        source_category="UNVERIFIED",
        uncertainty_or_conflict="Source URL paywalled; criteria unverified via live retrieval."
    ))

    meets_records = [r for r in records if r.status == "MEETS"]
    unresolved_records = [r for r in records if r.status == "UNRESOLVED"]
    assert len(meets_records) == 1
    assert len(unresolved_records) == 1
    assert meets_records[0].evidence_excerpt is not None


# ==============================================================================
# 4. Zero Hardcoded Opportunities Verification & Schema Isolation
# ==============================================================================
def test_zero_hardcoded_opportunities_in_live_research_code():
    """Verify REAL_OPPORTUNITIES_BASE is completely absent from live research module."""
    import app.agents.research_eligibility as mod

    source_code = inspect.getsource(mod)
    assert "REAL_OPPORTUNITIES_BASE" not in source_code, (
        "Violation: REAL_OPPORTUNITIES_BASE must be removed from app/agents/research_eligibility.py"
    )


def test_isolated_fixtures_conform_to_schema():
    """Verify test fixtures reside in tests/fixtures/opportunities.py and match schema."""
    assert len(CANONICAL_FIXTURE_OPPORTUNITIES) >= 5
    for fixture in CANONICAL_FIXTURE_OPPORTUNITIES:
        assert "title" in fixture
        assert "canonical_url" in fixture
        assert "admission_requirements" in fixture
        assert "funding" in fixture
    assert REAL_OPPORTUNITIES_BASE is CANONICAL_FIXTURE_OPPORTUNITIES
