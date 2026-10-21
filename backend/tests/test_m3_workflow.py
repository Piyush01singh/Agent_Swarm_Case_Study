"""
Milestone M3 Test Suite: 5-Agent Workflow, Bounded Quality Reviewer Loop,
Candidate Preservation, and Fault Recovery.
"""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone, timedelta

from app.graph.state import SwarmState
from app.graph.workflow import (
    swarm_app,
    route_after_review,
    node_profile_intelligence,
    node_research_discovery,
    node_match_strategist,
    node_match_strategy,
    node_quality_reviewer,
    node_quality_review,
    node_application_coaching
)
from app.agents.quality_reviewer import QualityReviewerAgent, ReviewerIssue
from app.models.profile import StudentProfile
from app.models.opportunity import Opportunity, FundingDetails
from app.models.evidence import EvidenceRecord
from app.db.repository import repository
from tests.fixtures.opportunities import get_fixture_opportunity_models


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


@pytest.mark.asyncio
async def test_m3_f11_swarm_state_schema_attributes():
    """F11: Verify SwarmState schema fields and default initialization."""
    state = SwarmState(run_id="run-test-schema")
    assert state.research_round == 1
    assert state.max_research_rounds == 2
    assert state.opportunities == []
    assert state.approved_opportunities == []
    assert state.reviewer_issues == []
    assert state.needs_re_research is False
    assert state.current_phase == "INITIALIZED"

    # Verify string normalization in reviewer_issues
    state_with_strings = SwarmState(
        run_id="run-test-str",
        reviewer_issues=["Issue 1: Deadline expired", "Issue 2: Secondary source"]
    )
    assert len(state_with_strings.reviewer_issues) == 2
    assert isinstance(state_with_strings.reviewer_issues[0], dict)
    assert state_with_strings.reviewer_issues[0]["description"] == "Issue 1: Deadline expired"
    assert state_with_strings.reviewer_issues[0]["issue_type"] == "GENERAL"


def test_m3_f11_reviewer_issue_dual_dict_str_compatibility():
    """F11: Verify ReviewerIssue functions as both a dict and a string."""
    issue = ReviewerIssue({
        "opportunity_id": "opp-123",
        "university": "University of Toronto",
        "program_name": "MSc Computer Science",
        "issue_type": "EXPIRED_DEADLINE",
        "description": "University of Toronto: Application deadline has passed and is expired; cannot present as active.",
        "issue": "University of Toronto: Application deadline has passed and is expired; cannot present as active."
    })
    
    # Dict behavior
    assert isinstance(issue, dict)
    assert issue["issue_type"] == "EXPIRED_DEADLINE"
    assert issue.get("university") == "University of Toronto"
    
    # String behavior
    assert "expired" in issue.lower()
    assert "cannot present as active" in issue
    assert str(issue).startswith("University of Toronto")


@pytest.mark.asyncio
async def test_m3_f12_quality_reviewer_expired_deadline_triggers_re_research(sample_profile):
    """F12: Expired deadline triggers needs_re_research=True and structured ReviewerIssue."""
    reviewer = QualityReviewerAgent()
    yesterday = (datetime.now(timezone.utc).date() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    expired_opp = Opportunity(
        id="opp-exp",
        run_id="run-exp",
        canonical_url="https://utoronto.ca",
        title="UofT Fellowship",
        program_name="MSc CS",
        university="University of Toronto",
        country="Canada",
        degree_level="Master's",
        field="CS",
        deadline=yesterday,
        deadline_type="Fixed",
        funding_details=FundingDetails(funding_type="Partial", coverage_description="Tuition waiver")
    )

    reviewed_opps, needs_re_research, issues = await reviewer.execute_audit(
        run_id="run-exp",
        profile=sample_profile,
        opportunities=[expired_opp]
    )

    assert needs_re_research is True
    assert expired_opp.reviewer_status == "FLAGGED"
    assert len(issues) >= 1
    assert any(iss.get("issue_type") == "EXPIRED_DEADLINE" for iss in issues if isinstance(iss, dict))
    assert any("expired" in iss.lower() for iss in issues)


@pytest.mark.asyncio
async def test_m3_f12_route_after_review_bounded_loop_transitions():
    """F12: Verify bounded loop transitions in route_after_review."""
    # Under limit -> retry
    state_r1 = SwarmState(run_id="run-1", needs_re_research=True, research_round=1, max_research_rounds=2)
    assert route_after_review(state_r1) == "research_discovery"

    # At limit -> terminates
    state_r2 = SwarmState(run_id="run-1", needs_re_research=True, research_round=3, max_research_rounds=2)
    assert route_after_review(state_r2) == "__end__"

    # Clean audit -> terminates
    state_clean = SwarmState(run_id="run-1", needs_re_research=False, research_round=1)
    assert route_after_review(state_clean) == "__end__"

    # Re-ranking route
    state_rerank = SwarmState(run_id="run-1", needs_re_research=False, needs_re_ranking=True, research_round=1)
    assert route_after_review(state_rerank) == "match_strategy"


@pytest.mark.asyncio
async def test_m3_f13_cross_round_candidate_preservation(sample_profile):
    """F13: Approved opportunities from round 1 must not be overwritten in round 2."""
    opp_approved = Opportunity(
        id="opp-approved-r1",
        run_id="run-f13",
        canonical_url="https://tum.de/msc",
        title="TUM MSc Informatics",
        program_name="Informatics",
        university="Technical University of Munich",
        country="Germany",
        degree_level="Master's",
        field="Informatics",
        reviewer_status="APPROVED",
        funding_details=FundingDetails(funding_type="Fully Funded", coverage_description="Stipend")
    )
    
    opp_new_r2 = Opportunity(
        id="opp-new-r2",
        run_id="run-f13",
        canonical_url="https://nus.edu.sg/msc",
        title="NUS Fellowship",
        program_name="MSc CS",
        university="National University of Singapore",
        country="Singapore",
        degree_level="Master's",
        field="CS",
        funding_details=FundingDetails(funding_type="Partial", coverage_description="Tuition")
    )

    state = SwarmState(
        run_id="run-f13",
        student_profile=sample_profile,
        research_round=2,
        approved_opportunities=[opp_approved],
        reviewer_issues=[{"issue": "Search alternative programs in Singapore"}]
    )

    with patch("app.graph.workflow.research_agent.execute_discovery_and_audit", new_callable=AsyncMock) as mock_disc:
        mock_disc.return_value = [opp_new_r2]
        res = await node_research_discovery(state)

        # Opportunities must contain BOTH the preserved approved opportunity and the new opportunity
        opp_ids = [o.id for o in res["opportunities"]]
        assert "opp-approved-r1" in opp_ids
        assert "opp-new-r2" in opp_ids
        assert len(res["opportunities"]) == 2


@pytest.mark.asyncio
async def test_m3_f14_comprehensive_reviewer_audit_shortlist(sample_profile):
    """F14: Reviewer audits all candidates in the shortlist, not just index 0."""
    opp1 = Opportunity(
        id="opp-f14-1",
        run_id="run-f14",
        canonical_url="https://utoronto.ca",
        title="UofT Fellowship",
        program_name="MSc CS",
        university="University of Toronto",
        country="Canada",
        degree_level="Master's",
        field="CS",
        funding_details=FundingDetails(funding_type="Partial", coverage_description="Waiver")
    )
    opp2 = Opportunity(
        id="opp-f14-2",
        run_id="run-f14",
        canonical_url="https://unverified-blog.org/scholarship",
        title="Blog Scholarship",
        program_name="MSc CS",
        university="Blog University",
        country="Canada",
        degree_level="Master's",
        field="CS",
        official_source_urls=["https://unverified-blog.org/scholarship"],
        funding_details=FundingDetails(funding_type="Partial", coverage_description="Waiver")
    )

    reviewer = QualityReviewerAgent()
    reviewed, needs_re, issues = await reviewer.execute_audit(
        run_id="run-f14",
        profile=sample_profile,
        opportunities=[opp1, opp2]
    )

    assert opp1.reviewer_status == "APPROVED"
    assert opp2.reviewer_status == "FLAGGED"
    assert opp2.evidence_quality == "SECONDARY"
    assert needs_re is True


@pytest.mark.asyncio
async def test_m3_f15_node_application_coaching_operational_boundary(sample_profile):
    """F15: Application Coach node drafts SOP for selected top opportunity on demand."""
    top_opp = Opportunity(
        id="opp-coach-1",
        run_id="run-coach",
        canonical_url="https://utoronto.ca",
        title="Vector Institute AI Fellowship",
        program_name="MSc Applied Computing",
        university="University of Toronto",
        country="Canada",
        degree_level="Master's",
        field="AI",
        is_top_five=True,
        funding_details=FundingDetails(funding_type="Fully Funded", coverage_description="Full funding")
    )

    state = SwarmState(
        run_id="run-coach",
        student_profile=sample_profile,
        opportunities=[top_opp]
    )

    res = await node_application_coaching(state)
    assert res["current_phase"] == "COMPLETED"
    
    draft = await repository.get_application_draft(top_opp.id)
    assert draft is not None
    assert draft.program_name == top_opp.program_name
    assert draft.university == top_opp.university
    assert "Rahul Sharma" in draft.sop_content


@pytest.mark.asyncio
async def test_m3_f16_repository_evidence_records_and_opportunity_by_id():
    """F16: Evidence records persistence and crash-free get_opportunity_by_id."""
    await repository.reset_all_data()

    # 1. Non-existent ID returns None without IndexError
    missing_opp = await repository.get_opportunity_by_id("non-existent-uuid")
    assert missing_opp is None

    # 2. Existing opportunity retrieval
    test_opp = Opportunity(
        id="opp-repo-test",
        run_id="run-repo-test",
        canonical_url="https://tum.de",
        title="TUM Informatics",
        program_name="Informatics",
        university="Technical University of Munich",
        country="Germany",
        degree_level="Master's",
        field="Informatics",
        funding_details=FundingDetails(funding_type="Partial", coverage_description="Waiver")
    )
    await repository.save_opportunities("run-repo-test", [test_opp])
    found_opp = await repository.get_opportunity_by_id("opp-repo-test")
    assert found_opp is not None
    assert found_opp.id == "opp-repo-test"

    # 3. Evidence records persistence and retrieval
    ev = EvidenceRecord(
        opportunity_id="opp-repo-test",
        run_id="run-repo-test",
        criterion_name="CGPA Minimum",
        stated_requirement="Minimum 7.5/10 CGPA",
        student_value="8.2/10",
        status="MEETS",
        evidence_excerpt="Published cutoff is 7.5 CGPA.",
        source_url="https://tum.de/admissions"
    )
    await repository.save_evidence_records([ev])

    by_opp = await repository.get_evidence_for_opportunity("opp-repo-test")
    assert len(by_opp) == 1
    assert by_opp[0].criterion_name == "CGPA Minimum"
    assert by_opp[0].status == "MEETS"

    by_run = await repository.get_evidence_records(run_id="run-repo-test")
    assert len(by_run) == 1
    assert by_run[0].opportunity_id == "opp-repo-test"
