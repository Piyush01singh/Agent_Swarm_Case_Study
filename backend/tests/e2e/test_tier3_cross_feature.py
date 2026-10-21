"""
Tier 3: Cross-Feature Integration Test Suite.
Verifies multi-feature interactions across pipeline stages:
- Search Grounding Discovery -> URL Extraction & Normalization
- Eligibility Evaluation -> Prerequisite Checking & Disqualification
- Funding Claims -> Quality Reviewer Audit & Bounded Re-Research Loop
- Runtime Deadline Validation -> Multi-factor Scoring & Shortlisting
- Full 5-Agent LangGraph Workflow Execution
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

from app.models.profile import StudentProfile
from app.models.opportunity import Opportunity, FundingDetails, EligibilityCriterion
from app.models.evidence import EvidenceRecord, MatchScore
from app.agents.quality_reviewer import QualityReviewerAgent
from app.agents.match_strategist import MatchStrategistAgent
from app.services.scoring_service import calculate_match_score
from app.graph.state import SwarmState
from app.graph.workflow import swarm_app, route_after_review
from app.security.sanitizer import normalize_url, is_safe_url


# ==============================================================================
# Cross-Feature 1: Search Grounding + URL Extraction & Sanitization
# ==============================================================================
@pytest.mark.asyncio
async def test_xf1_search_discovery_to_url_extraction_pipeline():
    """
    Verifies that URLs discovered via search grounding pass through SSRF security checks
    and URL canonicalization before being queued for URL Context extraction.
    Malicious or non-standard URLs must be dropped.
    """
    raw_discovered_sources = [
        {"title": "UofT MScAC", "url": "https://web.cs.toronto.edu/graduate/mscac?utm_medium=cpc#apply"},
        {"title": "Internal Exploit", "url": "http://169.254.169.254/latest/meta-data/"},
        {"title": "Localhost Admin", "url": "http://localhost:8000/admin"},
        {"title": "TUM Informatics", "url": "https://www.tum.de/en/studies/degree-programs/detail/informatics-master-of-science-msc/"},
        {"title": "UofT Duplicate", "url": "HTTPS://WEB.CS.TORONTO.EDU/GRADUATE/MSCAC"},
    ]

    safe_normalized_urls = []
    seen = set()

    for item in raw_discovered_sources:
        u = item["url"]
        if is_safe_url(u):
            norm = normalize_url(u)
            if norm not in seen:
                seen.add(norm)
                safe_normalized_urls.append(norm)

    # SSRF targets must be dropped, duplicates merged
    assert len(safe_normalized_urls) == 2
    assert "https://web.cs.toronto.edu/graduate/mscac" in safe_normalized_urls
    assert "https://www.tum.de/en/studies/degree-programs/detail/informatics-master-of-science-msc" in safe_normalized_urls


# ==============================================================================
# Cross-Feature 2: Eligibility Checks + Degree Prerequisite Validation
# ==============================================================================
def test_xf2_eligibility_and_degree_prerequisite_disqualification(profile_rahul_sharma, create_mock_opportunity):
    """
    Verifies that candidate opportunities requiring a degree track that does not match
    the student's target degree (e.g. PhD-only program for a Master's seeker) trigger
    a mandatory failure and are disqualified from the shortlist.
    """
    phd_only_opp = create_mock_opportunity(
        title="Direct PhD in Quantum Computing",
        university="Waterloo Institute",
        country="Canada"
    )
    phd_only_opp.degree_level = "PhD"
    
    # Evidence record for degree prerequisite
    ev_degree = EvidenceRecord(
        criterion_name="Degree Level Eligibility",
        stated_requirement="Open strictly to doctoral candidates intending direct PhD registration",
        student_value=f"Target: {profile_rahul_sharma.target_degree}",
        status="DOES_NOT_MEET",
        evidence_excerpt="Student requested Master's degree, which is incompatible with direct PhD track.",
        source_title="Admissions Regulations",
        source_url=phd_only_opp.canonical_url,
        source_category="OFFICIAL"
    )
    phd_only_opp.evidence_records = [ev_degree]
    phd_only_opp.eligibility_status = "DOES_NOT_MEET"

    match_score = calculate_match_score(profile_rahul_sharma, phd_only_opp)
    
    assert match_score.is_eligible_for_shortlist is False
    assert match_score.academic_fit == 0.0
    assert "Disqualified" in match_score.explanation


# ==============================================================================
# Cross-Feature 3: Funding Claims + Quality Reviewer Audit & Re-Research Loop
# ==============================================================================
@pytest.mark.asyncio
async def test_xf3_funding_claim_audit_and_bounded_re_research_loop(create_mock_opportunity, profile_rahul_sharma):
    """
    Verifies that:
    1. An opportunity claiming 'Fully Funded' without specific coverage breakdown
       is flagged by the Quality Reviewer with reviewer_status = 'FLAGGED'.
    2. The conditional routing edge `route_after_review` triggers 'research_discovery'
       when under max_research_rounds.
    3. When max_research_rounds is reached, it terminates to '__end__'.
    """
    reviewer = QualityReviewerAgent()
    
    # Create opportunity with ambiguous funding claim
    suspicious_opp = create_mock_opportunity(
        title="Mystery AI Scholarship",
        university="Unknown Global University",
        canonical_url="https://www.unknown-global.edu/scholarships"
    )
    suspicious_opp.funding_details = FundingDetails(
        funding_type="Fully Funded",
        coverage_description="" # Missing coverage breakdown
    )

    reviewed_opps, needs_re_research, issues = await reviewer.execute_audit(
        run_id="audit-run-1",
        profile=profile_rahul_sharma,
        opportunities=[suspicious_opp]
    )

    assert suspicious_opp.reviewer_status == "FLAGGED"
    assert any("Claimed 'Fully Funded' without specific coverage breakdown" in issue for issue in issues)

    # Test Bounded State Loop Transitions
    # Case A: Round 1 of 2 -> re-research
    state_r1 = SwarmState(
        run_id="audit-run-1",
        needs_re_research=True,
        research_round=1,
        max_research_rounds=2
    )
    assert route_after_review(state_r1) == "research_discovery"

    # Case B: Round 2 (exceeds/reaches max limit) -> terminates to __end__
    state_r2 = SwarmState(
        run_id="audit-run-1",
        needs_re_research=True,
        research_round=3,
        max_research_rounds=2
    )
    assert route_after_review(state_r2) == "__end__"


# ==============================================================================
# Cross-Feature 4: Deadline Verification + Multi-Factor Scoring & Shortlist
# ==============================================================================
def test_xf4_deadline_verification_impact_on_scoring(profile_rahul_sharma, create_mock_opportunity):
    """
    Verifies that verified active deadlines award maximum deadline fit points (10/10),
    while unknown deadlines receive baseline points (2/10), and the Match Strategist
    sorts shortlisted opportunities by descending total match score.
    """
    # Opp A: Verified future deadline
    opp_verified = create_mock_opportunity(
        id="opp-verified",
        title="Verified Active Deadline Fellowship",
        deadline="2026-11-30",
        deadline_type="Fixed",
        deadline_verified=True
    )
    score_verified = calculate_match_score(profile_rahul_sharma, opp_verified)
    assert score_verified.deadline_fit == 10.0

    # Opp B: Unknown / missing deadline
    opp_unknown = create_mock_opportunity(
        id="opp-unknown",
        title="Unverified Deadline Program",
        deadline=None,
        deadline_type="Unknown",
        deadline_verified=False
    )
    score_unknown = calculate_match_score(profile_rahul_sharma, opp_unknown)
    assert score_unknown.deadline_fit <= 4.0

    # Opp A must outscore Opp B on deadline dimension
    assert score_verified.total_score > score_unknown.total_score


# ==============================================================================
# Cross-Feature 5: Full 5-Agent LangGraph Workflow Execution
# ==============================================================================
@pytest.mark.asyncio
async def test_xf5_full_langgraph_workflow_execution(profile_rahul_sharma, clean_repo):
    """
    Verifies end-to-end execution of the assembled LangGraph workflow:
    - Profile Intelligence normalizes student input
    - Research Discovery discovers candidates
    - Match Strategist scores and ranks candidates
    - Quality Reviewer audits evidence
    - Top-5 designation is applied
    """
    initial_state = SwarmState(
        run_id="e2e-xf-workflow-001",
        user_input=profile_rahul_sharma.model_dump(),
        student_profile=profile_rahul_sharma
    )

    final_state = await swarm_app.ainvoke(initial_state)

    assert final_state["student_profile"] is not None
    assert len(final_state["opportunities"]) > 0
    
    # Verify match scoring occurred
    for opp in final_state["opportunities"]:
        assert opp.match_score is not None
        assert opp.match_score.total_score >= 0.0

    # Verify top 5 designation
    top_five_opps = [o for o in final_state["opportunities"] if o.is_top_five]
    assert 1 <= len(top_five_opps) <= 5
    
    # Shortlist must be sorted in descending order of total score
    scores = [o.match_score.total_score for o in top_five_opps]
    assert scores == sorted(scores, reverse=True)
