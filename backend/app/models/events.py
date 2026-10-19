from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field
from app.models.profile import StudentProfile
from app.models.opportunity import Opportunity

class AgentEvent(BaseModel):
    id: Optional[str] = None
    run_id: str
    sequence_number: Optional[int] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    agent_role: str # "Profile Intelligence Agent", "Research & Eligibility Agent", "Match Strategist Agent", "Application Coach Agent", "Quality Reviewer Agent", "System Supervisor"
    event_type: str # "SEARCH_QUERY", "CANDIDATE_FOUND", "URL_RETRIEVED", "REQUIREMENT_EXTRACTED", "ELIGIBILITY_EVALUATED", "DUPLICATE_REMOVED", "RETRIEVAL_FAILED", "RETRY_SCHEDULED", "REVIEWER_FLAGGED", "SCORE_CALCULATED", "SOP_GENERATED", "COMPLETED", "ERROR"
    title: str
    description: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ResearchRun(BaseModel):
    id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = "QUEUED" # "QUEUED", "RUNNING", "COMPLETED", "PARTIAL", "FAILED", "INTERRUPTED"
    student_profile: StudentProfile
    current_phase: Optional[str] = None
    research_round: int = 1
    total_candidates_found: int = 0
    total_verified: int = 0
    error_message: Optional[str] = None
    retry_count: int = 0
    opportunities: List[Opportunity] = Field(default_factory=list)
