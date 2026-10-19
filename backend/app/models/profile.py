from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class AcademicRecord(BaseModel):
    degree: str
    institution: str
    cgpa_or_percentage: float
    grading_scale: str = "10.0"
    graduation_year: Optional[int] = None
    major: Optional[str] = None
    transcripts_attached: bool = False
    provenance: str = "document" # "document", "user_input", "inferred"

class ProjectOrAchievement(BaseModel):
    title: str
    description: str
    technologies: List[str] = Field(default_factory=list)
    repo_url: Optional[str] = None
    is_ai_ml: bool = False
    evidence_source: str = "resume" # "resume", "github", "user_input"

class StudentProfile(BaseModel):
    full_name: str = "Rahul Sharma"
    email: Optional[str] = None
    current_degree: str = "B.Tech Computer Science"
    institution: str = "Punjab Technical University / NIT Jalandhar"
    cgpa: float = 8.2
    grading_scale: str = "10.0"
    graduation_year: Optional[int] = 2026
    
    target_degree: str = "Master's" # "Master's", "PhD", "Either"
    target_field: str = "Computer Science / Artificial Intelligence"
    target_countries: List[str] = Field(default_factory=lambda: ["Canada", "Germany", "Singapore"])
    intended_intake: Optional[str] = "Fall 2026"
    citizenship: Optional[str] = "India"
    funding_preference: Optional[str] = "Full Funding / Tuition Assistance"
    
    language_tests: Dict[str, Any] = Field(default_factory=lambda: {"test": "IELTS", "score": None, "status": "planned"})
    skills: List[str] = Field(default_factory=lambda: ["Python", "PyTorch", "FastAPI", "Machine Learning", "NLP"])
    projects: List[ProjectOrAchievement] = Field(default_factory=list)
    
    github_username: Optional[str] = None
    github_url: Optional[str] = None
    github_data: Optional[Dict[str, Any]] = None
    
    career_goals: Optional[str] = "To pursue research in scalable AI systems and return or contribute to cutting-edge research institutes."
    consent_given: bool = True
    missing_or_conflicting_facts: List[str] = Field(default_factory=list)

class ProfileExtractionRequest(BaseModel):
    resume_text: Optional[str] = None
    transcript_text: Optional[str] = None
    github_username_or_url: Optional[str] = None
    user_overrides: Optional[Dict[str, Any]] = None
    consent_given: bool = True
