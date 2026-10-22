"""
Empirical Challenge Test Suite — Challenger 2 (Eligibility & Query Challenger)

Covers:
1. extract_numeric_cgpa_cutoff with diverse inputs (4.0 vs 10.0, percentages, qualitative honours, boundaries).
2. evaluate_single_criterion with scale mismatches, percentages, qualitative phrases, verifying UNRESOLVED status and actionable gap notes unless official equivalencies are present.
3. Round 2 re-research query construction, verifying that student failure strings never appear in search queries.
"""

import pytest
from unittest.mock import AsyncMock, patch
from app.models.profile import StudentProfile
from app.agents.research_eligibility import (
    extract_numeric_cgpa_cutoff,
    extract_raw_grade_cutoffs_and_scales,
    extract_raw_grade_cutoff_and_scale,
    evaluate_single_criterion,
    ResearchEligibilityAgent,
)
from app.agents.quality_reviewer import ReviewerIssue


# ==============================================================================
# Task 1A: extract_numeric_cgpa_cutoff Empirical Stress Testing
# ==============================================================================

class TestExtractNumericCgpaCutoffEmpirical:
    """Stress-tests extract_numeric_cgpa_cutoff across diverse inputs."""

    @pytest.mark.parametrize("text,expected", [
        # Explicit published 10-point scale equivalencies
        ("Minimum 8.0/10.0 CGPA from recognized Indian institutions", 8.0),
        ("Minimum 8.5/10 CGPA required", 8.5),
        ("typically 8.0/10", 8.0),
        ("Requires First Class with Distinction (typically 8.0/10)", 8.0),
        ("Minimum B average (7.0/10) required", 7.0),
        ("Must have at least 7.25 / 10.0 CGPA", 7.25),
        ("Cutoff: 9.0/10", 9.0),

        # Standalone 10-point CGPA > 4.0 after keyword
        ("Applicant must hold a minimum 7.5 CGPA", 7.5),
        ("CGPA of 8.0 or above", 8.0),
        ("Minimum average of 8.2 in undergraduate degree", 8.2),
        ("Requires minimum: 7.8", 7.8),
        ("GPA ~ 8.0 required for consideration", 8.0),

        # Pre-CGPA keyword with value > 4.0
        ("8.0+ CGPA required for direct entry", 8.0),
        ("at least 7.8 CGPA from accredited university", 7.8),
        ("minimum 8.5 gpa required", 8.5),
    ])
    def test_extract_valid_10_point_scale(self, text, expected):
        """Valid 10-point scale thresholds must be extracted accurately."""
        result = extract_numeric_cgpa_cutoff(text)
        assert result == expected, f"Failed on input: '{text}', expected {expected}, got {result}"

    @pytest.mark.parametrize("text", [
        # 4.0 scale criteria without published 10-point equivalency
        "Minimum 3.2/4.0 GPA in Computer Science",
        "Minimum 3.5/4.0 GPA",
        "3.0 / 4.0 GPA required",
        "Requires 3.8 out of 4.0",
        "Minimum 3.0 GPA",
        "CGPA of 3.5",
        "at least 3.7 GPA",
        "3.2+ GPA",
        "Minimum 4.0/4.0 GPA",
        "Requires 4.0 GPA",

        # Percentages (no arbitrary division by 10)
        "Minimum 75% aggregate marks from recognized university",
        "Requires 80% or higher in undergraduate study",
        "Minimum 60% percentage in Bachelor degree",
        "Requires 85.5% marks",
        "Overall score: 70%",
        "Percentage cutoff: 65%",

        # Qualitative honours classifications without published /10 figures
        "Requires First Class with Distinction",
        "Requires Second Upper Class Honours / B+ average",
        "First Class Honours degree required",
        "Second Class Honours (Upper Division 2:1)",
        "Second Class Honours (Lower Division 2:2)",
        "Minimum B+ average required for admission",
        "A- average across all major courses",
        "Good honours degree in a relevant subject",
        "Distinction or equivalent from international institution",

        # Unquantified / holistic / empty phrases
        "Holistic assessment based on portfolio and statement",
        "Admission is highly competitive; portfolio reviewed holistically",
        "No minimum GPA specified; comprehensive file review",
        "Applicant must hold an accredited bachelor's degree",
        "",
        "   ",
    ])
    def test_extract_returns_none_for_ungrounded_or_mismatched(self, text):
        """Ungrounded 4.0 scales, percentages, and qualitative descriptors MUST return None."""
        result = extract_numeric_cgpa_cutoff(text)
        assert result is None, f"Expected None for '{text}', but got {result}"

    def test_extract_none_on_none_input(self):
        """None input returns None without exception."""
        assert extract_numeric_cgpa_cutoff(None) is None


# ==============================================================================
# Task 1B: evaluate_single_criterion Empirical Stress Testing
# ==============================================================================

class TestEvaluateSingleCriterionEmpirical:
    """Stress-tests evaluate_single_criterion for scale mismatches, percentages, and qualitative descriptors."""

    @pytest.fixture
    def profile_10_scale(self):
        return StudentProfile(
            full_name="Priya Sharma",
            current_degree="B.Tech in Computer Science",
            institution="IIT Bombay",
            cgpa=8.5,
            grading_scale="10.0",
            target_degree="M.Sc.",
            target_field="Data Science",
            target_countries=["Germany", "Canada"],
            language_tests={"test": "IELTS", "score": 7.5, "status": "verified"}
        )

    @pytest.fixture
    def profile_4_scale(self):
        return StudentProfile(
            full_name="Alex Chen",
            current_degree="B.S. in Computer Science",
            institution="UC Berkeley",
            cgpa=3.6,
            grading_scale="4.0",
            target_degree="M.Sc.",
            target_field="Data Science",
            target_countries=["Germany", "UK"],
            language_tests={"test": "TOEFL", "score": 105, "status": "verified"}
        )

    def test_scale_mismatch_10_student_vs_4_requirement(self, profile_10_scale):
        """Student on 10.0 scale vs 3.5/4.0 requirement without official note must resolve to UNRESOLVED."""
        criterion = {
            "criterion_name": "Academic Grade",
            "criterion_type": "ACADEMIC_GRADE",
            "stated_requirement": "Minimum 3.5/4.0 GPA in Computer Science or related field",
            "evidence_excerpt": "Minimum 3.5/4.0 GPA required for graduate admission.",
            "source_url": "https://example.edu/admissions"
        }
        res = evaluate_single_criterion(criterion, profile_10_scale, is_admission=True)

        assert res["status"] == "UNRESOLVED", f"Expected UNRESOLVED, got {res['status']}"
        assert res["actionable_gap"] is not None
        assert "admissions office" in res["actionable_gap"].lower()
        assert "10.0" in res["actionable_gap"] or "10" in res["actionable_gap"]
        assert "IIT Bombay" in res["actionable_gap"]
        assert "3.5/4.0" in res["uncertainty_or_conflict"]

    def test_scale_mismatch_4_student_vs_10_requirement(self, profile_4_scale):
        """Student on 4.0 scale vs 8.0/10.0 requirement without official note must resolve to UNRESOLVED."""
        criterion = {
            "criterion_name": "Academic Grade",
            "criterion_type": "ACADEMIC_GRADE",
            "stated_requirement": "Minimum 8.0/10.0 CGPA from accredited institutions",
            "evidence_excerpt": "Minimum 8.0/10.0 CGPA required.",
            "source_url": "https://example.edu/admissions"
        }
        res = evaluate_single_criterion(criterion, profile_4_scale, is_admission=True)

        assert res["status"] == "UNRESOLVED", f"Expected UNRESOLVED, got {res['status']}"
        assert res["actionable_gap"] is not None
        assert "admissions office" in res["actionable_gap"].lower()
        assert "UC Berkeley" in res["actionable_gap"]
        assert "4.0" in res["actionable_gap"] or "4" in res["actionable_gap"]

    def test_percentage_requirement_resolves_to_unresolved(self, profile_10_scale):
        """Percentage requirement without official note must resolve to UNRESOLVED with actionable gap."""
        criterion = {
            "criterion_name": "Academic Grade",
            "criterion_type": "ACADEMIC_GRADE",
            "stated_requirement": "Requires minimum 75% aggregate marks in undergraduate degree",
            "evidence_excerpt": "Requires minimum 75% aggregate marks.",
            "source_url": "https://example.edu/admissions"
        }
        res = evaluate_single_criterion(criterion, profile_10_scale, is_admission=True)

        assert res["status"] == "UNRESOLVED", f"Expected UNRESOLVED, got {res['status']}"
        assert res["actionable_gap"] is not None
        assert "admissions office" in res["actionable_gap"].lower()
        assert "institutional equivalency must be verified" in res["uncertainty_or_conflict"].lower()

    @pytest.mark.parametrize("honours_req", [
        "Requires First Class with Distinction in engineering",
        "Requires Second Upper Class Honours / B+ average",
        "First class honours degree or international equivalent",
        "Applicant must hold Second Class Honours (2:1)",
        "Minimum B+ average across all undergraduate coursework",
        "Distinction or superior academic record",
    ])
    def test_qualitative_honours_phrases_resolve_to_unresolved(self, profile_10_scale, honours_req):
        """Qualitative honours descriptors without published scale equivalency must resolve to UNRESOLVED."""
        criterion = {
            "criterion_name": "Academic Grade",
            "criterion_type": "ACADEMIC_GRADE",
            "stated_requirement": honours_req,
            "evidence_excerpt": honours_req,
            "source_url": "https://example.edu/admissions"
        }
        res = evaluate_single_criterion(criterion, profile_10_scale, is_admission=True)

        assert res["status"] == "UNRESOLVED", f"Expected UNRESOLVED for '{honours_req}', got {res['status']}"
        assert res["actionable_gap"] is not None
        assert "admissions office" in res["actionable_gap"].lower()
        assert "institutional equivalency must be verified" in res["uncertainty_or_conflict"].lower()

    def test_official_equivalency_note_overrides_to_meets(self, profile_10_scale):
        """When official institutional equivalency guidance is published, criterion resolves to MEETS."""
        criterion = {
            "criterion_name": "Academic Grade",
            "criterion_type": "ACADEMIC_GRADE",
            "stated_requirement": "Minimum 3.5/4.0 GPA in Computer Science",
            "official_equivalency_note": "Official DAAD institutional conversion: 8.0/10.0 CGPA from Indian Institute of Technology satisfies 3.5/4.0 cutoff.",
            "evidence_excerpt": "Minimum 3.5/4.0 GPA; Indian IIT 8.0/10 recognized equivalent.",
            "source_url": "https://example.edu/admissions"
        }
        res = evaluate_single_criterion(criterion, profile_10_scale, is_admission=True)

        assert res["status"] == "MEETS"
        assert res["actionable_gap"] is None
        assert res["uncertainty_or_conflict"] == criterion["official_equivalency_note"]

    def test_same_scale_matching_meets(self, profile_10_scale):
        """Student 8.5/10.0 against 8.0/10.0 requirement resolves to MEETS."""
        criterion = {
            "criterion_name": "Academic Grade",
            "criterion_type": "ACADEMIC_GRADE",
            "stated_requirement": "Minimum 8.0/10.0 CGPA from accredited institutions",
            "evidence_excerpt": "Minimum 8.0/10.0 CGPA required.",
            "source_url": "https://example.edu/admissions"
        }
        res = evaluate_single_criterion(criterion, profile_10_scale, is_admission=True)

        assert res["status"] == "MEETS"
        assert res["actionable_gap"] is None

    def test_same_scale_matching_fails(self, profile_10_scale):
        """Student 8.5/10.0 against 9.0/10.0 requirement resolves to DOES_NOT_MEET with gap."""
        criterion = {
            "criterion_name": "Academic Grade",
            "criterion_type": "ACADEMIC_GRADE",
            "stated_requirement": "Minimum 9.0/10.0 CGPA required for fellowship",
            "evidence_excerpt": "Minimum 9.0/10.0 CGPA required.",
            "source_url": "https://example.edu/admissions"
        }
        res = evaluate_single_criterion(criterion, profile_10_scale, is_admission=True)

        assert res["status"] == "DOES_NOT_MEET"
        assert res["actionable_gap"] is not None
        assert "below the program minimum entrance cutoff" in res["actionable_gap"]

    def test_multi_scale_requirement_direct_match(self, profile_10_scale, profile_4_scale):
        """Dual-scale requirement ('3.5/4.0 or 8.0/10.0') matches each student on their own scale."""
        req_text = "Minimum 3.5/4.0 GPA or 8.0/10.0 CGPA required."
        criterion = {
            "criterion_name": "Academic Grade",
            "criterion_type": "ACADEMIC_GRADE",
            "stated_requirement": req_text,
            "evidence_excerpt": req_text,
            "source_url": "https://example.edu/admissions"
        }

        # 10.0 scale student with 8.5 >= 8.0
        res_10 = evaluate_single_criterion(criterion, profile_10_scale, is_admission=True)
        assert res_10["status"] == "MEETS"
        assert res_10["actionable_gap"] is None

        # 4.0 scale student with 3.6 >= 3.5
        res_4 = evaluate_single_criterion(criterion, profile_4_scale, is_admission=True)
        assert res_4["status"] == "MEETS"
        assert res_4["actionable_gap"] is None


# ==============================================================================
# Task 2: Round 2 Re-research Query Construction Empirical Verification
# ==============================================================================

class TestRound2QueryConstructionEmpirical:
    """Empirically verifies that Round 2 re-research queries do not contain student failure strings."""

    @pytest.fixture
    def sample_profile(self):
        return StudentProfile(
            full_name="Arjun Patel",
            current_degree="B.Tech in Computer Science",
            institution="NIT Trichy",
            cgpa=7.4,
            grading_scale="10.0",
            target_degree="M.Sc.",
            target_field="Computer Science",
            target_countries=["Germany"],
            language_tests={"test": "IELTS", "score": 6.5, "status": "verified"}
        )

    @pytest.mark.asyncio
    async def test_round_2_mandatory_criteria_failure_query_is_clean(self, sample_profile):
        """Verify that 'Student fails published mandatory admission criteria' is NOT in query."""
        agent = ResearchEligibilityAgent()
        captured_queries = []

        mock_search = AsyncMock(return_value={"success": False, "error": "Search mocked for query check"})

        reviewer_issues = [
            ReviewerIssue({
                "opportunity_id": "opp-1",
                "university": "Technical University of Munich",
                "program_name": "M.Sc. Informatics",
                "issue_type": "MANDATORY_CRITERIA_FAILED",
                "description": "Technical University of Munich: Student fails published mandatory admission criteria.",
                "issue": "Technical University of Munich: Student fails published mandatory admission criteria."
            })
        ]

        with patch("app.agents.research_eligibility.gemini_service.search_grounded_discovery", mock_search):
            with patch("app.agents.research_eligibility.gemini_service.ensure_available"):
                await agent.execute_discovery_and_audit(
                    run_id="run-test-q1",
                    profile=sample_profile,
                    research_round=2,
                    reviewer_issues=reviewer_issues
                )

        assert mock_search.called, "Expected search_grounded_discovery to be called"
        for call_args in mock_search.call_args_list:
            q = call_args.kwargs.get("query") or call_args.args[0]
            captured_queries.append(q)

        assert len(captured_queries) > 0
        for q in captured_queries:
            # Strictly verify failure strings are absent
            assert "Student fails published mandatory admission criteria" not in q
            assert "fails published mandatory" not in q
            assert "fails" not in q.lower()
            assert "below the program minimum" not in q
            assert "not eligible" not in q.lower()

            # Verify query contains targeted tokens
            assert '"Technical University of Munich"' in q
            assert '"M.Sc. Informatics"' in q
            assert "degree admission requirements" in q
            assert "Germany" in q

    @pytest.mark.asyncio
    async def test_round_2_expired_deadline_query_is_clean(self, sample_profile):
        """Verify that expired deadline failure strings are NOT in query."""
        agent = ResearchEligibilityAgent()
        captured_queries = []

        mock_search = AsyncMock(return_value={"success": False, "error": "Search mocked for query check"})

        reviewer_issues = [
            ReviewerIssue({
                "opportunity_id": "opp-2",
                "university": "University of Oxford",
                "program_name": "MSc Advanced Computer Science",
                "issue_type": "EXPIRED_DEADLINE",
                "description": "University of Oxford: Application deadline (2025-01-15) has passed and is expired; cannot present as active.",
                "issue": "University of Oxford: Application deadline (2025-01-15) has passed and is expired; cannot present as active."
            })
        ]

        with patch("app.agents.research_eligibility.gemini_service.search_grounded_discovery", mock_search):
            with patch("app.agents.research_eligibility.gemini_service.ensure_available"):
                await agent.execute_discovery_and_audit(
                    run_id="run-test-q2",
                    profile=sample_profile,
                    research_round=2,
                    reviewer_issues=reviewer_issues
                )

        assert mock_search.called
        for call_args in mock_search.call_args_list:
            q = call_args.kwargs.get("query") or call_args.args[0]
            captured_queries.append(q)

        assert len(captured_queries) > 0
        for q in captured_queries:
            # Strictly verify failure strings are absent
            assert "Application deadline" not in q or "admissions deadline" in q
            assert "expired" not in q.lower()
            assert "cannot present as active" not in q
            assert "has passed" not in q

            # Verify query contains targeted tokens
            assert '"University of Oxford"' in q
            assert '"MSc Advanced Computer Science"' in q
            assert "admissions deadline current intake" in q

    @pytest.mark.asyncio
    async def test_round_2_secondary_source_query_is_clean(self, sample_profile):
        """Verify secondary source issues generate clean official portal queries."""
        agent = ResearchEligibilityAgent()
        captured_queries = []

        mock_search = AsyncMock(return_value={"success": False, "error": "Search mocked"})

        reviewer_issues = [
            ReviewerIssue({
                "opportunity_id": "opp-3",
                "university": "ETH Zurich",
                "program_name": "Master in Computer Science",
                "issue_type": "SECONDARY_SOURCE",
                "description": "ETH Zurich: Source URL is a secondary aggregator, not official provider domain.",
                "issue": "ETH Zurich: Source URL is a secondary aggregator, not official provider domain."
            })
        ]

        with patch("app.agents.research_eligibility.gemini_service.search_grounded_discovery", mock_search):
            with patch("app.agents.research_eligibility.gemini_service.ensure_available"):
                await agent.execute_discovery_and_audit(
                    run_id="run-test-q3",
                    profile=sample_profile,
                    research_round=2,
                    reviewer_issues=reviewer_issues
                )

        for call_args in mock_search.call_args_list:
            q = call_args.kwargs.get("query") or call_args.args[0]
            captured_queries.append(q)

        for q in captured_queries:
            assert "secondary aggregator" not in q
            assert '"ETH Zurich"' in q
            assert "official portal admission" in q

    @pytest.mark.asyncio
    async def test_round_1_ignores_reviewer_issues(self, sample_profile):
        """When research_round == 1, reviewer issues must not be used even if passed."""
        agent = ResearchEligibilityAgent()
        captured_queries = []

        mock_search = AsyncMock(return_value={"success": False, "error": "Search mocked"})

        reviewer_issues = [
            ReviewerIssue({
                "university": "Harvard University",
                "program_name": "CS",
                "issue_type": "MANDATORY_CRITERIA_FAILED",
                "description": "Student fails published mandatory admission criteria."
            })
        ]

        with patch("app.agents.research_eligibility.gemini_service.search_grounded_discovery", mock_search):
            with patch("app.agents.research_eligibility.gemini_service.ensure_available"):
                await agent.execute_discovery_and_audit(
                    run_id="run-test-q4",
                    profile=sample_profile,
                    research_round=1,
                    reviewer_issues=reviewer_issues
                )

        for call_args in mock_search.call_args_list:
            q = call_args.kwargs.get("query") or call_args.args[0]
            captured_queries.append(q)

        for q in captured_queries:
            # In round 1, standard discovery query is used
            assert "scholarship fully funded" in q
            assert "Harvard University" not in q
            assert "Student fails" not in q

    @pytest.mark.asyncio
    async def test_legacy_string_reviewer_issues_do_not_leak_into_queries(self, sample_profile):
        """If reviewer_issues contains plain legacy strings, they must never leak into queries."""
        agent = ResearchEligibilityAgent()
        captured_queries = []

        mock_search = AsyncMock(return_value={"success": False, "error": "Search mocked"})

        # Pass legacy strings
        reviewer_issues = [
            "Technical University of Munich: Student fails published mandatory admission criteria.",
            "University of Oxford: Application deadline (2025-01-15) has passed and is expired; cannot present as active."
        ]

        with patch("app.agents.research_eligibility.gemini_service.search_grounded_discovery", mock_search):
            with patch("app.agents.research_eligibility.gemini_service.ensure_available"):
                await agent.execute_discovery_and_audit(
                    run_id="run-test-q5",
                    profile=sample_profile,
                    research_round=2,
                    reviewer_issues=reviewer_issues
                )

        for call_args in mock_search.call_args_list:
            q = call_args.kwargs.get("query") or call_args.args[0]
            captured_queries.append(q)

        assert len(captured_queries) > 0
        for q in captured_queries:
            assert "Student fails published mandatory admission criteria" not in q
            assert "expired; cannot present as active" not in q
            assert "fails" not in q.lower()
