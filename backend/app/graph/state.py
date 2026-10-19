from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from app.models.profile import StudentProfile
from app.models.opportunity import Opportunity
from app.models.events import AgentEvent

class SwarmState(BaseModel):
    run_id: str
    user_input: Dict[str, Any] = Field(default_factory=dict)
    resume_text: Optional[str] = None
    transcript_text: Optional[str] = None
    github_url: Optional[str] = None
    
    student_profile: Optional[StudentProfile] = None
    opportunities: List[Opportunity] = Field(default_factory=list)
    
    current_phase: str = "INITIALIZED"
    research_round: int = 1
    max_research_rounds: int = 2
    
    needs_re_research: bool = False
    reviewer_issues: List[str] = Field(default_factory=list)
    error_message: Optional[str] = None
