from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field

class EvidenceRecord(BaseModel):
    id: Optional[str] = None
    opportunity_id: Optional[str] = None
    run_id: Optional[str] = None
    criterion_name: str
    stated_requirement: str
    student_value: Optional[str] = None
    status: str = "UNRESOLVED" # "MEETS", "DOES_NOT_MEET", "UNRESOLVED", "NOT_APPLICABLE"
    evidence_excerpt: Optional[str] = None
    source_title: Optional[str] = None
    source_url: str
    source_category: str = "OFFICIAL" # "OFFICIAL", "SECONDARY", "UNVERIFIED"
    checked_at: datetime = Field(default_factory=datetime.utcnow)
    uncertainty_or_conflict: Optional[str] = None

class EligibilityAssessment(BaseModel):
    overall_status: str = "INSUFFICIENT_EVIDENCE" # "MEETS_STATED_CRITERIA", "POTENTIAL_MATCH", "DOES_NOT_MEET", "INSUFFICIENT_EVIDENCE"
    mandatory_criteria_passed: bool = False
    has_mandatory_failure: bool = False
    unresolved_mandatory_count: int = 0
    reasons: list[str] = Field(default_factory=list)
    actionable_gaps: list[str] = Field(default_factory=list)

class MatchScore(BaseModel):
    total_score: float = 0.0 # 0 to 100
    academic_fit: float = 0.0 # max 35
    funding_fit: float = 0.0 # max 25
    subject_fit: float = 0.0 # max 20
    deadline_fit: float = 0.0 # max 10
    evidence_fit: float = 0.0 # max 10
    explanation: str = ""
    is_eligible_for_shortlist: bool = True
