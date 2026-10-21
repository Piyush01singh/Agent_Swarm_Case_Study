from typing import Tuple, Optional, List
from datetime import datetime, timezone, date
from app.models.profile import StudentProfile
from app.models.opportunity import Opportunity
from app.models.evidence import MatchScore

def calculate_match_score(
    profile: StudentProfile,
    opportunity: Opportunity,
    as_of_date: Optional[date] = None
) -> MatchScore:
    """
    Computes a deterministic match score (0-100) based on five dimensions:
    1. Academic and eligibility fit (max 35)
    2. Funding coverage and financial suitability (max 25)
    3. Subject and program fit (max 20)
    4. Deadline and application readiness (max 10)
    5. Evidence quality and freshness (max 10)
    
    Hard disqualifiers (unmet mandatory admission criteria or expired deadlines)
    set `is_eligible_for_shortlist = False`.
    """
    # 0. Check mandatory eligibility disqualifiers (Feature F8: Admission vs Scholarship)
    has_mandatory_failure = False
    
    # Check admission requirements
    for req in opportunity.admission_requirements:
        if req.is_mandatory:
            for ev in opportunity.evidence_records:
                if ev.criterion_name == req.criterion_type or req.requirement_text in ev.stated_requirement:
                    if ev.status == "DOES_NOT_MEET":
                        has_mandatory_failure = True
                        break

    # Check evidence records directly, ensuring optional scholarship criteria do NOT cause mandatory failure
    for ev in opportunity.evidence_records:
        if ev.status == "DOES_NOT_MEET":
            is_scholarship = (
                "scholarship" in (ev.criterion_name or "").lower()
                or (ev.source_title and "scholarship" in ev.source_title.lower())
                or any(
                    (sch.requirement_text in ev.stated_requirement or ev.stated_requirement in sch.requirement_text)
                    for sch in opportunity.scholarship_requirements
                )
            )
            if is_scholarship:
                continue

            crit_text = f"{ev.criterion_name} {ev.stated_requirement}".lower()
            is_mandatory_prereq = (
                not opportunity.admission_requirements
                or any(
                    req.is_mandatory and (
                        req.criterion_type in ev.criterion_name
                        or req.requirement_text in ev.stated_requirement
                        or ev.stated_requirement in req.requirement_text
                    )
                    for req in opportunity.admission_requirements
                )
                or any(k in crit_text for k in ["admission", "gpa", "cgpa", "grade", "ielts", "toefl", "language", "degree", "prerequisite", "entrance"])
            )
            if is_mandatory_prereq:
                has_mandatory_failure = True
                break
            
    if opportunity.eligibility_status == "DOES_NOT_MEET":
        has_mandatory_failure = True

    # Dimension 1: Academic and Eligibility Fit (35 points)
    academic_score = 0.0
    if has_mandatory_failure:
        academic_score = 0.0
    elif opportunity.eligibility_status == "MEETS_STATED_CRITERIA":
        academic_score = 35.0
    elif opportunity.eligibility_status == "POTENTIAL_MATCH":
        # Dependent on CGPA and degree fit
        base = 25.0
        # If student CGPA >= 8.0, reward high confidence
        if profile.cgpa >= 8.0:
            base += 5.0
        academic_score = min(30.0, base)
    else: # INSUFFICIENT_EVIDENCE
        academic_score = 15.0

    # Dimension 2: Funding Coverage & Suitability (25 points)
    funding_score = 0.0
    f_type = (opportunity.funding_details.funding_type or "").lower()
    coverage = (opportunity.funding_details.coverage_description or "").lower()
    
    if "full" in f_type or "full" in coverage or opportunity.funding_details.tuition_covered:
        funding_score = 25.0
    elif "partial" in f_type or "stipend" in f_type or "waiver" in f_type:
        funding_score = 18.0
    elif opportunity.funding_details.amount and opportunity.funding_details.amount > 10000:
        funding_score = 15.0
    elif "none" in f_type:
        funding_score = 0.0
    else:
        # Unknown/TBD
        funding_score = 10.0

    # Dimension 3: Subject and Program Fit (20 points)
    subject_score = 0.0
    target_field = (profile.target_field or "").lower()
    opp_field = (opportunity.field or "").lower()
    opp_prog = (opportunity.program_name or "").lower()
    
    # Check degree level match
    degree_match = False
    if profile.target_degree.lower() in ("either", opportunity.degree_level.lower()):
        degree_match = True
    elif "master" in profile.target_degree.lower() and "master" in opportunity.degree_level.lower():
        degree_match = True
    elif "phd" in profile.target_degree.lower() and "phd" in opportunity.degree_level.lower():
        degree_match = True
        
    if degree_match:
        subject_score += 8.0

    # Check field keywords
    field_keywords = ["computer science", "artificial intelligence", "ai", "machine learning", "data science", "informatics"]
    matched_keywords = [kw for kw in field_keywords if (kw in opp_field or kw in opp_prog)]
    if matched_keywords:
        subject_score += 12.0
    elif any(word in (opp_field + " " + opp_prog) for word in target_field.split()):
        subject_score += 8.0
    else:
        subject_score += 4.0
    subject_score = min(20.0, subject_score)

    # Dimension 4: Deadline and Application Readiness (10 points - Feature F9)
    now_utc = as_of_date or datetime.now(timezone.utc).date()
    deadline_status = getattr(opportunity, "deadline_status", None)
    d_type = (opportunity.deadline_type or "").strip().lower()
    d_str = (opportunity.deadline or "").strip()

    if not deadline_status or deadline_status == "UNKNOWN":
        if d_type == "rolling" or d_str.lower() == "rolling":
            deadline_status = "ROLLING"
        elif not d_str:
            deadline_status = "UNKNOWN"
        else:
            try:
                parsed_d = datetime.strptime(d_str, "%Y-%m-%d").date()
                if parsed_d < now_utc:
                    deadline_status = "EXPIRED"
                else:
                    deadline_status = "ACTIVE"
            except ValueError:
                deadline_status = "UNKNOWN"
        try:
            object.__setattr__(opportunity, "deadline_status", deadline_status)
        except Exception:
            pass

    deadline_score = 0.0
    if deadline_status == "EXPIRED":
        # Do NOT award deadline readiness score to expired deadlines
        deadline_score = 0.0
    elif deadline_status == "ACTIVE":
        if opportunity.deadline_verified:
            deadline_score = 10.0
        else:
            deadline_score = 6.0
    elif deadline_status == "ROLLING":
        if opportunity.deadline_verified:
            deadline_score = 10.0
        else:
            deadline_score = 8.0
    else: # UNKNOWN
        deadline_score = 2.0

    deadline_score = min(10.0, max(0.0, deadline_score))

    # Dimension 5: Evidence Quality and Freshness (10 points)
    evidence_score = 0.0
    if opportunity.evidence_quality == "OFFICIAL":
        evidence_score = 10.0
    elif opportunity.evidence_quality == "SECONDARY":
        evidence_score = 5.0
    elif opportunity.evidence_quality == "INSUFFICIENT":
        evidence_score = 2.0
    else:
        evidence_score = 1.0

    total = round(academic_score + funding_score + subject_score + deadline_score + evidence_score, 1)
    
    # Eligibility check: mandatory admission passed AND not expired
    is_eligible = not has_mandatory_failure and deadline_status != "EXPIRED"

    # Generate explanatory summary
    reasons = []
    if deadline_status == "EXPIRED":
        reasons.append("Application deadline has passed (EXPIRED); cycle closed")
    
    if has_mandatory_failure:
        reasons.append("Disqualified from shortlist due to unmet mandatory admission or scholarship criteria")
    elif is_eligible:
        if academic_score >= 30:
            reasons.append("Strong academic qualification and eligibility alignment")
        elif academic_score >= 20:
            reasons.append("Potential eligibility match with some criteria pending official confirmation")
        if funding_score >= 20:
            reasons.append("Comprehensive funding/scholarship coverage")
        if subject_score >= 15:
            reasons.append(f"High relevance to student's {profile.target_degree} goals in {opportunity.field}")
        if not reasons:
            reasons.append("General alignment with stated student profile preferences")

    explanation = "; ".join(reasons)

    return MatchScore(
        total_score=total,
        academic_fit=round(academic_score, 1),
        funding_fit=round(funding_score, 1),
        subject_fit=round(subject_score, 1),
        deadline_fit=round(deadline_score, 1),
        evidence_fit=round(evidence_score, 1),
        explanation=explanation,
        is_eligible_for_shortlist=is_eligible
    )
