"""
Tier 5 White-Box Adversarial Stress Test Suite: Backend Discovery, Sanitization & Scoring.
Comprehensive empirical challenge verification covering:
1. Malformed URLs, SSRF/loopback injections, homograph/punycode spoofing, and subdomain tricks.
2. Edge-case CGPA values (negative, zero, >4.0 on 4.0 scale, boundary 2.99 vs 3.0 cutoffs, qualitative descriptions).
3. Runtime UTC deadline boundary values (intake today, yesterday, leap years, non-leap year Feb 29, ISO timestamps).
4. Admission vs. Scholarship criteria separation under mixed eligibility states.
5. Mocked URL retrieval failures (PAYWALL, ERROR, TIMEOUT, UNSAFE) and graceful degradation to UNRESOLVED.
6. Opportunity and EvidenceRecord serialization schemas and strict shortlist disqualifier invariants.
"""

import uuid
from datetime import datetime, timezone, date, timedelta
from typing import Dict, Any, List
from unittest.mock import AsyncMock, patch, MagicMock
import pytest
from google.genai import types

from app.security.sanitizer import is_safe_url, is_official_domain, normalize_url
from app.agents.research_eligibility import (
    ResearchEligibilityAgent,
    extract_numeric_cgpa_cutoff,
    extract_language_cutoff,
    evaluate_single_criterion,
)
from app.services.scoring_service import calculate_match_score
from app.models.profile import StudentProfile
from app.models.opportunity import Opportunity, FundingDetails, EligibilityCriterion
from app.models.evidence import EvidenceRecord, MatchScore


# ==============================================================================
# Suite 1: Malformed URLs, SSRF Injections, Homograph & Subdomain Spoofing
# ==============================================================================

class TestAdversarialUrlSanitization:
    """Stress-tests URL safety, SSRF rejection, and authoritative domain classification."""

    @pytest.mark.parametrize("hostile_url, expected_safe", [
        ("http://127.0.0.1", False),
        ("http://127.0.0.1:8080/admin", False),
        ("http://localhost", False),
        ("http://localhost:3000", False),
        ("http://169.254.169.254/latest/meta-data/", False),
        ("http://[::1]/", False),
        ("http://[::ffff:127.0.0.1]/", False),
        ("http://10.0.0.1/internal", False),
        ("http://172.16.0.1/conf", False),
        ("http://192.168.1.1/router", False),
        ("http://0.0.0.0", False),
        ("http://internal.service.local", False),
        ("http://cluster.internal", False),
        ("http://api.docker.localhost", False),
        ("ftp://utoronto.ca/dataset", False),
        ("file:///etc/passwd", False),
        ("javascript:alert(1)", False),
        ("data:text/html,<h1>PWNED</h1>", False),
        ("", False),
        (None, False),
    ])
    def test_ssrf_and_hostile_url_rejection(self, hostile_url, expected_safe):
        """Verifies that all loopback, link-local, private network, and non-http schemes are rejected."""
        assert is_safe_url(hostile_url) is expected_safe
        assert is_official_domain(hostile_url) is False

    @pytest.mark.parametrize("spoofed_url", [
        "https://evil.edu.attacker.org",
        "https://fake.ac.scam.net",
        "https://attacker.gov.scam.net",
        "https://scholarship.ac.fake.com",
        "https://phishing.ac.com",
        "https://utoronto.ca.attacker.com",
        "https://utoronto.ca.attacker.org",
        "https://utoronto.ca@evil.com",
        "https://attacker.com?utoronto.ca",
        "https://attacker.com#utoronto.ca",
        "https://xn--utoronto-v0a.ca",           # Punycode / IDN homograph attack
        "https://utoronto.ca%2eattacker.com",     # Percent-encoded dot
        "http://8.8.8.8/scholarships",            # Public raw IP without educational domain
        "https://attacker-ac.uk",                 # Hyphenated academic SLD exploit
        "https://scam-edu.in",                    # Hyphenated educational SLD exploit
        "https://phishing-gov.sg",                # Hyphenated government SLD exploit
    ])
    def test_domain_spoofing_and_subdomain_exploits_rejected(self, spoofed_url):
        """Verifies that deceptive subdomains, userinfo bypasses, punycode, raw IPs, and hyphenated SLDs are rejected."""
        assert is_official_domain(spoofed_url) is False

    @pytest.mark.parametrize("hyphenated_url", [
        "https://attacker-ac.uk",
        "https://scam-edu.in",
        "https://phishing-gov.sg",
    ])
    def test_hyphenated_domains_rejected(self, hyphenated_url):
        """Verifies that hyphenated domains mimicking academic/government SLDs are strictly rejected."""
        assert is_official_domain(hyphenated_url) is False

    @pytest.mark.parametrize("genuine_url", [
        "https://www.ox.ac.uk",
        "https://www.cam.ac.uk",
        "https://ox.ac.uk",
        "https://cam.ac.uk",
    ])
    def test_genuine_academic_subdomains_accepted(self, genuine_url):
        """Verifies that genuine academic subdomains are accepted with strict dot anchoring."""
        assert is_safe_url(genuine_url) is True
        assert is_official_domain(genuine_url) is True

    @pytest.mark.parametrize("legitimate_url", [
        "https://web.cs.toronto.edu/graduate/mscac",
        "https://cs.stanford.edu/admissions",
        "https://www.ox.ac.uk/admissions/graduate",
        "https://www.cam.ac.uk/apply",
        "https://www.tum.de/en/studies",
        "https://www.nus.edu.sg/programmes",
        "https://vectorinstitute.ai/scholarships",
        "https://www.canada.ca/en/services/benefits/education.html",
    ])
    def test_legitimate_official_domains_accepted(self, legitimate_url):
        """Verifies that genuine educational, government, and registry domains pass classification."""
        assert is_safe_url(legitimate_url) is True
        assert is_official_domain(legitimate_url) is True

    def test_url_normalization_cleans_tracking_and_fragments(self):
        """Verifies query parameter sanitization, fragment removal, and trailing slash normalization."""
        raw = "HTTPS://Web.CS.Toronto.Edu/Graduate/MScAC/?utm_source=google&utm_medium=cpc&id=123#requirements"
        normalized = normalize_url(raw)
        assert normalized == "https://web.cs.toronto.edu/graduate/mscac?id=123"
        assert "#" not in normalized
        assert "utm_source" not in normalized


# ==============================================================================
# Suite 2: Edge-Case CGPA & Language Criteria Matching
# ==============================================================================

class TestEdgeCaseEligibilityMatching:
    """Stress-tests criterion evaluation against extreme, boundary, and malformed inputs."""

    @pytest.mark.parametrize("req_text, expected_cutoff", [
        ("Minimum 3.0/4.0 CGPA", None),
        ("Minimum 3.5/4.0 GPA", None),
        ("Minimum 4.0/4.0 scale", None),
        ("Minimum 8.0/10 CGPA", 8.0),
        ("Minimum 3.2 CGPA", None),              # Standalone <= 4.0 without scale returns None (no invented 10 scale conversion)
        ("Minimum 7.8 CGPA", 7.8),              # Standalone > 4.0 preserved on 10 scale
        ("78% overall standing", None),          # Percentage without published equivalency returns None
        ("First class honours", None),           # Qualitative benchmark without published equivalency returns None
        ("First Class with Distinction", None),  # Qualitative benchmark without published equivalency returns None
        ("Second class upper", None),            # Qualitative benchmark without published equivalency returns None
        ("B+ average", None),                    # Qualitative benchmark without published equivalency returns None
        ("B average", None),                     # Qualitative benchmark without published equivalency returns None
        ("High standing evaluated case-by-case", None), # Unspecified threshold
        ("", None),
    ])
    def test_cgpa_cutoff_extraction_formats(self, req_text, expected_cutoff):
        """Empirically checks extraction and normalization across diverse international formats."""
        assert extract_numeric_cgpa_cutoff(req_text) == expected_cutoff

    def test_scale_mismatch_without_published_equivalency_resolves_unresolved(self):
        """Student on 10.0 scale evaluated against 4.0 requirement resolves UNRESOLVED without invented scaling."""
        profile = StudentProfile(
            full_name="Scale Mismatch Tester",
            cgpa=8.2,
            grading_scale="10.0",
            target_degree="Master of Science",
            target_field="Computer Science",
            target_countries=["Canada"]
        )
        crit = {"criterion_type": "ACADEMIC_GRADE", "stated_requirement": "Minimum 3.2/4.0 GPA in Computer Science"}
        res = evaluate_single_criterion(crit, profile, is_admission=True)
        assert res["status"] == "UNRESOLVED"
        assert res["actionable_gap"] is not None
        assert "Verify institutional grade conversion" in res["actionable_gap"]

    def test_boundary_cgpa_evaluation_exact_cutoff_meets(self):
        """Student with exactly 3.0/4.0 meets a 3.0/4.0 minimum entrance requirement."""
        profile = StudentProfile(
            full_name="Boundary Tester",
            cgpa=3.0,
            grading_scale="4.0",
            target_degree="Master of Science",
            target_field="Computer Science",
            target_countries=["Canada"]
        )
        crit = {"criterion_type": "ACADEMIC_GRADE", "stated_requirement": "Minimum 3.0/4.0 CGPA"}
        res = evaluate_single_criterion(crit, profile, is_admission=True)
        assert res["status"] == "MEETS"
        assert res["actionable_gap"] is None

    def test_boundary_cgpa_evaluation_below_cutoff_fails(self):
        """Student with 2.99/4.0 fails a 3.0/4.0 cutoff and receives an actionable gap."""
        profile = StudentProfile(
            full_name="Marginal Fail",
            cgpa=2.99,
            grading_scale="4.0",
            target_degree="Master of Science",
            target_field="Computer Science",
            target_countries=["Canada"]
        )
        crit = {"criterion_type": "ACADEMIC_GRADE", "stated_requirement": "Minimum 3.0/4.0 CGPA"}
        res = evaluate_single_criterion(crit, profile, is_admission=True)
        assert res["status"] == "DOES_NOT_MEET"
        assert res["actionable_gap"] is not None
        assert "below the program minimum" in res["actionable_gap"]

    def test_negative_cgpa_handled_as_failure(self):
        """Negative CGPA value is gracefully evaluated and classified as DOES_NOT_MEET without crashing."""
        profile = StudentProfile(
            full_name="Negative CGPA",
            cgpa=-1.0,
            grading_scale="10.0",
            target_degree="Master of Science",
            target_field="Computer Science",
            target_countries=["Canada"]
        )
        crit = {"criterion_type": "ACADEMIC_GRADE", "stated_requirement": "Minimum 7.5 CGPA"}
        res = evaluate_single_criterion(crit, profile, is_admission=True)
        assert res["status"] == "DOES_NOT_MEET"
        assert "below the program minimum" in res["actionable_gap"]

    def test_cgpa_exceeding_four_on_four_scale_normalizes_cleanly(self):
        """Honors CGPA > 4.0 (e.g. 4.5/4.0 AP/weighted) normalizes (>10.0) and meets requirements."""
        profile = StudentProfile(
            full_name="Weighted Scale",
            cgpa=4.5,
            grading_scale="4.0",
            target_degree="Master of Science",
            target_field="Computer Science",
            target_countries=["Canada"]
        )
        crit = {"criterion_type": "ACADEMIC_GRADE", "stated_requirement": "Minimum 3.5/4.0 CGPA"}
        res = evaluate_single_criterion(crit, profile, is_admission=True)
        assert res["status"] == "MEETS"

    def test_pending_language_score_marked_unresolved(self):
        """Language score with planned status or None score produces UNRESOLVED and actionable gap."""
        profile = StudentProfile(
            full_name="Language Pending",
            cgpa=8.5,
            language_tests={"test": "IELTS", "score": None, "status": "planned"}
        )
        crit = {"criterion_type": "LANGUAGE_TEST", "stated_requirement": "IELTS Academic minimum 7.0"}
        res = evaluate_single_criterion(crit, profile, is_admission=True)
        assert res["status"] == "UNRESOLVED"
        assert "planned but not yet submitted" in res["uncertainty_or_conflict"]
        assert "Submit official IELTS score" in res["actionable_gap"]

    def test_synthetic_fstring_quotes_stripped_to_none(self):
        """Feature F7: Any synthesized f-string quote matching banned fake markers is discarded to None."""
        profile = StudentProfile(cgpa=8.5)
        crit = {
            "criterion_type": "ACADEMIC_GRADE",
            "stated_requirement": "Minimum 8.0 CGPA",
            "evidence_excerpt": "Student's 8.5/10.0 CGPA meets B+ average requirement."
        }
        res = evaluate_single_criterion(crit, profile, is_admission=True)
        assert res["evidence_excerpt"] is None


# ==============================================================================
# Suite 3: Runtime Deadline Boundary Values & ISO Variations
# ==============================================================================

class TestRuntimeDeadlineBoundaries:
    """Stress-tests deadline status evaluation and scoring behavior under temporal boundaries."""

    @pytest.fixture
    def student_profile(self):
        return StudentProfile(
            full_name="Deadline Tester",
            cgpa=8.8,
            grading_scale="10.0",
            target_degree="Master of Science",
            target_field="Computer Science",
            target_countries=["Canada"]
        )

    def _build_opp_with_deadline(self, deadline: str, deadline_type: str = "Fixed") -> Opportunity:
        return Opportunity(
            id=str(uuid.uuid4()),
            run_id="run-deadline-test",
            canonical_url="https://utoronto.ca/cs/apply",
            title="MSc Computer Science - UofT",
            program_name="MSc Computer Science",
            university="University of Toronto",
            country="Canada",
            funding_details=FundingDetails(funding_type="Fully Funded", tuition_covered=True),
            deadline=deadline,
            deadline_type=deadline_type,
            deadline_verified=True,
            evidence_quality="OFFICIAL",
            eligibility_status="MEETS_STATED_CRITERIA"
        )

    def test_deadline_exactly_today_is_active_and_eligible(self, student_profile):
        """Intake with deadline equal to runtime UTC date is ACTIVE and eligible for shortlist."""
        ref_date = date(2026, 10, 21)
        opp = self._build_opp_with_deadline(deadline="2026-10-21")
        score = calculate_match_score(student_profile, opp, as_of_date=ref_date)

        assert opp.deadline_status == "ACTIVE"
        assert score.deadline_fit == 10.0
        assert score.is_eligible_for_shortlist is True

    def test_deadline_yesterday_is_expired_and_disqualified(self, student_profile):
        """Intake with deadline prior to runtime UTC date is EXPIRED, receives 0 deadline points, and disqualified."""
        ref_date = date(2026, 10, 21)
        opp = self._build_opp_with_deadline(deadline="2026-10-20")
        score = calculate_match_score(student_profile, opp, as_of_date=ref_date)

        assert opp.deadline_status == "EXPIRED"
        assert score.deadline_fit == 0.0
        assert score.is_eligible_for_shortlist is False
        assert "Application deadline has passed (EXPIRED)" in score.explanation

    def test_leap_year_february_29_valid_and_active(self, student_profile):
        """Valid leap year date 2028-02-29 is parsed correctly as ACTIVE when evaluated prior."""
        ref_date = date(2028, 2, 1)
        opp = self._build_opp_with_deadline(deadline="2028-02-29")
        score = calculate_match_score(student_profile, opp, as_of_date=ref_date)

        assert opp.deadline_status == "ACTIVE"
        assert score.deadline_fit == 10.0
        assert score.is_eligible_for_shortlist is True

    def test_non_leap_year_february_29_handled_gracefully_as_unknown(self, student_profile):
        """Invalid date (2026-02-29) does not raise ValueError; defaults gracefully to UNKNOWN."""
        ref_date = date(2026, 1, 15)
        opp = self._build_opp_with_deadline(deadline="2026-02-29")
        score = calculate_match_score(student_profile, opp, as_of_date=ref_date)

        assert opp.deadline_status == "UNKNOWN"
        assert score.deadline_fit == 2.0
        assert score.is_eligible_for_shortlist is True

    def test_iso_timestamp_with_time_component_handled_gracefully(self, student_profile):
        """Non-YYYY-MM-DD ISO format (e.g. 2026-12-31T23:59:59Z) does not crash; defaults to UNKNOWN."""
        ref_date = date(2026, 10, 21)
        opp = self._build_opp_with_deadline(deadline="2026-12-31T23:59:59Z")
        score = calculate_match_score(student_profile, opp, as_of_date=ref_date)

        assert opp.deadline_status == "UNKNOWN"
        assert score.deadline_fit == 2.0

    def test_rolling_deadline_awarded_maximum_verified_score(self, student_profile):
        """Verified rolling deadline is classified as ROLLING and awarded 10.0 deadline fit."""
        opp = self._build_opp_with_deadline(deadline="Rolling", deadline_type="Rolling")
        score = calculate_match_score(student_profile, opp)

        assert opp.deadline_status == "ROLLING"
        assert score.deadline_fit == 10.0
        assert score.is_eligible_for_shortlist is True


# ==============================================================================
# Suite 4: Admission vs. Scholarship Separation Under Mixed Eligibility
# ==============================================================================

class TestAdmissionVsScholarshipCriteriaSeparation:
    """Feature F8: Stress-tests separate evaluation of admission prerequisites vs. scholarship rules."""

    @pytest.fixture
    def candidate_factory(self):
        def _factory(admission_status: str, scholarship_status: str, overall_status: str) -> Opportunity:
            opp_id = str(uuid.uuid4())
            return Opportunity(
                id=opp_id,
                run_id="run-mixed-test",
                canonical_url="https://cs.ox.ac.uk/msc",
                title="MSc Computer Science - University of Oxford",
                program_name="MSc Computer Science",
                university="University of Oxford",
                country="UK",
                funding_details=FundingDetails(funding_type="Fully Funded", tuition_covered=True),
                deadline="2027-01-15",
                deadline_type="Fixed",
                deadline_verified=True,
                deadline_status="ACTIVE",
                evidence_quality="OFFICIAL",
                eligibility_status=overall_status,
                admission_requirements=[
                    EligibilityCriterion(
                        criterion_type="ACADEMIC_GRADE",
                        is_mandatory=True,
                        requirement_text="First class undergraduate degree in CS (Minimum 8.0/10 CGPA)"
                    )
                ],
                scholarship_requirements=[
                    EligibilityCriterion(
                        criterion_type="SCHOLARSHIP_CRITERION",
                        is_mandatory=False,
                        requirement_text="Clarendon Fund Scholarship: Top 5% academic ranking in graduating cohort"
                    )
                ],
                evidence_records=[
                    EvidenceRecord(
                        id=str(uuid.uuid4()),
                        opportunity_id=opp_id,
                        run_id="run-mixed-test",
                        criterion_name="Academic Grade / CGPA",
                        stated_requirement="First class undergraduate degree in CS (Minimum 8.0/10 CGPA)",
                        student_value="8.8 / 10.0",
                        status=admission_status,
                        source_url="https://cs.ox.ac.uk"
                    ),
                    EvidenceRecord(
                        id=str(uuid.uuid4()),
                        opportunity_id=opp_id,
                        run_id="run-mixed-test",
                        criterion_name="Clarendon Fund Scholarship Award",
                        stated_requirement="Clarendon Fund Scholarship: Top 5% academic ranking",
                        student_value="Top 10% cohort standing",
                        status=scholarship_status,
                        source_url="https://ox.ac.uk/clarendon"
                    )
                ]
            )
        return _factory

    def test_mandatory_admission_failure_zeros_academic_fit_and_disqualifies(self, candidate_factory):
        """Unmet mandatory admission prerequisite zeros academic fit (0.0) and hard-disqualifies candidate."""
        profile = StudentProfile(cgpa=7.0, target_degree="Master of Science", target_field="Computer Science")
        opp = candidate_factory(
            admission_status="DOES_NOT_MEET",
            scholarship_status="MEETS",
            overall_status="DOES_NOT_MEET"
        )
        score = calculate_match_score(profile, opp)

        assert score.academic_fit == 0.0
        assert score.is_eligible_for_shortlist is False
        assert "Disqualified from shortlist" in score.explanation

    def test_admission_meets_and_scholarship_fails_remains_eligible(self, candidate_factory):
        """Failing an optional/competitive scholarship does NOT disqualify from program shortlist."""
        profile = StudentProfile(cgpa=8.8, target_degree="Master of Science", target_field="Computer Science")
        opp = candidate_factory(
            admission_status="MEETS",
            scholarship_status="DOES_NOT_MEET",
            overall_status="POTENTIAL_MATCH"
        )
        score = calculate_match_score(profile, opp)

        assert score.academic_fit >= 25.0
        assert score.is_eligible_for_shortlist is True

    def test_admission_meets_and_scholarship_unresolved_remains_eligible(self, candidate_factory):
        """Unresolved scholarship criteria preserves eligibility as POTENTIAL_MATCH."""
        profile = StudentProfile(cgpa=8.8, target_degree="Master of Science", target_field="Computer Science")
        opp = candidate_factory(
            admission_status="MEETS",
            scholarship_status="UNRESOLVED",
            overall_status="POTENTIAL_MATCH"
        )
        score = calculate_match_score(profile, opp)

        assert score.academic_fit >= 25.0
        assert score.is_eligible_for_shortlist is True

    def test_both_admission_and_scholarship_meet_awards_maximum_academic_score(self, candidate_factory):
        """Full compliance across admission and scholarship criteria awards maximum 35.0 academic fit."""
        profile = StudentProfile(cgpa=9.5, target_degree="Master of Science", target_field="Computer Science")
        opp = candidate_factory(
            admission_status="MEETS",
            scholarship_status="MEETS",
            overall_status="MEETS_STATED_CRITERIA"
        )
        score = calculate_match_score(profile, opp)

        assert score.academic_fit == 35.0
        assert score.is_eligible_for_shortlist is True


# ==============================================================================
# Suite 5: Mocked URL Retrieval Failures (PAYWALL, ERROR, TIMEOUT, UNSAFE)
# ==============================================================================

class TestUrlRetrievalFailureResilience:
    """Stress-tests the discovery and extraction pipeline when URL context retrieval fails."""

    @pytest.fixture
    def student_profile(self):
        return StudentProfile(
            full_name="Fault Recovery Tester",
            cgpa=8.5,
            grading_scale="10.0",
            target_degree="Master of Science",
            target_field="Artificial Intelligence",
            target_countries=["Germany"]
        )

    @pytest.mark.asyncio
    @pytest.mark.parametrize("status_enum, status_name", [
        (types.UrlRetrievalStatus.URL_RETRIEVAL_STATUS_PAYWALL, "URL_RETRIEVAL_STATUS_PAYWALL"),
        (types.UrlRetrievalStatus.URL_RETRIEVAL_STATUS_ERROR, "URL_RETRIEVAL_STATUS_ERROR"),
        (types.UrlRetrievalStatus.URL_RETRIEVAL_STATUS_UNSAFE, "URL_RETRIEVAL_STATUS_UNSAFE"),
    ])
    async def test_retrieval_status_failure_degrades_to_unresolved(
        self,
        student_profile,
        status_enum,
        status_name
    ):
        """
        Feature F4 & F7: When official portal retrieval returns PAYWALL, ERROR, or UNSAFE,
        the agent does NOT fabricate quotes, sets evidence_quality to UNVERIFIED,
        and marks criteria UNRESOLVED with manual verification gaps.
        """
        agent = ResearchEligibilityAgent()

        mock_discovery = {
            "success": True,
            "candidates": [
                {
                    "canonical_url": "https://tum.de/in/msc-ai",
                    "program_name": "MSc AI",
                    "university": "Technical University of Munich",
                    "country": "Germany"
                }
            ],
            "sources": []
        }

        # Simulated response from Gemini where URL Context tool reported failure
        mock_extraction = {
            "success": True,
            "is_retrieval_successful": False,
            "retrieval_status": status_name,
            "evidence_quality": "UNVERIFIED",
            "data": {
                "program_name": "MSc AI",
                "university": "Technical University of Munich",
                "country": "Germany",
                "deadline": "2027-05-31",
                "deadline_type": "Fixed"
            }
        }

        with patch("app.agents.research_eligibility.gemini_service.ensure_available"):
            with patch("app.agents.research_eligibility.gemini_service.search_grounded_discovery", new=AsyncMock(return_value=mock_discovery)):
                with patch("app.agents.research_eligibility.gemini_service.analyze_url_and_extract_criteria", new=AsyncMock(return_value=mock_extraction)):
                    with patch("app.db.repository.repository.save_agent_event", new=AsyncMock()):
                        with patch("app.db.repository.repository.save_evidence_records", new=AsyncMock()):
                            opps = await agent.execute_discovery_and_audit(
                                run_id="test-run-fault",
                                profile=student_profile
                            )

        assert len(opps) == 1
        opp = opps[0]
        assert opp.evidence_quality == "UNVERIFIED"
        assert opp.eligibility_status == "INSUFFICIENT_EVIDENCE"
        assert len(opp.evidence_records) >= 1
        ev = opp.evidence_records[0]
        assert ev.status == "UNRESOLVED"
        assert ev.evidence_excerpt is None
        assert "cannot be verified" in ev.uncertainty_or_conflict
        assert any("verify requirements manually" in gap for gap in opp.actionable_gaps)

    @pytest.mark.asyncio
    async def test_extraction_timeout_or_network_exception_does_not_crash_pipeline(self, student_profile):
        """Network timeout/exception during URL analysis is caught, logged, and does not crash the agent."""
        agent = ResearchEligibilityAgent()

        mock_discovery = {
            "success": True,
            "candidates": [
                {"canonical_url": "https://tum.de/failing", "title": "TUM Timeout", "university": "TUM"},
                {"canonical_url": "https://lmu.de/working", "title": "LMU Working", "university": "LMU"}
            ],
            "sources": []
        }

        call_count = 0
        async def mock_analyze(urls, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise TimeoutError("Network connection to Gemini URL Context timed out.")
            return {
                "success": True,
                "is_retrieval_successful": True,
                "retrieval_status": "URL_RETRIEVAL_STATUS_SUCCESS",
                "evidence_quality": "OFFICIAL",
                "data": {
                    "program_name": "MSc Data Science",
                    "university": "LMU Munich",
                    "country": "Germany",
                    "admission_requirements": [
                        {"criterion_type": "ACADEMIC_GRADE", "stated_requirement": "Minimum 7.5 CGPA"}
                    ]
                }
            }

        with patch("app.agents.research_eligibility.gemini_service.ensure_available"):
            with patch("app.agents.research_eligibility.gemini_service.search_grounded_discovery", new=AsyncMock(return_value=mock_discovery)):
                with patch("app.agents.research_eligibility.gemini_service.analyze_url_and_extract_criteria", side_effect=mock_analyze):
                    with patch("app.db.repository.repository.save_agent_event", new=AsyncMock()):
                        with patch("app.db.repository.repository.save_evidence_records", new=AsyncMock()):
                            opps = await agent.execute_discovery_and_audit(
                                run_id="test-run-timeout",
                                profile=student_profile
                            )

        # First candidate failed gracefully; second candidate successfully extracted
        assert len(opps) == 1
        assert opps[0].university == "LMU Munich"


# ==============================================================================
# Suite 6: Serialization, Schema Conformance & Shortlist Invariants
# ==============================================================================

class TestOpportunitySerializationAndInvariants:
    """Verifies Pydantic schema serialization, deadline_status fields, and hard invariants."""

    def test_opportunity_model_serialization_includes_deadline_status(self):
        """Opportunity model serialization contains deadline_status, evidence_records, and funding_details."""
        now_dt = datetime.now(timezone.utc)
        opp = Opportunity(
            id="test-serial-1",
            run_id="run-serial",
            canonical_url="https://utoronto.ca/cs",
            title="MSc Computer Science",
            program_name="MSc Computer Science",
            university="University of Toronto",
            country="Canada",
            deadline="2027-01-15",
            deadline_status="ACTIVE",
            created_at=now_dt
        )
        data = opp.model_dump()
        assert data["deadline_status"] == "ACTIVE"
        assert "evidence_records" in data
        assert "funding_details" in data

        json_str = opp.model_dump_json()
        assert '"deadline_status":"ACTIVE"' in json_str

    def test_invariant_disqualified_if_expired_regardless_of_academic_excellence(self):
        """Strict Invariant: Even with a perfect 35.0 academic score, an EXPIRED deadline hard-disqualifies."""
        profile = StudentProfile(cgpa=10.0, grading_scale="10.0", target_degree="Master of Science", target_field="CS")
        opp = Opportunity(
            id="test-inv-expired",
            run_id="run-inv",
            canonical_url="https://stanford.edu/cs",
            title="Stanford Fellowship",
            program_name="MSc CS",
            university="Stanford University",
            country="USA",
            deadline="2020-01-01",
            deadline_status="EXPIRED",
            funding_details=FundingDetails(funding_type="Fully Funded", tuition_covered=True),
            eligibility_status="MEETS_STATED_CRITERIA"
        )
        score = calculate_match_score(profile, opp)
        assert score.is_eligible_for_shortlist is False
        assert score.deadline_fit == 0.0

    def test_invariant_disqualified_if_admission_fails_regardless_of_active_deadline(self):
        """Strict Invariant: Even with an ACTIVE deadline and full funding, unmet admission hard-disqualifies."""
        profile = StudentProfile(cgpa=5.0, grading_scale="10.0", target_degree="Master of Science", target_field="CS")
        opp = Opportunity(
            id="test-inv-fail",
            run_id="run-inv",
            canonical_url="https://mit.edu/cs",
            title="MIT AI Program",
            program_name="MSc AI",
            university="MIT",
            country="USA",
            deadline="2027-01-01",
            deadline_status="ACTIVE",
            funding_details=FundingDetails(funding_type="Fully Funded", tuition_covered=True),
            eligibility_status="DOES_NOT_MEET"
        )
        score = calculate_match_score(profile, opp)
        assert score.is_eligible_for_shortlist is False
        assert score.academic_fit == 0.0
