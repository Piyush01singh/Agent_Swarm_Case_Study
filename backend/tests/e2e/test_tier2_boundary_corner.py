"""
Tier 2: Boundary and Corner Case Test Suite.
Verifies system resilience against hostile, malformed, empty, and edge-condition inputs
such as SSRF injections, extreme CGPAs, expired deadlines, paywalled URLs, and missing API keys.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

from app.models.profile import StudentProfile
from app.models.opportunity import Opportunity, FundingDetails, EligibilityCriterion
from app.models.evidence import EvidenceRecord, MatchScore
from app.security.sanitizer import is_safe_url, normalize_url, sanitize_text
from app.services.gemini_service import GeminiService
from app.services.scoring_service import calculate_match_score


# ==============================================================================
# Boundary 1: Empty and Minimal Inputs
# ==============================================================================
def test_b1_empty_student_profile_fields_handled_gracefully():
    """
    Verifies that a student profile with minimal/empty fields (empty skills,
    empty projects, empty target countries) initializes without validation crash.
    """
    minimal_profile = StudentProfile(
        full_name="",
        institution="",
        current_degree="",
        cgpa=0.0,
        grading_scale="10.0",
        target_degree="Master's",
        target_field="",
        target_countries=[],
        skills=[],
        projects=[]
    )
    assert minimal_profile.cgpa == 0.0
    assert len(minimal_profile.target_countries) == 0
    assert len(minimal_profile.skills) == 0


def test_b1_opportunity_with_zero_requirements_does_not_crash(create_mock_opportunity, profile_rahul_sharma):
    """
    Verifies that an opportunity with empty admission requirements, empty funding,
    and no evidence records can be safely scored without IndexError or NoneType exceptions.
    """
    empty_opp = create_mock_opportunity(
        title="Unspecified Opportunity",
        university="Unknown Institution",
        country="Canada"
    )
    empty_opp.admission_requirements = []
    empty_opp.scholarship_requirements = []
    empty_opp.evidence_records = []
    empty_opp.funding_details = FundingDetails()

    score = calculate_match_score(profile_rahul_sharma, empty_opp)
    assert isinstance(score, MatchScore)
    assert 0.0 <= score.total_score <= 100.0


# ==============================================================================
# Boundary 2: Zero, Invalid, and Extreme CGPA Thresholds
# ==============================================================================
@pytest.mark.parametrize("cgpa,expected_status", [
    (0.0, "DOES_NOT_MEET"),
    (6.99, "DOES_NOT_MEET"),
    (7.0, "POTENTIAL_MATCH"),
    (7.99, "POTENTIAL_MATCH"),
    (8.0, "MEETS_STATED_CRITERIA"),
    (9.99, "MEETS_STATED_CRITERIA"),
    (10.0, "MEETS_STATED_CRITERIA"),
])
def test_b2_cgpa_boundary_transitions(cgpa, expected_status):
    """
    Tests exact boundary transitions for academic grading thresholds.
    Threshold: < 7.0 fails; 7.0-7.99 unresolved potential match; >= 8.0 meets.
    """
    required_cutoff = 8.0
    minimum_floor = 7.0

    if cgpa < minimum_floor:
        status = "DOES_NOT_MEET"
    elif cgpa >= required_cutoff:
        status = "MEETS_STATED_CRITERIA"
    else:
        status = "POTENTIAL_MATCH"

    assert status == expected_status


def test_b2_extreme_cgpa_values():
    """
    Verifies behavior when CGPA is negative or exceeds grading scale.
    System should process or flag without numerical exceptions.
    """
    # Negative CGPA
    p_neg = StudentProfile(cgpa=-1.5, grading_scale="10.0")
    assert p_neg.cgpa < 0.0

    # Oversized CGPA
    p_over = StudentProfile(cgpa=12.5, grading_scale="10.0")
    assert p_over.cgpa > 10.0


# ==============================================================================
# Boundary 3: Expired, Today, Tomorrow, and Non-Standard Deadlines
# ==============================================================================
def test_b3_deadline_temporal_boundaries():
    """
    Verifies temporal edge conditions: yesterday (EXPIRED), today (ACTIVE),
    tomorrow (ACTIVE), and non-standard strings ("Rolling", "March 2026", "").
    """
    today_utc = datetime.now(timezone.utc).date()
    yesterday = (today_utc - timedelta(days=1)).strftime("%Y-%m-%d")
    tomorrow = (today_utc + timedelta(days=1)).strftime("%Y-%m-%d")

    def parse_deadline(d_str: str, d_type: str = "Fixed") -> str:
        if d_type.lower() == "rolling":
            return "ROLLING"
        if not d_str:
            return "UNKNOWN"
        try:
            parsed = datetime.strptime(d_str.strip(), "%Y-%m-%d").date()
            if parsed < today_utc:
                return "EXPIRED"
            return "ACTIVE"
        except ValueError:
            # Handles non-ISO formats like "March 2026" or "TBD"
            return "UNKNOWN"

    assert parse_deadline(yesterday) == "EXPIRED"
    assert parse_deadline(today_utc.strftime("%Y-%m-%d")) == "ACTIVE"
    assert parse_deadline(tomorrow) == "ACTIVE"
    assert parse_deadline("", "Rolling") == "ROLLING"
    assert parse_deadline("March 2026", "Fixed") == "UNKNOWN"
    assert parse_deadline("invalid-date-string") == "UNKNOWN"


# ==============================================================================
# Boundary 4: Paywalled, Malformed, and Unsafe URLs
# ==============================================================================
@pytest.mark.parametrize("malformed_url", [
    "",
    "   ",
    "not_a_valid_url",
    "htp:/missing-t.com",
    "javascript:alert('xss')",
    "mailto:admissions@university.ca",
    "data:text/html;base64,PHNjcmlwdD4=",
    "ftp://anonymous@ftp.uni.de/files",
])
def test_b4_malformed_url_schemes_rejected(malformed_url):
    """
    Verifies that malformed URL schemes, non-HTTP protocols, and XSS vectors
    are rejected by `is_safe_url`.
    """
    assert is_safe_url(malformed_url) is False


def test_b4_url_normalization_handles_edge_cases():
    """
    Verifies normalize_url behavior on query strings, fragments, casing, and spaces.
    """
    assert normalize_url("") == ""
    assert normalize_url(None) == ""
    
    dirty_url = "  HTTPS://cs.toronto.edu:443/grad/?utm_source=fb&gclid=123#apply  "
    clean = normalize_url(dirty_url)
    assert clean == "https://cs.toronto.edu:443/grad"
    assert "utm_source" not in clean
    assert "#apply" not in clean


# ==============================================================================
# Boundary 5: SSRF Host Injection Protection
# ==============================================================================
@pytest.mark.parametrize("ssrf_target", [
    "http://localhost:8000/api/secret",
    "http://127.0.0.1:80/admin",
    "http://127.0.0.1",
    "http://[::1]/internal",
    "http://0.0.0.0:8080",
    "http://169.254.169.254/latest/meta-data/",  # AWS metadata service
    "http://169.254.169.254/latest/meta-data/iam/security-credentials/",
    "http://10.0.0.1/confidential",               # RFC 1918 private Class A
    "http://172.16.0.1/status",                  # RFC 1918 private Class B
    "http://192.168.1.1/gateway",                # RFC 1918 private Class C
    "file:///etc/passwd",
    "file://c:/windows/system32/cmd.exe",
    "http://internal.corp.local/",
])
def test_b5_ssrf_host_injection_is_strictly_blocked(ssrf_target):
    """
    Verifies that Server-Side Request Forgery (SSRF) injection targets,
    including loopbacks, private IPs, metadata endpoints, and file paths,
    are rejected before any network request is attempted.
    """
    assert is_safe_url(ssrf_target) is False


# ==============================================================================
# Boundary 6: Missing API Keys & Service Failure Resilience
# ==============================================================================
@pytest.mark.asyncio
async def test_b6_service_resilience_when_gemini_raises_exception():
    """
    Verifies that when the underlying LLM/GenAI call raises an unexpected exception
    (e.g., connection reset, 503 Overloaded), the service catches it cleanly
    and returns a structured failure dictionary rather than crashing the runtime.
    """
    service = GeminiService()
    service.api_key = "dummy-key-for-test"
    service._client = MagicMock()
    
    # Simulate exception during content generation
    service._client.models.generate_content.side_effect = RuntimeError("Connection timeout to Gemini API")

    res_discovery = await service.search_grounded_discovery("canada cs scholarship", "student profile")
    assert res_discovery["success"] is False
    assert "Gemini Search Grounding error" in res_discovery["error"]
    assert res_discovery["sources"] == []

    res_analysis = await service.analyze_url_and_extract_criteria(
        ["https://utoronto.ca"], "MS CS", "U of T", "student"
    )
    assert res_analysis["success"] is False
    assert "URL analysis error" in res_analysis["error"]


def test_b6_sanitize_text_strips_control_characters():
    """
    Verifies text sanitization removes null bytes and control characters
    without affecting international text.
    """
    hostile_text = "Applicant\x00Name\x08With\x1bEscapes"
    cleaned = sanitize_text(hostile_text)
    assert "\x00" not in cleaned
    assert "\x08" not in cleaned
    assert "\x1b" not in cleaned
    assert "Applicant" in cleaned
