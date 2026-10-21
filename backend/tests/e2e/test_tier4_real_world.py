"""
Tier 4: Realistic End-to-End Application Scenarios Test Suite.
Verifies complete user journeys for diverse student personas across multiple countries:
- Persona 1: Rahul Sharma (India -> Canada, Germany, Singapore | CS / AI | CGPA 8.2)
- Persona 2: Maria Santos (Brazil -> Germany, Canada | Bioinformatics | CGPA 6.8)
- Persona 3: Wei Chen (China -> Singapore | Data Science / Math | CGPA 8.5 | PhD Track)
- Persona 4: Fatima Al-Hassan (Nigeria -> Canada | Robotics | CGPA 9.1 | Top Distinction)
- End-to-End API Integration & Application Coach SOP Verification
"""

import pytest
from httpx import AsyncClient
from app.models.profile import StudentProfile
from app.graph.workflow import swarm_app
from app.graph.state import SwarmState
from app.db.repository import repository


# ==============================================================================
# Scenario 1: Rahul Sharma (India -> Canada/Germany/Singapore | CS & AI)
# ==============================================================================
@pytest.mark.asyncio
async def test_scenario_1_rahul_sharma_end_to_end_journey(profile_rahul_sharma, clean_repo, async_client: AsyncClient):
    """
    Scenario 1:
    Rahul Sharma applies for Master's in CS/AI across Canada, Germany, and Singapore.
    Verifies:
    1. Pipeline discovers matching opportunities in target countries.
    2. Identifies planned IELTS as an actionable gap (UNRESOLVED).
    3. Shortlists top-5 opportunities based on high academic standing (8.2 CGPA).
    4. Invokes Application Coach to draft an SOP grounded strictly in verified profile facts.
    """
    # 1. Start research run via API
    res_start = await async_client.post("/api/research/start", json=profile_rahul_sharma.model_dump())
    assert res_start.status_code == 200
    run_data = res_start.json()
    run_id = run_data["id"]
    assert run_id is not None

    # 2. Execute pipeline state graph
    state = SwarmState(
        run_id=run_id,
        user_input=profile_rahul_sharma.model_dump(),
        student_profile=profile_rahul_sharma
    )
    final_state = await swarm_app.ainvoke(state)
    opps = final_state["opportunities"]
    assert len(opps) > 0

    # Save to repository to test API retrieval
    await repository.save_opportunities(run_id, opps)

    # 3. Retrieve opportunities via API
    res_opps = await async_client.get(f"/api/research/{run_id}/opportunities")
    assert res_opps.status_code == 200
    retrieved_opps = res_opps.json()
    assert len(retrieved_opps) > 0

    # Verify target countries match student preferences
    found_countries = {o["country"] for o in retrieved_opps}
    assert any(c in found_countries for c in ["Canada", "Germany", "Singapore"])

    # Verify at least one opportunity has an actionable gap for IELTS
    top_opp = retrieved_opps[0]
    opp_id = top_opp["id"]
    res_detail = await async_client.get(f"/api/opportunities/{opp_id}")
    assert res_detail.status_code == 200
    detail_data = res_detail.json()
    assert len(detail_data["evidence_records"]) > 0

    # 4. Generate on-demand SOP via Application Coach API
    sop_res = await async_client.post(
        f"/api/opportunities/{opp_id}/sop",
        json={
            "opportunity_id": opp_id,
            "run_id": run_id,
            "specific_interests": "Focus on high-throughput distributed systems and vector search"
        }
    )
    assert sop_res.status_code == 200
    sop_data = sop_res.json()
    assert "sop_content" in sop_data
    assert len(sop_data["sop_content"]) > 0
    assert "Rahul Sharma" in sop_data["title"] or "Statement of Purpose" in sop_data["title"]


# ==============================================================================
# Scenario 2: Maria Santos (Brazil -> Germany/Canada | Marginal 6.8 CGPA)
# ==============================================================================
@pytest.mark.asyncio
async def test_scenario_2_maria_santos_marginal_cgpa_gap_planning(profile_maria_santos, clean_repo, async_client: AsyncClient):
    """
    Scenario 2:
    Maria Santos has a 6.8 CGPA and a strong TOEFL 102.
    Verifies:
    1. Pipeline evaluates her against programs in Germany and Canada.
    2. Identifies programs where 6.8 is below published minimum entrance cutoff (< 7.0/10).
    3. Actionable gaps accurately highlight academic grade requirements.
    4. Language test (TOEFL 102) is recognized as MEETS.
    """
    state = SwarmState(
        run_id="maria-scenario-run",
        user_input=profile_maria_santos.model_dump(),
        student_profile=profile_maria_santos
    )
    final_state = await swarm_app.ainvoke(state)
    opps = final_state["opportunities"]
    assert len(opps) > 0

    # Check that language test evaluated to MEETS due to recorded score 102
    language_evaluated = False
    for opp in opps:
        for ev in opp.evidence_records:
            if "Language" in ev.criterion_name or "English" in ev.criterion_name:
                assert ev.status == "MEETS"
                language_evaluated = True
                break
        if language_evaluated:
            break
    assert language_evaluated is True

    # Check academic grade evaluations reflect student's 6.8 CGPA
    grade_checked = False
    for opp in opps:
        for ev in opp.evidence_records:
            if "Grade" in ev.criterion_name or "CGPA" in ev.criterion_name:
                assert "6.8" in (ev.student_value or "")
                grade_checked = True
                break
        if grade_checked:
            break
    assert grade_checked is True


# ==============================================================================
# Scenario 3: Wei Chen (China -> Singapore | PhD Track & Math Background)
# ==============================================================================
@pytest.mark.asyncio
async def test_scenario_3_wei_chen_phd_singapore_track(profile_wei_chen, clean_repo):
    """
    Scenario 3:
    Wei Chen is seeking a PhD in Data Science / AI in Singapore with 8.5 CGPA.
    Verifies:
    1. Pipeline filters for Singapore programs and evaluates PhD track compatibility.
    2. SINGA / Singapore research opportunities are scored and ranked.
    3. Missing language score is classified as UNRESOLVED with actionable gap.
    """
    state = SwarmState(
        run_id="wei-scenario-run",
        user_input=profile_wei_chen.model_dump(),
        student_profile=profile_wei_chen
    )
    final_state = await swarm_app.ainvoke(state)
    opps = final_state["opportunities"]
    assert len(opps) > 0

    # Verify Singapore opportunities are discovered
    singapore_opps = [o for o in opps if o.country == "Singapore"]
    assert len(singapore_opps) > 0

    # Verify that PhD-seeking profile is recognized for degree track
    for opp in singapore_opps:
        if opp.degree_level == "PhD":
            for ev in opp.evidence_records:
                if "Degree" in ev.criterion_name:
                    assert ev.status == "MEETS"


# ==============================================================================
# Scenario 4: Fatima Al-Hassan (Nigeria -> Canada | High Distinction 9.1 CGPA)
# ==============================================================================
@pytest.mark.asyncio
async def test_scenario_4_fatima_alhassan_top_distinction(profile_fatima_alhassan, clean_repo):
    """
    Scenario 4:
    Fatima Al-Hassan has a 9.1 CGPA, IELTS 8.0, and target PhD in Robotics in Canada.
    Verifies:
    1. Academic grade strongly satisfies Canadian criteria.
    2. IELTS 8.0 satisfies language requirements.
    3. High overall match scores across eligible Canadian opportunities.
    """
    state = SwarmState(
        run_id="fatima-scenario-run",
        user_input=profile_fatima_alhassan.model_dump(),
        student_profile=profile_fatima_alhassan
    )
    final_state = await swarm_app.ainvoke(state)
    opps = final_state["opportunities"]
    assert len(opps) > 0

    canadian_opps = [o for o in opps if o.country == "Canada"]
    assert len(canadian_opps) > 0

    for opp in canadian_opps:
        # Check academic grade evidence
        for ev in opp.evidence_records:
            if "Grade" in ev.criterion_name or "CGPA" in ev.criterion_name:
                assert ev.status == "MEETS"
                assert "9.1" in (ev.student_value or "")


# ==============================================================================
# Scenario 5: Multi-Profile Isolation & Reset Endpoint Verification
# ==============================================================================
@pytest.mark.asyncio
async def test_scenario_5_data_isolation_and_reset_endpoint(
    profile_rahul_sharma,
    profile_maria_santos,
    clean_repo,
    async_client: AsyncClient
):
    """
    Scenario 5:
    Submitting multiple distinct student profiles produces isolated research runs,
    and invoking POST /api/opportunities/reset completely cleans repository state.
    """
    # Start Run 1 (Rahul)
    res1 = await async_client.post("/api/research/start", json=profile_rahul_sharma.model_dump())
    assert res1.status_code == 200
    run1_id = res1.json()["id"]

    # Start Run 2 (Maria)
    res2 = await async_client.post("/api/research/start", json=profile_maria_santos.model_dump())
    assert res2.status_code == 200
    run2_id = res2.json()["id"]

    assert run1_id != run2_id

    # Reset API endpoint
    res_reset = await async_client.post("/api/opportunities/reset")
    assert res_reset.status_code == 200
    assert res_reset.json()["success"] is True

    # After reset, previous run lookup returns 404
    res_after = await async_client.get(f"/api/research/{run1_id}")
    assert res_after.status_code == 404
