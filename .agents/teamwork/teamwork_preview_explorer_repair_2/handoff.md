# Handoff Report: Eligibility, Query Construction & Architecture Refinement

**Agent Role**: Explorer 2 (Eligibility & Workflow Explorer)  
**Target Milestone**: Repair & Refinement Preview  
**Working Directory**: `D:\Case_study_drive\TetraNoodle_AI_Hackathon\.agents\teamwork\teamwork_preview_explorer_repair_2`  
**Date**: 2026-10-22  
**Status**: COMPLETE (Investigation & Synthesis)  

---

## 1. Observation

### R3: Invented Universal Grade Conversion Formulas
Direct observation of `backend/app/agents/research_eligibility.py`:

1. **Linear 4.0-to-10.0 Scaling in Pattern 1** (`extract_numeric_cgpa_cutoff`, lines 24–30):
   ```python
   scale_match = re.search(r'(\d+(?:\.\d+)?)\s*/\s*(10(?:\.0)?|4(?:\.0)?)', requirement_text, re.I)
   if scale_match:
       val = float(scale_match.group(1))
       scale = float(scale_match.group(2))
       if scale == 4.0:
           return round((val / 4.0) * 10.0, 2)
       return val
   ```
   *Issue*: Automatically multiplies 4.0-scale GPA by 2.5 (`(val / 4.0) * 10.0`) without institutional equivalency guidance.

2. **Unchecked Standalone Heuristics in Patterns 2a & 2b** (lines 33–46):
   ```python
   pre_cgpa = re.search(r'(?:~|approx\.?|minimum|at least)?\s*(\d+\.\d+)\s*\+?\s*(?:cgpa|gpa)', requirement_text, re.I)
   if pre_cgpa:
       val = float(pre_cgpa.group(1))
       if val <= 4.0:
           return round((val / 4.0) * 10.0, 2)
       return val

   cgpa_match = re.search(r'(?:cgpa|gpa|average|minimum)\s*(?:of|is|:|~)?\s*(\d+\.\d+)', requirement_text, re.I)
   if cgpa_match:
       val = float(cgpa_match.group(1))
       if val <= 4.0:
           return round((val / 4.0) * 10.0, 2)
       return val
   ```
   *Issue*: Any standalone number $\le 4.0$ is arbitrarily presumed to be on a 4.0 scale and multiplied by 2.5 to convert to a 10.0 scale.

3. **Percentage-to-CGPA Division in Pattern 2c** (lines 49–52):
   ```python
   pct_match = re.search(r'(\d{2}(?:\.\d+)?)\s*%\s*(?:overall|standing|average|marks)?', requirement_text, re.I)
   if pct_match:
       pct = float(pct_match.group(1))
       return round((pct / 10.0), 2)
   ```
   *Issue*: Divides percentage by 10 (e.g., $78\% \rightarrow 7.8$), which is an ungrounded mathematical conversion not recognized by international admissions offices without specific conversion formulas.

4. **Hardcoded Qualitative Mappings in Pattern 3** (lines 55–63):
   ```python
   req_lower = requirement_text.lower()
   if "first class with distinction" in req_lower:
       return 8.0
   if "first class honours" in req_lower or "first class" in req_lower or "b+ average" in req_lower:
       return 7.5
   if "second upper" in req_lower or "second class upper" in req_lower:
       return 7.5
   if "b average" in req_lower or "b minimum" in req_lower:
       return 7.0
   ```
   *Issue*: Hardcodes qualitative degree benchmarks to arbitrary floating point values (`8.0`, `7.5`, `7.0`) regardless of the country, grading system, or institution.

5. **Linear Student Scale Conversion in `evaluate_single_criterion`** (lines 146–148):
   ```python
   effective_student_cgpa = student_cgpa
   if str(getattr(profile, "grading_scale", "")).strip() == "4.0" and student_cgpa is not None:
       effective_student_cgpa = (student_cgpa / 4.0) * 10.0
   ```
   *Issue*: If a student's profile scale is 4.0, their GPA is scaled by 2.5; furthermore, `official_note` is only inspected when `required_cgpa is None` (line 156), meaning published equivalency notes are ignored if `extract_numeric_cgpa_cutoff` returned a synthetic value.

6. **Test Suite Dependencies on Old Conversions**:
   - `backend/tests/test_m2_eligibility.py`:
     - Line 44: `assert extract_numeric_cgpa_cutoff("Minimum 3.2/4.0 GPA in Computer Science") == 8.0 # scaled to 10`
     - Line 47: `assert extract_numeric_cgpa_cutoff("Requires Second Upper Class Honours / B+ average") == 7.5`
   - `backend/tests/test_tier5_adversarial_backend.py`:
     - Lines 140–151: Parameterized test expecting `7.5`, `8.75`, `10.0`, `8.0`, `7.8`, `7.5`, `7.0` for 4.0-scale cutoffs, percentages, and qualitative strings.

---

### R4: Reviewer Feedback Query Construction
Direct observation of `backend/app/agents/research_eligibility.py` and `backend/app/agents/quality_reviewer.py`:

1. **Concatenation in Discovery Query** (`research_eligibility.py`, lines 288–292):
   ```python
   if reviewer_issues and research_round > 1:
       issue_text = " ".join([str(issue.get("issue", issue)) if isinstance(issue, dict) else str(issue) for issue in reviewer_issues])
       if issue_text:
           query += f" official admissions {issue_text[:80]}"
   ```

2. **Source Strings Produced by Quality Reviewer** (`quality_reviewer.py`, lines 87, 145, 196):
   - Line 87: `issue_msg = f"{opp.university}: Only secondary sources found; requires targeted official page retrieval."`
   - Line 145: `issue_msg = f"{opp.university}: Application deadline ({opp.deadline}) has passed and is expired; cannot present as active."`
   - Line 196: `issue_msg = f"{opp.university}: Student fails published mandatory admission criteria."`

3. **Verbatim Query Result Sent to Google Search Grounding**:
   When re-research executes in Round 2, the query becomes:
   `"official site:edu OR site:gov OR site:ac scholarship fully funded Master's in Computer Science in Canada admission requirements CGPA deadline official admissions University of Toronto: Student fails published mandatory admission criteria."`
   *Issue*: Search Grounding receives internal student audit rejection notes (`Student fails published mandatory admission criteria`, `Application deadline ... has passed and is expired; cannot present as active`). This pollutes search results and hinders discovering legitimate programs and official admission requirements.

---

### R6: Clarify Agent 4 Architecture & Polish UI/Templates
Direct observation of `backend/app/agents/application_coach.py`, `frontend/index.html`, `backend/app/graph/workflow.py`, `backend/app/api/opportunities.py`, `docs/ARCHITECTURE.md`, and `README.md`:

1. **Hardcoded Test Type in `application_coach.py`** (lines 92–96):
   ```python
   unconfirmed = [
       f"Confirm specific faculty members or laboratories at {opportunity.university} you wish to collaborate with.",
       "Verify whether any unpublished undergraduate research paper drafts should be referenced.",
       f"Ensure planned language proficiency test (IELTS) is scheduled prior to {opportunity.deadline or 'application deadline'}."
   ]
   ```
   *Issue*: Line 95 rigidly hardcodes `(IELTS)`. The student's `StudentProfile.language_tests` (in `backend/app/models/profile.py` line 38) can be TOEFL, Duolingo, GRE, or completed with a specific score. The test type is never dynamically injected.

2. **Default Document Title in `frontend/index.html`** (line 7):
   ```html
   <title>frontend</title>
   ```
   *Issue*: Title is the Vite default template string `"frontend"` rather than `"ScholarSwarm — AI Scholarship Intelligence"`.

3. **Agent 4 Architecture in Workflow vs. API**:
   - In `backend/app/graph/workflow.py` (lines 143–166):
     ```python
     workflow.add_node("profile_intelligence", node_profile_intelligence)
     workflow.add_node("research_discovery", node_research_discovery)
     workflow.add_node("match_strategist", node_match_strategist)
     workflow.add_node("quality_reviewer", node_quality_reviewer)
     workflow.add_node("application_coaching", node_application_coaching)

     workflow.set_entry_point("profile_intelligence")
     workflow.add_edge("profile_intelligence", "research_discovery")
     workflow.add_edge("research_discovery", "match_strategist")
     workflow.add_edge("match_strategist", "quality_reviewer")

     workflow.add_conditional_edges(
         "quality_reviewer",
         route_after_review,
         {
             "research_discovery": "research_discovery",
             "match_strategy": "match_strategist",
             "__end__": END
         }
     )
     ```
     `application_coaching` is defined as a node but has **no incoming or outgoing graph edges**. The discovery loop terminates at `END` after `quality_reviewer`.
   - In `backend/app/api/opportunities.py` (lines 30–57):
     ```python
     @router.post("/{opportunity_id}/sop", response_model=ApplicationDraft)
     async def generate_sop_for_opportunity(opportunity_id: str, payload: Optional[SopGenerationRequest] = None):
         ...
         draft = await coach_agent.execute_sop_draft(
             run_id=opp.run_id,
             profile=run.student_profile,
             opportunity=opp,
             user_notes=user_notes
         )
         return draft
     ```
     Agent 4 operates **on-demand** when the user selects a specific shortlisted candidate, avoiding redundant LLM generation across all unranked or rejected candidates.
   - In `docs/ARCHITECTURE.md` (lines 19, 26, 90) and `README.md` (lines 5, 23, 63): Agent 4 is listed alongside the discovery agents without explicit documentation stating that Agent 4 operates as an on-demand application specialist rather than an autonomous node inside the LangGraph discovery cycle.

---

## 2. Logic Chain

### Logic Chain for R3: Eliminating Invented Universal Conversions
1. **Fact**: In academia, there is no universal mathematical constant or linear mapping to convert a 4.0 GPA scale to a 10.0 scale, nor does dividing a percentage by 10 represent an accredited conversion. A $3.0/4.0$ cutoff at one university may correspond to $65\%$ (or $7.0/10$) in India, while at another it may correspond to $8.0/10$.
2. **Fact**: `extract_numeric_cgpa_cutoff` lines 28–29, 36–37, 44–45 linearly multiply by 2.5; line 52 divides percentages by 10; lines 56–63 map qualitative terms ("first class with distinction", "b+ average") to fixed floats (`8.0`, `7.5`, `7.0`).
3. **Fact**: `evaluate_single_criterion` lines 147–148 converts a student's 4.0 scale to 10.0 linearly.
4. **Deduction**: Because these conversions are ungrounded heuristics, an Indian applicant evaluated against a 4.0-scale requirement will pass or fail based on an invented formula rather than authentic admissions guidance.
5. **Solution**:
   - Separate cutoff value extraction from grading scale normalization.
   - Retain numeric extraction for published criteria that specify their scale (e.g., $8.0/10.0$ or $3.2/4.0$).
   - If requirement text explicitly contains published equivalency guidance (e.g., `"equivalent to 8.0/10 from Indian universities"` or `"approx. 7.5+ CGPA on 10-point scale"`), or if `official_equivalency_note` is attached, evaluate against that published threshold.
   - When the student's scale and requirement scale differ (e.g., student $10.0$, requirement $4.0$) and no published equivalency exists, do NOT perform linear math. Mark status as `UNRESOLVED` with:
     - `uncertainty_or_conflict`: `"Program requirement uses a 4.0 GPA scale while student credentials are on a 10.0 scale without published institutional equivalency."`
     - `actionable_gap`: `f"Verify institutional grade conversion for {profile.institution} with admissions office ({req_text})."`
   - For qualitative requirements (e.g., `"First Class with Distinction"`), if no `official_note` is present, do NOT invent $8.0$. Mark status as `UNRESOLVED` with an actionable gap to verify institutional grade conversion.

### Logic Chain for R4: Targeted Search Query Construction
1. **Fact**: In Round 2 re-research, `reviewer_issues` contains diagnostic reasons such as `"{opp.university}: Student fails published mandatory admission criteria."` or `"{opp.university}: Application deadline ({opp.deadline}) has passed and is expired; cannot present as active."`.
2. **Fact**: `research_eligibility.py` line 291 directly appends these raw diagnostic strings to the Google Search Grounding query string.
3. **Deduction**: Google Search evaluates keywords literally; searching for `Student fails published mandatory admission criteria` retrieves forum discussions on failure rather than official university admission portals, active deadlines, or prerequisite requirements.
4. **Solution**:
   - Parse `reviewer_issues` into structured tokens: provider (`university`), program (`program_name`), and specific unresolved/flagged criterion (`criterion_name` or `issue_type`).
   - Construct short, high-precision search queries:
     - For `SECONDARY_SOURCE`: `f'"{provider}" "{program_name}" official admissions portal'`
     - For `EXPIRED_DEADLINE`: `f'"{provider}" "{program_name}" admissions deadline 2025 2026'`
     - For `MANDATORY_CRITERIA_FAILED` / `UNRESOLVED`: `f'"{provider}" {profile.target_degree} in {profile.target_field} official admission requirements'`
   - Strip all student failure statements (`"fails"`, `"expired"`, `"cannot present"`) from search query text.

### Logic Chain for R6: Architecture Clarification & UI Polish
1. **Fact**: `frontend/index.html` line 7 currently has `<title>frontend</title>`, which is unthemed. Changing this to `<title>ScholarSwarm — AI Scholarship Intelligence</title>` fulfills the UI requirement.
2. **Fact**: In `backend/app/agents/application_coach.py` line 95, `(IELTS)` is hardcoded. `StudentProfile` contains `language_tests` (which stores the actual test name, score, and status). Extracting `profile.language_tests.get("test")` (or checking for GRE/TOEFL) allows dynamic injection into the unconfirmed statements and SOP text.
3. **Fact**: In `workflow.py`, `application_coaching` is added to `StateGraph` without incoming/outgoing edges. The actual user workflow invokes Agent 4 via `POST /opportunities/{id}/sop` in `opportunities.py`. Clarifying this in `docs/ARCHITECTURE.md` and `README.md` resolves architectural ambiguity.

---

## 3. Caveats

1. **Backwards Compatibility in Tests**:
   - Existing unit tests in `backend/tests/test_m2_eligibility.py` (lines 44, 47) and `backend/tests/test_tier5_adversarial_backend.py` (lines 140–151) were originally written to verify the legacy scaling formulas (e.g., expecting `extract_numeric_cgpa_cutoff("Minimum 3.2/4.0 GPA") == 8.0`).
   - When the implementer removes ungrounded conversions, those test assertions must be updated to expect either the raw unscaled cutoff, `None` for ungrounded qualitative mappings, or to test `evaluate_single_criterion` resolving to `UNRESOLVED`.
2. **Official Equivalencies in Fixtures**:
   - Test fixtures in `backend/tests/fixtures/opportunities.py` contain explicit `official_equivalency_note` strings (e.g., `"PTU/NIT first class with distinction satisfied by 8.2 CGPA"`). The new evaluation logic must preserve `MEETS` when this official guidance is provided.

---

## 4. Conclusion & Precise Recommended Changes

### Recommended Change 1 (R3): `backend/app/agents/research_eligibility.py`
Refactor grade extraction and criterion evaluation:

#### 1.A: Update `extract_numeric_cgpa_cutoff` (lines 15–66)
```python
def extract_numeric_cgpa_cutoff(requirement_text: str) -> Optional[float]:
    """
    Feature F6 & R3: Extracts program-specific numeric CGPA cutoff
    from published criteria text without applying ungrounded conversion formulas.
    Returns the explicitly published numeric cutoff for 10-point scale or standalone CGPA.
    Does not invent 4.0-to-10.0 scaling, percentage divisions, or qualitative mappings.
    """
    if not requirement_text:
        return None

    # Check for explicit published 10-point scale equivalency first
    # e.g. 'typically 8.0/10', 'equivalent to 8.0/10', '8.0/10.0 CGPA'
    explicit_10 = re.search(r'(\d+(?:\.\d+)?)\s*/\s*10(?:\.0)?', requirement_text, re.I)
    if explicit_10:
        return float(explicit_10.group(1))

    # Pattern: standalone 10-point CGPA after keyword (e.g. 'minimum 7.5 CGPA', 'CGPA of 8.0')
    # Valid only if > 4.0 or explicitly stated as CGPA/10
    cgpa_match = re.search(r'(?:cgpa|gpa|average|minimum)\s*(?:of|is|:|~)?\s*(\d+\.\d+)', requirement_text, re.I)
    if cgpa_match:
        val = float(cgpa_match.group(1))
        if val > 4.0:
            return val

    # Pattern: X.X+ CGPA (e.g. '8.0+ CGPA', '7.5 CGPA')
    pre_cgpa = re.search(r'(?:~|approx\.?|minimum|at least)?\s*(\d+\.\d+)\s*\+?\s*(?:cgpa|gpa)', requirement_text, re.I)
    if pre_cgpa:
        val = float(pre_cgpa.group(1))
        if val > 4.0:
            return val

    # All qualitative descriptors without published 10-point figures and ungrounded percentages return None
    return None


def extract_raw_grade_cutoff_and_scale(requirement_text: str) -> Tuple[Optional[float], Optional[float]]:
    """
    Helper to extract raw cutoff and explicit scale (e.g., 3.2 on 4.0 scale, 8.0 on 10.0 scale).
    """
    if not requirement_text:
        return None, None

    # Check for published X/10 or X/4
    m = re.search(r'(\d+(?:\.\d+)?)\s*/\s*(10(?:\.0)?|4(?:\.0)?)', requirement_text, re.I)
    if m:
        return float(m.group(1)), float(m.group(2))

    cgpa = extract_numeric_cgpa_cutoff(requirement_text)
    if cgpa is not None:
        return cgpa, 10.0

    return None, None
```

#### 1.B: Update `evaluate_single_criterion` (lines 139–163)
```python
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
            raw_cutoff, req_scale = extract_raw_grade_cutoff_and_scale(req_text)
            
            if raw_cutoff is not None and req_scale is not None:
                if req_scale == student_scale:
                    # Direct comparison on identical scale
                    if student_cgpa is not None and student_cgpa >= raw_cutoff:
                        status = "MEETS"
                    else:
                        status = "DOES_NOT_MEET"
                        actionable_gap = f"Student CGPA {student_cgpa}/{profile.grading_scale} is below the program minimum entrance cutoff ({req_text})."
                else:
                    # Scale mismatch without published institutional equivalency
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
                # Qualitative requirement or percentage without published equivalency
                status = "UNRESOLVED"
                uncertainty_note = (
                    "Program requirement lacks published numeric threshold or equivalency formula for applicant's grading scale."
                )
                actionable_gap = (
                    f"Verify institutional grade conversion for {profile.institution} with admissions office ({req_text})."
                )
```

---

### Recommended Change 2 (R4): `backend/app/agents/research_eligibility.py`
Replace lines 288–292 in `execute_discovery_and_audit`:

#### Before:
```python
            if reviewer_issues and research_round > 1:
                issue_text = " ".join([str(issue.get("issue", issue)) if isinstance(issue, dict) else str(issue) for issue in reviewer_issues])
                if issue_text:
                    query += f" official admissions {issue_text[:80]}"
```

#### After:
```python
            if reviewer_issues and research_round > 1:
                # Feature R4: Construct clean, targeted queries without concatenating failure reasons
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
                        elif issue_type == "MANDATORY_CRITERIA_FAILED":
                            target_tokens.append("degree admission requirements")
                        
                        if target_tokens:
                            targeted_elements.append(" ".join(target_tokens))

                if targeted_elements:
                    # Derive short, targeted search phrase from the primary unresolved issue
                    query = (
                        f"official site:edu OR site:gov OR site:ac "
                        f"{targeted_elements[0]} {country}"
                    )
```

---

### Recommended Change 3 (R6):
#### 3.A: `backend/app/agents/application_coach.py` (lines 65–108)
Dynamically inject actual applicant test type from `profile.language_tests`:
```python
        # Extract applicant's actual test type dynamically
        lang_info = profile.language_tests if isinstance(profile.language_tests, dict) else {}
        actual_test = lang_info.get("test") or "standardized examination"
        test_score = lang_info.get("score")
        test_status = (lang_info.get("status") or "planned").lower()

        test_verification_note = (
            f"Ensure planned {actual_test} examination is scheduled prior to {opportunity.deadline or 'application deadline'}."
            if (test_status == "planned" or test_score is None)
            else f"Verify official {actual_test} score report ({test_score}) is received prior to {opportunity.deadline or 'application deadline'}."
        )

        unconfirmed = [
            f"Confirm specific faculty members or laboratories at {opportunity.university} you wish to collaborate with.",
            "Verify whether any unpublished undergraduate research paper drafts should be referenced.",
            test_verification_note
        ]
```

#### 3.B: `frontend/index.html` (line 7)
```html
<!-- Before -->
<title>frontend</title>

<!-- After -->
<title>ScholarSwarm — AI Scholarship Intelligence</title>
```

#### 3.C: `docs/ARCHITECTURE.md` and `README.md`
Add clear documentation explaining the Agent 4 execution model:
1. In `docs/ARCHITECTURE.md` Section 3 ("The Five Agent Roles and Division of Labor"):
   Add a note below the table:
   > **Note on Agent 4 Execution Model**: Agent 4 (Application Coach) is designed as an **on-demand application specialist** invoked selectively via `POST /api/opportunities/{id}/sop`. It does not execute as an autonomous looping node inside the core LangGraph research discovery loop (`Profile Intelligence -> Research Discovery -> Match Strategist -> Quality Reviewer`). This ensures zero speculative LLM token consumption for unranked or rejected candidates.
2. In `README.md` Section 1 ("Architecture"):
   Clarify in the multi-agent description that Agents 1, 2, 3, and 5 form the autonomous discovery and self-correction loop, while Agent 4 is invoked on-demand when a user selects a specific matched opportunity to draft a Statement of Purpose.

---

## 5. Verification Method

### 1. Grade Conversion Verification
- File: `backend/tests/test_m2_eligibility.py` and `backend/tests/test_tier5_adversarial_backend.py`
- Command:
  ```bash
  pytest backend/tests/test_m2_eligibility.py backend/tests/test_tier5_adversarial_backend.py -v
  ```
- Invalidation Condition: Any test asserting an ungrounded linear conversion ($3.2/4.0 \rightarrow 8.0/10.0$ or percentage division) without published institution equivalency must fail if the conversion is still active. Scale mismatches must evaluate to `UNRESOLVED`.

### 2. Reviewer Feedback Query Verification
- Inspect generated query in `research_eligibility.py`:
  Ensure search queries in Round 2 contain provider name and program requirements, but never contain strings such as `"Student fails published mandatory admission criteria"` or `"Application deadline ... expired"`.

### 3. Agent 4 Test Type Injection Verification
- Instantiate a `StudentProfile` with `language_tests={"test": "TOEFL", "score": "105", "status": "completed"}`.
- Execute `coach_agent.execute_sop_draft` in offline mode.
- Invalidation Condition: If `unconfirmed` contains `"IELTS"`, the test fails.

### 4. Frontend Title Verification
- Command:
  ```bash
  grep "<title>" frontend/index.html
  ```
- Expected output:
  `<title>ScholarSwarm — AI Scholarship Intelligence</title>`

### 5. Full Offline Suite Verification
- Command:
  ```bash
  pytest backend/tests/
  ```
  All tests must pass with zero external network access and zero quota consumption.
