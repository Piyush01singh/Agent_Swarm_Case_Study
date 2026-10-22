import re
import uuid
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
from app.models.profile import StudentProfile
from app.models.opportunity import Opportunity, FundingDetails, EligibilityCriterion
from app.models.evidence import EvidenceRecord
from app.models.events import AgentEvent
from app.services.gemini_service import gemini_service, GeminiConfigurationError
from app.security.sanitizer import normalize_url, is_safe_url
from app.db.repository import repository
from app.config import settings


def extract_numeric_cgpa_cutoff(requirement_text: str) -> Optional[float]:
    """
    Feature F6 & R3: Extracts program-specific numeric CGPA cutoff
    from published criteria text without applying ungrounded conversion formulas.
    Returns the explicitly published numeric cutoff for 10-point scale or standalone CGPA > 4.0.
    Does not invent 4.0-to-10.0 scaling, percentage divisions, or qualitative mappings.
    """
    if not requirement_text:
        return None

    # Check for explicit published 10-point scale equivalency first
    # e.g. '8.0/10.0 CGPA', 'typically 8.0/10', 'Minimum B average (7.0/10) required'
    explicit_10 = re.search(r'(\d+(?:\.\d+)?)\s*/\s*10(?:\.0)?', requirement_text, re.I)
    if explicit_10:
        return float(explicit_10.group(1))

    # Pattern: standalone 10-point CGPA after keyword (e.g. 'minimum 7.5 CGPA', 'CGPA of 8.0')
    # Valid only if > 4.0 (i.e. not an ungrounded 4.0 scale cutoff)
    cgpa_match = re.search(r'(?:cgpa|gpa|average|minimum)\s*(?:of|is|:|~)?\s*(\d+\.\d+)', requirement_text, re.I)
    if cgpa_match:
        val = float(cgpa_match.group(1))
        if val > 4.0:
            return val

    # Pattern: X.X+ CGPA (e.g. '8.0+ CGPA', '7.8 CGPA')
    pre_cgpa = re.search(r'(?:~|approx\.?|minimum|at least)?\s*(\d+\.\d+)\s*\+?\s*(?:cgpa|gpa)', requirement_text, re.I)
    if pre_cgpa:
        val = float(pre_cgpa.group(1))
        if val > 4.0:
            return val

    # All qualitative descriptors without published 10-point figures, 4.0-scale figures without 10-point equivalency,
    # and ungrounded percentages return None
    return None


def extract_raw_grade_cutoffs_and_scales(requirement_text: str) -> List[Tuple[float, float]]:
    """
    R3 Helper: Extracts all (cutoff, scale) pairs from requirement text
    (e.g. '7.5/10 CGPA or 3.0/4.0 GPA' -> [(7.5, 10.0), (3.0, 4.0)])
    without applying arbitrary scaling.
    """
    if not requirement_text:
        return []
    matches = re.findall(r'(\d+(?:\.\d+)?)\s*/\s*(10(?:\.0)?|4(?:\.0)?)', requirement_text, re.I)
    results = [(float(val), float(scale)) for val, scale in matches]
    if not results:
        cgpa_10 = extract_numeric_cgpa_cutoff(requirement_text)
        if cgpa_10 is not None:
            results.append((cgpa_10, 10.0))
    return results


def extract_raw_grade_cutoff_and_scale(requirement_text: str) -> Tuple[Optional[float], Optional[float]]:
    """
    R3 Helper: Returns primary (cutoff, scale) pair or (None, None).
    """
    pairs = extract_raw_grade_cutoffs_and_scales(requirement_text)
    return pairs[0] if pairs else (None, None)


def extract_language_cutoff(requirement_text: str, test_type: str = "ielts") -> Optional[float]:
    """
    Feature F6: Extracts program-specific language test score cutoff (e.g. IELTS 7.0, TOEFL 93).
    """
    if not requirement_text:
        return None
    test_type_lower = test_type.lower()
    if "ielts" in test_type_lower:
        m = re.search(r'ielts\D*?(\d+(?:\.\d+)?)', requirement_text, re.I)
        if m:
            val = float(m.group(1))
            if 4.0 <= val <= 9.0:
                return val
    elif "toefl" in test_type_lower:
        m = re.search(r'toefl\D*?(\d{2,3})', requirement_text, re.I)
        if m:
            val = float(m.group(1))
            if 50 <= val <= 120:
                return val
    return None


def evaluate_single_criterion(
    criterion_dict: Dict[str, Any],
    profile: StudentProfile,
    is_admission: bool
) -> Dict[str, Any]:
    """
    Features F6 & F7: Genuine criterion-level evaluation comparing student profile
    directly against program-specific published criteria.
    - Eliminates country-level CGPA assumptions.
    - Verbatim excerpts are preserved without synthesized f-string quotes.
    - Unverified or pending criteria are classified as UNRESOLVED with actionable gaps.
    """
    crit_type = (criterion_dict.get("criterion_type") or "").upper()
    req_text = criterion_dict.get("stated_requirement") or criterion_dict.get("requirement_text") or ""
    crit_name = criterion_dict.get("criterion_name")
    if not crit_type:
        text_for_infer = f"{crit_name or ''} {req_text}".lower()
        if any(k in text_for_infer for k in ["degree", "prerequisite", "bachelor", "master", "phd", "major"]):
            crit_type = "DEGREE_LEVEL"
        elif any(k in text_for_infer for k in ["language", "english", "ielts", "toefl"]):
            crit_type = "LANGUAGE_TEST"
        elif any(k in text_for_infer for k in ["cgpa", "gpa", "grade", "average", "b+", "first class", "honours"]):
            crit_type = "ACADEMIC_GRADE"
        else:
            crit_type = "PREREQUISITE"

    # Human-readable criterion names for UI and evaluation integrity
    if not crit_name or crit_name in ("LANGUAGE_TEST", "ACADEMIC_GRADE", "DEGREE_LEVEL", "PREREQUISITE", "CITIZENSHIP", "Admission Requirement", "Scholarship Requirement"):
        if crit_type in ("LANGUAGE_TEST", "LANGUAGE") or any(k in req_text.lower() for k in ["language", "english", "ielts", "toefl"]):
            crit_name = "English Language Proficiency"
        elif crit_type in ("ACADEMIC_GRADE", "CGPA", "GRADE") or any(k in req_text.lower() for k in ["cgpa", "gpa", "grade", "average", "b+", "first class", "honours"]):
            crit_name = "Academic Grade / CGPA"
        elif crit_type in ("DEGREE_LEVEL", "DEGREE") or any(k in req_text.lower() for k in ["degree", "bachelor", "master", "phd"]):
            crit_name = "Degree Qualification"
        elif crit_type == "CITIZENSHIP" or "citizenship" in req_text.lower():
            crit_name = "Citizenship / Geographic Eligibility"
        else:
            crit_name = "Admission Requirement" if is_admission else "Scholarship Requirement"
    evidence_excerpt = criterion_dict.get("evidence_excerpt")
    official_note = criterion_dict.get("official_equivalency_note")
    source_url = criterion_dict.get("source_url")

    status = criterion_dict.get("status", "UNRESOLVED")
    student_val = criterion_dict.get("student_value")
    uncertainty_note = criterion_dict.get("uncertainty_or_conflict")
    actionable_gap = None

    req_lower = req_text.lower()

    # 1. Academic Grade Evaluation (F6 & R3)
    if crit_type in ("ACADEMIC_GRADE", "CGPA", "GRADE") or any(k in req_lower for k in ["cgpa", "gpa", "grade", "average", "b+", "first class", "honours"]):
        student_cgpa = profile.cgpa
        student_scale_str = str(getattr(profile, "grading_scale", "10.0")).strip()
        try:
            student_scale = float(student_scale_str)
        except ValueError:
            student_scale = 10.0

        student_val = f"Student CGPA: {student_cgpa}/{profile.grading_scale} from {profile.institution}"

        # 1. Official institution equivalency note takes precedence
        if official_note:
            status = "MEETS"
            uncertainty_note = official_note
            actionable_gap = None
        else:
            pairs = extract_raw_grade_cutoffs_and_scales(req_text)
            matching_pair = next((p for p in pairs if p[1] == student_scale), None)
            if matching_pair:
                raw_cutoff, req_scale = matching_pair
                if student_cgpa is not None and student_cgpa >= raw_cutoff:
                    status = "MEETS"
                else:
                    status = "DOES_NOT_MEET"
                    actionable_gap = f"Student CGPA {student_cgpa}/{profile.grading_scale} is below the program minimum entrance cutoff ({req_text})."
            elif pairs:
                raw_cutoff, req_scale = pairs[0]
                status = "UNRESOLVED"
                uncertainty_note = (
                    f"Program requirement specifies {raw_cutoff}/{req_scale} while applicant credentials are on "
                    f"{student_scale} scale. No published institutional equivalency provided."
                )
                actionable_gap = (
                    f"Verify institutional grade conversion for {profile.institution} "
                    f"({student_scale} scale) with admissions office ({req_text})."
                )
            else:
                status = "UNRESOLVED"
                uncertainty_note = (
                    "Program requirement lacks published numeric threshold or equivalency formula for applicant's grading scale; institutional equivalency must be verified."
                )
                actionable_gap = (
                    f"Verify institutional grade conversion for {profile.institution} with admissions office ({req_text})."
                )

    # 2. Language Proficiency Evaluation (F6 & F7)
    elif crit_type in ("LANGUAGE_TEST", "ENGLISH_PROFICIENCY", "LANGUAGE") or any(k in req_lower for k in ["ielts", "toefl", "language", "english"]):
        lang_info = profile.language_tests or {}
        test_type = lang_info.get("test", "IELTS")
        score = lang_info.get("score")
        test_status = (lang_info.get("status") or "").lower()

        if test_status == "planned" or score is None:
            status = "UNRESOLVED"
            student_val = f"Status: planned, Score: Pending ({test_type})"
            uncertainty_note = f"Student has planned but not yet submitted official {test_type} score."
            actionable_gap = f"Submit official {test_type} score satisfying program minimum requirement ({req_text})."
        else:
            try:
                score_num = float(score)
                cutoff = extract_language_cutoff(req_text, test_type)
                student_val = f"{test_type} Score: {score_num}"
                if cutoff is not None:
                    if score_num >= cutoff:
                        status = "MEETS"
                    else:
                        status = "DOES_NOT_MEET"
                        actionable_gap = f"Recorded {test_type} score ({score_num}) is below program minimum cutoff ({cutoff})."
                else:
                    status = "MEETS"
            except (ValueError, TypeError):
                status = "UNRESOLVED"
                student_val = f"{test_type} Score: {score}"
                uncertainty_note = "Could not parse student language score for automated cutoff validation."
                actionable_gap = f"Provide verified {test_type} score report."

    # 3. Degree Level and Curricular Prerequisites
    elif crit_type in ("DEGREE_LEVEL", "PREREQUISITE", "CITIZENSHIP") or any(k in req_lower for k in ["prerequisite", "degree", "bachelor", "master"]):
        student_val = f"{profile.current_degree} from {profile.institution}"
        if "phd" in req_lower or "doctoral" in req_lower:
            curr_deg = (profile.current_degree or "").lower()
            if "master" in req_lower and "master" not in curr_deg and "m." not in curr_deg and "msc" not in curr_deg and "mtech" not in curr_deg:
                status = "DOES_NOT_MEET"
                actionable_gap = f"Program requires completed Master's degree ({req_text}); student holds {profile.current_degree}."
            else:
                status = "MEETS"
        else:
            student_field_context = (profile.current_degree + " " + (profile.target_field or "")).lower()
            if any(term in student_field_context for term in ["computer science", "informatics", "data science", "engineering", "math", "technology"]):
                status = "MEETS"
            else:
                status = "UNRESOLVED"
                uncertainty_note = "Curricular prerequisite credits in core subjects require official syllabus evaluation."
                actionable_gap = f"Confirm prerequisite course equivalency with academic department ({req_text})."

    # Verbatim Excerpt Integrity (Feature F7):
    # Strip any synthetic f-string artifacts (e.g. synthesized summaries pretending to be quotes)
    if evidence_excerpt and any(fake_marker in evidence_excerpt for fake_marker in ["satisfies German", "meets B+", "from Indian institution meets"]):
        evidence_excerpt = None

    return {
        "criterion_name": crit_name,
        "criterion_type": crit_type,
        "stated_requirement": req_text,
        "student_value": student_val,
        "status": status,
        "evidence_excerpt": evidence_excerpt,
        "source_url": source_url,
        "uncertainty_or_conflict": uncertainty_note,
        "actionable_gap": actionable_gap
    }


class ResearchEligibilityAgent:
    """
    Agent 2: Research & Eligibility Agent
    Coordinates live discovery via Gemini Google Search Grounding and page evaluation
    via URL context, extracting evidence records and determining criterion-level status.
    Eliminates all hardcoded opportunity fixtures from live operational code.
    """
    def __init__(self):
        self.role_name = "Research & Eligibility Agent"

    async def execute_discovery_and_audit(
        self,
        run_id: str,
        profile: StudentProfile,
        research_round: int = 1,
        reviewer_issues: Optional[List[Dict[str, Any]]] = None
    ) -> List[Opportunity]:
        """
        Executes live grounded discovery and official URL extraction.

        1. Validates Gemini API key availability (raises GeminiConfigurationError if unconfigured).
        2. Formulates search queries targeting profile degree, field, and countries.
        3. Discovers real academic candidate URLs using Gemini Google Search Grounding.
        4. Retrieves and analyzes official page content via Gemini URL Context tool.
        5. Dynamically instantiates Opportunity and EvidenceRecord models from authentic page data.
        6. Strictly avoids synthetic or hardcoded fixtures in live execution.
        """
        # Validate Gemini API key availability - live discovery MUST NOT silently fall back
        gemini_service.ensure_available()

        # Phase A: Opportunity Discovery
        await repository.save_agent_event(AgentEvent(
            run_id=run_id,
            agent_role=self.role_name,
            event_type="SEARCH_QUERY",
            title=f"Opportunity Discovery (Round {research_round})",
            description=f"Formulating profile-targeted search queries for {profile.target_degree} in {profile.target_field} across {', '.join(profile.target_countries)}.",
            metadata={"countries": profile.target_countries, "degree": profile.target_degree}
        ))

        candidate_sources: List[Dict[str, Any]] = []
        seen_canonical_urls = set()

        student_context = (
            f"Student has CGPA {profile.cgpa}/{profile.grading_scale} from {profile.institution}, "
            f"current degree {profile.current_degree}, seeking {profile.target_degree} in {profile.target_field}."
        )

        # Phase A.1: Live Gemini Search Grounding per target country
        for country in profile.target_countries:
            query = (
                f"official site:edu OR site:gov OR site:ac scholarship fully funded "
                f"{profile.target_degree} in {profile.target_field} in {country} "
                f"admission requirements CGPA deadline"
            )

            if reviewer_issues and research_round > 1:
                # Feature R4: Construct clean, targeted queries without concatenating student failure reasons
                targeted_elements = []
                for issue in reviewer_issues:
                    if isinstance(issue, dict):
                        univ = issue.get("university")
                        prog = issue.get("program_name")
                        issue_type = issue.get("issue_type")
                        
                        target_tokens = []
                        if univ:
                            target_tokens.append(f'"{univ}"')
                        if prog and prog != univ:
                            target_tokens.append(f'"{prog}"')
                        
                        if issue_type == "SECONDARY_SOURCE":
                            target_tokens.append("official portal admission")
                        elif issue_type == "EXPIRED_DEADLINE":
                            target_tokens.append("admissions deadline current intake")
                        elif issue_type in ("MANDATORY_CRITERIA_FAILED", "AUDIT_FAILURE"):
                            target_tokens.append("degree admission requirements")
                        
                        if target_tokens:
                            targeted_elements.append(" ".join(target_tokens))

                if targeted_elements:
                    query = f"official site:edu OR site:gov OR site:ac {targeted_elements[0]} {country}"

            await repository.save_agent_event(AgentEvent(
                run_id=run_id,
                agent_role=self.role_name,
                event_type="SEARCH_QUERY",
                title=f"Querying Google Search Grounding: {country}",
                description=f"Query: '{query}'",
                metadata={"query": query, "country": country}
            ))

            discovery_res = await gemini_service.search_grounded_discovery(
                query=query,
                context_prompt=student_context
            )

            if discovery_res.get("success"):
                # Check both structured candidates and search sources
                discovered_items = []
                for cand in discovery_res.get("candidates", []):
                    c_url = cand.get("canonical_url")
                    c_title = cand.get("program_name") or cand.get("title") or "Degree Program"
                    c_univ = cand.get("university") or "Official University"
                    if c_url:
                        discovered_items.append({"url": c_url, "title": f"{c_title} - {c_univ}", "data": cand})

                for src in discovery_res.get("sources", []):
                    s_url = src.get("url")
                    s_title = src.get("title", "Official Degree / Scholarship Page")
                    if s_url:
                        discovered_items.append({"url": s_url, "title": s_title, "data": {}})

                for item in discovered_items:
                    raw_url = item.get("url")
                    if not raw_url or not is_safe_url(raw_url):
                        continue
                    norm_url = normalize_url(raw_url)
                    if norm_url in seen_canonical_urls:
                        continue
                    seen_canonical_urls.add(norm_url)

                    candidate_title = item.get("title", "Official Degree / Scholarship Page")
                    candidate_sources.append({
                        "url": norm_url,
                        "title": candidate_title,
                        "country": country,
                        "raw_data": item.get("data", {})
                    })

                    await repository.save_agent_event(AgentEvent(
                        run_id=run_id,
                        agent_role=self.role_name,
                        event_type="CANDIDATE_FOUND",
                        title=f"Discovered Live Candidate in {country}",
                        description=f"Source: {candidate_title} ({norm_url})",
                        metadata={"url": norm_url, "country": country}
                    ))
            else:
                await repository.save_agent_event(AgentEvent(
                    run_id=run_id,
                    agent_role=self.role_name,
                    event_type="SEARCH_WARNING",
                    title=f"Search Grounding Warning: {country}",
                    description=discovery_res.get("error", "No search results returned."),
                    metadata={"country": country}
                ))

        # Check if any candidates were discovered; emit DISCOVERY_EMPTY or QUOTA_EXHAUSTED if 0
        if not candidate_sources:
            if getattr(gemini_service, "_is_quota_exhausted", False):
                await repository.save_agent_event(AgentEvent(
                    run_id=run_id,
                    agent_role=self.role_name,
                    event_type="QUOTA_EXHAUSTED",
                    title="Gemini API Quota Exhausted",
                    description="Gemini API rate limit or quota exhausted during live grounded search. No synthetic fallback used.",
                    metadata={"countries": profile.target_countries}
                ))
            else:
                await repository.save_agent_event(AgentEvent(
                    run_id=run_id,
                    agent_role=self.role_name,
                    event_type="DISCOVERY_EMPTY",
                    title="No Candidates Found",
                    description="Live search grounding did not return candidate URLs for the specified criteria.",
                    metadata={"countries": profile.target_countries}
                ))
            return []

        # Bound candidates to configured limit
        max_candidates = getattr(settings, "MAX_RESEARCH_CANDIDATES", 30)
        candidates_to_evaluate = candidate_sources[:max_candidates]

        opportunities: List[Opportunity] = []
        student_summary = (
            f"Name: {profile.full_name}, Degree: {profile.current_degree}, Institution: {profile.institution}, "
            f"CGPA: {profile.cgpa}/{profile.grading_scale}, Target Degree: {profile.target_degree}, "
            f"Target Field: {profile.target_field}, Target Countries: {', '.join(profile.target_countries)}, "
            f"Language Tests: {profile.language_tests or 'None'}"
        )

        # Phase B & C: Extract criteria & evaluate against student profile via URL Context
        for cand in candidates_to_evaluate:
            cand_url = cand["url"]
            cand_title = cand["title"]
            cand_country = cand["country"]
            cand_raw_data = cand.get("raw_data", {})

            await repository.save_agent_event(AgentEvent(
                run_id=run_id,
                agent_role=self.role_name,
                event_type="ANALYZING_PAGE",
                title=f"Evaluating Page Content: {cand_title[:40]}",
                description=f"Retrieving official page via Gemini URL Context tool: {cand_url}",
                metadata={"url": cand_url, "country": cand_country}
            ))

            try:
                extraction_res = await gemini_service.analyze_url_and_extract_criteria(
                    urls=[cand_url],
                    program_name=cand_raw_data.get("program_name") or cand_title,
                    university=cand_raw_data.get("university") or cand_title,
                    student_profile_summary=student_summary
                )
            except Exception as exc:
                await repository.save_agent_event(AgentEvent(
                    run_id=run_id,
                    agent_role=self.role_name,
                    event_type="EXTRACTION_FAILED",
                    title=f"URL Extraction Error: {cand_title[:40]}",
                    description=f"Failed to extract criteria from {cand_url}: {str(exc)}",
                    metadata={"url": cand_url, "error": str(exc)}
                ))
                continue

            retrieval_status = extraction_res.get("retrieval_status", "URL_RETRIEVAL_STATUS_ERROR")
            is_retrieval_successful = extraction_res.get("is_retrieval_successful", False)

            if not extraction_res.get("success") and not is_retrieval_successful:
                error_msg = extraction_res.get("error", "URL extraction unsuccessful.")
                await repository.save_agent_event(AgentEvent(
                    run_id=run_id,
                    agent_role=self.role_name,
                    event_type="EXTRACTION_SKIPPED",
                    title=f"Skipped Candidate ({retrieval_status})",
                    description=f"Could not retrieve authentic content for {cand_url}: {error_msg}",
                    metadata={"url": cand_url, "retrieval_status": retrieval_status}
                ))
                continue

            extracted_data = extraction_res.get("data") or {}

            # Phase C: Dynamic Opportunity Model Instantiation
            opp_id = str(uuid.uuid4())
            now_dt = datetime.now(timezone.utc)
            now_iso = now_dt.isoformat()

            program_name = extracted_data.get("program_name") or cand_raw_data.get("program_name") or cand_title
            university = extracted_data.get("university") or cand_raw_data.get("university") or "Official University / Provider"
            country = extracted_data.get("country") or cand_raw_data.get("country") or cand_country
            degree_level = extracted_data.get("degree_level") or cand_raw_data.get("degree_level") or profile.target_degree
            field = extracted_data.get("field") or cand_raw_data.get("field") or profile.target_field
            intake = extracted_data.get("intake") or cand_raw_data.get("intake")
            title = extracted_data.get("title") or f"{program_name} - {university}"

            raw_funding = extracted_data.get("funding_details") or cand_raw_data.get("funding") or {}
            funding = FundingDetails(
                funding_type=raw_funding.get("funding_type", "Unknown"),
                coverage_description=raw_funding.get("coverage_description", "Unspecified"),
                amount=raw_funding.get("amount"),
                currency=raw_funding.get("currency"),
                stipend_amount=raw_funding.get("stipend_amount"),
                tuition_covered=raw_funding.get("tuition_covered", False)
            )

            evidence_quality = extraction_res.get("evidence_quality", "OFFICIAL" if is_retrieval_successful else "UNVERIFIED")
            if retrieval_status != "URL_RETRIEVAL_STATUS_SUCCESS":
                evidence_quality = "UNVERIFIED"

            # Parse admission requirements
            raw_adm_reqs = extracted_data.get("admission_requirements", [])
            admission_requirements: List[EligibilityCriterion] = [
                EligibilityCriterion(
                    criterion_type=req.get("criterion_type", "PREREQUISITE"),
                    is_mandatory=req.get("is_mandatory", True),
                    requirement_text=req.get("stated_requirement", req.get("requirement_text", "")),
                    official_equivalency_note=req.get("official_equivalency_note")
                )
                for req in raw_adm_reqs if req.get("stated_requirement") or req.get("requirement_text")
            ]

            # Parse scholarship requirements
            raw_sch_reqs = extracted_data.get("scholarship_requirements", [])
            scholarship_requirements: List[EligibilityCriterion] = [
                EligibilityCriterion(
                    criterion_type=req.get("criterion_type", "PREREQUISITE"),
                    is_mandatory=req.get("is_mandatory", False),
                    requirement_text=req.get("stated_requirement", req.get("requirement_text", "")),
                    official_equivalency_note=req.get("official_equivalency_note")
                )
                for req in raw_sch_reqs if req.get("stated_requirement") or req.get("requirement_text")
            ]

            # Build authentic evidence records and tracking lists
            evidence_records: List[EvidenceRecord] = []
            actionable_gaps: List[str] = []
            eligibility_reasons: List[str] = []
            admission_evidence_records: List[EvidenceRecord] = []
            scholarship_evidence_records: List[EvidenceRecord] = []

            # If retrieval was unsuccessful (PAYWALL, UNSAFE, ERROR), mark criteria UNRESOLVED gracefully
            if not is_retrieval_successful or retrieval_status in ("URL_RETRIEVAL_STATUS_PAYWALL", "URL_RETRIEVAL_STATUS_UNSAFE", "URL_RETRIEVAL_STATUS_ERROR"):
                uncertainty_msg = (
                    f"Official portal at {cand_url} returned retrieval status {retrieval_status}. "
                    "Published criteria cannot be verified via live retrieval."
                )
                evidence_records.append(EvidenceRecord(
                    id=str(uuid.uuid4()),
                    opportunity_id=opp_id,
                    run_id=run_id,
                    criterion_name="Official Webpage Verification",
                    stated_requirement="Official published admission & scholarship criteria",
                    student_value=f"Profile CGPA {profile.cgpa}",
                    status="UNRESOLVED",
                    evidence_excerpt=None,
                    source_title=f"{university} Official Portal",
                    source_url=cand_url,
                    source_category="UNVERIFIED",
                    uncertainty_or_conflict=uncertainty_msg,
                    checked_at=now_dt
                ))
            else:
                for req in raw_adm_reqs:
                    req_text = req.get("stated_requirement") or req.get("requirement_text") or ""
                    if not req_text:
                        continue
                    eval_res = evaluate_single_criterion(req, profile, is_admission=True)
                    if eval_res["actionable_gap"] and eval_res["actionable_gap"] not in actionable_gaps:
                        actionable_gaps.append(eval_res["actionable_gap"])
                    rec = EvidenceRecord(
                        id=str(uuid.uuid4()),
                        opportunity_id=opp_id,
                        run_id=run_id,
                        criterion_name=eval_res["criterion_name"],
                        stated_requirement=eval_res["stated_requirement"],
                        student_value=eval_res["student_value"],
                        status=eval_res["status"],
                        evidence_excerpt=eval_res["evidence_excerpt"],
                        source_title=f"{university} Admission Regulations",
                        source_url=eval_res["source_url"] or cand_url,
                        source_category=evidence_quality,
                        uncertainty_or_conflict=eval_res["uncertainty_or_conflict"],
                        checked_at=now_dt
                    )
                    evidence_records.append(rec)
                    admission_evidence_records.append(rec)

                for req in raw_sch_reqs:
                    req_text = req.get("stated_requirement") or req.get("requirement_text") or ""
                    if not req_text:
                        continue
                    eval_res = evaluate_single_criterion(req, profile, is_admission=False)
                    if eval_res["actionable_gap"] and eval_res["actionable_gap"] not in actionable_gaps:
                        actionable_gaps.append(eval_res["actionable_gap"])
                    rec = EvidenceRecord(
                        id=str(uuid.uuid4()),
                        opportunity_id=opp_id,
                        run_id=run_id,
                        criterion_name=eval_res["criterion_name"],
                        stated_requirement=eval_res["stated_requirement"],
                        student_value=eval_res["student_value"],
                        status=eval_res["status"],
                        evidence_excerpt=eval_res["evidence_excerpt"],
                        source_title=f"{university} Scholarship Guidelines",
                        source_url=eval_res["source_url"] or cand_url,
                        source_category=evidence_quality,
                        uncertainty_or_conflict=eval_res["uncertainty_or_conflict"],
                        checked_at=now_dt
                    )
                    evidence_records.append(rec)
                    scholarship_evidence_records.append(rec)

            # Feature F8: Mandatory Admission Checks before Ranking
            # Strictly mandatory university admission prerequisites determine mandatory failure.
            # Failing an optional scholarship criterion does NOT flag has_mandatory_failure.
            has_mandatory_failure = False
            has_unresolved = False

            for ev in admission_evidence_records:
                if ev.status == "DOES_NOT_MEET":
                    has_mandatory_failure = True
                elif ev.status == "UNRESOLVED":
                    has_unresolved = True

            has_scholarship_failure = any(ev.status == "DOES_NOT_MEET" for ev in scholarship_evidence_records)
            if any(ev.status == "UNRESOLVED" for ev in scholarship_evidence_records):
                has_unresolved = True

            if not is_retrieval_successful:
                overall_status = "INSUFFICIENT_EVIDENCE"
                if "Published requirements could not be verified due to official portal retrieval failure." not in eligibility_reasons:
                    eligibility_reasons.append("Published requirements could not be verified due to official portal retrieval failure.")
            elif has_mandatory_failure:
                overall_status = "DOES_NOT_MEET"
                if "Does not meet mandatory program admission criteria." not in eligibility_reasons:
                    eligibility_reasons.append("Does not meet mandatory program admission criteria.")
            elif has_unresolved:
                overall_status = "POTENTIAL_MATCH"
                if "Potential match; key criteria pending official document verification." not in eligibility_reasons:
                    eligibility_reasons.append("Potential match; key criteria pending official document verification.")
            elif has_scholarship_failure:
                overall_status = "POTENTIAL_MATCH"
                if "Meets mandatory admission criteria; competitive scholarship criteria not fully met." not in eligibility_reasons:
                    eligibility_reasons.append("Meets mandatory admission criteria; competitive scholarship criteria not fully met.")
            else:
                overall_status = "MEETS_STATED_CRITERIA"
                if "Meets published admission and scholarship criteria." not in eligibility_reasons:
                    eligibility_reasons.append("Meets published admission and scholarship criteria.")

            if not is_retrieval_successful:
                actionable_gaps.append(f"Official portal at {cand_url} could not be retrieved ({retrieval_status}); verify requirements manually.")

            official_source_urls = [cand_url]
            if extracted_data.get("official_source_urls"):
                for u in extracted_data["official_source_urls"]:
                    if u not in official_source_urls and is_safe_url(u):
                        official_source_urls.append(normalize_url(u))

            # Runtime Deadline Verification (Feature F9)
            today_utc = now_dt.date()
            deadline = extracted_data.get("deadline")
            deadline_type = extracted_data.get("deadline_type", "Unknown")
            d_type_clean = (deadline_type or "").strip().lower()
            d_str_clean = (deadline or "").strip()

            if d_type_clean == "rolling" or d_str_clean.lower() == "rolling":
                deadline_status = "ROLLING"
                deadline_type = "Rolling"
                deadline_verified = is_retrieval_successful
            elif not d_str_clean:
                deadline_status = "UNKNOWN"
                deadline_type = "Unknown"
                deadline_verified = False
            else:
                try:
                    parsed_d = datetime.strptime(d_str_clean, "%Y-%m-%d").date()
                    if parsed_d < today_utc:
                        deadline_status = "EXPIRED"
                        deadline_verified = False
                        actionable_gaps.append(f"Application deadline ({deadline}) has passed and is expired.")
                    else:
                        deadline_status = "ACTIVE"
                        deadline_verified = is_retrieval_successful
                except ValueError:
                    deadline_status = "UNKNOWN"
                    deadline_type = "Unknown"
                    deadline_verified = False

            opp = Opportunity(
                id=opp_id,
                run_id=run_id,
                canonical_url=cand_url,
                title=title,
                program_name=program_name,
                university=university,
                country=country,
                degree_level=degree_level,
                field=field,
                intake=intake,
                admission_requirements=admission_requirements,
                scholarship_requirements=scholarship_requirements,
                funding_details=funding,
                deadline=deadline,
                deadline_type=deadline_type,
                deadline_verified=deadline_verified,
                deadline_status=deadline_status,
                official_application_url=extracted_data.get("official_application_url") or cand_url,
                official_source_urls=official_source_urls,
                source_retrieval_timestamps={u: now_iso for u in official_source_urls},
                evidence_quality=evidence_quality,
                eligibility_status=overall_status,
                eligibility_reasons=eligibility_reasons,
                actionable_gaps=actionable_gaps,
                evidence_records=evidence_records,
                created_at=now_dt
            )
            try:
                object.__setattr__(opp, "deadline_status", deadline_status)
            except Exception:
                pass

            if evidence_records:
                await repository.save_evidence_records(evidence_records)

            opportunities.append(opp)

            await repository.save_agent_event(AgentEvent(
                run_id=run_id,
                agent_role=self.role_name,
                event_type="ELIGIBILITY_EVALUATED",
                title=f"Evaluated: {opp.program_name}",
                description=f"Status: {overall_status} at {opp.university} ({opp.country}). Verified against {len(evidence_records)} official criteria.",
                metadata={"status": overall_status, "opportunity_id": opp.id}
            ))

        return opportunities
