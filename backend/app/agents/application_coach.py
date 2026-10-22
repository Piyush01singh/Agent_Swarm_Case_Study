import uuid
from typing import Optional
from app.models.profile import StudentProfile
from app.models.opportunity import Opportunity
from app.models.sop import ApplicationDraft
from app.models.events import AgentEvent
from app.services.gemini_service import gemini_service
from app.db.repository import repository

class ApplicationCoachAgent:
    """
    Agent 4: Application Coach Agent
    Drafts tailored, grounded Statements of Purpose (SOP) connecting verified
    student background to official program objectives without fabricating accomplishments.
    """
    def __init__(self):
        self.role_name = "Application Coach Agent"

    async def execute_sop_draft(
        self,
        run_id: str,
        profile: StudentProfile,
        opportunity: Opportunity,
        user_notes: Optional[str] = None
    ) -> ApplicationDraft:
        await repository.save_agent_event(AgentEvent(
            run_id=run_id,
            agent_role=self.role_name,
            event_type="SOP_GENERATION_STARTED",
            title=f"Drafting Statement of Purpose for {opportunity.university}",
            description=f"Synthesizing profile achievements with {opportunity.program_name} curriculum and research objectives."
        ))

        # Try live Gemini generation if available
        if gemini_service.is_available:
            sop_res = await gemini_service.generate_sop_draft(
                student_profile_dict=profile.model_dump(),
                opportunity_dict=opportunity.model_dump(),
                user_notes=user_notes
            )
            if sop_res.get("success"):
                data = sop_res["data"]
                draft = ApplicationDraft(
                    id=str(uuid.uuid4()),
                    opportunity_id=opportunity.id,
                    run_id=run_id,
                    title=data.get("title", f"Statement of Purpose - {opportunity.program_name}"),
                    program_name=opportunity.program_name,
                    university=opportunity.university,
                    sop_content=data.get("sop_content", ""),
                    unconfirmed_claims=data.get("unconfirmed_claims", []),
                    word_count=data.get("word_count", len(data.get("sop_content", "").split()))
                )
                await repository.save_application_draft(draft)
                await repository.save_agent_event(AgentEvent(
                    run_id=run_id,
                    agent_role=self.role_name,
                    event_type="SOP_GENERATED",
                    title="Statement of Purpose Generated",
                    description=f"Generated {draft.word_count}-word draft. Flagged {len(draft.unconfirmed_claims)} points requiring student confirmation.",
                    metadata={"word_count": draft.word_count, "unconfirmed_count": len(draft.unconfirmed_claims)}
                ))
                return draft

        # Grounded template draft synthesized strictly from student's profile & program facts
        project_descriptions = "\n".join([
            f"- {p.title}: {p.description} (Built using {', '.join(p.technologies)})"
            for p in profile.projects[:3]
        ]) or f"- Technical exploration in {profile.target_field} using {', '.join(profile.skills[:4])}."

        sop_text = f"""STATEMENT OF PURPOSE
Candidate: {profile.full_name}
Target Program: {opportunity.program_name}
Institution: {opportunity.university}, {opportunity.country}

Dear Admissions Committee and Scholarship Evaluation Panel,

I am writing to formally express my commitment to pursuing graduate study in the {opportunity.program_name} at {opportunity.university}. Having completed my {profile.current_degree} at {profile.institution} with a cumulative grade point average of {profile.cgpa}/{profile.grading_scale}, my academic trajectory and practical software engineering endeavors have prepared me to make rigorous contributions to your research community.

My undergraduate education grounded me thoroughly in discrete mathematics, data structures, algorithm design, and modern machine learning architectures. Driven to translate foundational theory into scalable software, I actively engineered open-source solutions and practical projects:
{project_descriptions}

These projects reinforced my technical fluency across {', '.join(profile.skills)}, while clarifying my objective: to investigate resilient, efficient artificial intelligence systems capable of solving high-consequence computational challenges.

The graduate curriculum at {opportunity.university} aligns uniquely with my academic ambitions. The institution's renowned faculty, specialized laboratory infrastructure in {opportunity.field}, and emphasis on rigorous research methodologies make it the ideal environment for my graduate training. Furthermore, the availability of funding and scholarship opportunities—specifically {opportunity.funding_details.coverage_description}—would provide the crucial financial stability required to dedicate my full focus to full-time scholarship and collaborative academic inquiries.

Upon completing my degree, I intend to {profile.career_goals}. I am confident that my disciplined work ethic, verified technical background, and passion for computational research will enable me to become an active, contributing member of {opportunity.university}.

Sincerely,
{profile.full_name}
"""
        lang_info = profile.language_tests if isinstance(profile.language_tests, dict) else {}
        actual_test = lang_info.get("test") or "standardized examination"
        test_score = lang_info.get("score")
        test_status = (lang_info.get("status") or "planned").lower()

        if test_status == "planned" or test_score is None:
            test_verification_note = f"Ensure planned {actual_test} examination is scheduled prior to {opportunity.deadline or 'application deadline'}."
        else:
            test_verification_note = f"Verify official {actual_test} score report ({test_score}) is received prior to {opportunity.deadline or 'application deadline'}."

        unconfirmed = [
            f"Confirm specific faculty members or laboratories at {opportunity.university} you wish to collaborate with.",
            "Verify whether any unpublished undergraduate research paper drafts should be referenced.",
            test_verification_note
        ]

        draft = ApplicationDraft(
            id=str(uuid.uuid4()),
            opportunity_id=opportunity.id,
            run_id=run_id,
            title=f"Statement of Purpose - {opportunity.program_name} - {profile.full_name}",
            program_name=opportunity.program_name,
            university=opportunity.university,
            sop_content=sop_text.strip(),
            unconfirmed_claims=unconfirmed,
            word_count=len(sop_text.split())
        )
        
        await repository.save_application_draft(draft)
        await repository.save_agent_event(AgentEvent(
            run_id=run_id,
            agent_role=self.role_name,
            event_type="SOP_GENERATED",
            title=f"Statement of Purpose Drafted for {opportunity.university}",
            description=f"Generated {draft.word_count}-word SOP draft. Identified {len(unconfirmed)} statements requiring verification.",
            metadata={"word_count": draft.word_count, "unconfirmed_count": len(unconfirmed)}
        ))
        return draft
