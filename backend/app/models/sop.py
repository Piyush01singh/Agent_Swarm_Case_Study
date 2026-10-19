from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

class ApplicationDraft(BaseModel):
    id: Optional[str] = None
    opportunity_id: str
    run_id: str
    title: str
    program_name: str
    university: str
    sop_content: str
    unconfirmed_claims: List[str] = Field(default_factory=list)
    is_reviewed_by_agent: bool = False
    reviewer_feedback: Optional[str] = None
    word_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class SopGenerationRequest(BaseModel):
    opportunity_id: str
    run_id: str
    specific_interests: Optional[str] = None
    target_professors_or_labs: Optional[str] = None
