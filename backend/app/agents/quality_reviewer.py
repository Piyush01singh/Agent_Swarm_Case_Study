from typing import List, Dict, Any, Tuple
from app.models.profile import StudentProfile
from app.models.opportunity import Opportunity
from app.models.events import AgentEvent
from app.services.gemini_service import gemini_service
from app.db.repository import repository

class QualityReviewerAgent:
    """
    Agent 5: Quality Reviewer Agent
    Independently audits research findings, eligibility decisions, and citations to prevent
    unsupported claims from being presented as verified truth.
    """
    def __init__(self):
        self.role_name = "Quality Reviewer Agent"

    async def execute_audit(
        self,
        run_id: str,
        profile: StudentProfile,
        opportunities: List[Opportunity]
    ) -> Tuple[List[Opportunity], bool, List[str]]:
        """
        Audits opportunity claims against official evidence.
        Returns: (reviewed_opportunities, needs_re_research, issues_list)
        """
        await repository.save_agent_event(AgentEvent(
            run_id=run_id,
            agent_role=self.role_name,
            event_type="REVIEW_STARTED",
            title="Independent Evidence Audit",
            description=f"Auditing {len(opportunities)} opportunities against evidence policies and source citations."
        ))

        issues: List[str] = []
        needs_re_research = False

        for opp in opportunities:
            # Check 1: Official Source Domain Validation
            official_urls = opp.official_source_urls or [opp.canonical_url]
            has_official_domain = any(
                u.startswith("https://") and any(dom in u for dom in [".edu", ".ac.", ".ca", ".de", ".sg", ".gov", ".org", "vectorinstitute.ai", "daad.de", "a-star.edu.sg"])
                for u in official_urls
            )
            
            if not has_official_domain:
                opp.evidence_quality = "SECONDARY"
                opp.reviewer_status = "FLAGGED"
                issue_msg = f"{opp.university}: Only secondary sources found; requires targeted official page retrieval."
                opp.reviewer_notes = issue_msg
                issues.append(issue_msg)
                needs_re_research = True
                
                await repository.save_agent_event(AgentEvent(
                    run_id=run_id,
                    agent_role=self.role_name,
                    event_type="REVIEWER_FLAGGED",
                    title=f"Flagged Secondary Source: {opp.university}",
                    description=issue_msg,
                    metadata={"opportunity_id": opp.id}
                ))
                continue

            # Check 2: Funding Claim Grounds
            if opp.funding_details.funding_type == "Fully Funded" and not opp.funding_details.coverage_description:
                opp.reviewer_status = "FLAGGED"
                issue_msg = f"{opp.university}: Claimed 'Fully Funded' without specific coverage breakdown."
                opp.reviewer_notes = issue_msg
                issues.append(issue_msg)
                continue

            # Check 3: Deadline Verification
            if not opp.deadline:
                opp.deadline_type = "Unknown"
                opp.deadline_verified = False
                opp.reviewer_notes = "Application deadline is not explicitly documented on published page."
                
            # If all checks pass
            opp.reviewer_status = "APPROVED"
            opp.reviewer_notes = "Official source verified; requirements ground student eligibility."

        # Audit with Gemini if available
        if gemini_service.is_available and opportunities:
            top_opp = opportunities[0]
            audit_res = await gemini_service.review_evidence_and_claims(
                opportunity_data=top_opp.model_dump(mode="json"),
                student_data=profile.model_dump(mode="json")
            )
            if audit_res.get("success"):
                gemini_audit = audit_res["data"]
                if not gemini_audit.get("approved"):
                    for item in gemini_audit.get("issues_detected", []):
                        issues.append(f"{top_opp.university}: {item.get('issue')}")

        await repository.save_agent_event(AgentEvent(
            run_id=run_id,
            agent_role=self.role_name,
            event_type="REVIEW_COMPLETED",
            title="Quality Review Completed",
            description=f"Audit complete. Approved: {sum(1 for o in opportunities if o.reviewer_status == 'APPROVED')}, Flagged: {sum(1 for o in opportunities if o.reviewer_status == 'FLAGGED')}.",
            metadata={"issues_count": len(issues), "needs_re_research": needs_re_research}
        ))

        # Save reviewed opportunities
        await repository.save_opportunities(run_id, opportunities)
        return opportunities, needs_re_research, issues
