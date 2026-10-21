from typing import List, Optional, Dict
from datetime import datetime
from pydantic import BaseModel, Field
from app.models.evidence import EvidenceRecord, MatchScore

class FundingDetails(BaseModel):
    funding_type: str = "Unknown" # "Fully Funded", "Partial Tuition", "Stipend", "Tuition Waiver", "None"
    coverage_description: str = "TBD"
    amount: Optional[float] = None
    currency: Optional[str] = None
    stipend_amount: Optional[str] = None
    tuition_covered: bool = False

class EligibilityCriterion(BaseModel):
    criterion_type: str # "ACADEMIC_GRADE", "LANGUAGE_TEST", "CITIZENSHIP", "DEGREE_LEVEL", "PREREQUISITE"
    is_mandatory: bool = True
    requirement_text: str
    official_equivalency_note: Optional[str] = None

class Opportunity(BaseModel):
    id: str
    run_id: str
    canonical_url: str
    title: str
    program_name: str
    university: str
    country: str
    degree_level: str = "Master's"
    field: str = "Computer Science"
    intake: Optional[str] = None
    
    admission_requirements: List[EligibilityCriterion] = Field(default_factory=list)
    scholarship_requirements: List[EligibilityCriterion] = Field(default_factory=list)
    funding_details: FundingDetails = Field(default_factory=FundingDetails)
    
    deadline: Optional[str] = None
    deadline_type: str = "Unknown" # "Fixed", "Rolling", "Priority", "Unknown"
    deadline_verified: bool = False
    deadline_status: str = "UNKNOWN" # "ACTIVE", "EXPIRED", "ROLLING", "UNKNOWN"
    
    official_application_url: Optional[str] = None
    official_source_urls: List[str] = Field(default_factory=list)
    source_retrieval_timestamps: Dict[str, str] = Field(default_factory=dict)
    evidence_quality: str = "UNVERIFIED" # "OFFICIAL", "SECONDARY", "INSUFFICIENT", "UNVERIFIED"
    
    eligibility_status: str = "INSUFFICIENT_EVIDENCE" # "MEETS_STATED_CRITERIA", "POTENTIAL_MATCH", "DOES_NOT_MEET", "INSUFFICIENT_EVIDENCE"
    eligibility_reasons: List[str] = Field(default_factory=list)
    actionable_gaps: List[str] = Field(default_factory=list)
    evidence_records: List[EvidenceRecord] = Field(default_factory=list)
    
    match_score: Optional[MatchScore] = None
    is_top_five: bool = False
    reviewer_status: str = "PENDING" # "PENDING", "APPROVED", "REJECTED", "FLAGGED"
    reviewer_notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
