"""
Challenger 1 Empirical Resilience and Offline Isolation Stress Suite.
Tests boundary error resilience across GeminiService, fail-closed reviewer behavior,
ungrounded grading scale assertions, and zero-synthetic-fallback guarantees.
"""

import pytest
import asyncio
from unittest.mock import MagicMock
from app.services.gemini_service import GeminiService
from app.agents.research_eligibility import (
    ResearchEligibilityAgent,
    evaluate_single_criterion,
    extract_numeric_cgpa_cutoff
)
from app.models.profile import StudentProfile
from app.models.opportunity import Opportunity, FundingDetails, EligibilityCriterion
from app.db.repository import repository


@pytest.mark.asyncio
async def test_gemini_service_resilience_matrix():
    """
    Stress-tests GeminiService against an adversarial matrix of connection and API exceptions.
    Asserts:
    1. Every exception is safely caught.
    2. success=False is returned.
    3. candidates, sources, citations are empty lists (no synthetic data).
    4. status correctly differentiates QUOTA_EXHAUSTED vs ERROR.
    """
    service = GeminiService()
    service.api_key = "test-challenger-key"
    service._client = MagicMock()

    exception_matrix = [
        (RuntimeError("Connection timeout to Gemini API"), "ERROR"),
        (ConnectionResetError("Remote host forcibly closed an existing connection"), "ERROR"),
        (TimeoutError("Gateway timeout 504"), "ERROR"),
        (Exception("429 Resource has been exhausted (e.g. check quota)."), "QUOTA_EXHAUSTED"),
        (Exception("RESOURCE_EXHAUSTED: Quota exceeded for quota metric"), "QUOTA_EXHAUSTED"),
        (Exception("503 The model is overloaded. Please try again later."), "ERROR"),
        (ValueError("Malformed input parameters"), "ERROR"),
    ]

    for exc, expected_status in exception_matrix:
        # Test Discovery
        service._is_quota_exhausted = False
        service._client.models.generate_content.side_effect = exc

        res_disc = await service.search_grounded_discovery("ai scholarship", "profile")
        assert res_disc["success"] is False
        assert res_disc["candidates"] == []
        assert res_disc["sources"] == []
        assert res_disc["citations"] == []
        assert res_disc["status"] == expected_status
        assert "Gemini Search Grounding error" in res_disc["error"]

        # Test URL Extraction with clean quota flag
        service._is_quota_exhausted = False
        service._client.models.generate_content.side_effect = exc
        res_extract = await service.analyze_url_and_extract_criteria(
            ["https://utoronto.ca/admissions"], "MS CS", "University of Toronto", "student"
        )
        assert res_extract["success"] is False
        assert res_extract["data"] is None
        assert res_extract["is_retrieval_successful"] is False
        assert res_extract["retrieval_status"] == "URL_RETRIEVAL_STATUS_ERROR"
        assert res_extract["evidence_quality"] == "UNVERIFIED"
        assert res_extract["status"] == expected_status
        assert ("URL analysis error" in res_extract["error"] or "QUOTA_EXHAUSTED" in res_extract["error"])


@pytest.mark.asyncio
async def test_reviewer_fail_closed_under_failure_modes():
    """
    Stress-tests Quality Reviewer fail-closed contract.
    Asserts:
    - Missing key -> approved=False, confidence_rating=LOW
    - 429 Quota exhaustion -> approved=False, error=QUOTA_EXHAUSTED, confidence_rating=LOW
    - Unexpected runtime crash -> approved=False, success=False
    """
    service = GeminiService()
    service.api_key = "test-challenger-key"
    service._client = MagicMock()

    # 1. Missing key
    service_no_key = GeminiService()
    service_no_key.api_key = None
    res_no_key = await service_no_key.review_evidence_and_claims({}, {})
    assert res_no_key["success"] is False
    assert res_no_key["approved"] is False
    assert res_no_key["data"]["approved"] is False
    assert res_no_key["data"]["confidence_rating"] == "LOW"

    # 2. 429 Quota exhausted
    service._is_quota_exhausted = False
    service._client.models.generate_content.side_effect = Exception("429 RESOURCE_EXHAUSTED")
    res_quota = await service.review_evidence_and_claims({}, {})
    assert res_quota["success"] is False
    assert res_quota["approved"] is False
    assert res_quota["error"] == "QUOTA_EXHAUSTED"
    assert res_quota["data"]["approved"] is False
    assert res_quota["data"]["confidence_rating"] == "LOW"

    # 3. Server error 500
    service._is_quota_exhausted = False
    service._client.models.generate_content.side_effect = RuntimeError("500 Internal Error")
    res_crash = await service.review_evidence_and_claims({}, {})
    assert res_crash["success"] is False
    assert res_crash["approved"] is False


def test_scale_mismatch_without_equivalency_resolves_unresolved():
    """
    Verifies that grading scale mismatch without official equivalency note
    resolves to UNRESOLVED with actionable gap guidance and never applies
    invented linear formulas (e.g. 4.0 -> 10.0 or percentage division).
    """
    profile_10_scale = StudentProfile(
        full_name="Test Applicant",
        institution="Delhi Technological University",
        current_degree="B.Tech Computer Science",
        cgpa=8.2,
        grading_scale="10.0",
        graduation_year=2025,
        target_degree="Master's",
        target_field="Computer Science",
        target_countries=["USA"],
        citizenship="India",
        funding_preference="Full Funding",
        skills=["Python"],
        projects=[],
        language_tests={"test": "IELTS", "status": "completed", "score": "7.5"},
        career_goals="Graduate Studies"
    )

    # Case A: with explicit slash ratio (3.5/4.0)
    req_ratio = {
        "criterion_type": "ACADEMIC_GRADE",
        "stated_requirement": "Minimum 3.5/4.0 GPA",
        "requirement_text": "Minimum 3.5/4.0 GPA",
        "official_equivalency_note": None
    }
    eval_ratio = evaluate_single_criterion(req_ratio, profile_10_scale, is_admission=True)
    assert eval_ratio["status"] == "UNRESOLVED"
    assert "No published institutional equivalency provided" in eval_ratio["uncertainty_or_conflict"]
    assert "Verify institutional grade conversion" in eval_ratio["actionable_gap"]

    # Case B: without slash (3.5 on a 4.0 scale)
    req_text_scale = {
        "criterion_type": "ACADEMIC_GRADE",
        "stated_requirement": "Minimum GPA of 3.5 on a 4.0 scale",
        "requirement_text": "Minimum GPA of 3.5 on a 4.0 scale",
        "official_equivalency_note": None
    }
    eval_text = evaluate_single_criterion(req_text_scale, profile_10_scale, is_admission=True)
    assert eval_text["status"] == "UNRESOLVED"
    assert "institutional equivalency must be verified" in eval_text["uncertainty_or_conflict"]
    assert "Verify institutional grade conversion" in eval_text["actionable_gap"]

    # Verify extract_numeric_cgpa_cutoff returns None for ungrounded scales
    assert extract_numeric_cgpa_cutoff("Minimum 3.5 on a 4.0 scale") is None
    assert extract_numeric_cgpa_cutoff("Minimum 3.5/4.0 GPA") is None
    assert extract_numeric_cgpa_cutoff("Minimum 8.0/10.0 CGPA") == 8.0
    assert extract_numeric_cgpa_cutoff("First class with distinction") is None


@pytest.mark.asyncio
async def test_research_agent_quota_exhaustion_emits_quota_event():
    """
    Verifies that when live discovery experiences quota exhaustion,
    ResearchEligibilityAgent emits QUOTA_EXHAUSTED event and returns []
    without falling back to synthetic fixtures.
    """
    agent = ResearchEligibilityAgent()
    profile = StudentProfile(
        full_name="Quota Test Student",
        institution="University",
        current_degree="B.Sc",
        cgpa=8.0,
        grading_scale="10.0",
        graduation_year=2025,
        target_degree="Master's",
        target_field="Data Science",
        target_countries=["Germany"],
        citizenship="India",
        funding_preference="Full",
        skills=[],
        projects=[],
        language_tests={"test": "IELTS", "status": "completed", "score": "7.0"},
        career_goals="Research"
    )

    # Mock service with quota exhausted
    mock_service = MagicMock()
    mock_service._is_quota_exhausted = True
    mock_service.is_available = True
    async def mock_exhausted(*args, **kwargs):
        return {
            "success": False,
            "error": "QUOTA_EXHAUSTED",
            "status": "QUOTA_EXHAUSTED",
            "candidates": [],
            "sources": [],
            "citations": [],
            "search_queries": []
        }
    mock_service.search_grounded_discovery = mock_exhausted

    import app.agents.research_eligibility as re_mod
    orig_service = re_mod.gemini_service
    re_mod.gemini_service = mock_service
    try:
        results = await agent.execute_discovery_and_audit("test-run-quota-1", profile)
        assert results == [], "Expected empty list on quota exhaustion, no synthetic opportunities"
        
        events = await repository.get_agent_events("test-run-quota-1")
        quota_events = [e for e in events if e.event_type == "QUOTA_EXHAUSTED"]
        assert len(quota_events) >= 1, "Expected QUOTA_EXHAUSTED event to be logged"
    finally:
        re_mod.gemini_service = orig_service
