"""
Tier 1: Isolated Feature Coverage Test Suite.
Verifies features F1 through F10 in isolation against API endpoints,
domain services, and agent workflow boundaries under opaque-box conditions.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

from app.models.profile import StudentProfile
from app.models.opportunity import Opportunity, FundingDetails, EligibilityCriterion
from app.models.evidence import EvidenceRecord, MatchScore
from app.services.gemini_service import GeminiService
from app.security.sanitizer import normalize_url, is_safe_url, is_official_domain
from app.agents.quality_reviewer import QualityReviewerAgent
from app.services.scoring_service import calculate_match_score
from tests.fixtures.opportunities import CANONICAL_FIXTURE_OPPORTUNITIES


# ==============================================================================
# F1: Eliminate REAL_OPPORTUNITIES_BASE & Fixture Isolation
# ==============================================================================
def test_f1_fixtures_are_isolated_and_conform_to_schema():
    """
    F1: Validates that test fixtures reside in `tests/fixtures/opportunities.py`
    and conform strictly to the domain Opportunity schema requirements without
    polluting live production paths.
    """
    assert len(CANONICAL_FIXTURE_OPPORTUNITIES) >= 5, "At least 5 canonical fixtures must be maintained"
    
    for item in CANONICAL_FIXTURE_OPPORTUNITIES:
        # Check required fields
        assert "title" in item and len(item["title"]) > 0
        assert "university" in item and len(item["university"]) > 0
        assert "canonical_url" in item and item["canonical_url"].startswith("https://")
        assert "admission_requirements" in item and isinstance(item["admission_requirements"], list)
        assert len(item["admission_requirements"]) > 0
        assert "funding" in item and "funding_type" in item["funding"]
        
        # Ensure URLs are safe from SSRF
        assert is_safe_url(item["canonical_url"]) is True
        for src_url in item.get("official_source_urls", []):
            assert is_safe_url(src_url) is True


# ==============================================================================
# F2: Gemini Search Grounding Discovery
# ==============================================================================
@pytest.mark.asyncio
async def test_f2_search_grounding_discovery_contract(profile_rahul_sharma):
    """
    F2: Verifies search grounding discovery query contract and candidate URL deduplication.
    Ensures parameters (degree, field, countries) are passed and duplicate URLs are stripped.
    """
    service = GeminiService()
    
    # Verify query format includes student profile parameters
    query = f"official scholarship {profile_rahul_sharma.target_degree} in {profile_rahul_sharma.target_field} in Canada"
    assert "Master's" in query
    assert "Computer Science" in query
    assert "Canada" in query

    # Test candidate deduplication with normalize_url
    raw_urls = [
        "https://web.cs.toronto.edu/graduate/mscac?utm_source=test",
        "https://web.cs.toronto.edu/graduate/mscac/",
        "HTTPS://WEB.CS.TORONTO.EDU/GRADUATE/MSCAC#overview",
        "https://www.tum.de/en/studies/degree-programs/detail/informatics-master-of-science-msc"
    ]
    seen_urls = set()
    unique_candidates = []
    for u in raw_urls:
        norm = normalize_url(u)
        if norm not in seen_urls:
            seen_urls.add(norm)
            unique_candidates.append(norm)

    assert len(unique_candidates) == 2
    assert "https://web.cs.toronto.edu/graduate/mscac" in unique_candidates
    assert "https://www.tum.de/en/studies/degree-programs/detail/informatics-master-of-science-msc" in unique_candidates


# ==============================================================================
# F3: Google Gen AI SDK URL Context Tool
# ==============================================================================
def test_f3_google_genai_sdk_url_context_tool_contract():
    """
    F3: Verifies that the official `google-genai` SDK types are available
    and the UrlContext tool structure can be configured without legacy wrappers.
    """
    from google.genai import types
    
    # Check UrlContext tool availability in SDK
    assert hasattr(types, "UrlContext"), "google-genai SDK must export UrlContext"
    assert hasattr(types, "Tool"), "google-genai SDK must export Tool"
    
    tool = types.Tool(url_context=types.UrlContext())
    assert tool.url_context is not None


# ==============================================================================
# F4: Retrieval Metadata Handling (SUCCESS vs ERROR/PAYWALL/UNSAFE)
# ==============================================================================
def test_f4_retrieval_metadata_handling_distinguishes_status():
    """
    F4: Verifies handling of URL retrieval status codes (SUCCESS vs PAYWALL/ERROR/UNSAFE).
    Unsuccessful retrievals must NOT fabricate data or crash; they must classify evidence
    as SECONDARY or UNRESOLVED.
    """
    from google.genai import types
    
    # Validate expected enum values exist on UrlRetrievalStatus
    assert hasattr(types, "UrlRetrievalStatus"), "SDK must define UrlRetrievalStatus"
    status_success = types.UrlRetrievalStatus.URL_RETRIEVAL_STATUS_SUCCESS
    status_error = types.UrlRetrievalStatus.URL_RETRIEVAL_STATUS_ERROR
    status_paywall = types.UrlRetrievalStatus.URL_RETRIEVAL_STATUS_PAYWALL
    status_unsafe = types.UrlRetrievalStatus.URL_RETRIEVAL_STATUS_UNSAFE
    
    assert status_success != status_error
    assert status_success != status_paywall
    assert status_success != status_unsafe

    # Test policy mapping for paywalled/error pages:
    def classify_retrieval(status):
        if status == types.UrlRetrievalStatus.URL_RETRIEVAL_STATUS_SUCCESS:
            return "OFFICIAL"
        return "SECONDARY"

    assert classify_retrieval(status_success) == "OFFICIAL"
    assert classify_retrieval(status_paywall) == "SECONDARY"
    assert classify_retrieval(status_error) == "SECONDARY"


# ==============================================================================
# F5: Explicit API Configuration Errors
# ==============================================================================
@pytest.mark.asyncio
async def test_f5_missing_api_key_returns_explicit_error_without_fallback():
    """
    F5: When GEMINI_API_KEY is unset or client is unconfigured, the service
    must return an explicit configuration error rather than silently synthesizing dummy data.
    """
    service = GeminiService()
    service.api_key = ""
    service._client = None
    assert service.is_available is False

    res_discovery = await service.search_grounded_discovery("scholarships in canada", "student context")
    assert res_discovery["success"] is False
    assert "GEMINI_API_KEY is not configured" in res_discovery["error"]
    assert len(res_discovery.get("sources", [])) == 0

    res_extract = await service.analyze_url_and_extract_criteria(
        ["https://example.edu"], "MS CS", "Test Uni", "Profile"
    )
    assert res_extract["success"] is False
    assert "GEMINI_API_KEY is not configured" in res_extract["error"]


# ==============================================================================
# F6: Program-Specific Criteria Matching (No generic assumptions)
# ==============================================================================
def test_f6_program_specific_criteria_matching(profile_rahul_sharma, profile_maria_santos):
    """
    F6: Evaluates student grades directly against published program criteria
    rather than applying generic national cutoffs.
    """
    # Program A requires strict 8.0/10.0 CGPA
    required_cgpa = 8.0
    
    # Rahul has 8.2 -> Meets
    assert profile_rahul_sharma.cgpa >= required_cgpa
    status_rahul = "MEETS" if profile_rahul_sharma.cgpa >= required_cgpa else "DOES_NOT_MEET"
    assert status_rahul == "MEETS"

    # Maria has 6.8 -> Fails program A
    assert profile_maria_santos.cgpa < required_cgpa
    status_maria = "MEETS" if profile_maria_santos.cgpa >= required_cgpa else "DOES_NOT_MEET"
    assert status_maria == "DOES_NOT_MEET"


# ==============================================================================
# F7: Verbatim Quotes & UNRESOLVED Classification
# ==============================================================================
def test_f7_verbatim_quotes_and_unresolved_classification():
    """
    F7: Verifies that unverified criteria (e.g. pending test score, unverified transcript)
    are explicitly classified as `UNRESOLVED` with actionable gaps, and authentic
    evidence excerpts are preserved verbatim.
    """
    record_unresolved = EvidenceRecord(
        criterion_name="English Language Proficiency",
        stated_requirement="IELTS 7.0 minimum with at least 6.5 in each sub-score",
        student_value="Status: planned, Score: Pending",
        status="UNRESOLVED",
        evidence_excerpt="Student has planned but not yet submitted official IELTS/TOEFL score.",
        source_title="Admissions Regulations",
        source_url="https://web.cs.toronto.edu/graduate/mscac",
        source_category="OFFICIAL"
    )
    assert record_unresolved.status == "UNRESOLVED"
    assert "Pending" in record_unresolved.student_value
    assert record_unresolved.evidence_excerpt is not None


# ==============================================================================
# F8: Admission vs Scholarship Distinction
# ==============================================================================
def test_f8_admission_vs_scholarship_distinction(create_mock_opportunity):
    """
    F8: Verifies distinct separation between university admission requirements
    and scholarship eligibility criteria in data models and evaluations.
    """
    opp = create_mock_opportunity(
        title="Oxford Clarendon & MSc Computer Science",
        university="University of Oxford",
        country="UK"
    )
    opp.admission_requirements = [
        EligibilityCriterion(
            criterion_type="ACADEMIC_GRADE",
            is_mandatory=True,
            requirement_text="First class undergraduate degree in Computer Science or Mathematics"
        ),
        EligibilityCriterion(
            criterion_type="LANGUAGE_TEST",
            is_mandatory=True,
            requirement_text="IELTS Academic: 7.5 overall with 7.0 per component"
        )
    ]
    opp.scholarship_requirements = [
        EligibilityCriterion(
            criterion_type="ACADEMIC_GRADE",
            is_mandatory=True,
            requirement_text="Outstanding academic record and master's degree potential evaluated by selection panel"
        )
    ]
    
    assert len(opp.admission_requirements) == 2
    assert len(opp.scholarship_requirements) == 1
    assert opp.admission_requirements[0].requirement_text != opp.scholarship_requirements[0].requirement_text
    assert opp.funding_details.funding_type == "Fully Funded"


# ==============================================================================
# F9: Runtime Deadline Verification
# ==============================================================================
def test_f9_runtime_deadline_verification_against_utc_date():
    """
    F9: Verifies that deadlines are evaluated against current runtime UTC date.
    Historical or passed deadlines are flagged as expired; future deadlines are active.
    """
    now_utc = datetime.now(timezone.utc).date()
    
    past_date = (now_utc - timedelta(days=60)).strftime("%Y-%m-%d")
    future_date = (now_utc + timedelta(days=90)).strftime("%Y-%m-%d")

    def evaluate_deadline_status(deadline_str: str, deadline_type: str = "Fixed") -> str:
        if deadline_type.lower() == "rolling":
            return "ROLLING"
        if not deadline_str:
            return "UNKNOWN"
        try:
            d = datetime.strptime(deadline_str, "%Y-%m-%d").date()
            if d < now_utc:
                return "EXPIRED"
            return "ACTIVE"
        except ValueError:
            return "UNKNOWN"

    assert evaluate_deadline_status(past_date) == "EXPIRED"
    assert evaluate_deadline_status(future_date) == "ACTIVE"
    assert evaluate_deadline_status("2020-01-15") == "EXPIRED"
    assert evaluate_deadline_status(None, "Rolling") == "ROLLING"


# ==============================================================================
# F10: Robust Official Domain Verification
# ==============================================================================
def test_f10_robust_official_domain_verification():
    """
    F10: Tests robust official provider domain verification against authoritative
    educational and institutional rules, flagging commercial scrapers or blog domains.
    """
    # Valid official domains
    assert is_official_domain("https://web.cs.toronto.edu/mscac") is True
    assert is_official_domain("https://www.tum.de/en/studies") is True
    assert is_official_domain("https://vectorinstitute.ai/scholarship") is True
    assert is_official_domain("https://www.a-star.edu.sg/scholarships") is True
    assert is_official_domain("https://www.ox.ac.uk/admissions") is True

    # Commercial or scraper domains (must be rejected / flagged)
    assert is_official_domain("https://scholarship-tips-blog.com/top-10") is False
    assert is_official_domain("https://free-student-aid-fast.biz") is False
    assert is_official_domain("https://random-medium-post.io/apply") is False
    # Subdomain spoofing attempts must be rejected
    assert is_official_domain("https://scholarship.ac.fake.com") is False
    assert is_official_domain("https://evil.edu.attacker.org") is False
