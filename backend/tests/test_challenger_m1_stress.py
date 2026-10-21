"""
Challenger M1 Stress & Empirical Adversarial Test Harness.
Adversarial stress-testing of Milestone M1 Grounded Discovery & Real Extraction:
- Hostile SSRF URL injection in discovery candidates
- High-volume URL deduplication and normalization
- Graceful degradation across all UrlRetrievalStatus enum codes
- Strict zero-dummy guarantee on missing API credentials
- AST verification across the entire backend/app/ directory
"""

import os
import ast
import pytest
from unittest.mock import AsyncMock, patch, MagicMock, PropertyMock
from google.genai import types

from app.models.profile import StudentProfile
from app.agents.research_eligibility import ResearchEligibilityAgent
from app.services.gemini_service import GeminiService, GeminiConfigurationError
from app.security.sanitizer import is_safe_url, normalize_url


# ==============================================================================
# Challenge 1: Hostile SSRF Injections into Live Discovery Pipeline
# ==============================================================================
@pytest.mark.asyncio
async def test_adversarial_ssrf_injection_filtered_by_discovery_pipeline():
    """
    Stress-tests execute_discovery_and_audit with hostile SSRF targets injected
    into both structured candidates and unstructured search sources.
    Asserts that NO unsafe URLs reach URL Context analysis or get persisted as opportunities.
    """
    agent = ResearchEligibilityAgent()
    profile = StudentProfile(
        full_name="Adversarial Challenger",
        cgpa=8.8,
        target_degree="Master of Science",
        target_field="Computer Science",
        target_countries=["Canada"]
    )

    malicious_inputs = [
        {"canonical_url": "http://127.0.0.1:8000/internal-api", "title": "SSRF Loopback"},
        {"canonical_url": "http://localhost:9090/keys", "title": "SSRF Localhost"},
        {"canonical_url": "http://169.254.169.254/latest/meta-data/", "title": "SSRF AWS Metadata"},
        {"canonical_url": "http://[::1]/root", "title": "SSRF IPv6 Loopback"},
        {"canonical_url": "http://10.0.0.5/admin", "title": "SSRF Private Subnet A"},
        {"canonical_url": "http://172.16.1.1/env", "title": "SSRF Private Subnet B"},
        {"canonical_url": "http://192.168.1.1/secret", "title": "SSRF Private Subnet C"},
        {"canonical_url": "file:///etc/shadow", "title": "Local File Read"},
        {"canonical_url": "javascript:alert(document.cookie)", "title": "XSS Script"},
        {"canonical_url": "ftp://anonymous@ftp.server.internal/", "title": "FTP Scheme"},
        {"canonical_url": "https://web.cs.toronto.edu/graduate/mscac", "title": "Legit Program", "university": "University of Toronto"}
    ]

    mock_discovery = {
        "success": True,
        "candidates": malicious_inputs,
        "sources": [
            {"url": "http://127.0.0.1:3000/metrics", "title": "Source SSRF 1"},
            {"url": "https://web.cs.toronto.edu/graduate/mscac", "title": "Legit Source"}
        ]
    }

    mock_analysis = {
        "success": True,
        "is_retrieval_successful": True,
        "retrieval_status": "URL_RETRIEVAL_STATUS_SUCCESS",
        "evidence_quality": "OFFICIAL",
        "admission_requirements": [
            {
                "criterion_name": "CGPA",
                "stated_requirement": "B+ average (8.0/10)",
                "student_value": "8.8",
                "status": "MEETS",
                "evidence_excerpt": "Minimum B+ required for admission",
                "source_url": "https://web.cs.toronto.edu/graduate/mscac"
            }
        ],
        "funding_details": {"funding_type": "Partial"},
        "official_source_urls": [
            "https://web.cs.toronto.edu/graduate/mscac",
            "http://127.0.0.1/leaked_internal_link"  # hostile link in extraction
        ]
    }

    analyzed_urls = []

    async def fake_analyze(urls, program_name, university, student_profile_summary):
        analyzed_urls.extend(urls)
        return mock_analysis

    with patch("app.agents.research_eligibility.gemini_service.ensure_available"):
        with patch("app.agents.research_eligibility.gemini_service.search_grounded_discovery", new=AsyncMock(return_value=mock_discovery)):
            with patch("app.agents.research_eligibility.gemini_service.analyze_url_and_extract_criteria", side_effect=fake_analyze):
                with patch("app.db.repository.repository.save_agent_event", new=AsyncMock()):
                    with patch("app.db.repository.repository.save_evidence_records", new=AsyncMock()):
                        opps = await agent.execute_discovery_and_audit(
                            run_id="test-adversarial-ssrf",
                            profile=profile,
                            research_round=1
                        )

    # Assert only safe URLs were passed to URL Context analysis
    assert len(analyzed_urls) == 1
    assert analyzed_urls[0] == "https://web.cs.toronto.edu/graduate/mscac"
    for malicious_candidate in malicious_inputs[:-1]:
        assert malicious_candidate["canonical_url"] not in analyzed_urls

    # Assert only legitimate opportunity was returned
    assert len(opps) == 1
    opp = opps[0]
    assert opp.canonical_url == "https://web.cs.toronto.edu/graduate/mscac"
    assert "127.0.0.1" not in opp.canonical_url
    assert "169.254.169.254" not in opp.canonical_url

    # Assert hostile link inside official_source_urls was filtered out by line 320
    assert not any("127.0.0.1" in u for u in opp.official_source_urls)


# ==============================================================================
# Challenge 2: Aggressive URL Deduplication & Normalization
# ==============================================================================
@pytest.mark.asyncio
async def test_aggressive_url_deduplication_and_normalization():
    """
    Asserts that variations of the same URL (casing, trailing slash, utm params, fragments)
    are collapsed into a single candidate, preventing redundant LLM calls.
    """
    agent = ResearchEligibilityAgent()
    profile = StudentProfile(
        full_name="Dedup Test",
        cgpa=9.0,
        target_degree="Master's",
        target_field="AI",
        target_countries=["Germany"]
    )

    duplicate_candidates = [
        {"canonical_url": "https://www.tum.de/en/studies/degree-programs/informatics", "title": "TUM 1"},
        {"canonical_url": "https://www.tum.de/en/studies/degree-programs/informatics/", "title": "TUM 2 (slash)"},
        {"canonical_url": "HTTPS://WWW.TUM.DE/en/studies/degree-programs/informatics", "title": "TUM 3 (upper)"},
        {"canonical_url": "https://www.tum.de/en/studies/degree-programs/informatics?utm_source=google&gclid=test", "title": "TUM 4 (tracking)"},
        {"canonical_url": "https://www.tum.de/en/studies/degree-programs/informatics#requirements", "title": "TUM 5 (fragment)"},
    ]

    mock_discovery = {"success": True, "candidates": duplicate_candidates, "sources": []}
    mock_analysis = {
        "success": True,
        "is_retrieval_successful": True,
        "retrieval_status": "URL_RETRIEVAL_STATUS_SUCCESS",
        "evidence_quality": "OFFICIAL",
        "admission_requirements": [],
        "funding_details": {},
        "official_source_urls": []
    }

    analyzed_calls = []

    async def fake_analyze(urls, program_name, university, student_profile_summary):
        analyzed_calls.append(urls)
        return mock_analysis

    with patch("app.agents.research_eligibility.gemini_service.ensure_available"):
        with patch("app.agents.research_eligibility.gemini_service.search_grounded_discovery", new=AsyncMock(return_value=mock_discovery)):
            with patch("app.agents.research_eligibility.gemini_service.analyze_url_and_extract_criteria", side_effect=fake_analyze):
                with patch("app.db.repository.repository.save_agent_event", new=AsyncMock()):
                    with patch("app.db.repository.repository.save_evidence_records", new=AsyncMock()):
                        opps = await agent.execute_discovery_and_audit(
                            run_id="test-dedup",
                            profile=profile,
                            research_round=1
                        )

    assert len(analyzed_calls) == 1, f"Expected 1 analysis call for deduplicated candidates, got {len(analyzed_calls)}"
    assert len(opps) == 1


# ==============================================================================
# Challenge 3: Degradation Across All UrlRetrievalStatus Enums
# ==============================================================================
@pytest.mark.parametrize("status_name,is_expected_success,expected_quality", [
    ("URL_RETRIEVAL_STATUS_SUCCESS", True, "OFFICIAL"),
    ("URL_RETRIEVAL_STATUS_PAYWALL", False, "UNVERIFIED"),
    ("URL_RETRIEVAL_STATUS_UNSAFE", False, "UNVERIFIED"),
    ("URL_RETRIEVAL_STATUS_ERROR", False, "UNVERIFIED"),
])
@pytest.mark.asyncio
async def test_graceful_degradation_across_all_retrieval_statuses(status_name, is_expected_success, expected_quality):
    """
    Asserts that non-successful retrieval statuses degrade gracefully to UNVERIFIED evidence
    and actionable gap warnings without crashing or synthesizing fake facts.
    """
    agent = ResearchEligibilityAgent()
    profile = StudentProfile(full_name="Enum Tester", cgpa=8.0, target_countries=["Canada"])

    mock_discovery = {
        "success": True,
        "candidates": [{"canonical_url": "https://test.edu/program", "title": "Test Program"}],
        "sources": []
    }

    mock_data = {
        "admission_requirements": [
            {
                "criterion_name": "Degree Prerequisite",
                "stated_requirement": "Bachelor in CS",
                "status": "MEETS" if is_expected_success else "UNRESOLVED",
                "evidence_excerpt": "Direct quote from portal" if is_expected_success else None,
                "source_url": "https://test.edu/program"
            }
        ],
        "funding_details": {"funding_type": "Unknown"},
        "overall_eligibility_status": "MEETS_STATED_CRITERIA" if is_expected_success else "INSUFFICIENT_EVIDENCE",
        "actionable_gaps": []
    }

    mock_analysis = {
        "success": True,
        "is_retrieval_successful": is_expected_success,
        "retrieval_status": status_name,
        "evidence_quality": expected_quality,
        "data": mock_data
    }

    with patch("app.agents.research_eligibility.gemini_service.ensure_available"):
        with patch("app.agents.research_eligibility.gemini_service.search_grounded_discovery", new=AsyncMock(return_value=mock_discovery)):
            with patch("app.agents.research_eligibility.gemini_service.analyze_url_and_extract_criteria", new=AsyncMock(return_value=mock_analysis)):
                with patch("app.db.repository.repository.save_agent_event", new=AsyncMock()):
                    with patch("app.db.repository.repository.save_evidence_records", new=AsyncMock()):
                        opps = await agent.execute_discovery_and_audit(
                            run_id=f"test-status-{status_name}",
                            profile=profile,
                            research_round=1
                        )

    assert len(opps) == 1
    opp = opps[0]
    if not is_expected_success:
        assert opp.eligibility_status == "INSUFFICIENT_EVIDENCE"
        assert any(status_name in gap for gap in opp.actionable_gaps)
        assert len(opp.evidence_records) >= 1
        assert opp.evidence_records[0].status == "UNRESOLVED"
        assert opp.evidence_records[0].evidence_excerpt is None
    else:
        assert opp.eligibility_status == "MEETS_STATED_CRITERIA"
        assert len(opp.evidence_records) >= 1
        assert opp.evidence_records[0].evidence_excerpt is not None


# ==============================================================================
# Challenge 4: Zero Dummy Guarantee on Missing API Key
# ==============================================================================
@pytest.mark.asyncio
async def test_missing_credentials_never_returns_canned_records():
    """
    Asserts that unconfigured credentials never produce fallback opportunity records.
    """
    agent = ResearchEligibilityAgent()
    profile = StudentProfile(full_name="No Key Tester", cgpa=8.0, target_countries=["Canada"])

    with patch.object(GeminiService, "is_available", new_callable=PropertyMock, return_value=False):
        with pytest.raises(GeminiConfigurationError):
            await agent.execute_discovery_and_audit("test-run", profile, 1)


# ==============================================================================
# Challenge 5: Static AST Assertion Across All Production Files
# ==============================================================================
def test_static_ast_zero_real_opportunities_base_in_backend_app():
    """
    Scans every Python file under backend/app/ via AST and text matching to guarantee
    zero occurrences of REAL_OPPORTUNITIES_BASE in production code.
    """
    backend_app_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app"))
    assert os.path.isdir(backend_app_dir)

    violations = []
    py_file_count = 0

    for root, _, files in os.walk(backend_app_dir):
        for f in files:
            if f.endswith(".py"):
                py_file_count += 1
                path = os.path.join(root, f)
                with open(path, "r", encoding="utf-8", errors="ignore") as fp:
                    content = fp.read()
                if "REAL_OPPORTUNITIES_BASE" in content:
                    violations.append(f"{path}: text match")
                
                tree = ast.parse(content, filename=path)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Name) and node.id == "REAL_OPPORTUNITIES_BASE":
                        violations.append(f"{path}:{node.lineno}: AST Name")
                    elif isinstance(node, ast.Constant) and "REAL_OPPORTUNITIES_BASE" in str(node.value):
                        violations.append(f"{path}:{node.lineno}: AST Constant")
                    elif isinstance(node, ast.Attribute) and node.attr == "REAL_OPPORTUNITIES_BASE":
                        violations.append(f"{path}:{node.lineno}: AST Attribute")

    assert py_file_count > 0, "No Python files found in backend/app!"
    assert len(violations) == 0, f"Found REAL_OPPORTUNITIES_BASE in production code: {violations}"
