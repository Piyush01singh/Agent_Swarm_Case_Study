"""
Unit and Contract Test Suite for Milestone M2:
Strict Eligibility & Domain/Deadline Verification (Features F6, F7, F8, F9, F10).

Verifies:
- F6: Program-Specific Criteria Matching (eliminates generic country-level CGPA heuristics)
- F7: Verbatim Quotes & UNRESOLVED Classification (authentic quotes, explicit uncertainty notes & actionable gaps)
- F8: Admission vs Scholarship Distinction (separate models, mandatory admission checks before ranking)
- F9: Runtime Deadline Verification (compares deadlines against datetime.now(timezone.utc).date())
- F10: Robust Official Domain Verification (parsed hostname validation against authoritative policy & registry)
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

from app.models.profile import StudentProfile
from app.models.opportunity import Opportunity, FundingDetails, EligibilityCriterion
from app.models.evidence import EvidenceRecord, MatchScore
from app.agents.research_eligibility import (
    ResearchEligibilityAgent,
    extract_numeric_cgpa_cutoff,
    extract_language_cutoff,
    evaluate_single_criterion,
)
from app.agents.quality_reviewer import QualityReviewerAgent
from app.services.scoring_service import calculate_match_score
from app.security.sanitizer import (
    is_official_domain,
    is_safe_url,
    APPROVED_OFFICIAL_REGISTRY,
    OFFICIAL_TLD_SUFFIXES,
    OFFICIAL_ACADEMIC_PARTS,
)


# ==============================================================================
# Feature F6: Program-Specific Criteria Matching
# ==============================================================================

def test_f6_extract_numeric_cgpa_cutoff_various_formats():
    """F6 & R3: Tests numeric CGPA extraction across diverse university requirement formats without ungrounded scaling."""
    assert extract_numeric_cgpa_cutoff("Minimum 8.0/10.0 CGPA from recognized Indian institutions") == 8.0
    assert extract_numeric_cgpa_cutoff("Minimum 3.2/4.0 GPA in Computer Science") is None  # ungrounded scale without published 10-point equivalency
    assert extract_numeric_cgpa_cutoff("Applicant must hold a minimum 7.5 CGPA") == 7.5
    assert extract_numeric_cgpa_cutoff("Requires First Class with Distinction (typically 8.0/10)") == 8.0
    assert extract_numeric_cgpa_cutoff("Requires Second Upper Class Honours / B+ average") is None  # ungrounded qualitative mapping returns None
    assert extract_numeric_cgpa_cutoff("Minimum B average (7.0/10) required") == 7.0
    assert extract_numeric_cgpa_cutoff("Holistic assessment based on portfolio and statement") is None


def test_f6_program_specific_criteria_matching_rahul_meets_and_fails():
    """
    F6: Rahul Sharma (CGPA 8.2/10) evaluated directly against specific program cutoffs.
    - Meets Program requiring 8.0 CGPA
    - Fails Program requiring strict 8.5 CGPA
    """
    rahul = StudentProfile(
        full_name="Rahul Sharma",
        current_degree="B.Tech Computer Science",
        institution="Punjab Technical University",
        cgpa=8.2,
        grading_scale="10.0",
        target_degree="Master's",
        target_field="Computer Science"
    )

    # Program A: Cutoff 8.0
    crit_a = {
        "criterion_name": "Academic CGPA",
        "criterion_type": "ACADEMIC_GRADE",
        "stated_requirement": "Minimum 8.0/10.0 CGPA required for international applicants",
        "evidence_excerpt": "Minimum 8.0/10.0 CGPA required for international applicants."
    }
    eval_a = evaluate_single_criterion(crit_a, rahul, is_admission=True)
    assert eval_a["status"] == "MEETS"
    assert eval_a["actionable_gap"] is None

    # Program B: Strict Cutoff 8.5
    crit_b = {
        "criterion_name": "Academic CGPA",
        "criterion_type": "ACADEMIC_GRADE",
        "stated_requirement": "Strict minimum 8.5/10.0 CGPA required for competitive admission",
        "evidence_excerpt": "Strict minimum 8.5/10.0 CGPA required for competitive admission."
    }
    eval_b = evaluate_single_criterion(crit_b, rahul, is_admission=True)
    assert eval_b["status"] == "DOES_NOT_MEET"
    assert "below the program minimum" in eval_b["actionable_gap"]


def test_f6_no_generic_country_assumptions_two_canadian_programs():
    """
    F6: Demonstrates elimination of generic country-level assumptions.
    Two Canadian programs evaluate the same student differently based on published criteria,
    rather than treating all Canadian universities as having a universal threshold.
    """
    student = StudentProfile(
        full_name="Applicant",
        current_degree="B.Sc Computing",
        institution="University",
        cgpa=7.8,
        grading_scale="10.0",
        target_degree="Master's",
        target_field="Computer Science"
    )

    # University of Toronto cutoff: 8.0
    uoft_crit = {
        "stated_requirement": "B+ average in final year (equivalent to 8.0/10 from Indian universities)",
        "criterion_type": "ACADEMIC_GRADE"
    }
    # University of Calgary cutoff: 7.5
    ucalgary_crit = {
        "stated_requirement": "Minimum 7.5/10 CGPA or 3.0/4.0 GPA for MSc entrance",
        "criterion_type": "ACADEMIC_GRADE"
    }

    eval_uoft = evaluate_single_criterion(uoft_crit, student, is_admission=True)
    eval_ucalgary = evaluate_single_criterion(ucalgary_crit, student, is_admission=True)

    # 7.8 fails Toronto (8.0) but satisfies Calgary (7.5) within the SAME country
    assert eval_uoft["status"] == "DOES_NOT_MEET"
    assert eval_ucalgary["status"] == "MEETS"


def test_f6_language_criteria_matching_specific_cutoffs():
    """F6: Evaluates student language scores directly against specific published thresholds."""
    # Student with IELTS 7.0
    student_ielts_7 = StudentProfile(
        cgpa=8.0,
        language_tests={"test": "IELTS", "score": 7.0, "status": "taken"}
    )

    # Program requiring IELTS 6.5 (e.g. McGill)
    crit_6_5 = {
        "stated_requirement": "Minimum IELTS score of 6.5 overall",
        "criterion_type": "LANGUAGE_TEST"
    }
    # Program requiring IELTS 7.5 (e.g. Waterloo)
    crit_7_5 = {
        "stated_requirement": "Minimum IELTS score of 7.5 overall with 7.0 writing",
        "criterion_type": "LANGUAGE_TEST"
    }

    res_6_5 = evaluate_single_criterion(crit_6_5, student_ielts_7, is_admission=True)
    res_7_5 = evaluate_single_criterion(crit_7_5, student_ielts_7, is_admission=True)

    assert res_6_5["status"] == "MEETS"
    assert res_7_5["status"] == "DOES_NOT_MEET"
    assert "below program minimum cutoff" in res_7_5["actionable_gap"]


def test_f6_degree_prerequisites_matching_phd_requires_masters():
    """F6: Verifies curricular/degree prerequisite checks (PhD requiring Master's rejects Bachelor's)."""
    bachelor_student = StudentProfile(
        full_name="Student",
        current_degree="B.Tech Computer Science",
        cgpa=8.5,
        target_degree="PhD"
    )

    phd_crit = {
        "criterion_type": "DEGREE_LEVEL",
        "stated_requirement": "Direct doctoral admission requires a completed Master's degree in Computer Science."
    }
    eval_phd = evaluate_single_criterion(phd_crit, bachelor_student, is_admission=True)
    assert eval_phd["status"] == "DOES_NOT_MEET"
    assert "Program requires completed Master's degree" in eval_phd["actionable_gap"]


# ==============================================================================
# Feature F7: Verbatim Quotes & UNRESOLVED Classification
# ==============================================================================

def test_f7_verbatim_quotes_preserved_and_synthetic_quotes_purged():
    """
    F7: Verifies that authentic quotes are preserved verbatim,
    and synthetic template strings ('satisfies German', 'meets B+') are discarded.
    """
    authentic_quote = "Applicants must achieve a minimum cumulative grade point average of 8.0 out of 10.0."
    crit_authentic = {
        "criterion_type": "ACADEMIC_GRADE",
        "stated_requirement": "Minimum 8.0 CGPA",
        "evidence_excerpt": authentic_quote
    }
    profile = StudentProfile(cgpa=8.2)
    eval_auth = evaluate_single_criterion(crit_authentic, profile, is_admission=True)
    assert eval_auth["evidence_excerpt"] == authentic_quote

    # Synthetic quote attempt
    crit_synthetic = {
        "criterion_type": "ACADEMIC_GRADE",
        "stated_requirement": "Minimum 7.5 CGPA",
        "evidence_excerpt": "Student's 8.2/10.0 CGPA satisfies German 2.0 conversion threshold."
    }
    eval_synth = evaluate_single_criterion(crit_synthetic, profile, is_admission=True)
    # Synthetic f-string quote must be stripped to None
    assert eval_synth["evidence_excerpt"] is None


def test_f7_pending_language_test_marked_unresolved_with_actionable_gap():
    """
    F7: Verifies that planned or pending language test scores are explicitly
    classified as UNRESOLVED with clear uncertainty notes and actionable gaps.
    """
    student_pending_lang = StudentProfile(
        full_name="Rahul Sharma",
        cgpa=8.2,
        language_tests={"test": "IELTS", "score": None, "status": "planned"}
    )
    crit = {
        "criterion_type": "LANGUAGE_TEST",
        "stated_requirement": "IELTS Academic 7.0 minimum overall"
    }

    eval_res = evaluate_single_criterion(crit, student_pending_lang, is_admission=True)
    assert eval_res["status"] == "UNRESOLVED"
    assert "Pending" in eval_res["student_value"]
    assert eval_res["uncertainty_or_conflict"] is not None
    assert "planned but not yet submitted" in eval_res["uncertainty_or_conflict"]
    assert eval_res["actionable_gap"] is not None
    assert "Submit official IELTS score" in eval_res["actionable_gap"]


def test_f7_ambiguous_criteria_marked_unresolved():
    """F7: Verifies that qualitative criteria without documented conversion tables are UNRESOLVED."""
    profile = StudentProfile(cgpa=7.2, institution="Unrecognized College")
    crit = {
        "criterion_type": "ACADEMIC_GRADE",
        "stated_requirement": "High academic standing from an accredited university evaluated on a case-by-case basis"
    }
    eval_res = evaluate_single_criterion(crit, profile, is_admission=True)
    assert eval_res["status"] == "UNRESOLVED"
    assert "institutional equivalency must be verified" in eval_res["uncertainty_or_conflict"]
    assert "Verify institutional grade conversion" in eval_res["actionable_gap"]


# ==============================================================================
# Feature F8: Admission vs Scholarship Distinction
# ==============================================================================

def test_f8_distinct_admission_and_scholarship_data_models():
    """F8: Confirms separate data structures for admission criteria vs scholarship criteria."""
    opp = Opportunity(
        id="opp-distinction",
        run_id="run-test",
        canonical_url="https://cs.ox.ac.uk/msc",
        title="Oxford Clarendon & MSc CS",
        program_name="MSc Computer Science",
        university="University of Oxford",
        country="UK",
        admission_requirements=[
            EligibilityCriterion(
                criterion_type="ACADEMIC_GRADE",
                is_mandatory=True,
                requirement_text="First class undergraduate degree in CS or Mathematics"
            ),
            EligibilityCriterion(
                criterion_type="LANGUAGE_TEST",
                is_mandatory=True,
                requirement_text="IELTS 7.5 overall with 7.0 per component"
            )
        ],
        scholarship_requirements=[
            EligibilityCriterion(
                criterion_type="ACADEMIC_GRADE",
                is_mandatory=False,
                requirement_text="Outstanding academic record and potential evaluated by Clarendon panel"
            )
        ]
    )
    assert len(opp.admission_requirements) == 2
    assert len(opp.scholarship_requirements) == 1
    assert opp.admission_requirements[0].is_mandatory is True
    assert opp.scholarship_requirements[0].is_mandatory is False


def test_f8_mandatory_admission_failure_disqualifies_before_ranking():
    """
    F8: Verifies mandatory admission check is applied before ranking.
    Failure in mandatory admission criteria sets is_eligible_for_shortlist = False and academic_fit = 0.
    """
    profile = StudentProfile(cgpa=6.0) # Low CGPA
    opp = Opportunity(
        id="opp-fail-adm",
        run_id="run-test",
        canonical_url="https://utoronto.ca/mscac",
        title="MSc Applied Computing",
        program_name="MSc Applied Computing",
        university="University of Toronto",
        country="Canada",
        admission_requirements=[
            EligibilityCriterion(
                criterion_type="ACADEMIC_GRADE",
                is_mandatory=True,
                requirement_text="Minimum 8.0/10 CGPA required"
            )
        ],
        evidence_records=[
            EvidenceRecord(
                criterion_name="ACADEMIC_GRADE",
                stated_requirement="Minimum 8.0/10 CGPA required",
                student_value="6.0 / 10.0",
                status="DOES_NOT_MEET",
                source_url="https://utoronto.ca"
            )
        ],
        eligibility_status="DOES_NOT_MEET"
    )

    score = calculate_match_score(profile, opp)
    assert score.is_eligible_for_shortlist is False
    assert score.academic_fit == 0.0
    assert "Disqualified from shortlist" in score.explanation


def test_f8_admission_passed_with_unresolved_scholarship_remains_potential_match():
    """
    F8: If admission requirements pass, but scholarship criteria remain pending/unresolved,
    the candidate is not hard-disqualified; they remain a POTENTIAL_MATCH for the shortlist.
    """
    profile = StudentProfile(cgpa=8.5, target_degree="Master's", target_field="Computer Science")
    opp = Opportunity(
        id="opp-pass-adm-unresolved-sch",
        run_id="run-test",
        canonical_url="https://tum.de/msc",
        title="TUM Informatics DAAD",
        program_name="MSc Informatics",
        university="TUM",
        country="Germany",
        admission_requirements=[
            EligibilityCriterion(
                criterion_type="ACADEMIC_GRADE",
                is_mandatory=True,
                requirement_text="German grade 2.0 or better (~7.5/10 CGPA)"
            )
        ],
        evidence_records=[
            EvidenceRecord(
                criterion_name="Admission Requirement",
                stated_requirement="German grade 2.0 or better (~7.5/10 CGPA)",
                student_value="8.5 / 10.0",
                status="MEETS",
                source_url="https://tum.de"
            ),
            EvidenceRecord(
                criterion_name="Scholarship Requirement",
                stated_requirement="DAAD selection committee interview and reference evaluation",
                student_value="References pending submission",
                status="UNRESOLVED",
                source_url="https://daad.de"
            )
        ],
        eligibility_status="POTENTIAL_MATCH"
    )

    score = calculate_match_score(profile, opp)
    assert score.is_eligible_for_shortlist is True
    assert score.academic_fit >= 25.0


# ==============================================================================
# Feature F9: Runtime Deadline Verification
# ==============================================================================

@pytest.mark.asyncio
async def test_f9_quality_reviewer_flags_expired_deadlines():
    """
    F9: In quality_reviewer.py, compare deadlines against datetime.now(timezone.utc).date().
    Flag historical or passed deadlines as EXPIRED and never present them as active.
    """
    reviewer = QualityReviewerAgent()
    today_utc = datetime.now(timezone.utc).date()
    yesterday_str = (today_utc - timedelta(days=5)).strftime("%Y-%m-%d")

    expired_opp = Opportunity(
        id="opp-expired",
        run_id="run-rev",
        canonical_url="https://web.cs.toronto.edu/mscac",
        title="Expired Toronto Opportunity",
        program_name="MSc Applied Computing",
        university="University of Toronto",
        country="Canada",
        official_source_urls=["https://web.cs.toronto.edu/mscac"],
        deadline=yesterday_str,
        deadline_type="Fixed",
        deadline_verified=True,
        funding_details=FundingDetails(funding_type="Partial", coverage_description="Tuition waiver")
    )

    reviewed_opps, needs_re_research, issues = await reviewer.execute_audit(
        run_id="run-rev",
        profile=StudentProfile(cgpa=8.2),
        opportunities=[expired_opp]
    )

    assert expired_opp.reviewer_status == "FLAGGED"
    assert expired_opp.deadline_verified is False
    assert getattr(expired_opp, "deadline_status", None) == "EXPIRED"
    assert any("expired" in issue.lower() for issue in issues)
    assert needs_re_research is True


def test_f9_scoring_service_zero_readiness_score_for_expired_deadline():
    """F9: In scoring_service.py, do NOT award deadline readiness score to expired deadlines."""
    today_utc = datetime.now(timezone.utc).date()
    past_date = (today_utc - timedelta(days=30)).strftime("%Y-%m-%d")

    profile = StudentProfile(cgpa=8.2)
    opp = Opportunity(
        id="opp-scoring-expired",
        run_id="run-1",
        canonical_url="https://tum.de/studies",
        title="TUM Past Intake",
        program_name="MSc Informatics",
        university="TUM",
        country="Germany",
        deadline=past_date,
        deadline_type="Fixed",
        deadline_verified=True,
        funding_details=FundingDetails(funding_type="None"),
        eligibility_status="MEETS_STATED_CRITERIA"
    )

    score = calculate_match_score(profile, opp)
    assert score.deadline_fit == 0.0
    assert score.is_eligible_for_shortlist is False
    assert "EXPIRED" in score.explanation


def test_f9_rolling_and_unknown_deadlines_handled_correctly():
    """F9: Distinguishes rolling intakes (active) from unannounced intakes (unknown)."""
    profile = StudentProfile(cgpa=8.2)

    # Rolling deadline
    opp_rolling = Opportunity(
        id="opp-rolling",
        run_id="run-1",
        canonical_url="https://nus.edu.sg/mcomp",
        title="NUS MComp Rolling",
        program_name="MComp AI",
        university="NUS",
        country="Singapore",
        deadline=None,
        deadline_type="Rolling",
        deadline_verified=True,
        funding_details=FundingDetails(funding_type="Partial"),
        eligibility_status="MEETS_STATED_CRITERIA"
    )
    score_rolling = calculate_match_score(profile, opp_rolling)
    assert score_rolling.deadline_fit == 10.0
    assert getattr(opp_rolling, "deadline_status", None) == "ROLLING"
    assert score_rolling.is_eligible_for_shortlist is True

    # Unknown / Unannounced deadline
    opp_unknown = Opportunity(
        id="opp-unknown",
        run_id="run-1",
        canonical_url="https://sfu.ca/cs",
        title="SFU Unannounced",
        program_name="MSc CS",
        university="SFU",
        country="Canada",
        deadline=None,
        deadline_type="Unknown",
        deadline_verified=False,
        funding_details=FundingDetails(funding_type="Partial"),
        eligibility_status="MEETS_STATED_CRITERIA"
    )
    score_unknown = calculate_match_score(profile, opp_unknown)
    assert score_unknown.deadline_fit == 2.0
    assert getattr(opp_unknown, "deadline_status", None) == "UNKNOWN"


def test_f9_active_future_deadline_awarded_maximum_score():
    """F9: Active future verified deadline awards full 10.0 deadline fit points."""
    today_utc = datetime.now(timezone.utc).date()
    future_date = (today_utc + timedelta(days=90)).strftime("%Y-%m-%d")

    profile = StudentProfile(cgpa=8.2)
    opp_active = Opportunity(
        id="opp-active",
        run_id="run-1",
        canonical_url="https://vectorinstitute.ai/scholarship",
        title="Vector Institute AI Fellowship",
        program_name="MSc AI",
        university="University of Toronto",
        country="Canada",
        deadline=future_date,
        deadline_type="Fixed",
        deadline_verified=True,
        funding_details=FundingDetails(funding_type="Fully Funded", tuition_covered=True),
        eligibility_status="MEETS_STATED_CRITERIA"
    )
    score_active = calculate_match_score(profile, opp_active)
    assert score_active.deadline_fit == 10.0
    assert getattr(opp_active, "deadline_status", None) == "ACTIVE"
    assert score_active.is_eligible_for_shortlist is True


# ==============================================================================
# Feature F10: Robust Official Domain Verification
# ==============================================================================

def test_f10_is_official_domain_authoritative_tlds_and_registries():
    """F10: Verifies parsed hostname verification against educational and official registry rules."""
    # Official TLDs and Academic second-level domains
    assert is_official_domain("https://web.cs.toronto.edu/mscac") is True
    assert is_official_domain("https://cs.stanford.edu/admissions") is True
    assert is_official_domain("https://www.ox.ac.uk/admissions/graduate") is True
    assert is_official_domain("https://www.cam.ac.uk/apply") is True
    assert is_official_domain("https://www.u-tokyo.ac.jp/en") is True
    assert is_official_domain("https://www.nus.edu.sg/programmes") is True
    assert is_official_domain("https://www.ntu.edu.sg/admissions") is True
    assert is_official_domain("https://www.canada.ca/en/services/benefits/education.html") is True

    # Approved Registry Hosts & Subdomains
    assert is_official_domain("https://www.tum.de/en/studies") is True
    assert is_official_domain("https://in.tum.de/master") is True
    assert is_official_domain("https://vectorinstitute.ai/scholarship") is True
    assert is_official_domain("https://www.a-star.edu.sg/scholarships") is True
    assert is_official_domain("https://daad.de/en") is True
    assert is_official_domain("https://www.mcgill.ca/gradapplicants") is True
    assert is_official_domain("https://grad.ubc.ca/apply") is True
    assert is_official_domain("https://uwaterloo.ca/graduate") is True


def test_f10_is_official_domain_rejects_commercial_blogs_and_substring_exploits():
    """
    F10: Tests rejection of commercial blogs, scrapers, and malicious substring matches
    that would previously pass naive substring checks (e.g. '.org', '.ca', '.de').
    """
    # Commercial blogs and lead-gen scrapers
    assert is_official_domain("https://scholarship-tips-blog.com/top-10") is False
    assert is_official_domain("https://free-student-aid-fast.biz") is False
    assert is_official_domain("https://random-medium-post.io/apply") is False
    assert is_official_domain("https://student-loans-now.net") is False

    # Substring exploits that contain country code or .org inside path or hostname
    assert is_official_domain("https://scamsite.org/university-scholarships") is False
    assert is_official_domain("https://fake-visa-agent.ca/apply") is False
    assert is_official_domain("https://unrelated-tech-news.de/study-in-germany") is False
    assert is_official_domain("https://spamblog.com/about-canada.html") is False
    assert is_official_domain("https://malicious.com/daad.de/fake-link") is False

    # Subdomain spoofing attempts attempting to bypass .ac. or .edu. checks
    assert is_official_domain("https://scholarship.ac.fake.com") is False
    assert is_official_domain("https://evil.edu.attacker.org") is False
    assert is_official_domain("https://attacker.gov.scam.net") is False
    assert is_official_domain("https://phishing.ac.com") is False

    # SSRF / Loopback / Malformed URLs
    assert is_official_domain("http://localhost:8000/apply") is False
    assert is_official_domain("http://127.0.0.1/admin") is False
    assert is_official_domain("ftp://ftp.uni-bonn.de") is False
    assert is_official_domain("") is False
    assert is_official_domain(None) is False


@pytest.mark.asyncio
async def test_f10_quality_reviewer_flags_secondary_domain_and_triggers_reresearch():
    """
    F10: Verifies that Quality Reviewer flags opportunities citing commercial/secondary sources,
    sets evidence_quality = SECONDARY, reviewer_status = FLAGGED, and needs_re_research = True.
    """
    reviewer = QualityReviewerAgent()

    commercial_opp = Opportunity(
        id="opp-commercial-source",
        run_id="run-rev-dom",
        canonical_url="https://scholarship-blog-portal.com/toronto-mscac",
        title="Toronto Fellowship via Blog",
        program_name="MSc Applied Computing",
        university="University of Toronto",
        country="Canada",
        official_source_urls=["https://scholarship-blog-portal.com/toronto-mscac"],
        funding_details=FundingDetails(funding_type="Partial", coverage_description="Stipend")
    )

    reviewed_opps, needs_re_research, issues = await reviewer.execute_audit(
        run_id="run-rev-dom",
        profile=StudentProfile(cgpa=8.2),
        opportunities=[commercial_opp]
    )

    assert commercial_opp.evidence_quality == "SECONDARY"
    assert commercial_opp.reviewer_status == "FLAGGED"
    assert needs_re_research is True
    assert any("Only secondary sources found" in issue for issue in issues)


# ==============================================================================
# Iteration 2 Remediation & Regression Tests
# ==============================================================================

def test_f6_grading_scale_4_point_scale_normalized_to_10():
    """
    R3: When student profile grading_scale is '4.0' and requirement is '10.0' without
    published institution equivalency, criterion resolves to UNRESOLVED with actionable gap.
    """
    profile_mismatch = StudentProfile(cgpa=3.8, grading_scale="4.0", institution="US College")
    criterion = {"criterion_type": "ACADEMIC_GRADE", "stated_requirement": "Minimum 8.0/10 CGPA required"}
    res_mismatch = evaluate_single_criterion(criterion, profile_mismatch, is_admission=True)
    assert res_mismatch["status"] == "UNRESOLVED"
    assert res_mismatch["actionable_gap"] is not None
    assert "Verify institutional grade conversion" in res_mismatch["actionable_gap"]


def test_f8_failing_optional_scholarship_remains_eligible_for_admission_shortlist():
    """
    F8: A student who meets mandatory university admission requirements but fails
    an optional, competitive scholarship criterion must remain eligible for admission
    and shortlist ranking (not hard-disqualified).
    """
    profile = StudentProfile(cgpa=8.5, target_degree="Master's", target_field="Computer Science")
    opp = Opportunity(
        id="opp-pass-adm-fail-sch",
        run_id="run-f8-test",
        canonical_url="https://utoronto.ca/mscac",
        title="UofT MScAC with Competitive Fellowship",
        program_name="MSc Applied Computing",
        university="University of Toronto",
        country="Canada",
        admission_requirements=[
            EligibilityCriterion(
                criterion_type="ACADEMIC_GRADE",
                is_mandatory=True,
                requirement_text="Minimum 8.0/10 CGPA in computer science or related discipline"
            )
        ],
        scholarship_requirements=[
            EligibilityCriterion(
                criterion_type="ACADEMIC_GRADE",
                is_mandatory=False,
                requirement_text="Top 1% graduating class rank for Dean's Full Fellowship"
            )
        ],
        evidence_records=[
            EvidenceRecord(
                criterion_name="Admission Requirement",
                stated_requirement="Minimum 8.0/10 CGPA in computer science or related discipline",
                student_value="8.5 / 10.0",
                status="MEETS",
                source_url="https://utoronto.ca"
            ),
            EvidenceRecord(
                criterion_name="Scholarship Requirement",
                stated_requirement="Top 1% graduating class rank for Dean's Full Fellowship",
                student_value="Class rank: top 10%",
                status="DOES_NOT_MEET",
                source_url="https://utoronto.ca"
            )
        ],
        eligibility_status="POTENTIAL_MATCH",
        deadline="2026-12-01",
        deadline_status="ACTIVE",
        deadline_verified=True
    )

    score = calculate_match_score(profile, opp)
    assert score.is_eligible_for_shortlist is True
    assert score.academic_fit >= 25.0
    assert "Disqualified from shortlist" not in score.explanation


def test_f9_opportunity_model_dump_serializes_deadline_status():
    """
    F9: Opportunity model must declare deadline_status field so that opp.model_dump()
    and FastAPI endpoints serialize deadline_status per the PROJECT.md API contract.
    """
    opp = Opportunity(
        id="opp-serialize-test",
        run_id="run-f9",
        canonical_url="https://utoronto.ca",
        title="Test Opportunity",
        program_name="Computer Science",
        university="University of Toronto",
        country="Canada",
        deadline="2026-12-01",
        deadline_status="ACTIVE",
        deadline_verified=True
    )
    dumped = opp.model_dump()
    assert "deadline_status" in dumped
    assert dumped["deadline_status"] == "ACTIVE"


@pytest.mark.asyncio
async def test_discovery_and_audit_candidate_loop_integration_no_name_error():
    """
    Integration verification: Ensures ResearchEligibilityAgent.execute_discovery_and_audit
    evaluates candidates with admission and scholarship requirements without raising NameError
    and correctly generates populated Opportunity instances with deadline_status.
    """
    from unittest.mock import AsyncMock
    from app.models.profile import StudentProfile

    agent = ResearchEligibilityAgent()
    profile = StudentProfile(cgpa=8.5, target_countries=["Canada"])

    with patch("app.services.gemini_service.gemini_service.ensure_available"), \
         patch("app.services.gemini_service.gemini_service.search_grounded_discovery", new_callable=AsyncMock) as mock_search, \
         patch("app.services.gemini_service.gemini_service.analyze_url_and_extract_criteria", new_callable=AsyncMock) as mock_extract, \
         patch("app.db.repository.repository.save_agent_event", new_callable=AsyncMock), \
         patch("app.db.repository.repository.save_evidence_records", new_callable=AsyncMock):

        mock_search.return_value = {
            "success": True,
            "candidates": [
                {"canonical_url": "https://web.cs.toronto.edu/mscac", "title": "UofT MScAC", "university": "University of Toronto"}
            ]
        }
        mock_extract.return_value = {
            "success": True,
            "is_retrieval_successful": True,
            "retrieval_status": "URL_RETRIEVAL_STATUS_SUCCESS",
            "data": {
                "program_name": "MSc Applied Computing",
                "university": "University of Toronto",
                "country": "Canada",
                "deadline": "2026-12-15",
                "deadline_type": "Fixed",
                "admission_requirements": [
                    {"criterion_type": "ACADEMIC_GRADE", "stated_requirement": "Min 8.0 CGPA", "is_mandatory": True}
                ],
                "scholarship_requirements": [
                    {"criterion_type": "ACADEMIC_GRADE", "stated_requirement": "Competitive merit award", "is_mandatory": False}
                ]
            }
        }

        opportunities = await agent.execute_discovery_and_audit("run-test-integration", profile)
        assert len(opportunities) == 1
        opp = opportunities[0]
        assert "deadline_status" in opp.model_dump()
        assert opp.deadline_status == "ACTIVE"
        assert opp.eligibility_status in ("MEETS_STATED_CRITERIA", "POTENTIAL_MATCH")
        assert isinstance(opp.actionable_gaps, list)
        assert isinstance(opp.eligibility_reasons, list)

