from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, END
from app.graph.state import SwarmState
from app.agents.profile_intelligence import ProfileIntelligenceAgent
from app.agents.research_eligibility import ResearchEligibilityAgent
from app.agents.match_strategist import MatchStrategistAgent
from app.agents.quality_reviewer import QualityReviewerAgent
from app.agents.application_coach import ApplicationCoachAgent
from app.db.repository import repository

profile_agent = ProfileIntelligenceAgent()
research_agent = ResearchEligibilityAgent()
match_agent = MatchStrategistAgent()
reviewer_agent = QualityReviewerAgent()
coach_agent = ApplicationCoachAgent()


async def node_profile_intelligence(state: SwarmState) -> Dict[str, Any]:
    """Node 1: Profile Intelligence Extraction & Verification."""
    profile = await profile_agent.execute(
        run_id=state.run_id,
        user_input=state.user_input,
        resume_text=state.resume_text,
        transcript_text=state.transcript_text,
        github_url=state.github_url
    )
    await repository.update_research_run_status(state.run_id, status="RUNNING", current_phase="DISCOVERY")
    return {"student_profile": profile, "current_phase": "DISCOVERY"}


async def node_research_discovery(state: SwarmState) -> Dict[str, Any]:
    """Node 2: Search Grounding, Page Audit & Eligibility Assessment."""
    if not state.student_profile:
        raise ValueError("Cannot research without student profile")
        
    opps = await research_agent.execute_discovery_and_audit(
        run_id=state.run_id,
        profile=state.student_profile,
        research_round=state.research_round,
        reviewer_issues=state.reviewer_issues
    )

    # Feature F13: Cross-Round Candidate Preservation
    approved = list(state.approved_opportunities or [])
    approved_ids = {o.id for o in approved}
    approved_urls = {o.canonical_url for o in approved}

    combined_opps = list(approved)
    for opp in opps:
        if opp.id not in approved_ids and opp.canonical_url not in approved_urls:
            combined_opps.append(opp)
            
    await repository.update_research_run_status(state.run_id, status="RUNNING", current_phase="RANKING")
    return {"opportunities": combined_opps, "current_phase": "RANKING"}


async def node_match_strategist(state: SwarmState) -> Dict[str, Any]:
    """Node 3: Deterministic Scoring & Top-5 Recommendation."""
    if not state.student_profile:
        raise ValueError("Cannot score without student profile")
        
    ranked_opps = await match_agent.execute_ranking(
        run_id=state.run_id,
        profile=state.student_profile,
        opportunities=state.opportunities
    )
    await repository.update_research_run_status(state.run_id, status="RUNNING", current_phase="REVIEW")
    return {"opportunities": ranked_opps, "current_phase": "REVIEW"}


async def node_quality_reviewer(state: SwarmState) -> Dict[str, Any]:
    """Node 4: Independent Evidence Audit & Self-Correction Evaluation."""
    if not state.student_profile:
        raise ValueError("Cannot review without student profile")
        
    reviewed_opps, needs_re_research, issues = await reviewer_agent.execute_audit(
        run_id=state.run_id,
        profile=state.student_profile,
        opportunities=state.opportunities
    )

    # Feature F13: Aggregate approved opportunities across iterations
    approved_dict = {o.id: o for o in (state.approved_opportunities or [])}
    for opp in reviewed_opps:
        if opp.reviewer_status == "APPROVED":
            approved_dict[opp.id] = opp
    all_approved = list(approved_dict.values())

    # Feature F12: Bounded Quality Reviewer Loop Counter
    new_round = state.research_round + 1 if needs_re_research else state.research_round
    is_terminal = (not needs_re_research) or (new_round > state.max_research_rounds)
    
    return {
        "opportunities": reviewed_opps,
        "approved_opportunities": all_approved,
        "needs_re_research": needs_re_research,
        "reviewer_issues": issues,
        "research_round": new_round,
        "current_phase": "COMPLETED" if is_terminal else "RE_RESEARCH"
    }


async def node_application_coaching(state: SwarmState) -> Dict[str, Any]:
    """
    Node 5: On-Demand Application Coaching & SOP Drafting (Agent 4).
    Operational Boundary: Invoked on-demand per selected opportunity
    via POST /api/opportunities/{id}/sop, or optionally as a terminal node.
    """
    if not state.student_profile or not state.opportunities:
        return {"current_phase": "COMPLETED"}

    top_opp = next((o for o in state.opportunities if o.is_top_five), state.opportunities[0])
    draft = await coach_agent.execute_sop_draft(
        run_id=state.run_id,
        profile=state.student_profile,
        opportunity=top_opp,
        user_notes=state.user_input.get("specific_interests")
    )
    return {"current_phase": "COMPLETED"}


# Function Aliases for flexible import conventions
node_quality_review = node_quality_reviewer
node_match_strategy = node_match_strategist


def route_after_review(state: SwarmState) -> Literal["research_discovery", "match_strategy", "__end__"]:
    """
    Conditional Edge: bounded re-research loop if reviewer flagged issues.
    Routes to:
    - 'research_discovery': when issues require alternative programs or official retrieval (needs_re_research=True)
    - 'match_strategy': when only candidate ranking recalculation is needed (needs_re_ranking=True)
    - '__end__': when audit passes or max_research_rounds is reached.
    """
    if state.needs_re_research and state.research_round <= state.max_research_rounds:
        return "research_discovery"
    if getattr(state, "needs_re_ranking", False):
        return "match_strategy"
    return "__end__"


# Assemble the LangGraph workflow
workflow = StateGraph(SwarmState)

workflow.add_node("profile_intelligence", node_profile_intelligence)
workflow.add_node("research_discovery", node_research_discovery)
workflow.add_node("match_strategist", node_match_strategist)
workflow.add_node("quality_reviewer", node_quality_reviewer)
workflow.add_node("application_coaching", node_application_coaching)

workflow.set_entry_point("profile_intelligence")
workflow.add_edge("profile_intelligence", "research_discovery")
workflow.add_edge("research_discovery", "match_strategist")
workflow.add_edge("match_strategist", "quality_reviewer")

workflow.add_conditional_edges(
    "quality_reviewer",
    route_after_review,
    {
        "research_discovery": "research_discovery",
        "match_strategy": "match_strategist",
        "__end__": END
    }
)

swarm_app = workflow.compile()
