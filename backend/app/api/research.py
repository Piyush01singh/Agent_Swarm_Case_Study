import uuid
import asyncio
import json
from typing import Optional, List
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import StreamingResponse
from app.models.profile import StudentProfile
from app.models.events import ResearchRun, AgentEvent
from app.models.opportunity import Opportunity
from app.graph.workflow import swarm_app
from app.graph.state import SwarmState
from app.db.repository import repository

router = APIRouter(prefix="/research", tags=["Research"])

async def run_swarm_pipeline(run_id: str, state: SwarmState):
    """Executes the compiled LangGraph workflow in background."""
    try:
        await repository.update_research_run_status(run_id, status="RUNNING", current_phase="DISCOVERY")
        
        # Invoke LangGraph workflow
        final_state = await swarm_app.ainvoke(state)
        
        opps = final_state.get("opportunities", [])
        await repository.update_research_run_status(
            run_id,
            status="COMPLETED",
            current_phase="COMPLETED"
        )
        
        # Record completion event
        await repository.save_agent_event(AgentEvent(
            run_id=run_id,
            agent_role="System Supervisor",
            event_type="COMPLETED",
            title="ScholarSwarm Research Cycle Complete",
            description=f"Verified {len(opps)} opportunities. Top 5 shortlist prepared.",
            metadata={"total_opportunities": len(opps)}
        ))
    except Exception as e:
        await repository.update_research_run_status(
            run_id,
            status="FAILED",
            current_phase="FAILED",
            error_message=str(e)
        )
        await repository.save_agent_event(AgentEvent(
            run_id=run_id,
            agent_role="System Supervisor",
            event_type="ERROR",
            title="Research Workflow Error",
            description=f"Workflow encountered exception: {str(e)}",
            metadata={"error": str(e)}
        ))

@router.post("/start", response_model=ResearchRun)
async def start_research(profile: StudentProfile, background_tasks: BackgroundTasks):
    """
    Initiates a multi-agent research run for a student profile.
    Coordinates the 5 agent roles via LangGraph.
    """
    run_id = str(uuid.uuid4())
    run = ResearchRun(
        id=run_id,
        status="RUNNING",
        student_profile=profile,
        current_phase="PROFILE_INTELLIGENCE"
    )
    await repository.create_research_run(run)

    state = SwarmState(
        run_id=run_id,
        user_input=profile.model_dump(),
        student_profile=profile,
        github_url=profile.github_url
    )

    background_tasks.add_task(run_swarm_pipeline, run_id, state)
    return run

@router.get("/{run_id}", response_model=ResearchRun)
async def get_research_status(run_id: str):
    """Returns the current state and summary of a research run."""
    run = await repository.get_research_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Research run not found.")
    return run

@router.get("/{run_id}/opportunities", response_model=List[Opportunity])
async def get_run_opportunities(run_id: str):
    """Returns opportunities discovered and evaluated for a specific research run."""
    run = await repository.get_research_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Research run not found.")
    return await repository.get_opportunities(run_id)

@router.get("/{run_id}/events")
async def stream_agent_events(run_id: str, request: Request, last_event_id: Optional[int] = None):
    """
    Server-Sent Events (SSE) streaming real agent events to the frontend.
    Allows reconnection and replays historical events.
    """
    run = await repository.get_research_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Research run not found.")

    async def event_generator():
        last_seq = last_event_id or 0
        poll_count = 0
        
        while True:
            if await request.is_disconnected():
                break
                
            events = await repository.get_agent_events(run_id, after_seq=last_seq)
            for event in events:
                last_seq = max(last_seq, event.sequence_number or 0)
                event_data = {
                    "id": event.id,
                    "sequence_number": event.sequence_number,
                    "timestamp": event.timestamp.isoformat(),
                    "agent_role": event.agent_role,
                    "event_type": event.event_type,
                    "title": event.title,
                    "description": event.description,
                    "metadata": event.metadata
                }
                yield f"id: {last_seq}\nevent: agent_event\ndata: {json.dumps(event_data)}\n\n"
            
            # Check if run has reached terminal state and all events delivered
            curr_run = await repository.get_research_run(run_id)
            if curr_run and curr_run.status in ("COMPLETED", "FAILED", "INTERRUPTED"):
                if not events and poll_count > 2:
                    yield f"event: done\ndata: {json.dumps({'status': curr_run.status})}\n\n"
                    break
                poll_count += 1

            await asyncio.sleep(0.5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
