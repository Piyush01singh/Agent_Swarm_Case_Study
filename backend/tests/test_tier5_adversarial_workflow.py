"""
Tier 5 White-Box Adversarial Stress Testing Suite:
LangGraph 5-Agent Workflow, State Transitions, Quality Reviewer Feedback Loop,
Repository Fault Recovery, SwarmState Resilience, and API Error Paths.
"""

import asyncio
import uuid
import pytest
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
from unittest.mock import AsyncMock, patch, MagicMock, PropertyMock
from fastapi.testclient import TestClient

from app.main import app
from app.graph.state import SwarmState
from app.graph.workflow import (
    swarm_app,
    route_after_review,
    node_profile_intelligence,
    node_research_discovery,
    node_match_strategist,
    node_quality_reviewer,
    node_application_coaching
)
from app.agents.quality_reviewer import QualityReviewerAgent, ReviewerIssue
from app.models.profile import StudentProfile
from app.models.opportunity import Opportunity, FundingDetails
from app.models.evidence import EvidenceRecord, MatchScore
from app.models.events import ResearchRun, AgentEvent
from app.services.gemini_service import GeminiService, gemini_service
from app.db.repository import repository


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


@pytest.fixture
def api_client():
    return TestClient(app)


# ==============================================================================
# Group 1: Repeated Re-Research Rejection Cycles & Bounded Loop
# ==============================================================================

class TestRepeatedReResearchRejectionCycles:
    """
    Stress-tests the LangGraph workflow feedback loop under repeated rejections.
    Verifies strict termination at max_research_rounds without deadlock, infinite recursion,
    or orphaned state.
    """

    @pytest.mark.asyncio
    async def test_workflow_repeated_rejections_terminates_strictly_at_max_rounds_default_2(self, sample_profile):
        """
        Adversarial test: Discovery continuously returns candidates that Quality Reviewer rejects.
        Verify workflow executes exactly max_research_rounds (default 2) and halts at __end__
        without runaway recursion or deadlock.
        """
        await repository.reset_all_data()

        run_id = f"run-adversarial-loop-{uuid.uuid4().hex[:8]}"
        initial_state = SwarmState(
            run_id=run_id,
            student_profile=sample_profile,
            research_round=1,
            max_research_rounds=2
        )

        # Candidate that will be rejected on every round (secondary unverified source)
        def create_rejected_opp(round_idx: int) -> Opportunity:
            return Opportunity(
                id=f"opp-rejected-r{round_idx}",
                run_id=run_id,
                canonical_url=f"https://unverified-blog.org/scholarship-{round_idx}",
                official_source_urls=[f"https://unverified-blog.org/scholarship-{round_idx}"],
                title=f"Unverified Award Round {round_idx}",
                program_name="MSc Computer Science",
                university="Blog University",
                country="Canada",
                degree_level="Master's",
                field="CS",
                evidence_quality="UNVERIFIED",
                funding_details=FundingDetails(funding_type="Partial", coverage_description="Tuition waiver")
            )

        discovery_call_count = 0

        async def mock_discovery_and_audit(*args, **kwargs):
            nonlocal discovery_call_count
            discovery_call_count += 1
            return [create_rejected_opp(discovery_call_count)]

        with patch("app.graph.workflow.profile_agent.execute", new_callable=AsyncMock) as mock_prof, \
             patch("app.graph.workflow.research_agent.execute_discovery_and_audit", side_effect=mock_discovery_and_audit), \
             patch.object(GeminiService, "is_available", new_callable=PropertyMock, return_value=False):
            
            mock_prof.return_value = sample_profile

            # Execute compiled LangGraph workflow
            final_state = await swarm_app.ainvoke(initial_state)

        # Loop must terminate strictly after 2 discovery rounds
        assert discovery_call_count == 2, f"Expected 2 discovery rounds, got {discovery_call_count}"
        assert final_state["research_round"] == 3, f"Expected research_round to be 3 (incremented at round 2), got {final_state['research_round']}"
        assert final_state["current_phase"] == "COMPLETED"
        assert final_state["needs_re_research"] is True
        assert len(final_state["opportunities"]) >= 1
        assert all(o.reviewer_status == "FLAGGED" for o in final_state["opportunities"])

    @pytest.mark.asyncio
    async def test_workflow_repeated_rejections_terminates_strictly_at_custom_max_rounds_3(self, sample_profile):
        """
        Adversarial test: Custom max_research_rounds=3.
        Verify workflow iterates exactly 3 times before halting at __end__.
        """
        await repository.reset_all_data()

        run_id = f"run-adversarial-loop3-{uuid.uuid4().hex[:8]}"
        initial_state = SwarmState(
            run_id=run_id,
            student_profile=sample_profile,
            research_round=1,
            max_research_rounds=3
        )

        discovery_call_count = 0

        async def mock_discovery_and_audit(*args, **kwargs):
            nonlocal discovery_call_count
            discovery_call_count += 1
            return [
                Opportunity(
                    id=f"opp-rejected-{discovery_call_count}",
                    run_id=run_id,
                    canonical_url=f"https://unverified-blog.org/scholarship-{discovery_call_count}",
                    official_source_urls=[f"https://unverified-blog.org/scholarship-{discovery_call_count}"],
                    title=f"Unverified Award {discovery_call_count}",
                    program_name="MSc Computer Science",
                    university="Blog University",
                    country="Canada",
                    degree_level="Master's",
                    field="CS",
                    evidence_quality="UNVERIFIED",
                    funding_details=FundingDetails(funding_type="Partial", coverage_description="Tuition waiver")
                )
            ]

        with patch("app.graph.workflow.profile_agent.execute", new_callable=AsyncMock) as mock_prof, \
             patch("app.graph.workflow.research_agent.execute_discovery_and_audit", side_effect=mock_discovery_and_audit), \
             patch.object(GeminiService, "is_available", new_callable=PropertyMock, return_value=False):
            
            mock_prof.return_value = sample_profile
            final_state = await swarm_app.ainvoke(initial_state)

        assert discovery_call_count == 3
        assert final_state["research_round"] == 4
        assert final_state["current_phase"] == "COMPLETED"

    @pytest.mark.asyncio
    async def test_workflow_immediate_approval_terminates_in_single_round(self, sample_profile):
        """
        Adversarial test: Valid official candidate approved on round 1.
        Verify workflow executes exactly 1 round and halts without triggering re-research.
        """
        await repository.reset_all_data()

        run_id = f"run-single-pass-{uuid.uuid4().hex[:8]}"
        initial_state = SwarmState(
            run_id=run_id,
            student_profile=sample_profile,
            research_round=1,
            max_research_rounds=2
        )

        official_opp = Opportunity(
            id="opp-official-1",
            run_id=run_id,
            canonical_url="https://web.cs.toronto.edu/graduate/mscac",
            official_source_urls=["https://web.cs.toronto.edu/graduate/mscac"],
            title="UofT MScAC Program",
            program_name="MSc Applied Computing",
            university="University of Toronto",
            country="Canada",
            degree_level="Master's",
            field="Computer Science",
            deadline_type="Rolling",
            evidence_quality="OFFICIAL",
            funding_details=FundingDetails(funding_type="Fully Funded", coverage_description="$17,500 CAD stipend")
        )

        discovery_call_count = 0

        async def mock_discovery_and_audit(*args, **kwargs):
            nonlocal discovery_call_count
            discovery_call_count += 1
            return [official_opp]

        with patch("app.graph.workflow.profile_agent.execute", new_callable=AsyncMock) as mock_prof, \
             patch("app.graph.workflow.research_agent.execute_discovery_and_audit", side_effect=mock_discovery_and_audit), \
             patch.object(GeminiService, "is_available", new_callable=PropertyMock, return_value=False):
            
            mock_prof.return_value = sample_profile
            final_state = await swarm_app.ainvoke(initial_state)

        assert discovery_call_count == 1
        assert final_state["research_round"] == 1
        assert final_state["needs_re_research"] is False
        assert final_state["current_phase"] == "COMPLETED"
        assert len(final_state["approved_opportunities"]) == 1

    def test_route_after_review_exhaustive_boundary_matrix(self):
        """
        Adversarial matrix: Verifies all boundary conditions of route_after_review conditional edge.
        """
        # 1. Round 1 of 2 with rejection -> route to research_discovery
        s1 = SwarmState(run_id="r1", needs_re_research=True, research_round=1, max_research_rounds=2)
        assert route_after_review(s1) == "research_discovery"

        # 2. Round 2 of 2 with rejection -> route to research_discovery
        s2 = SwarmState(run_id="r2", needs_re_research=True, research_round=2, max_research_rounds=2)
        assert route_after_review(s2) == "research_discovery"

        # 3. Round 3 of 2 (exceeded) with rejection -> terminate
        s3 = SwarmState(run_id="r3", needs_re_research=True, research_round=3, max_research_rounds=2)
        assert route_after_review(s3) == "__end__"

        # 4. Clean review with no issues -> terminate
        s4 = SwarmState(run_id="r4", needs_re_research=False, research_round=1, max_research_rounds=2)
        assert route_after_review(s4) == "__end__"

        # 5. Re-ranking requested without re-research -> route to match_strategy
        s5 = SwarmState(run_id="r5", needs_re_research=False, needs_re_ranking=True, research_round=1)
        assert route_after_review(s5) == "match_strategy"

        # 6. Both re-research and re-ranking requested: re-research must take priority
        s6 = SwarmState(run_id="r6", needs_re_research=True, needs_re_ranking=True, research_round=1, max_research_rounds=2)
        assert route_after_review(s6) == "research_discovery"

        # 7. Zero max rounds -> terminate immediately
        s7 = SwarmState(run_id="r7", needs_re_research=True, research_round=1, max_research_rounds=0)
        assert route_after_review(s7) == "__end__"


# ==============================================================================
# Group 2: Multi-Round Candidate Preservation Stress Testing
# ==============================================================================

class TestMultiRoundCandidatePreservation:
    """
    Stress-tests Feature F13: Cross-Round Candidate Preservation.
    Verifies approved candidates from round 1 are preserved through round 2 even when
    round 2 yields 0 candidates or 100% rejected candidates.
    """

    @pytest.mark.asyncio
    async def test_preservation_when_round_two_yields_zero_candidates(self, sample_profile):
        """
        Adversarial test: Round 1 approves Opp A. Round 2 yields 0 candidates.
        Verify Opp A is not dropped or overwritten.
        """
        opp_a = Opportunity(
            id="opp-tum-approved",
            run_id="run-pres-0",
            canonical_url="https://tum.de/in/msc",
            official_source_urls=["https://tum.de/in/msc"],
            title="TUM Informatics",
            program_name="Informatics",
            university="Technical University of Munich",
            country="Germany",
            degree_level="Master's",
            field="Informatics",
            reviewer_status="APPROVED",
            evidence_quality="OFFICIAL",
            deadline_type="Rolling",
            funding_details=FundingDetails(funding_type="Fully Funded", coverage_description="DAAD Stipend")
        )

        state = SwarmState(
            run_id="run-pres-0",
            student_profile=sample_profile,
            research_round=2,
            approved_opportunities=[opp_a],
            reviewer_issues=[{"issue": "Search additional German universities"}]
        )

        # Round 2 discovery returns empty list
        with patch("app.graph.workflow.research_agent.execute_discovery_and_audit", new_callable=AsyncMock) as mock_disc:
            mock_disc.return_value = []
            res = await node_research_discovery(state)

        assert len(res["opportunities"]) == 1
        assert res["opportunities"][0].id == "opp-tum-approved"
        assert res["opportunities"][0].university == "Technical University of Munich"

        # Verify quality reviewer also preserves it
        state.opportunities = res["opportunities"]
        with patch.object(GeminiService, "is_available", new_callable=PropertyMock, return_value=False):
            rev_res = await node_quality_reviewer(state)

        assert len(rev_res["approved_opportunities"]) == 1
        assert rev_res["approved_opportunities"][0].id == "opp-tum-approved"

    @pytest.mark.asyncio
    async def test_preservation_when_round_two_yields_only_rejected_candidates(self, sample_profile):
        """
        Adversarial test: Round 1 approves Opp A. Round 2 yields Opp B (which is FLAGGED).
        Verify approved_opportunities retains Opp A, and Opp B is not added to approved list.
        """
        opp_a = Opportunity(
            id="opp-utoronto-approved",
            run_id="run-pres-rej",
            canonical_url="https://web.cs.toronto.edu/graduate/mscac",
            official_source_urls=["https://web.cs.toronto.edu/graduate/mscac"],
            title="UofT MScAC",
            program_name="MSc Applied Computing",
            university="University of Toronto",
            country="Canada",
            degree_level="Master's",
            field="CS",
            reviewer_status="APPROVED",
            evidence_quality="OFFICIAL",
            deadline_type="Rolling",
            funding_details=FundingDetails(funding_type="Fully Funded", coverage_description="Vector Fellowship")
        )

        opp_b_bad = Opportunity(
            id="opp-bad-round-2",
            run_id="run-pres-rej",
            canonical_url="https://scam-blog.org/scholarship",
            official_source_urls=["https://scam-blog.org/scholarship"],
            title="Scam Blog Fellowship",
            program_name="MSc Computer Science",
            university="Scam Institute",
            country="Canada",
            degree_level="Master's",
            field="CS",
            evidence_quality="UNVERIFIED",
            funding_details=FundingDetails(funding_type="Partial", coverage_description="Fee waiver")
        )

        state = SwarmState(
            run_id="run-pres-rej",
            student_profile=sample_profile,
            research_round=2,
            approved_opportunities=[opp_a]
        )

        with patch("app.graph.workflow.research_agent.execute_discovery_and_audit", new_callable=AsyncMock) as mock_disc:
            mock_disc.return_value = [opp_b_bad]
            disc_res = await node_research_discovery(state)

        opp_ids = [o.id for o in disc_res["opportunities"]]
        assert "opp-utoronto-approved" in opp_ids
        assert "opp-bad-round-2" in opp_ids
        assert len(disc_res["opportunities"]) == 2

        # Pass through Quality Reviewer
        state.opportunities = disc_res["opportunities"]
        with patch.object(GeminiService, "is_available", new_callable=PropertyMock, return_value=False):
            rev_res = await node_quality_reviewer(state)

        approved_ids = [o.id for o in rev_res["approved_opportunities"]]
        assert "opp-utoronto-approved" in approved_ids
        assert "opp-bad-round-2" not in approved_ids
        assert len(rev_res["approved_opportunities"]) == 1

    @pytest.mark.asyncio
    async def test_preservation_deduplication_by_id_and_canonical_url(self, sample_profile):
        """
        Adversarial test: Round 2 returns duplicates of round 1 approved candidate by both ID
        and canonical URL. Verify node_research_discovery deduplicates cleanly.
        """
        opp_orig = Opportunity(
            id="opp-nus-1",
            run_id="run-dedup",
            canonical_url="https://nus.edu.sg/msc-ai",
            official_source_urls=["https://nus.edu.sg/msc-ai"],
            title="NUS MSc AI",
            program_name="MSc AI",
            university="National University of Singapore",
            country="Singapore",
            degree_level="Master's",
            field="AI",
            reviewer_status="APPROVED",
            funding_details=FundingDetails(funding_type="Fully Funded", coverage_description="SINGA Award")
        )

        # Duplicate with same ID
        opp_dup_id = Opportunity(
            id="opp-nus-1",
            run_id="run-dedup",
            canonical_url="https://other-url.com",
            title="Duplicate ID",
            program_name="MSc AI",
            university="NUS",
            country="Singapore",
            degree_level="Master's",
            field="AI",
            funding_details=FundingDetails(funding_type="Partial", coverage_description="Tuition")
        )

        # Duplicate with different ID but same canonical_url
        opp_dup_url = Opportunity(
            id="opp-nus-diff-id",
            run_id="run-dedup",
            canonical_url="https://nus.edu.sg/msc-ai",
            title="Duplicate URL",
            program_name="MSc AI",
            university="NUS",
            country="Singapore",
            degree_level="Master's",
            field="AI",
            funding_details=FundingDetails(funding_type="Partial", coverage_description="Tuition")
        )

        # Distinct new opportunity
        opp_distinct = Opportunity(
            id="opp-ntu-2",
            run_id="run-dedup",
            canonical_url="https://ntu.edu.sg/msc-ds",
            official_source_urls=["https://ntu.edu.sg/msc-ds"],
            title="NTU Data Science",
            program_name="MSc Data Science",
            university="Nanyang Technological University",
            country="Singapore",
            degree_level="Master's",
            field="DS",
            funding_details=FundingDetails(funding_type="Partial", coverage_description="Waiver")
        )

        state = SwarmState(
            run_id="run-dedup",
            student_profile=sample_profile,
            research_round=2,
            approved_opportunities=[opp_orig]
        )

        with patch("app.graph.workflow.research_agent.execute_discovery_and_audit", new_callable=AsyncMock) as mock_disc:
            mock_disc.return_value = [opp_dup_id, opp_dup_url, opp_distinct]
            res = await node_research_discovery(state)

        opps = res["opportunities"]
        assert len(opps) == 2, f"Expected 2 opportunities after dedup, got {len(opps)}"
        ids = {o.id for o in opps}
        assert ids == {"opp-nus-1", "opp-ntu-2"}


# ==============================================================================
# Group 3: Repository Edge Cases & Fault Recovery
# ==============================================================================

class TestRepositoryEdgeCasesAndFaultTolerance:
    """
    Stress-tests the database / repository layer under adverse conditions:
    non-existent IDs, empty database results, malformed Supabase rows,
    simulated Supabase network exceptions, and concurrent writes.
    """

    @pytest.mark.asyncio
    async def test_get_opportunity_by_id_non_existent_returns_none_safely(self):
        """
        Adversarial test: Non-existent IDs must return None cleanly without IndexError.
        """
        await repository.reset_all_data()

        # Non-existent UUIDs and edge strings
        assert await repository.get_opportunity_by_id("00000000-0000-0000-0000-000000000000") is None
        assert await repository.get_opportunity_by_id("") is None
        assert await repository.get_opportunity_by_id("None") is None
        assert await repository.get_opportunity_by_id("   ") is None

    @pytest.mark.asyncio
    async def test_safe_handling_of_empty_results_across_all_repository_methods(self):
        """
        Adversarial test: All repository methods return clean empty collections or None
        when queried with non-existent identifiers.
        """
        await repository.reset_all_data()
        bogus_id = f"missing-{uuid.uuid4().hex}"

        assert await repository.get_research_run(bogus_id) is None
        assert await repository.get_opportunities(bogus_id) == []
        assert await repository.get_evidence_for_opportunity(bogus_id) == []
        assert await repository.get_evidence_records(run_id=bogus_id) == []
        assert await repository.get_evidence_records(opportunity_id=bogus_id) == []
        assert await repository.get_agent_events(bogus_id) == []
        assert await repository.get_agent_events(bogus_id, after_seq=10) == []
        assert await repository.get_application_draft(bogus_id) is None

    @pytest.mark.asyncio
    async def test_supabase_row_malformed_sparse_schema_deserialization(self):
        """
        Adversarial test: Supabase returns a row with missing optional keys.
        Repository must deserialize with graceful fallbacks.
        """
        await repository.reset_all_data()

        sparse_row = {
            "id": "opp-sparse-1",
            "run_id": "run-sparse-1",
            "canonical_url": "https://tum.de/sparse",
            "title": "Sparse Program",
            "program_name": "CS Sparse",
            "university": "Technical University of Munich",
            "country": "Germany",
            "degree_level": "Master's",
            "field": "CS"
            # Optional keys: funding_type, funding_coverage, match_breakdown, deadline, etc. omitted
        }

        mock_supabase = MagicMock()
        mock_execute = MagicMock()
        mock_execute.execute.return_value = MagicMock(data=[sparse_row])
        mock_supabase.table.return_value.select.return_value.eq.return_value = mock_execute

        with patch("app.db.repository.get_supabase_client", return_value=mock_supabase):
            opp = await repository.get_opportunity_by_id("opp-sparse-1")

        assert opp is not None
        assert opp.id == "opp-sparse-1"
        assert opp.funding_details.funding_type == "Unknown"
        assert opp.funding_details.coverage_description == "TBD"
        assert opp.match_score is None
        assert opp.deadline_status == "UNKNOWN"

    @pytest.mark.asyncio
    async def test_supabase_database_exception_fallback_to_memory(self):
        """
        Adversarial test: Supabase client raises arbitrary network or query exceptions.
        Repository must trap errors and fallback cleanly to in-memory state.
        """
        await repository.reset_all_data()

        failing_client = MagicMock()
        failing_client.table.side_effect = RuntimeError("Supabase simulated connection reset / timeout")

        with patch("app.db.repository.get_supabase_client", return_value=failing_client):
            # 1. Create run with failing DB
            run = ResearchRun(
                id="run-resilience-1",
                student_profile=StudentProfile(
                    full_name="Fault Test",
                    current_degree="B.Sc",
                    cgpa=3.5,
                    grading_scale="4.0",
                    target_degree="Master's",
                    target_field="Data Science"
                )
            )
            created_run = await repository.create_research_run(run)
            assert created_run.id == "run-resilience-1"

            # 2. Update run status with failing DB
            updated_run = await repository.update_research_run_status("run-resilience-1", status="RUNNING")
            assert updated_run is not None
            assert updated_run.status == "RUNNING"

            # 3. Save opportunities with failing DB
            opp = Opportunity(
                id="opp-resilience-1",
                run_id="run-resilience-1",
                canonical_url="https://tum.de",
                title="TUM Program",
                program_name="CS",
                university="TUM",
                country="Germany",
                degree_level="Master's",
                field="CS",
                funding_details=FundingDetails(funding_type="Partial", coverage_description="Tuition")
            )
            await repository.save_opportunities("run-resilience-1", [opp])
            retrieved_opp = await repository.get_opportunity_by_id("opp-resilience-1")
            assert retrieved_opp is not None
            assert retrieved_opp.id == "opp-resilience-1"

            # 4. Save evidence records with failing DB
            ev = EvidenceRecord(
                id="ev-resilience-1",
                opportunity_id="opp-resilience-1",
                run_id="run-resilience-1",
                criterion_name="Degree Prerequisite",
                stated_requirement="B.Sc in CS or related field",
                status="MEETS",
                source_url="https://tum.de/admission"
            )
            await repository.save_evidence_records([ev])
            evidence = await repository.get_evidence_for_opportunity("opp-resilience-1")
            assert len(evidence) == 1
            assert evidence[0].id == "ev-resilience-1"

            # 5. Save agent event with failing DB
            event = AgentEvent(
                run_id="run-resilience-1",
                agent_role="Test Role",
                event_type="TEST",
                title="Test Event",
                description="Testing fault recovery"
            )
            await repository.save_agent_event(event)
            events = await repository.get_agent_events("run-resilience-1")
            assert len(events) == 1
            assert events[0].title == "Test Event"

    @pytest.mark.asyncio
    async def test_concurrent_writes_thread_safety_stress(self):
        """
        Adversarial test: 25 concurrent tasks saving agent events and opportunities.
        Verify zero race conditions, no corrupted sequence numbers, and all records persisted.
        """
        await repository.reset_all_data()
        run_id = f"run-concurrent-{uuid.uuid4().hex[:8]}"

        async def worker_save_event(idx: int):
            event = AgentEvent(
                run_id=run_id,
                agent_role="Concurrent Worker",
                event_type="PARALLEL_STEP",
                title=f"Parallel Task {idx}",
                description=f"Running task {idx} under load"
            )
            await repository.save_agent_event(event)

        async def worker_save_opportunity(idx: int):
            opp = Opportunity(
                id=f"opp-concurrent-{idx}",
                run_id=run_id,
                canonical_url=f"https://tum.de/prog-{idx}",
                title=f"Parallel Program {idx}",
                program_name=f"CS {idx}",
                university="TUM",
                country="Germany",
                degree_level="Master's",
                field="CS",
                funding_details=FundingDetails(funding_type="Partial", coverage_description="Waiver")
            )
            await repository.save_opportunities(run_id, [opp])

        # Launch 25 concurrent events + 25 concurrent opportunities
        event_tasks = [worker_save_event(i) for i in range(25)]
        opp_tasks = [worker_save_opportunity(i) for i in range(25)]
        await asyncio.gather(*event_tasks, *opp_tasks)

        saved_events = await repository.get_agent_events(run_id)
        assert len(saved_events) == 25
        # Verify sequence numbers are monotonic 1..25
        seqs = [e.sequence_number for e in saved_events]
        assert sorted(seqs) == list(range(1, 26))

        saved_opps = await repository.get_opportunities(run_id)
        assert len(saved_opps) == 25

    @pytest.mark.asyncio
    async def test_evidence_records_idempotent_deduplication(self):
        """
        Adversarial test: Saving identical evidence records multiple times must be idempotent.
        """
        await repository.reset_all_data()

        ev = EvidenceRecord(
            id="ev-fixed-id",
            opportunity_id="opp-idem-1",
            run_id="run-idem-1",
            criterion_name="CGPA Cutoff",
            stated_requirement="7.5 / 10",
            status="MEETS",
            source_url="https://tum.de"
        )

        # Save twice
        await repository.save_evidence_records([ev])
        await repository.save_evidence_records([ev])

        records = await repository.get_evidence_for_opportunity("opp-idem-1")
        assert len(records) == 1
        assert records[0].id == "ev-fixed-id"


# ==============================================================================
# Group 4: SwarmState Resilience & Backward Compatibility
# ==============================================================================

class TestSwarmStateResilienceAndBackwardCompatibility:
    """
    Stress-tests SwarmState schema validation, ReviewerIssue normalization,
    and backward-compatibility between legacy string issues and modern dict issues.
    """

    def test_swarm_state_reviewer_issues_legacy_strings(self):
        """
        Adversarial test: Legacy string issues are normalized to dictionary structure.
        """
        state = SwarmState(
            run_id="run-legacy",
            reviewer_issues=["Legacy Issue: Expired deadline", "Legacy Issue: Missing official source"]
        )
        assert len(state.reviewer_issues) == 2
        for item in state.reviewer_issues:
            assert isinstance(item, dict)
            assert "description" in item
            assert "issue" in item
            assert item["issue_type"] == "GENERAL"

        assert state.reviewer_issues[0]["description"] == "Legacy Issue: Expired deadline"
        assert state.reviewer_issues[1]["description"] == "Legacy Issue: Missing official source"

    def test_swarm_state_mixed_reviewer_issues_types(self):
        """
        Adversarial test: List containing a mix of dicts, strings, integers, and custom objects.
        """
        state = SwarmState(
            run_id="run-mixed",
            reviewer_issues=[
                {"issue": "Valid Dict Issue", "issue_type": "EXPIRED_DEADLINE", "description": "Valid Dict Issue"},
                "Plain string issue",
                404,
                Exception("Custom error description")
            ]
        )
        assert len(state.reviewer_issues) == 4
        assert state.reviewer_issues[0]["issue_type"] == "EXPIRED_DEADLINE"
        assert state.reviewer_issues[1]["description"] == "Plain string issue"
        assert state.reviewer_issues[2]["description"] == "404"
        assert "Custom error description" in state.reviewer_issues[3]["description"]

    def test_swarm_state_non_list_reviewer_issues_recovery(self):
        """
        Adversarial test: reviewer_issues passed as None, a single string, or a dict.
        Validator must safely convert to empty list without raising a ValidationError.
        """
        state_none = SwarmState(run_id="r-none", reviewer_issues=None)
        assert state_none.reviewer_issues == []

        state_str = SwarmState(run_id="r-str", reviewer_issues="not a list")
        assert state_str.reviewer_issues == []

        state_dict = SwarmState(run_id="r-dict", reviewer_issues={"not": "a list"})
        assert state_dict.reviewer_issues == []

    def test_reviewer_issue_dual_interface_robustness(self):
        """
        Adversarial test: ReviewerIssue dual dict-string interface.
        Verifies .lower(), substring in, str(), and dict subscription.
        """
        # String initialization
        iss_str = ReviewerIssue("University of Toronto: Application deadline has passed.")
        assert isinstance(iss_str, dict)
        assert iss_str["issue"] == "University of Toronto: Application deadline has passed."
        assert iss_str["description"] == "University of Toronto: Application deadline has passed."
        assert "deadline" in iss_str.lower()
        assert "Toronto" in iss_str
        assert str(iss_str).startswith("University of Toronto")

        # Dict initialization with only description
        iss_dict1 = ReviewerIssue({"description": "Missing coverage details", "issue_type": "MISSING_COVERAGE"})
        assert iss_dict1["issue"] == "Missing coverage details"
        assert iss_dict1["issue_type"] == "MISSING_COVERAGE"
        assert "coverage" in iss_dict1

        # Dict initialization with only issue
        iss_dict2 = ReviewerIssue({"issue": "Secondary domain found", "issue_type": "SECONDARY_SOURCE"})
        assert iss_dict2["description"] == "Secondary domain found"
        assert "Secondary" in iss_dict2

        # Empty / None initialization
        iss_empty = ReviewerIssue()
        assert isinstance(iss_empty, dict)
        assert str(iss_empty) == ""


# ==============================================================================
# Group 5: QualityReviewer Hostile Input Stress Testing
# ==============================================================================

class TestQualityReviewerHostileInputStress:
    """
    Stress-tests QualityReviewerAgent.execute_audit against hostile, malformed,
    and adversarial opportunity candidate payloads.
    """

    @pytest.mark.asyncio
    async def test_hostile_candidate_missing_all_fields(self, sample_profile):
        """
        Adversarial test: Opportunity candidate with empty strings, empty URLs, and no criteria.
        Reviewer must not crash and must flag as SECONDARY with needs_re_research=True.
        """
        await repository.reset_all_data()
        reviewer = QualityReviewerAgent()

        hostile_opp = Opportunity(
            id="opp-hostile-empty",
            run_id="run-hostile",
            canonical_url="",
            official_source_urls=[],
            title="",
            program_name="",
            university="",
            country="",
            degree_level="Master's",
            field="CS",
            funding_details=FundingDetails(funding_type="Unknown", coverage_description="")
        )

        with patch.object(GeminiService, "is_available", new_callable=PropertyMock, return_value=False):
            reviewed, needs_re, issues = await reviewer.execute_audit(
                run_id="run-hostile",
                profile=sample_profile,
                opportunities=[hostile_opp]
            )

        assert hostile_opp.reviewer_status == "FLAGGED"
        assert hostile_opp.evidence_quality == "SECONDARY"
        assert needs_re is True
        assert len(issues) >= 1

    @pytest.mark.asyncio
    async def test_hostile_candidate_null_and_malicious_urls(self, sample_profile):
        """
        Adversarial test: Hostile SSRF URLs, loopbacks, and protocol manipulations.
        All must be rejected by official domain checks and flagged.
        """
        await repository.reset_all_data()
        reviewer = QualityReviewerAgent()

        malicious_urls = [
            "http://169.254.169.254/latest/meta-data",
            "http://127.0.0.1:8000/internal",
            "http://localhost/admin",
            "javascript:alert(1)",
            "ftp://anonymous@evil.com",
            "https://fake-academic.ac.attacker-phishing.org"
        ]

        opps = []
        for i, url in enumerate(malicious_urls):
            opps.append(Opportunity(
                id=f"opp-malicious-{i}",
                run_id="run-malicious",
                canonical_url=url,
                official_source_urls=[url],
                title=f"Malicious {i}",
                program_name="CS",
                university=f"Malicious Univ {i}",
                country="Canada",
                degree_level="Master's",
                field="CS",
                funding_details=FundingDetails(funding_type="Partial", coverage_description="Tuition")
            ))

        with patch.object(GeminiService, "is_available", new_callable=PropertyMock, return_value=False):
            reviewed, needs_re, issues = await reviewer.execute_audit(
                run_id="run-malicious",
                profile=sample_profile,
                opportunities=opps
            )

        assert needs_re is True
        assert all(o.reviewer_status == "FLAGGED" for o in opps)
        assert all(o.evidence_quality == "SECONDARY" for o in opps)

    @pytest.mark.asyncio
    async def test_hostile_candidate_contradictory_funding_claims(self, sample_profile):
        """
        Adversarial test: Candidate claiming 'Fully Funded' without specific coverage breakdown.
        Reviewer must flag with MISSING_COVERAGE.
        """
        await repository.reset_all_data()
        reviewer = QualityReviewerAgent()

        opp_contradictory = Opportunity(
            id="opp-contradictory-funding",
            run_id="run-funding-check",
            canonical_url="https://utoronto.ca/fellowship",
            official_source_urls=["https://utoronto.ca/fellowship"],
            title="Contradictory Award",
            program_name="MSc Applied Computing",
            university="University of Toronto",
            country="Canada",
            degree_level="Master's",
            field="CS",
            deadline_type="Rolling",
            funding_details=FundingDetails(funding_type="Fully Funded", coverage_description="") # Empty breakdown!
        )

        with patch.object(GeminiService, "is_available", new_callable=PropertyMock, return_value=False):
            reviewed, needs_re, issues = await reviewer.execute_audit(
                run_id="run-funding-check",
                profile=sample_profile,
                opportunities=[opp_contradictory]
            )

        assert opp_contradictory.reviewer_status == "FLAGGED"
        assert any(iss.get("issue_type") == "MISSING_COVERAGE" for iss in issues)

    @pytest.mark.asyncio
    async def test_hostile_candidate_adversarial_deadlines(self, sample_profile):
        """
        Adversarial test: Tests expired dates, future dates, rolling strings, and garbage dates.
        """
        await repository.reset_all_data()
        reviewer = QualityReviewerAgent()

        # 1. Expired deadline
        opp_expired = Opportunity(
            id="opp-exp-1",
            run_id="run-deadlines",
            canonical_url="https://utoronto.ca/msc",
            official_source_urls=["https://utoronto.ca/msc"],
            title="Expired Program",
            program_name="MSc CS",
            university="University of Toronto",
            country="Canada",
            degree_level="Master's",
            field="CS",
            deadline="2020-01-01", # Clearly expired
            deadline_type="Fixed",
            funding_details=FundingDetails(funding_type="Partial", coverage_description="Tuition")
        )

        # 2. Future deadline
        future_date = (datetime.now(timezone.utc).date() + timedelta(days=90)).strftime("%Y-%m-%d")
        opp_future = Opportunity(
            id="opp-future-1",
            run_id="run-deadlines",
            canonical_url="https://tum.de/msc",
            official_source_urls=["https://tum.de/msc"],
            title="Future Program",
            program_name="MSc Informatics",
            university="Technical University of Munich",
            country="Germany",
            degree_level="Master's",
            field="CS",
            deadline=future_date,
            deadline_type="Fixed",
            funding_details=FundingDetails(funding_type="Partial", coverage_description="Tuition")
        )

        # 3. Garbage deadline
        opp_garbage = Opportunity(
            id="opp-garbage-1",
            run_id="run-deadlines",
            canonical_url="https://nus.edu.sg/msc",
            official_source_urls=["https://nus.edu.sg/msc"],
            title="Garbage Deadline Program",
            program_name="MSc CS",
            university="National University of Singapore",
            country="Singapore",
            degree_level="Master's",
            field="CS",
            deadline="2025/15/99-garbage",
            deadline_type="Unknown",
            funding_details=FundingDetails(funding_type="Partial", coverage_description="Tuition")
        )

        with patch.object(GeminiService, "is_available", new_callable=PropertyMock, return_value=False):
            reviewed, needs_re, issues = await reviewer.execute_audit(
                run_id="run-deadlines",
                profile=sample_profile,
                opportunities=[opp_expired, opp_future, opp_garbage]
            )

        assert opp_expired.reviewer_status == "FLAGGED"
        assert opp_expired.deadline_status == "EXPIRED"

        assert opp_future.reviewer_status == "APPROVED"
        assert opp_future.deadline_status == "ACTIVE"

        assert opp_garbage.reviewer_status == "APPROVED" # Not expired, but marked UNKNOWN
        assert opp_garbage.deadline_status == "UNKNOWN"

    @pytest.mark.asyncio
    async def test_hostile_candidate_mandatory_criteria_failure(self, sample_profile):
        """
        Adversarial test: Student fails published mandatory criteria.
        Reviewer must flag with MANDATORY_CRITERIA_FAILED and set needs_re_research=True.
        """
        await repository.reset_all_data()
        reviewer = QualityReviewerAgent()

        opp_failed_criteria = Opportunity(
            id="opp-failed-mandatory",
            run_id="run-mandatory",
            canonical_url="https://utoronto.ca/msc",
            official_source_urls=["https://utoronto.ca/msc"],
            title="UofT Program",
            program_name="MSc CS",
            university="University of Toronto",
            country="Canada",
            degree_level="Master's",
            field="CS",
            deadline_type="Rolling",
            funding_details=FundingDetails(funding_type="Partial", coverage_description="Tuition"),
            evidence_records=[
                EvidenceRecord(
                    opportunity_id="opp-failed-mandatory",
                    criterion_name="Minimum CGPA",
                    stated_requirement="Minimum 9.0 / 10 CGPA required",
                    student_value="8.2 / 10",
                    status="DOES_NOT_MEET",
                    source_url="https://utoronto.ca/admissions"
                )
            ]
        )

        with patch.object(GeminiService, "is_available", new_callable=PropertyMock, return_value=False):
            reviewed, needs_re, issues = await reviewer.execute_audit(
                run_id="run-mandatory",
                profile=sample_profile,
                opportunities=[opp_failed_criteria]
            )

        assert opp_failed_criteria.reviewer_status == "FLAGGED"
        assert needs_re is True
        assert any(iss.get("issue_type") == "MANDATORY_CRITERIA_FAILED" for iss in issues)

    @pytest.mark.asyncio
    async def test_quality_reviewer_comprehensive_audit_multiple_top_five(self, sample_profile):
        """
        Adversarial test for Feature F14: Comprehensive Reviewer Audit.
        Verifies that when multiple candidates have is_top_five=True, ALL of them are audited,
        not just candidate[0].
        """
        await repository.reset_all_data()
        reviewer = QualityReviewerAgent()

        opps = []
        for i in range(3):
            opps.append(Opportunity(
                id=f"opp-top-{i}",
                run_id="run-top-five",
                canonical_url=f"https://utoronto.ca/prog-{i}",
                official_source_urls=[f"https://utoronto.ca/prog-{i}"],
                title=f"Top Program {i}",
                program_name=f"CS {i}",
                university="University of Toronto",
                country="Canada",
                degree_level="Master's",
                field="CS",
                deadline_type="Rolling",
                funding_details=FundingDetails(funding_type="Partial", coverage_description="Tuition"),
                is_top_five=True
            ))

        gemini_audit_calls = []

        async def mock_review_claims(opportunity_data, student_data):
            gemini_audit_calls.append(opportunity_data["id"])
            # Flag candidate 1 only
            if opportunity_data["id"] == "opp-top-1":
                return {
                    "success": True,
                    "data": {
                        "approved": False,
                        "issues_detected": [{"issue": "Insufficient mathematics prerequisite credits", "severity": "HIGH"}]
                    }
                }
            return {"success": True, "data": {"approved": True, "issues_detected": []}}

        with patch.object(GeminiService, "is_available", new_callable=PropertyMock, return_value=True), \
             patch.object(gemini_service, "review_evidence_and_claims", side_effect=mock_review_claims):
            
            reviewed, needs_re, issues = await reviewer.execute_audit(
                run_id="run-top-five",
                profile=sample_profile,
                opportunities=opps
            )

        # All 3 candidates must have been audited
        assert len(gemini_audit_calls) == 3
        assert gemini_audit_calls == ["opp-top-0", "opp-top-1", "opp-top-2"]

        assert opps[0].reviewer_status == "APPROVED"
        assert opps[1].reviewer_status == "FLAGGED"
        assert opps[2].reviewer_status == "APPROVED"
        assert needs_re is True


# ==============================================================================
# Group 6: API Integration & SopWorkspace Error Handling
# ==============================================================================

class TestApiEndpointsAndSopWorkspaceIntegration:
    """
    Stress-tests FastAPI endpoints for research runs, opportunity retrieval,
    and SOP generation error paths.
    """

    def test_api_get_run_opportunities_404_on_missing_run(self, api_client):
        """
        API test: GET /api/research/{run_id}/opportunities with non-existent run returns 404.
        """
        resp = api_client.get(f"/api/research/{uuid.uuid4()}/opportunities")
        assert resp.status_code == 404
        assert "Research run not found" in resp.json()["detail"]

    def test_api_get_opportunity_details_404_on_missing_opp(self, api_client):
        """
        API test: GET /api/opportunities/{id} with non-existent ID returns 404.
        """
        resp = api_client.get(f"/api/opportunities/{uuid.uuid4()}")
        assert resp.status_code == 404
        assert "Opportunity not found" in resp.json()["detail"]

    def test_api_sop_generation_404_when_opportunity_missing(self, api_client):
        """
        API test: POST /api/opportunities/{id}/sop with non-existent ID returns 404.
        """
        resp = api_client.post(f"/api/opportunities/{uuid.uuid4()}/sop")
        assert resp.status_code == 404
        assert "Opportunity not found" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_api_sop_generation_404_when_run_missing(self, api_client):
        """
        API test: Opportunity exists in repository, but parent research run does not.
        POST /api/opportunities/{id}/sop returns 404 with detail 'Associated research run not found.'
        """
        await repository.reset_all_data()

        orphaned_opp = Opportunity(
            id="opp-orphan-1",
            run_id="run-orphan-nonexistent",
            canonical_url="https://utoronto.ca/msc",
            title="Orphaned Program",
            program_name="MSc CS",
            university="University of Toronto",
            country="Canada",
            degree_level="Master's",
            field="CS",
            funding_details=FundingDetails(funding_type="Partial", coverage_description="Tuition")
        )
        await repository.save_opportunities("run-orphan-nonexistent", [orphaned_opp])

        resp = api_client.post(f"/api/opportunities/{orphaned_opp.id}/sop")
        assert resp.status_code == 404
        assert "Associated research run not found" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_api_sop_get_existing_404_when_no_draft(self, api_client):
        """
        API test: GET /api/opportunities/{id}/sop when draft has not yet been generated.
        Returns 404 with detail 'No SOP draft generated yet for this opportunity.'
        """
        await repository.reset_all_data()
        resp = api_client.get(f"/api/opportunities/{uuid.uuid4()}/sop")
        assert resp.status_code == 404
        assert "No SOP draft generated yet" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_api_reset_endpoint_clears_repository(self, api_client):
        """
        API test: POST /api/opportunities/reset wipes demo repository state.
        """
        await repository.reset_all_data()

        opp = Opportunity(
            id="opp-wipe-test",
            run_id="run-wipe",
            canonical_url="https://tum.de",
            title="Wipe Test",
            program_name="CS",
            university="TUM",
            country="Germany",
            degree_level="Master's",
            field="CS",
            funding_details=FundingDetails(funding_type="Partial", coverage_description="Tuition")
        )
        await repository.save_opportunities("run-wipe", [opp])
        assert await repository.get_opportunity_by_id("opp-wipe-test") is not None

        resp = api_client.post("/api/opportunities/reset")
        assert resp.status_code == 200
        assert resp.json()["success"] is True

        assert await repository.get_opportunity_by_id("opp-wipe-test") is None
