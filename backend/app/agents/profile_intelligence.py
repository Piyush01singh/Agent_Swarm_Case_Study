from typing import Dict, Any, List, Optional
from app.models.profile import StudentProfile, ProjectOrAchievement
from app.models.events import AgentEvent
from app.services.github_service import fetch_github_profile_data
from app.services.document_service import parse_profile_facts_from_text
from app.db.repository import repository

class ProfileIntelligenceAgent:
    """
    Agent 1: Profile Intelligence Agent
    Builds a reliable, structured representation of the student by combining
    resume text, transcripts, user input, and GitHub repository signals.
    """
    def __init__(self):
        self.role_name = "Profile Intelligence Agent"

    async def execute(
        self,
        run_id: str,
        user_input: Dict[str, Any],
        resume_text: Optional[str] = None,
        transcript_text: Optional[str] = None,
        github_url: Optional[str] = None
    ) -> StudentProfile:
        # Emit Start Event
        await repository.save_agent_event(AgentEvent(
            run_id=run_id,
            agent_role=self.role_name,
            event_type="PROFILE_EXTRACTION_STARTED",
            title="Analyzing Student Profile & Academic Documents",
            description="Extracting academic history, degree, grading scale, skills and achievements."
        ))

        # Base facts from user input
        name = user_input.get("full_name") or "Rahul Sharma"
        degree = user_input.get("current_degree") or "B.Tech Computer Science"
        institution = user_input.get("institution") or "Punjab Technical University / NIT Jalandhar"
        cgpa = float(user_input.get("cgpa", 8.2))
        grading_scale = user_input.get("grading_scale", "10.0")
        target_degree = user_input.get("target_degree", "Master's")
        target_field = user_input.get("target_field", "Computer Science / Artificial Intelligence")
        target_countries = user_input.get("target_countries") or ["Canada", "Germany", "Singapore"]
        intended_intake = user_input.get("intended_intake", "Fall 2026")
        citizenship = user_input.get("citizenship", "India")
        funding_pref = user_input.get("funding_preference", "Full Funding / Tuition Assistance")
        skills = list(user_input.get("skills") or ["Python", "PyTorch", "FastAPI", "Machine Learning", "NLP"])
        
        missing_or_conflicting: List[str] = []

        # 1. Parse Resume & Transcript Text
        extracted_doc_facts = {}
        combined_text = ""
        if resume_text:
            combined_text += resume_text + "\n"
        if transcript_text:
            combined_text += transcript_text + "\n"
            
        if combined_text:
            extracted_doc_facts = parse_profile_facts_from_text(combined_text)
            
            # Check for conflict in CGPA
            if extracted_doc_facts.get("cgpa") and abs(extracted_doc_facts["cgpa"] - cgpa) > 0.3:
                missing_or_conflicting.append(
                    f"CGPA Conflict: Document indicates {extracted_doc_facts['cgpa']}, but form specifies {cgpa}."
                )
            # Add skills discovered in resume
            for sk in extracted_doc_facts.get("skills", []):
                if sk not in skills:
                    skills.append(sk)

        # 2. GitHub Profile Enrichment
        github_handle = github_url or user_input.get("github_username") or user_input.get("github_url")
        projects: List[ProjectOrAchievement] = []
        github_data = None
        
        if github_handle:
            await repository.save_agent_event(AgentEvent(
                run_id=run_id,
                agent_role=self.role_name,
                event_type="GITHUB_ENRICHMENT",
                title=f"Enriching Profile from GitHub: {github_handle}",
                description="Querying GitHub REST API for verified repositories, stars, and AI/ML topic tags."
            ))
            github_data = await fetch_github_profile_data(github_handle)
            if "error" in github_data:
                missing_or_conflicting.append(f"GitHub Enrichment Warning: {github_data['error']}")
            else:
                for p in github_data.get("all_projects", []):
                    projects.append(ProjectOrAchievement(
                        title=p["title"],
                        description=p["description"] or "Public repository on GitHub",
                        technologies=p["technologies"],
                        repo_url=p["repo_url"],
                        is_ai_ml=p["is_ai_ml"],
                        evidence_source="github"
                    ))
                    
        # Check if language test is missing
        lang_tests = user_input.get("language_tests") or {"test": "IELTS", "score": None, "status": "planned"}
        if not lang_tests.get("score"):
            missing_or_conflicting.append(
                "Missing Language Score: IELTS/TOEFL score is not yet recorded. Will treat as planned test."
            )

        profile = StudentProfile(
            full_name=name,
            email=user_input.get("email"),
            current_degree=degree,
            institution=institution,
            cgpa=cgpa,
            grading_scale=grading_scale,
            graduation_year=user_input.get("graduation_year", 2026),
            target_degree=target_degree,
            target_field=target_field,
            target_countries=target_countries,
            intended_intake=intended_intake,
            citizenship=citizenship,
            funding_preference=funding_pref,
            language_tests=lang_tests,
            skills=skills,
            projects=projects,
            github_username=github_data.get("username") if github_data else None,
            github_url=github_data.get("profile_url") if github_data else github_handle,
            github_data=github_data,
            career_goals=user_input.get("career_goals") or "Pursue AI/ML graduate research and industry application.",
            consent_given=user_input.get("consent_given", True),
            missing_or_conflicting_facts=missing_or_conflicting
        )

        await repository.save_agent_event(AgentEvent(
            run_id=run_id,
            agent_role=self.role_name,
            event_type="PROFILE_EXTRACTION_COMPLETED",
            title="Profile Intelligence Complete",
            description=f"Constructed verified student profile for {name}. Skills: {len(skills)}, Repos: {len(projects)}, Flags: {len(missing_or_conflicting)}.",
            metadata={"skills_count": len(skills), "projects_count": len(projects), "flags": missing_or_conflicting}
        ))

        return profile
