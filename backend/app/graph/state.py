from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator
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
    approved_opportunities: List[Opportunity] = Field(default_factory=list)
    
    current_phase: str = "INITIALIZED"
    research_round: int = 1
    max_research_rounds: int = 2
    
    needs_re_research: bool = False
    needs_re_ranking: bool = False
    reviewer_issues: List[Dict[str, Any]] = Field(default_factory=list)
    error_message: Optional[str] = None

    @field_validator("reviewer_issues", mode="before")
    @classmethod
    def normalize_reviewer_issues(cls, v):
        if not v or not isinstance(v, list):
            return []
        normalized = []
        for item in v:
            if isinstance(item, dict):
                normalized.append(item)
            elif isinstance(item, str):
                normalized.append({
                    "issue": item,
                    "description": item,
                    "issue_type": "GENERAL"
                })
            else:
                s = str(item)
                normalized.append({
                    "issue": s,
                    "description": s,
                    "issue_type": "GENERAL"
                })
        return normalized
