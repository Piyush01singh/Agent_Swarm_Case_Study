from typing import Optional, List
from fastapi import APIRouter, HTTPException
from app.models.opportunity import Opportunity
from app.models.evidence import EvidenceRecord
from app.models.sop import ApplicationDraft, SopGenerationRequest
from app.agents.application_coach import ApplicationCoachAgent
from app.agents.quality_reviewer import QualityReviewerAgent
from app.db.repository import repository

router = APIRouter(prefix="/opportunities", tags=["Opportunities"])

coach_agent = ApplicationCoachAgent()
reviewer_agent = QualityReviewerAgent()

@router.get("/{opportunity_id}", response_model=Opportunity)
async def get_opportunity_details(opportunity_id: str):
    """Returns single opportunity and its evidence records."""
    opp = await repository.get_opportunity_by_id(opportunity_id)
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found.")
    evidence = await repository.get_evidence_for_opportunity(opportunity_id)
    opp.evidence_records = evidence
    return opp

@router.get("/{opportunity_id}/evidence", response_model=List[EvidenceRecord])
async def get_opportunity_evidence(opportunity_id: str):
    """Returns all criterion-level evidence records for an opportunity."""
    return await repository.get_evidence_for_opportunity(opportunity_id)

@router.post("/{opportunity_id}/sop", response_model=ApplicationDraft)
async def generate_sop_for_opportunity(opportunity_id: str, payload: Optional[SopGenerationRequest] = None):
    """
    Generates an editable Statement of Purpose (SOP) tailored to this specific opportunity
    and grounded in the student's profile facts.
    """
    opp = await repository.get_opportunity_by_id(opportunity_id)
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found.")

    run = await repository.get_research_run(opp.run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Associated research run not found.")

    user_notes = payload.specific_interests if payload else None

    # Check if a draft already exists
    existing = await repository.get_application_draft(opportunity_id)
    if existing:
        return existing

    draft = await coach_agent.execute_sop_draft(
        run_id=opp.run_id,
        profile=run.student_profile,
        opportunity=opp,
        user_notes=user_notes
    )
    return draft

@router.get("/{opportunity_id}/sop", response_model=ApplicationDraft)
async def get_existing_sop(opportunity_id: str):
    """Retrieves an existing SOP draft if previously generated."""
    draft = await repository.get_application_draft(opportunity_id)
    if not draft:
        raise HTTPException(status_code=404, detail="No SOP draft generated yet for this opportunity.")
    return draft

@router.post("/reset")
async def reset_demo_data():
    """Resets memory state for demo / testing purposes."""
    await repository.reset_all_data()
    return {"success": True, "message": "Demo data reset successfully."}
