"""
Comprehensive unit and integration test suite for Agent 5: Quality Reviewer Agent.
Validates official source verification, funding grounding, runtime deadline checks,
re-research loop routing, and Gemini review fallback handling.
"""

import pytest
from unittest.mock import patch, AsyncMock, PropertyMock
from datetime import datetime, timezone, timedelta

from app.agents.quality_reviewer import QualityReviewerAgent, ReviewerIssue
from app.graph.workflow import node_quality_reviewer, route_after_review
from app.graph.state import SwarmState
from app.models.profile import StudentProfile
from app.models.opportunity import Opportunity, FundingDetails
from app.models.evidence import EvidenceRecord
from app.services.gemini_service import gemini_service, GeminiService


@pytest.fixture
def sample_profile() -> StudentProfile:
    return StudentProfile(
        full_name="Rahul Sharma",
        current_degree="B.Tech Computer Science",
        cgpa=8.2,
        grading_scale="10.0",
        target_degree="Master's",
        target_field="Computer Science / Artificial Intelligence",
        target_countries=["Canada", "Germany", "Singapore"]
    )


def create_base_opportunity(
    opp_id: str = "opp-test-1",
    university: str = "University of Toronto",
    canonical_url: str = "https://web.cs.toronto.edu/graduate/mscac",
    official_source_urls: list = None,
    funding_type: str = "Fully Funded",
    coverage_description: str = "$17,500 CAD stipend + research internship",
    deadline: str = None,
    deadline_type: str = "Rolling",
    evidence_records: list = None,
    eligibility_status: str = "MEETS",
    evidence_quality: str = "OFFICIAL",
    is_top_five: bool = False
) -> Opportunity:
    if official_source_urls is None:
        official_source_urls = [canonical_url]
    if evidence_records is None:
        evidence_records = [
            EvidenceRecord(
                opportunity_id=opp_id,
                criterion_name="Minimum CGPA",
                stated_requirement="Minimum B+ average (approx 7.8/10 CGPA)",
                student_value="8.2/10",
                status="MEETS",
                evidence_excerpt="Applicants must demonstrate a minimum B+ standing in senior level work.",
                source_url=canonical_url
            )
        ]

    return Opportunity(
        id=opp_id,
        run_id="run-qr-test",
        canonical_url=canonical_url,
        official_source_urls=official_source_urls,
        title=f"{university} Graduate Opportunity",
        program_name="MSc Applied Computing",
        university=university,
        country="Canada",
        degree_level="Master's",
        field="Computer Science",
        deadline=deadline,
        deadline_type=deadline_type,
        funding_details=FundingDetails(
            funding_type=funding_type,
            coverage_description=coverage_description
        ),
        evidence_records=evidence_records,
        evidence_quality=evidence_quality,
        eligibility_status=eligibility_status,
        is_top_five=is_top_five
    )


@pytest.mark.asyncio
async def test_official_domain_approval(sample_profile):
    """
    1. Official domain approval:
       An opportunity sourced from an official educational domain (.edu, .ca, etc.)
       with valid funding and active/rolling deadline must be approved.
    """
    reviewer = QualityReviewerAgent()
    opp = create_base_opportunity(
        canonical_url="https://web.cs.toronto.edu/graduate/mscac",
        official_source_urls=["https://web.cs.toronto.edu/graduate/mscac"],
        evidence_quality="OFFICIAL"
    )

    with patch.object(GeminiService, "is_available", new_callable=PropertyMock, return_value=False):
        reviewed_opps, needs_re_research, issues = await reviewer.execute_audit(
            run_id="run-qr-test",
            profile=sample_profile,
            opportunities=[opp]
        )

    assert len(reviewed_opps) == 1
    assert opp.evidence_quality == "OFFICIAL"
    assert opp.reviewer_status == "APPROVED"
    assert needs_re_research is False
    assert len(issues) == 0


@pytest.mark.asyncio
async def test_secondary_domain_flagged_for_reresearch(sample_profile):
    """
    2. Secondary domain flagged for re-research:
       An opportunity from a secondary aggregator blog (e.g., scholarship-positions.com)
       must be flagged with evidence_quality='SECONDARY' and trigger re-research.
    """
    reviewer = QualityReviewerAgent()
    opp = create_base_opportunity(
        canonical_url="https://scholarship-positions.com/toronto-award",
        official_source_urls=["https://scholarship-positions.com/toronto-award"],
        evidence_quality="OFFICIAL"
    )

    with patch.object(GeminiService, "is_available", new_callable=PropertyMock, return_value=False):
        reviewed_opps, needs_re_research, issues = await reviewer.execute_audit(
            run_id="run-qr-test",
            profile=sample_profile,
            opportunities=[opp]
        )

    assert opp.evidence_quality == "SECONDARY"
    assert opp.reviewer_status == "FLAGGED"
    assert needs_re_research is True
    assert len(issues) >= 1
    assert any("Only secondary sources found" in str(iss) or iss.get("issue_type") == "SECONDARY_SOURCE" for iss in issues)


@pytest.mark.asyncio
async def test_unsupported_fully_funded_flagged(sample_profile):
    """
    3. Unsupported funding claim flagged:
       Claiming 'Fully Funded' without a concrete coverage breakdown must be flagged.
    """
    reviewer = QualityReviewerAgent()
    opp = create_base_opportunity(
        canonical_url="https://utoronto.ca/fellowship",
        funding_type="Fully Funded",
        coverage_description=""
    )

    with patch.object(GeminiService, "is_available", new_callable=PropertyMock, return_value=False):
        reviewed_opps, needs_re_research, issues = await reviewer.execute_audit(
            run_id="run-qr-test",
            profile=sample_profile,
            opportunities=[opp]
        )

    assert opp.reviewer_status == "FLAGGED"
    assert any("Claimed 'Fully Funded' without specific coverage breakdown" in str(iss) or iss.get("issue_type") == "MISSING_COVERAGE" for iss in issues)


@pytest.mark.asyncio
async def test_supported_funding_approved(sample_profile):
    """
    4. Supported funding claim approved:
       A 'Fully Funded' claim with verifiable coverage description is approved.
    """
    reviewer = QualityReviewerAgent()
    opp = create_base_opportunity(
        canonical_url="https://utoronto.ca/fellowship",
        funding_type="Fully Funded",
        coverage_description="$17,500 CAD scholarship + full tuition coverage"
    )

    with patch.object(GeminiService, "is_available", new_callable=PropertyMock, return_value=False):
        reviewed_opps, needs_re_research, issues = await reviewer.execute_audit(
            run_id="run-qr-test",
            profile=sample_profile,
            opportunities=[opp]
        )

    assert opp.reviewer_status == "APPROVED"
    assert opp.funding_details.coverage_description == "$17,500 CAD scholarship + full tuition coverage"


@pytest.mark.asyncio
async def test_missing_deadline_marked_unknown(sample_profile):
    """
    5. Missing deadline marked unknown:
       When no deadline is captured, it must be marked as 'Unknown' with deadline_verified=False.
    """
    reviewer = QualityReviewerAgent()
    opp = create_base_opportunity(
        canonical_url="https://utoronto.ca/msc",
        deadline=None,
        deadline_type="Unknown"
    )

    with patch.object(GeminiService, "is_available", new_callable=PropertyMock, return_value=False):
        reviewed_opps, needs_re_research, issues = await reviewer.execute_audit(
            run_id="run-qr-test",
            profile=sample_profile,
            opportunities=[opp]
        )

    assert opp.deadline_type == "Unknown"
    assert opp.deadline_verified is False
    assert opp.deadline_status == "UNKNOWN"


@pytest.mark.asyncio
async def test_reviewer_node_state_update_in_graph(sample_profile):
    """
    6. Reviewer node state update in graph:
       node_quality_reviewer must update research_round, needs_re_research, and current_phase.
    """
    opp = create_base_opportunity(
        canonical_url="https://unverified-blog.org/scholarship",
        official_source_urls=["https://unverified-blog.org/scholarship"]
    )
    state = SwarmState(
        run_id="run-state-test",
        student_profile=sample_profile,
        opportunities=[opp],
        research_round=1,
        max_research_rounds=2
    )

    with patch.object(GeminiService, "is_available", new_callable=PropertyMock, return_value=False):
        update = await node_quality_reviewer(state)

    assert update["needs_re_research"] is True
    assert update["research_round"] == 2
    assert update["current_phase"] == "RE_RESEARCH"
    assert len(update["reviewer_issues"]) >= 1


@pytest.mark.asyncio
async def test_re_research_loop_bounded_termination():
    """
    7. Re-research loop bounded termination:
       route_after_review must return '__end__' when research_round > max_research_rounds,
       preventing infinite execution loops.
    """
    # Case A: Within bounds -> re-research
    state_retry = SwarmState(
        run_id="run-loop-test",
        needs_re_research=True,
        research_round=2,
        max_research_rounds=2
    )
    assert route_after_review(state_retry) == "research_discovery"

    # Case B: Exceeded bounds -> terminate
    state_terminate = SwarmState(
        run_id="run-loop-test",
        needs_re_research=True,
        research_round=3,
        max_research_rounds=2
    )
    assert route_after_review(state_terminate) == "__end__"

    # Case C: Audit clean -> terminate
    state_clean = SwarmState(
        run_id="run-loop-test",
        needs_re_research=False,
        research_round=1,
        max_research_rounds=2
    )
    assert route_after_review(state_clean) == "__end__"


@pytest.mark.asyncio
async def test_gemini_reviewer_audit_mocked_failure_handling(sample_profile):
    """
    8. Gemini reviewer audit mocked failure handling:
       When Gemini audit detects evidence discrepancies, candidate is flagged and
       needs_re_research is set to True.
    """
    reviewer = QualityReviewerAgent()
    opp = create_base_opportunity(
        canonical_url="https://web.cs.toronto.edu/mscac",
        is_top_five=True
    )

    mock_audit_response = {
        "success": True,
        "data": {
            "approved": False,
            "issues_detected": [
                {
                    "issue": "Published transcript conversion guide requires minimum 8.5 CGPA for Indian tier-2 institutions",
                    "severity": "HIGH"
                }
            ]
        }
    }

    with patch.object(GeminiService, "is_available", new_callable=PropertyMock, return_value=True):
        with patch.object(gemini_service, "review_evidence_and_claims", new_callable=AsyncMock) as mock_gemini:
            mock_gemini.return_value = mock_audit_response
            reviewed_opps, needs_re_research, issues = await reviewer.execute_audit(
                run_id="run-qr-test",
                profile=sample_profile,
                opportunities=[opp]
            )

    assert opp.reviewer_status == "FLAGGED"
    assert needs_re_research is True
    assert any("transcript conversion guide" in str(iss) for iss in issues)


@pytest.mark.asyncio
async def test_reviewer_handles_gemini_service_unavailable(sample_profile):
    """
    9. Graceful offline fallback when Gemini service is unavailable:
       When gemini_service.is_available is False, reviewer executes full rule-based
       audits without throwing an unhandled exception.
    """
    reviewer = QualityReviewerAgent()
    opp = create_base_opportunity(
        canonical_url="https://tum.de/in/msc",
        official_source_urls=["https://tum.de/in/msc"]
    )

    with patch.object(GeminiService, "is_available", new_callable=PropertyMock, return_value=False):
        reviewed_opps, needs_re_research, issues = await reviewer.execute_audit(
            run_id="run-qr-offline",
            profile=sample_profile,
            opportunities=[opp]
        )

    assert len(reviewed_opps) == 1
    assert opp.reviewer_status == "APPROVED"
    assert needs_re_research is False
    assert len(issues) == 0
