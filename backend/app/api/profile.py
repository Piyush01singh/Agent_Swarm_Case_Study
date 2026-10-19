import json
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from app.config import settings
from app.services.document_service import extract_text_from_pdf, extract_text_from_docx, parse_profile_facts_from_text
from app.services.github_service import fetch_github_profile_data
from app.security.sanitizer import ALLOWED_EXTENSIONS
from app.models.profile import StudentProfile, ProjectOrAchievement

router = APIRouter(prefix="/profile", tags=["Profile"])

@router.post("/extract")
async def extract_profile_data(
    resume: Optional[UploadFile] = File(None),
    transcript: Optional[UploadFile] = File(None),
    github_handle: Optional[str] = Form(None),
    profile_json: Optional[str] = Form(None)
):
    """
    Parses resume & transcript files locally without exposing raw documents.
    Prefills academic metrics and enriches with GitHub data.
    """
    resume_text = ""
    transcript_text = ""
    
    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    
    # 1. Process Resume
    if resume:
        content = await resume.read()
        if len(content) > max_bytes:
            raise HTTPException(status_code=400, detail=f"Resume exceeds maximum allowed size of {settings.MAX_UPLOAD_MB}MB.")
        
        filename = (resume.filename or "").lower()
        if filename.endswith(".pdf"):
            try:
                resume_text = extract_text_from_pdf(content)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Error reading resume PDF: {str(e)}")
        elif filename.endswith(".docx"):
            try:
                resume_text = extract_text_from_docx(content)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Error reading resume DOCX: {str(e)}")
        else:
            raise HTTPException(status_code=400, detail="Unsupported resume format. Please upload PDF or DOCX.")

    # 2. Process Transcript
    if transcript:
        content = await transcript.read()
        if len(content) > max_bytes:
            raise HTTPException(status_code=400, detail=f"Transcript exceeds maximum allowed size of {settings.MAX_UPLOAD_MB}MB.")
            
        filename = (transcript.filename or "").lower()
        if filename.endswith(".pdf"):
            try:
                transcript_text = extract_text_from_pdf(content)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Error reading transcript PDF: {str(e)}")
        elif filename.endswith(".docx"):
            try:
                transcript_text = extract_text_from_docx(content)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Error reading transcript DOCX: {str(e)}")
        else:
            raise HTTPException(status_code=400, detail="Unsupported transcript format. Please upload PDF or DOCX.")

    # Base profile initialization
    user_data = {}
    if profile_json:
        try:
            user_data = json.loads(profile_json)
        except Exception:
            pass

    # Extract deterministic facts from text
    combined_text = f"{resume_text}\n{transcript_text}"
    extracted_facts = parse_profile_facts_from_text(combined_text) if combined_text.strip() else {}

    cgpa = user_data.get("cgpa") or extracted_facts.get("cgpa") or 8.2
    degree = user_data.get("current_degree") or extracted_facts.get("degree") or "B.Tech Computer Science"
    skills = list(set((user_data.get("skills") or []) + extracted_facts.get("skills", ["Python", "PyTorch", "FastAPI"])))

    # Fetch GitHub enrichment if provided
    gh_user = github_handle or user_data.get("github_username")
    github_data = None
    projects = []
    if gh_user:
        github_data = await fetch_github_profile_data(gh_user)
        for p in github_data.get("all_projects", []):
            projects.append(ProjectOrAchievement(
                title=p["title"],
                description=p["description"] or "Public GitHub Repository",
                technologies=p["technologies"],
                repo_url=p["repo_url"],
                is_ai_ml=p["is_ai_ml"],
                evidence_source="github"
            ))

    profile = StudentProfile(
        full_name=user_data.get("full_name") or "Rahul Sharma",
        email=user_data.get("email"),
        current_degree=degree,
        institution=user_data.get("institution") or "Punjab Technical University / NIT Jalandhar",
        cgpa=float(cgpa),
        grading_scale=user_data.get("grading_scale") or "10.0",
        target_degree=user_data.get("target_degree") or "Master's",
        target_field=user_data.get("target_field") or "Computer Science / Artificial Intelligence",
        target_countries=user_data.get("target_countries") or ["Canada", "Germany", "Singapore"],
        intended_intake=user_data.get("intended_intake") or "Fall 2026",
        citizenship=user_data.get("citizenship") or "India",
        funding_preference=user_data.get("funding_preference") or "Full Funding / Tuition Assistance",
        skills=skills,
        projects=projects,
        github_username=github_data.get("username") if github_data else gh_user,
        github_data=github_data,
        consent_given=True
    )

    return {
        "success": True,
        "profile": profile,
        "resume_detected": bool(resume_text),
        "transcript_detected": bool(transcript_text),
        "extracted_facts": extracted_facts
    }
