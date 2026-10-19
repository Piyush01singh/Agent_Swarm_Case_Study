import pytest
from app.graph.state import SwarmState
from app.graph.workflow import swarm_app, route_after_review
from app.models.profile import StudentProfile

def test_route_after_review_conditional_logic():
    # State with no re-research needed
    state_done = SwarmState(run_id="run-1", needs_re_research=False, research_round=1)
    assert route_after_review(state_done) == "__end__"
    
    # State with re-research needed and under max rounds
    state_retry = SwarmState(run_id="run-1", needs_re_research=True, research_round=1, max_research_rounds=2)
    assert route_after_review(state_retry) == "research_discovery"
    
    # State with re-research needed but reached max rounds limit
    state_limit = SwarmState(run_id="run-1", needs_re_research=True, research_round=3, max_research_rounds=2)
    assert route_after_review(state_limit) == "__end__"

@pytest.mark.asyncio
async def test_full_graph_workflow_execution():
    profile = StudentProfile(
        full_name="Rahul Sharma",
        current_degree="B.Tech Computer Science",
        cgpa=8.2,
        target_degree="Master's",
        target_field="Computer Science / Artificial Intelligence",
        target_countries=["Canada", "Germany", "Singapore"]
    )
    initial_state = SwarmState(
        run_id="test-run-123",
        user_input=profile.model_dump(),
        student_profile=profile
    )
    final_state = await swarm_app.ainvoke(initial_state)
    
    assert final_state["student_profile"] is not None
    assert len(final_state["opportunities"]) > 0
    # Top 5 should be designated
    top_fives = [o for o in final_state["opportunities"] if o.is_top_five]
    assert len(top_fives) <= 5
    assert len(top_fives) > 0
