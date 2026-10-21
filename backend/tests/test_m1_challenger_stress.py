"""
Adversarial Stress Test Harness: Milestone M1 Empirical Challenge
Targeting:
1. Simulated URL_RETRIEVAL_STATUS_PAYWALL and URL_RETRIEVAL_STATUS_ERROR in Gemini URL Context.
2. Missing GEMINI_API_KEY / gemini_service.is_available = False (ensuring GeminiConfigurationError without fallbacks).
3. Zero-candidate search discovery returning cleanly [] without dummy/synthetic records.
4. SSRF / Unsafe URL candidate filtering.
5. Malformed/unparsable model outputs during URL extraction resilience.
"""

import inspect
import json
import pytest
import time
from unittest.mock import MagicMock, AsyncMock, patch, PropertyMock
from google.genai import types

from app.services.gemini_service import GeminiService, GeminiConfigurationError, gemini_service
from app.agents.research_eligibility import ResearchEligibilityAgent
from app.models.profile import StudentProfile
from app.models.opportunity import Opportunity
from app.graph.workflow import swarm_app
from app.graph.state import SwarmState
from app.db.repository import repository


@pytest.fixture
def test_student_profile() -> StudentProfile:
    return StudentProfile(
        full_name="Amina El-Sayed",
        current_degree="BSc Informatics",
        institution="Cairo University",
        cgpa=8.8,
        grading_scale="10.0",
        target_degree="Master of Science",
        target_field="Data Science & Artificial Intelligence",
        target_countries=["Germany", "Canada"],
        language_tests={"IELTS": 7.5}
    )


# ==============================================================================
# Challenge Suite 1: Gemini URL Context Retrieval Statuses (PAYWALL, ERROR, UNSAFE, MIXED)
# ==============================================================================

@pytest.mark.asyncio
async def test_empirical_url_context_paywall_status_service_level():
    """Empirically test that analyze_url_and_extract_criteria correctly handles URL_RETRIEVAL_STATUS_PAYWALL."""
    service = GeminiService()
    service.api_key = "stress-test-key"
    mock_client = MagicMock()
    service._client = mock_client

    # Build simulated candidate with PAYWALL status
    mock_candidate = MagicMock()
    mock_meta_entry = MagicMock()
    mock_meta_entry.retrieved_url = "https://paywalled-journal.de/scholarships/postgrad"
    mock_meta_entry.url_retrieval_status = types.UrlRetrievalStatus.URL_RETRIEVAL_STATUS_PAYWALL
    mock_candidate.url_context_metadata.url_metadata = [mock_meta_entry]

    mock_response = MagicMock()
    mock_response.candidates = [mock_candidate]
    # Model cannot access full page due to paywall, returns minimal or partial structure
    mock_response.text = json.dumps({
        "admission_requirements": [],
        "scholarship_requirements": [],
        "funding_details": {"funding_type": "Unknown", "coverage_description": "Paywalled"},
        "deadline": None,
        "deadline_type": "Unknown",
        "deadline_verified": False,
        "overall_eligibility_status": "INSUFFICIENT_EVIDENCE",
        "eligibility_reasons": ["Source page is behind an institutional paywall"],
        "actionable_gaps": ["Requires institutional login to verify requirements"]
    })

    mock_client.models.generate_content.return_value = mock_response

    start_time = time.perf_counter()
    res = await service.analyze_url_and_extract_criteria(
        urls=["https://paywalled-journal.de/scholarships/postgrad"],
        program_name="MSc Data Science",
        university="Technical University",
        student_profile_summary="CGPA 8.8"
    )
    elapsed = time.perf_counter() - start_time

    assert res["success"] is True
    assert res["is_retrieval_successful"] is False
    assert res["retrieval_status"] == "URL_RETRIEVAL_STATUS_PAYWALL"
    assert res["evidence_quality"] == "UNVERIFIED"
    assert res["url_retrieval_statuses"]["https://paywalled-journal.de/scholarships/postgrad"] == "URL_RETRIEVAL_STATUS_PAYWALL"
    assert elapsed < 1.0


@pytest.mark.asyncio
async def test_empirical_url_context_error_status_service_level():
    """Empirically test that analyze_url_and_extract_criteria correctly handles URL_RETRIEVAL_STATUS_ERROR."""
    service = GeminiService()
    service.api_key = "stress-test-key"
    mock_client = MagicMock()
    service._client = mock_client

    # Build simulated candidate with ERROR status (e.g. HTTP 500, DNS failure, 404)
    mock_candidate = MagicMock()
    mock_meta_entry = MagicMock()
    mock_meta_entry.retrieved_url = "https://broken-server.ca/msc-admissions"
    mock_meta_entry.url_retrieval_status = types.UrlRetrievalStatus.URL_RETRIEVAL_STATUS_ERROR
    mock_candidate.url_context_metadata.url_metadata = [mock_meta_entry]

    mock_response = MagicMock()
    mock_response.candidates = [mock_candidate]
    mock_response.text = json.dumps({
        "admission_requirements": [],
        "scholarship_requirements": [],
        "funding_details": {"funding_type": "Unknown"},
        "deadline": None,
        "overall_eligibility_status": "INSUFFICIENT_EVIDENCE"
    })

    mock_client.models.generate_content.return_value = mock_response

    res = await service.analyze_url_and_extract_criteria(
        urls=["https://broken-server.ca/msc-admissions"],
        program_name="MSc AI",
        university="Broken University",
        student_profile_summary="CGPA 8.8"
    )

    assert res["success"] is True
    assert res["is_retrieval_successful"] is False
    assert res["retrieval_status"] == "URL_RETRIEVAL_STATUS_ERROR"
    assert res["evidence_quality"] == "UNVERIFIED"
    assert res["url_retrieval_statuses"]["https://broken-server.ca/msc-admissions"] == "URL_RETRIEVAL_STATUS_ERROR"


@pytest.mark.asyncio
async def test_empirical_url_context_unsafe_status_service_level():
    """Empirically test that analyze_url_and_extract_criteria correctly handles URL_RETRIEVAL_STATUS_UNSAFE."""
    service = GeminiService()
    service.api_key = "stress-test-key"
    mock_client = MagicMock()
    service._client = mock_client

    mock_candidate = MagicMock()
    mock_meta_entry = MagicMock()
    mock_meta_entry.retrieved_url = "https://phishing-site.com/aid"
    mock_meta_entry.url_retrieval_status = types.UrlRetrievalStatus.URL_RETRIEVAL_STATUS_UNSAFE
    mock_candidate.url_context_metadata.url_metadata = [mock_meta_entry]

    mock_response = MagicMock()
    mock_response.candidates = [mock_candidate]
    mock_response.text = json.dumps({
        "admission_requirements": [],
        "scholarship_requirements": [],
        "funding_details": {},
        "overall_eligibility_status": "INSUFFICIENT_EVIDENCE"
    })

    mock_client.models.generate_content.return_value = mock_response

    res = await service.analyze_url_and_extract_criteria(
        urls=["https://phishing-site.com/aid"],
        program_name="Phishing Program",
        university="Phishing Univ",
        student_profile_summary="CGPA 8.8"
    )

    assert res["success"] is True
    assert res["is_retrieval_successful"] is False
    assert res["retrieval_status"] == "URL_RETRIEVAL_STATUS_UNSAFE"
    assert res["evidence_quality"] == "UNVERIFIED"


@pytest.mark.asyncio
async def test_empirical_url_context_mixed_statuses_service_level():
    """Empirically test multi-URL query where one URL succeeds and one URL is paywalled."""
    service = GeminiService()
    service.api_key = "stress-test-key"
    mock_client = MagicMock()
    service._client = mock_client

    url_success = "https://tum.de/msc-informatics"
    url_paywall = "https://internal-portal.tum.de/stipend-details"

    mock_candidate = MagicMock()
    meta_success = MagicMock()
    meta_success.retrieved_url = url_success
    meta_success.url_retrieval_status = types.UrlRetrievalStatus.URL_RETRIEVAL_STATUS_SUCCESS

    meta_paywall = MagicMock()
    meta_paywall.retrieved_url = url_paywall
    meta_paywall.url_retrieval_status = types.UrlRetrievalStatus.URL_RETRIEVAL_STATUS_PAYWALL

    mock_candidate.url_context_metadata.url_metadata = [meta_success, meta_paywall]

    mock_response = MagicMock()
    mock_response.candidates = [mock_candidate]
    mock_response.text = json.dumps({
        "admission_requirements": [
            {
                "criterion_name": "Undergraduate Degree",
                "stated_requirement": "BSc in Computer Science or Informatics",
                "student_value": "BSc Informatics",
                "status": "MEETS",
                "evidence_excerpt": "Requires relevant Bachelor's degree in Informatics or related fields.",
                "source_url": url_success
            }
        ],
        "scholarship_requirements": [],
        "funding_details": {"funding_type": "Partial", "coverage_description": "Partial tuition waiver"},
        "deadline": "2026-05-31",
        "deadline_type": "Fixed",
        "deadline_verified": True,
        "overall_eligibility_status": "MEETS_STATED_CRITERIA"
    })

    mock_client.models.generate_content.return_value = mock_response

    res = await service.analyze_url_and_extract_criteria(
        urls=[url_success, url_paywall],
        program_name="MSc Informatics",
        university="Technical University of Munich",
        student_profile_summary="CGPA 8.8"
    )

    assert res["success"] is True
    # At least one succeeded, so overall is_retrieval_successful is True
    assert res["is_retrieval_successful"] is True
    assert res["evidence_quality"] == "OFFICIAL"
    assert res["url_retrieval_statuses"][url_success] == "URL_RETRIEVAL_STATUS_SUCCESS"
    assert res["url_retrieval_statuses"][url_paywall] == "URL_RETRIEVAL_STATUS_PAYWALL"


# ==============================================================================
# Challenge Suite 2: Agent Level URL Failure Handling (PAYWALL & ERROR Degradation)
# ==============================================================================

@pytest.mark.asyncio
async def test_empirical_research_agent_paywall_graceful_degradation(test_student_profile):
    """
    Empirically verify that when URL Context returns URL_RETRIEVAL_STATUS_PAYWALL:
    - Opportunity is created without crashing
    - evidence_quality is strictly 'UNVERIFIED'
    - eligibility_status is strictly 'INSUFFICIENT_EVIDENCE'
    - deadline_verified is False
    - evidence_records contains an UNRESOLVED record citing the paywall status
    - actionable_gaps flags manual verification
    """
    agent = ResearchEligibilityAgent()
    run_id = "test-challenger-paywall"

    # Mock search discovery to find one candidate URL
    mock_discovery = {
        "success": True,
        "candidates": [
            {
                "canonical_url": "https://restricted-portal.de/admissions/msc",
                "program_name": "MSc Informatics",
                "university": "Heidelberg University",
                "funding": {"funding_type": "Fully Funded"}
            }
        ],
        "sources": []
    }

    # Mock URL Context analysis returning PAYWALL status
    mock_url_analysis = {
        "success": True,
        "is_retrieval_successful": False,
        "retrieval_status": "URL_RETRIEVAL_STATUS_PAYWALL",
        "evidence_quality": "UNVERIFIED",
        "url_retrieval_statuses": {
            "https://restricted-portal.de/admissions/msc": "URL_RETRIEVAL_STATUS_PAYWALL"
        },
        "data": {
            "program_name": "MSc Informatics",
            "university": "Heidelberg University",
            "country": "Germany",
            "degree_level": "Master's",
            "funding_details": {"funding_type": "Unknown"},
            "deadline": None,
            "deadline_type": "Unknown",
            "deadline_verified": False,
            "overall_eligibility_status": "INSUFFICIENT_EVIDENCE",
            "actionable_gaps": []
        }
    }

    with patch.object(gemini_service, "ensure_available", return_value=None), \
         patch.object(gemini_service, "search_grounded_discovery", AsyncMock(return_value=mock_discovery)), \
         patch.object(gemini_service, "analyze_url_and_extract_criteria", AsyncMock(return_value=mock_url_analysis)):

        opps = await agent.execute_discovery_and_audit(
            run_id=run_id,
            profile=test_student_profile,
            research_round=1
        )

    assert len(opps) == 1
    opp = opps[0]
    assert opp.evidence_quality == "UNVERIFIED"
    assert opp.eligibility_status == "INSUFFICIENT_EVIDENCE"
    assert opp.deadline_verified is False
    assert any("URL_RETRIEVAL_STATUS_PAYWALL" in gap for gap in opp.actionable_gaps)
    
    # Check evidence records
    assert len(opp.evidence_records) >= 1
    unresolved_record = opp.evidence_records[0]
    assert unresolved_record.status == "UNRESOLVED"
    assert unresolved_record.evidence_excerpt is None
    assert unresolved_record.source_category == "UNVERIFIED"
    assert "URL_RETRIEVAL_STATUS_PAYWALL" in unresolved_record.uncertainty_or_conflict


@pytest.mark.asyncio
async def test_empirical_research_agent_network_failure_does_not_crash(test_student_profile):
    """Verify that network exceptions or timeouts during URL analysis are handled cleanly without crashing."""
    agent = ResearchEligibilityAgent()
    run_id = "test-challenger-network-error"

    mock_discovery = {
        "success": True,
        "candidates": [
            {
                "canonical_url": "https://timeout-host.ca/msc",
                "program_name": "MSc CS",
                "university": "Timeout Univ"
            }
        ],
        "sources": []
    }

    # Simulate unexpected network/timeout exception
    with patch.object(gemini_service, "ensure_available", return_value=None), \
         patch.object(gemini_service, "search_grounded_discovery", AsyncMock(return_value=mock_discovery)), \
         patch.object(gemini_service, "analyze_url_and_extract_criteria", AsyncMock(side_effect=TimeoutError("Connection timed out"))):

        opps = await agent.execute_discovery_and_audit(
            run_id=run_id,
            profile=test_student_profile,
            research_round=1
        )

    # Candidate was skipped cleanly after extraction error, no unhandled exception
    assert opps == []


# ==============================================================================
# Challenge Suite 3: Gemini Service Unavailable Policy (Zero Dummy Fallback)
# ==============================================================================

@pytest.mark.asyncio
async def test_empirical_is_available_false_raises_configuration_error(test_student_profile):
    """
    Verify that when gemini_service.is_available is False:
    - ensure_available() raises GeminiConfigurationError
    - execute_discovery_and_audit() raises GeminiConfigurationError
    - NO dummy opportunities are returned
    """
    agent = ResearchEligibilityAgent()
    run_id = "test-challenger-no-key"

    with patch.object(GeminiService, "is_available", new_callable=PropertyMock, return_value=False):
        # 1. ensure_available directly raises
        service = GeminiService()
        with pytest.raises(GeminiConfigurationError) as exc_service:
            service.ensure_available()
        assert "GEMINI_API_KEY is not configured" in str(exc_service.value)

        # 2. agent raises GeminiConfigurationError and NEVER falls back
        with pytest.raises(GeminiConfigurationError) as exc_agent:
            await agent.execute_discovery_and_audit(
                run_id=run_id,
                profile=test_student_profile,
                research_round=1
            )
        assert "GEMINI_API_KEY is not configured" in str(exc_agent.value)

        # 3. Verify no opportunities were persisted in repository for this run
        repo_opps = await repository.get_opportunities(run_id)
        assert repo_opps == []


@pytest.mark.asyncio
async def test_empirical_workflow_bubbles_configuration_error(test_student_profile):
    """Verify that the compiled LangGraph workflow propagates GeminiConfigurationError when API key is missing."""
    state = SwarmState(
        run_id="test-challenger-workflow-no-key",
        user_input=test_student_profile.model_dump(),
        student_profile=test_student_profile
    )

    with patch.object(GeminiService, "is_available", new_callable=PropertyMock, return_value=False):
        with pytest.raises(GeminiConfigurationError):
            await swarm_app.ainvoke(state)


# ==============================================================================
# Challenge Suite 4: Zero Candidate Discovery (Honest Reporting, No Fake Records)
# ==============================================================================

@pytest.mark.asyncio
async def test_empirical_zero_candidate_discovery_returns_clean_empty_list(test_student_profile):
    """
    Verify that when search grounded discovery returns zero candidates:
    - execute_discovery_and_audit returns strictly []
    - len(opportunities) == 0
    - No fake or hardcoded opportunities are populated
    - DISCOVERY_EMPTY event is emitted
    """
    agent = ResearchEligibilityAgent()
    run_id = "test-challenger-zero-discovery"

    # Search returns success but empty candidates and empty sources
    empty_discovery = {
        "success": True,
        "candidates": [],
        "sources": [],
        "citations": [],
        "search_queries": ["official query"]
    }

    with patch.object(gemini_service, "ensure_available", return_value=None), \
         patch.object(gemini_service, "search_grounded_discovery", AsyncMock(return_value=empty_discovery)):

        opps = await agent.execute_discovery_and_audit(
            run_id=run_id,
            profile=test_student_profile,
            research_round=1
        )

    assert isinstance(opps, list)
    assert len(opps) == 0
    assert opps == []

    # Verify agent events include DISCOVERY_EMPTY
    events = await repository.get_agent_events(run_id)
    empty_events = [e for e in events if e.event_type == "DISCOVERY_EMPTY"]
    assert len(empty_events) == 1
    assert "No Candidates Found" in empty_events[0].title


@pytest.mark.asyncio
async def test_empirical_zero_candidate_full_workflow_execution(test_student_profile):
    """
    Verify that the entire LangGraph swarm workflow handles zero discovered candidates cleanly:
    - Workflow finishes with current_phase == 'COMPLETED'
    - opportunities in state is strictly []
    - Match Strategist and Quality Reviewer do not crash or hallucinate
    """
    run_id = "test-challenger-workflow-zero"
    state = SwarmState(
        run_id=run_id,
        user_input=test_student_profile.model_dump(),
        student_profile=test_student_profile
    )

    empty_discovery = {
        "success": True,
        "candidates": [],
        "sources": [],
        "citations": [],
        "search_queries": []
    }

    with patch.object(gemini_service, "ensure_available", return_value=None), \
         patch.object(gemini_service, "search_grounded_discovery", AsyncMock(return_value=empty_discovery)):

        final_state = await swarm_app.ainvoke(state)

    assert final_state["opportunities"] == []
    assert final_state["current_phase"] == "COMPLETED"
    assert final_state["needs_re_research"] is False


# ==============================================================================
# Challenge Suite 5: SSRF / Unsafe Candidate Filter Stress Testing
# ==============================================================================

@pytest.mark.asyncio
async def test_empirical_unsafe_and_ssrf_urls_rejected_before_extraction(test_student_profile):
    """
    Empirically verify that malicious, loopback, metadata, or private IP URLs returned by search
    are filtered out and NEVER forwarded to Gemini URL Context tool.
    """
    agent = ResearchEligibilityAgent()
    run_id = "test-challenger-ssrf"

    malicious_discovery = {
        "success": True,
        "candidates": [
            {"canonical_url": "http://169.254.169.254/latest/meta-data/", "title": "AWS Metadata"},
            {"canonical_url": "http://localhost:8080/admin", "title": "Localhost Admin"},
            {"canonical_url": "http://127.0.0.1:5432", "title": "PostgreSQL Internal"},
            {"canonical_url": "ftp://files.internal.corp/secret.pdf", "title": "FTP File"},
            {"canonical_url": "file:///etc/passwd", "title": "Local Password File"},
            {"canonical_url": "https://tum.de/legitimate-program", "title": "TUM Valid Page"}
        ],
        "sources": []
    }

    analyzed_urls = []

    async def mock_analyze(urls, program_name, university, student_profile_summary):
        analyzed_urls.extend(urls)
        return {
            "success": True,
            "is_retrieval_successful": True,
            "retrieval_status": "URL_RETRIEVAL_STATUS_SUCCESS",
            "evidence_quality": "OFFICIAL",
            "url_retrieval_statuses": {urls[0]: "URL_RETRIEVAL_STATUS_SUCCESS"},
            "data": {
                "program_name": "TUM Valid",
                "university": "TUM",
                "funding_details": {"funding_type": "Partial"},
                "admission_requirements": [],
                "overall_eligibility_status": "POTENTIAL_MATCH"
            }
        }

    with patch.object(gemini_service, "ensure_available", return_value=None), \
         patch.object(gemini_service, "search_grounded_discovery", AsyncMock(return_value=malicious_discovery)), \
         patch.object(gemini_service, "analyze_url_and_extract_criteria", side_effect=mock_analyze):

        opps = await agent.execute_discovery_and_audit(
            run_id=run_id,
            profile=test_student_profile,
            research_round=1
        )

    # Verify only the legitimate https://tum.de URL was evaluated
    assert len(analyzed_urls) == 1
    assert analyzed_urls[0] == "https://tum.de/legitimate-program"
    assert not any("169.254" in u or "localhost" in u or "127.0.0.1" in u or "file://" in u for u in analyzed_urls)
    assert len(opps) == 1


# ==============================================================================
# Challenge Suite 6: Model Output Formatting Edge Cases (Malformed JSON / Truncation)
# ==============================================================================

@pytest.mark.asyncio
async def test_empirical_malformed_json_response_handling():
    """Verify analyze_url_and_extract_criteria handles unparseable JSON gracefully without crashing."""
    service = GeminiService()
    service.api_key = "stress-test-key"
    mock_client = MagicMock()
    service._client = mock_client

    mock_response = MagicMock()
    mock_response.candidates = []
    # Truncated or plain text error from model
    mock_response.text = "Error: I cannot analyze this page because it returned a 403 Forbidden."
    mock_client.models.generate_content.return_value = mock_response

    res = await service.analyze_url_and_extract_criteria(
        urls=["https://test.edu/program"],
        program_name="Test Program",
        university="Test Univ",
        student_profile_summary="CGPA 8.8"
    )

    assert res["success"] is False
    assert res["is_retrieval_successful"] is False
    assert "URL analysis error" in res["error"]
    assert res["retrieval_status"] == "URL_RETRIEVAL_STATUS_ERROR"


# ==============================================================================
# Challenge Suite 7: Absolute Absence of Hardcoded Fixtures via AST Inspection
# ==============================================================================

def test_empirical_ast_inspection_no_hardcoded_lists_in_research_eligibility():
    """Adversarial AST inspection of research_eligibility.py to prove no hardcoded opportunity dictionaries exist."""
    import app.agents.research_eligibility as mod
    source = inspect.getsource(mod)

    # 1. Check no reference to REAL_OPPORTUNITIES_BASE
    assert "REAL_OPPORTUNITIES_BASE" not in source

    # 2. Check no large inline dict literals resembling mock opportunities
    assert "ETH Zurich Excellence Scholarship" not in source
    assert "TU Delft Justus & Louise van Effen" not in source
    assert "Singapore International Graduate Award" not in source
    assert "Vector Institute Scholarship" not in source


# ==============================================================================
# Challenge Suite 8: Deduplication, Candidate Bounds & Edge Statuses
# ==============================================================================

@pytest.mark.asyncio
async def test_empirical_url_context_empty_urls_list():
    """Verify analyze_url_and_extract_criteria handles empty URL list gracefully."""
    service = GeminiService()
    service.api_key = "stress-test-key"
    mock_client = MagicMock()
    service._client = mock_client

    mock_response = MagicMock()
    mock_response.candidates = []
    mock_response.text = json.dumps({"admission_requirements": []})
    mock_client.models.generate_content.return_value = mock_response

    res = await service.analyze_url_and_extract_criteria(
        urls=[],
        program_name="Test",
        university="Test",
        student_profile_summary="Test"
    )

    assert res["success"] is True
    assert res["is_retrieval_successful"] is False
    assert res["retrieval_status"] == "URL_RETRIEVAL_STATUS_UNSPECIFIED"
    assert res["evidence_quality"] == "UNVERIFIED"


@pytest.mark.asyncio
async def test_empirical_url_context_unspecified_enum_defaults_to_unverified():
    """Verify that an UNSPECIFIED or unrecognized status enum safely defaults to UNVERIFIED."""
    service = GeminiService()
    service.api_key = "stress-test-key"
    mock_client = MagicMock()
    service._client = mock_client

    mock_candidate = MagicMock()
    mock_meta_entry = MagicMock()
    mock_meta_entry.retrieved_url = "https://example.edu/program"
    mock_meta_entry.url_retrieval_status = types.UrlRetrievalStatus.URL_RETRIEVAL_STATUS_UNSPECIFIED
    mock_candidate.url_context_metadata.url_metadata = [mock_meta_entry]

    mock_response = MagicMock()
    mock_response.candidates = [mock_candidate]
    mock_response.text = json.dumps({"admission_requirements": []})
    mock_client.models.generate_content.return_value = mock_response

    res = await service.analyze_url_and_extract_criteria(
        urls=["https://example.edu/program"],
        program_name="Test",
        university="Test",
        student_profile_summary="Test"
    )

    assert res["success"] is True
    assert res["is_retrieval_successful"] is False
    assert res["retrieval_status"] == "URL_RETRIEVAL_STATUS_UNSPECIFIED"
    assert res["evidence_quality"] == "UNVERIFIED"


@pytest.mark.asyncio
async def test_empirical_duplicate_url_deduplication_in_discovery(test_student_profile):
    """
    Verify that if search discovery returns duplicate or differently-formatted URLs
    pointing to the same canonical resource (e.g. trailing slashes, tracking parameters),
    they are deduplicated and analyzed exactly ONCE.
    """
    agent = ResearchEligibilityAgent()
    run_id = "test-challenger-dedup"

    # Both countries return same URL, one with tracking param and trailing slash
    discovery_res = {
        "success": True,
        "candidates": [
            {"canonical_url": "https://uni-bonn.de/msc-data-science/", "title": "Bonn Data Science 1"},
            {"canonical_url": "https://uni-bonn.de/msc-data-science?utm_source=scholarship", "title": "Bonn Data Science 2"},
            {"canonical_url": "https://uni-bonn.de/msc-data-science", "title": "Bonn Data Science 3"}
        ],
        "sources": []
    }

    analyzed_calls = []

    async def mock_analyze(urls, program_name, university, student_profile_summary):
        analyzed_calls.append(urls[0])
        return {
            "success": True,
            "is_retrieval_successful": True,
            "retrieval_status": "URL_RETRIEVAL_STATUS_SUCCESS",
            "evidence_quality": "OFFICIAL",
            "data": {
                "program_name": "MSc Data Science",
                "university": "University of Bonn",
                "funding_details": {"funding_type": "Full"},
                "admission_requirements": []
            }
        }

    with patch.object(gemini_service, "ensure_available", return_value=None), \
         patch.object(gemini_service, "search_grounded_discovery", AsyncMock(return_value=discovery_res)), \
         patch.object(gemini_service, "analyze_url_and_extract_criteria", side_effect=mock_analyze):

        opps = await agent.execute_discovery_and_audit(
            run_id=run_id,
            profile=test_student_profile,
            research_round=1
        )

    # All 3 variants normalize to 'https://uni-bonn.de/msc-data-science', analyzed only ONCE
    assert len(analyzed_calls) == 1
    assert analyzed_calls[0] == "https://uni-bonn.de/msc-data-science"
    assert len(opps) == 1


@pytest.mark.asyncio
async def test_empirical_candidate_bounding_to_max_configured(test_student_profile):
    """Verify that if search grounding returns 40 candidates, extraction is capped at MAX_RESEARCH_CANDIDATES."""
    agent = ResearchEligibilityAgent()
    run_id = "test-challenger-bound"

    # 40 distinct valid candidate URLs
    candidates = [{"canonical_url": f"https://uni-{i}.edu/grad", "title": f"Uni {i}"} for i in range(40)]
    discovery_res = {"success": True, "candidates": candidates, "sources": []}

    analyzed_calls = []

    async def mock_analyze(urls, program_name, university, student_profile_summary):
        analyzed_calls.append(urls[0])
        return {
            "success": True,
            "is_retrieval_successful": True,
            "retrieval_status": "URL_RETRIEVAL_STATUS_SUCCESS",
            "evidence_quality": "OFFICIAL",
            "data": {"program_name": "Test", "university": "Test", "funding_details": {}, "admission_requirements": []}
        }

    with patch.object(gemini_service, "ensure_available", return_value=None), \
         patch.object(gemini_service, "search_grounded_discovery", AsyncMock(return_value=discovery_res)), \
         patch.object(gemini_service, "analyze_url_and_extract_criteria", side_effect=mock_analyze):

        opps = await agent.execute_discovery_and_audit(
            run_id=run_id,
            profile=test_student_profile,
            research_round=1
        )

    # Should be strictly bounded to 30 (settings.MAX_RESEARCH_CANDIDATES default)
    assert len(analyzed_calls) <= 30
    assert len(opps) <= 30
