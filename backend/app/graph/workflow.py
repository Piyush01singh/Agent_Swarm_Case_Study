from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, END
from app.graph.state import SwarmState
from app.agents.profile_intelligence import ProfileIntelligenceAgent
from app.agents.research_eligibility import ResearchEligibilityAgent
from app.agents.match_strategist import MatchStrategistAgent
from app.agents.quality_reviewer import QualityReviewerAgent
from app.db.repository import repository

profile_agent = ProfileIntelligenceAgent()
research_agent = ResearchEligibilityAgent()
match_agent = MatchStrategistAgent()
reviewer_agent = QualityReviewerAgent()

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
        research_round=state.research_round
    )
    await repository.update_research_run_status(state.run_id, status="RUNNING", current_phase="RANKING")
    return {"opportunities": opps, "current_phase": "RANKING"}

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
    new_round = state.research_round + 1 if needs_re_research else state.research_round
    return {
        "opportunities": reviewed_opps,
        "needs_re_research": needs_re_research,
        "reviewer_issues": issues,
        "research_round": new_round,
        "current_phase": "COMPLETED" if not needs_re_research or new_round > state.max_research_rounds else "RE_RESEARCH"
    }

def route_after_review(state: SwarmState) -> Literal["research_discovery", "__end__"]:
    """Conditional Edge: bounded re-research loop if reviewer flagged issues."""
    if state.needs_re_research and state.research_round <= state.max_research_rounds:
        return "research_discovery"
    return "__end__"

# Assemble the LangGraph workflow
workflow = StateGraph(SwarmState)

workflow.add_node("profile_intelligence", node_profile_intelligence)
workflow.add_node("research_discovery", node_research_discovery)
workflow.add_node("match_strategist", node_match_strategist)
workflow.add_node("quality_reviewer", node_quality_reviewer)

workflow.set_entry_point("profile_intelligence")
workflow.add_edge("profile_intelligence", "research_discovery")
workflow.add_edge("research_discovery", "match_strategist")
workflow.add_edge("match_strategist", "quality_reviewer")

workflow.add_conditional_edges(
    "quality_reviewer",
    route_after_review,
    {
        "research_discovery": "research_discovery",
        "__end__": END
    }
)

swarm_app = workflow.compile()
