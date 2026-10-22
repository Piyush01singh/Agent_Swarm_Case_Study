from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timezone
from app.models.profile import StudentProfile
from app.models.opportunity import Opportunity
from app.models.events import AgentEvent
from app.services.gemini_service import gemini_service
from app.security.sanitizer import is_official_domain, is_safe_url
from app.db.repository import repository


class ReviewerIssue(dict):
    """
    Dual dict-string compatible reviewer issue.
    Serializes as Dict[str, Any] for Pydantic state schema, while providing
    string methods (.lower(), __contains__, __str__) for test backward compatibility.
    """
    def __init__(self, data_or_msg=None, **kwargs):
        if isinstance(data_or_msg, dict):
            init_data = dict(data_or_msg)
            init_data.update(kwargs)
        elif isinstance(data_or_msg, str):
            init_data = {"description": data_or_msg, "issue": data_or_msg, **kwargs}
        else:
            init_data = dict(kwargs)
        
        if "description" not in init_data and "issue" in init_data:
            init_data["description"] = init_data["issue"]
        if "issue" not in init_data and "description" in init_data:
            init_data["issue"] = init_data["description"]
            
        super().__init__(init_data)

    def lower(self) -> str:
        return str(self).lower()

    def __contains__(self, key):
        if super().__contains__(key):
            return True
        desc = self.get("description") or self.get("issue") or ""
        return str(key) in desc

    def __str__(self) -> str:
        return self.get("description") or self.get("issue") or ""


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
    ) -> Tuple[List[Opportunity], bool, List[ReviewerIssue]]:
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

        issues: List[ReviewerIssue] = []
        needs_re_research = False

        for opp in opportunities:
            # Check 1: Official Source Domain Validation (Feature F10)
            official_urls = opp.official_source_urls or [opp.canonical_url]
            has_official_domain = any(
                is_safe_url(u) and is_official_domain(u)
                for u in official_urls
            )
            
            if not has_official_domain:
                opp.evidence_quality = "SECONDARY"
                opp.reviewer_status = "FLAGGED"
                issue_msg = f"{opp.university}: Only secondary sources found; requires targeted official page retrieval."
                opp.reviewer_notes = issue_msg
                issues.append(ReviewerIssue({
                    "opportunity_id": opp.id,
                    "university": opp.university,
                    "program_name": opp.program_name,
                    "issue_type": "SECONDARY_SOURCE",
                    "description": issue_msg,
                    "issue": issue_msg
                }))
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
                issues.append(ReviewerIssue({
                    "opportunity_id": opp.id,
                    "university": opp.university,
                    "program_name": opp.program_name,
                    "issue_type": "MISSING_COVERAGE",
                    "description": issue_msg,
                    "issue": issue_msg
                }))
                continue

            # Check 3: Runtime Deadline Verification (Feature F9)
            today_utc = datetime.now(timezone.utc).date()
            d_type = (opp.deadline_type or "").strip().lower()
            d_str = (opp.deadline or "").strip()

            if d_type == "rolling" or d_str.lower() == "rolling":
                deadline_status = "ROLLING"
                opp.deadline_type = "Rolling"
                opp.deadline_verified = True
            elif not d_str:
                deadline_status = "UNKNOWN"
                opp.deadline_type = "Unknown"
                opp.deadline_verified = False
                opp.reviewer_notes = "Application deadline is not explicitly documented on published page."
            else:
                try:
                    parsed_d = datetime.strptime(d_str, "%Y-%m-%d").date()
                    if parsed_d < today_utc:
                        deadline_status = "EXPIRED"
                        opp.deadline_verified = False
                        opp.reviewer_status = "FLAGGED"
                        issue_msg = f"{opp.university}: Application deadline ({opp.deadline}) has passed and is expired; cannot present as active."
                        opp.reviewer_notes = issue_msg
                        issues.append(ReviewerIssue({
                            "opportunity_id": opp.id,
                            "university": opp.university,
                            "program_name": opp.program_name,
                            "issue_type": "EXPIRED_DEADLINE",
                            "description": issue_msg,
                            "issue": issue_msg
                        }))
                        needs_re_research = True

                        try:
                            object.__setattr__(opp, "deadline_status", deadline_status)
                        except Exception:
                            pass

                        await repository.save_agent_event(AgentEvent(
                            run_id=run_id,
                            agent_role=self.role_name,
                            event_type="REVIEWER_FLAGGED",
                            title=f"Flagged Expired Deadline: {opp.university}",
                            description=issue_msg,
                            metadata={"opportunity_id": opp.id, "deadline": opp.deadline}
                        ))
                        continue
                    else:
                        deadline_status = "ACTIVE"
                        opp.deadline_verified = True
                except ValueError:
                    deadline_status = "UNKNOWN"
                    opp.deadline_type = "Unknown"
                    opp.deadline_verified = False
                    opp.reviewer_notes = f"Application deadline '{opp.deadline}' is ambiguous or unverified."

            try:
                object.__setattr__(opp, "deadline_status", deadline_status)
            except Exception:
                pass

            # Check 4: Mandatory Eligibility Criteria (Feature F8)
            has_mandatory_failure = False
            for ev in opp.evidence_records:
                if ev.status == "DOES_NOT_MEET":
                    has_mandatory_failure = True
                    break
            if opp.eligibility_status == "DOES_NOT_MEET":
                has_mandatory_failure = True

            if has_mandatory_failure:
                opp.reviewer_status = "FLAGGED"
                issue_msg = f"{opp.university}: Student fails published mandatory admission criteria."
                opp.reviewer_notes = issue_msg
                issues.append(ReviewerIssue({
                    "opportunity_id": opp.id,
                    "university": opp.university,
                    "program_name": opp.program_name,
                    "issue_type": "MANDATORY_CRITERIA_FAILED",
                    "description": issue_msg,
                    "issue": issue_msg
                }))
                needs_re_research = True
                continue

            # If all checks pass
            opp.reviewer_status = "APPROVED"
            opp.reviewer_notes = "Official source verified; requirements ground student eligibility."

        # Feature F14: Comprehensive Reviewer Audit (Audit all top shortlist candidates, not only index 0)
        if gemini_service.is_available and opportunities:
            candidates_to_audit = [o for o in opportunities if o.is_top_five] or opportunities[:5]
            for candidate in candidates_to_audit:
                audit_res = await gemini_service.review_evidence_and_claims(
                    opportunity_data=candidate.model_dump(mode="json"),
                    student_data=profile.model_dump(mode="json")
                )
                if audit_res.get("success"):
                    gemini_audit = audit_res.get("data", {})
                    if not gemini_audit.get("approved"):
                        candidate.reviewer_status = "FLAGGED"
                        needs_re_research = True
                        issues_detected = gemini_audit.get("issues_detected", [])
                        if not issues_detected:
                            issue_text = f"{candidate.university}: Quality audit rejected by evidence review."
                            candidate.reviewer_notes = issue_text
                            issues.append(ReviewerIssue({
                                "opportunity_id": candidate.id,
                                "university": candidate.university,
                                "program_name": candidate.program_name,
                                "issue_type": "AUDIT_FAILURE",
                                "description": issue_text,
                                "issue": issue_text
                            }))
                        else:
                            for item in issues_detected:
                                issue_str = item.get("issue") if isinstance(item, dict) else str(item)
                                issue_text = f"{candidate.university}: {issue_str}"
                                candidate.reviewer_notes = issue_text
                                issues.append(ReviewerIssue({
                                    "opportunity_id": candidate.id,
                                    "university": candidate.university,
                                    "program_name": candidate.program_name,
                                    "issue_type": "AUDIT_FAILURE",
                                    "description": issue_text,
                                    "issue": issue_text
                                }))
                else:
                    # R2: If quota exhausted or audit uncompleted, mark status UNRESOLVED (fail-closed)
                    candidate.reviewer_status = "UNRESOLVED"
                    err_code = audit_res.get("error", "QUOTA_EXHAUSTED")
                    candidate.reviewer_notes = f"Quality review unreviewed / unresolved ({err_code})."

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
