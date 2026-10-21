# Handoff Report: Reviewer M2.1 — Milestone M2 Review & Adversarial Audit

**Agent**: Reviewer M2.1 (`teamwork_preview_reviewer_m2_1`)  
**Target Milestone**: M2 (Features F6, F7, F8, F9, F10)  
**Parent Orchestrator ID**: `6828b193-f5c1-4991-90e8-8c39694edfd6`  
**Worker Under Review**: Worker M2 (`teamwork_preview_worker_m2`)  
**Verdict**: **`REQUEST_CHANGES`**  
**Date**: 2026-10-20T22:28:30Z  

---

## 1. Observation

### 1.1 Mandated Test Command Executions
1. `pytest tests/test_m2_eligibility.py -v`:
   - Command: `pytest tests/test_m2_eligibility.py -v` in `D:\Case_study_drive\TetraNoodle_AI_Hackathon\backend`
   - Result: `18 passed in 2.59s`. All 18 unit tests passed cleanly.
2. `pytest tests/e2e/test_tier1_feature_coverage.py -k "f6 or f7 or f8 or f9 or f10" -v`:
   - Command: `pytest tests/e2e/test_tier1_feature_coverage.py -k "f6 or f7 or f8 or f9 or f10" -v` in `D:\Case_study_drive\TetraNoodle_AI_Hackathon\backend`
   - Result: `5 passed, 5 deselected in 0.06s`.
3. `pytest tests/test_m1_grounding.py -v`:
   - Command: `pytest tests/test_m1_grounding.py -v` in `D:\Case_study_drive\TetraNoodle_AI_Hackathon\backend`
   - Result: `14 passed in 6.79s`.

---

### 1.2 Regressions and Runtime Failures Observed in Wider Suite
When running the full test suite and challenger stress suites:
1. `pytest tests/test_m1_challenger_stress.py -v`:
   - Result: `4 failed, 13 passed in 8.98s`.
   - Verbatim failure traceback:
     ```
     FAILED tests/test_m1_challenger_stress.py::test_empirical_research_agent_paywall_graceful_degradation
     FAILED tests/test_m1_challenger_stress.py::test_empirical_unsafe_and_ssrf_urls_rejected_before_extraction
     FAILED tests/test_m1_challenger_stress.py::test_empirical_duplicate_url_deduplication_in_discovery
     FAILED tests/test_m1_challenger_stress.py::test_empirical_candidate_bounding_to_max_configured
     
     E   NameError: name 'eligibility_reasons' is not defined
     app\agents\research_eligibility.py:533: NameError
     ```
2. Direct invocation test of `ResearchEligibilityAgent.execute_discovery_and_audit` with mock extraction containing criteria:
   - Verbatim error:
     ```
     Traceback (most recent call last):
       File "D:\Case_study_drive\TetraNoodle_AI_Hackathon\backend\app\agents\research_eligibility.py", line 473, in execute_discovery_and_audit
         if eval_res["actionable_gap"] and eval_res["actionable_gap"] not in actionable_gaps:
                                                                             ^^^^^^^^^^^^^^^
     NameError: name 'actionable_gaps' is not defined
     ```

---

### 1.3 Direct Codebase Observations
1. **Uninitialized Variables in `research_eligibility.py`**:
   - In `backend/app/agents/research_eligibility.py`, lines 473–474:
     ```python
     if eval_res["actionable_gap"] and eval_res["actionable_gap"] not in actionable_gaps:
         actionable_gaps.append(eval_res["actionable_gap"])
     ```
   - In lines 525–534:
     ```python
     if has_mandatory_failure:
         overall_status = "DOES_NOT_MEET"
         if "Does not meet mandatory program admission criteria." not in eligibility_reasons:
             eligibility_reasons.append("Does not meet mandatory program admission criteria.")
     elif has_unresolved or not is_retrieval_successful:
         overall_status = "POTENTIAL_MATCH"
         if "Potential match; key criteria pending official document verification." not in eligibility_reasons:
             eligibility_reasons.append("Potential match; key criteria pending official document verification.")
     else:
         overall_status = "MEETS_STATED_CRITERIA"
         if "Meets published admission and scholarship criteria." not in eligibility_reasons:
             eligibility_reasons.append("Meets published admission and scholarship criteria.")
     ```
   - Neither `actionable_gaps` nor `eligibility_reasons` is initialized in the `for cand in candidates_to_evaluate:` loop before being accessed.

2. **Conflation of Mandatory Admission and Optional Scholarship Requirements**:
   - In `backend/app/agents/research_eligibility.py`, lines 515–520:
     ```python
     has_mandatory_failure = False
     has_unresolved = False
     for ev in evidence_records:
         if ev.status == "DOES_NOT_MEET":
             has_mandatory_failure = True
     ```
   - In `backend/app/services/scoring_service.py`, lines 36–39:
     ```python
     for ev in opportunity.evidence_records:
         if ev.status == "DOES_NOT_MEET":
             has_mandatory_failure = True
             break
     ```
   - Both admission and scholarship records are appended to `opportunity.evidence_records`. When evaluating `has_mandatory_failure`, any failure on an optional, competitive scholarship criterion marks `has_mandatory_failure = True`, zeroing `academic_fit = 0.0` and setting `is_eligible_for_shortlist = False`.

3. **Pydantic Model Schema Missing `deadline_status`**:
   - In `backend/app/models/opportunity.py`, lines 20–55: `deadline_status` is not defined as a field in `Opportunity`.
   - In `research_eligibility.py` line 603, `quality_reviewer.py` line 101, and `scoring_service.py` line 127: code relies on `object.__setattr__(opp, "deadline_status", deadline_status)`.
   - Serializing via `opp.model_dump()` drops `deadline_status` entirely, breaking the API contract in `PROJECT.md` line 130 (`deadline_status: "ACTIVE" | "EXPIRED" | "ROLLING" | "UNKNOWN"`).

4. **Grading Scale Conversion Omission in Student Profile**:
   - In `backend/app/agents/research_eligibility.py`, lines 104–110:
     ```python
     required_cgpa = extract_numeric_cgpa_cutoff(req_text)
     student_cgpa = profile.cgpa
     if required_cgpa is not None:
         if student_cgpa >= required_cgpa:
             status = "MEETS"
         else:
             status = "DOES_NOT_MEET"
     ```
   - `extract_numeric_cgpa_cutoff` converts 4.0 scale cutoffs to 10.0 scale (e.g. 3.2/4 -> 8.0/10). However, a student profile with `profile.cgpa = 3.8` and `profile.grading_scale = "4.0"` is compared directly as `3.8 >= 8.0` without scale normalization, incorrectly resulting in `DOES_NOT_MEET`.

---

## 2. Logic Chain

1. **Step 1 (Root Cause of Runtime Pipeline Crash)**:
   - *Observation*: `test_m1_challenger_stress.py` failed 4 tests with `NameError: name 'eligibility_reasons' is not defined`. Direct execution with extracted criteria failed with `NameError: name 'actionable_gaps' is not defined`.
   - *Reasoning*: The live pipeline's primary method `ResearchEligibilityAgent.execute_discovery_and_audit` instantiates an `Opportunity` for each discovered candidate. Inside the per-candidate loop, it appends to `actionable_gaps` and `eligibility_reasons` before those variables are declared.
   - *Inference*: Any call to `execute_discovery_and_audit` in production or mocked integration tests crashes with fatal `NameError`.

2. **Step 2 (Selective Test Suite Masking)**:
   - *Observation*: Worker M2's handoff section 5.1 listed a custom pytest command combining specific test files, omitting `test_m1_challenger_stress.py` and `test_challenger_m1_stress.py`.
   - *Reasoning*: Worker M2 tested helper functions (`evaluate_single_criterion`, `extract_numeric_cgpa_cutoff`, `is_official_domain`) in isolation within `test_m2_eligibility.py`, without running an integration test on `execute_discovery_and_audit` with mock search/extraction data.
   - *Inference*: Worker M2's claim of "zero regressions" was incorrect because regressions were introduced into `research_eligibility.py` that broke existing tests.

3. **Step 3 (Feature F8 Admission vs Scholarship Separation)**:
   - *Observation*: Lines 517–519 of `research_eligibility.py` and lines 36–39 of `scoring_service.py` set `has_mandatory_failure = True` if *any* record in `evidence_records` has `status == "DOES_NOT_MEET"`.
   - *Reasoning*: By definition, scholarships are competitive funding opportunities with separate criteria from university admission. A student who meets university entrance requirements but fails a competitive fellowship requirement (e.g., top 1% or domestic citizenship requirement) must still be eligible for admission (or self-funded/partial match), not hard-disqualified from admission shortlist.
   - *Inference*: Feature F8 is only partially implemented; admission and scholarship criteria are separated in data models, but conflated in evaluation logic.

4. **Step 4 (API Schema Integrity)**:
   - *Observation*: `opp.model_dump()` does not include `deadline_status` because `deadline_status` was not declared on the Pydantic `Opportunity` model.
   - *Reasoning*: `PROJECT.md` line 130 specifies `deadline_status` as part of the `GET /api/research/{run_id}/opportunities` contract. Monkey-patching via `object.__setattr__` does not survive Pydantic serialization or database persistence.
   - *Inference*: Feature F9 is incomplete without schema declaration in `backend/app/models/opportunity.py`.

---

## 3. Caveats

1. **SDK Live Tool Execution**:
   - The official Google Gen AI SDK live web search and URL context tool require active credentials and network access. Testing was conducted using local unit tests, integration contracts, and mocked response injections.
2. **Scope Boundary**:
   - E2E tests in `tests/e2e/test_tier3_cross_feature.py` and `tests/e2e/test_tier4_real_world.py` invoke unmocked workflow execution scheduled for Milestone M3/M6. Their failures are anticipated and documented in `PROJECT.md` dependencies.

---

## 4. Conclusion & Findings

### Verdict: **`REQUEST_CHANGES`**

### Findings Summary

| # | Severity | Category | Description | Status |
|---|----------|----------|-------------|--------|
| **1** | **CRITICAL** | Bug / Regression | `NameError: name 'actionable_gaps' is not defined` & `NameError: name 'eligibility_reasons' is not defined` in `ResearchEligibilityAgent.execute_discovery_and_audit`. Crashes 100% of candidate page evaluations and breaks 4 tests in `test_m1_challenger_stress.py`. | **Must Fix** |
| **2** | **MAJOR** | Logic Defect (F8) | Conflation of mandatory admission and optional scholarship criteria in `research_eligibility.py` (lines 515-522) and `scoring_service.py` (lines 36-39). Failing an optional scholarship criteria hard-disqualifies the student from admission. | **Must Fix** |
| **3** | **MAJOR** | Schema Defect (F9) | `deadline_status` is not declared in Pydantic `Opportunity` model (`app/models/opportunity.py`), causing it to be dropped during `model_dump()` and violating API contract. | **Must Fix** |
| **4** | **MINOR** | Edge Case (F6) | Student profile grading scale (`profile.grading_scale == "4.0"`) is not normalized before comparison against `required_cgpa` (scaled to 10.0), causing false rejection of 4.0 scale applicants. | **Should Fix** |
| **5** | **MINOR** | Edge Case (F10) | `OFFICIAL_ACADEMIC_PARTS` substring check (`.ac.` in hostname) could permit deceptive commercial domains such as `phishing.ac.com`. | **Nice to Fix** |

---

## 5. Verification Method

To verify the remediation of these issues:

1. **Verify Regression Fix for M1 Challenger Stress Tests**:
   ```powershell
   cd backend
   pytest tests/test_m1_challenger_stress.py -v
   ```
   *Expected*: All 17 tests pass with zero `NameError`.

2. **Verify M2 Test Suite**:
   ```powershell
   cd backend
   pytest tests/test_m2_eligibility.py -v
   ```
   *Expected*: All 18 tests pass.

3. **Verify Tier 1 Feature Coverage**:
   ```powershell
   cd backend
   pytest tests/e2e/test_tier1_feature_coverage.py -k "f6 or f7 or f8 or f9 or f10" -v
   ```
   *Expected*: All 5 selected tests pass.

4. **Verify Candidate Page Extraction Integration**:
   Run direct execution test in `backend`:
   ```powershell
   python -c "
   import asyncio
   from unittest.mock import AsyncMock, patch
   from app.models.profile import StudentProfile
   from app.agents.research_eligibility import ResearchEligibilityAgent

   async def run():
       agent = ResearchEligibilityAgent()
       profile = StudentProfile(cgpa=8.2)
       with patch('app.services.gemini_service.gemini_service.ensure_available'), \
            patch('app.services.gemini_service.gemini_service.search_grounded_discovery', new_callable=AsyncMock) as m_s, \
            patch('app.services.gemini_service.gemini_service.analyze_url_and_extract_criteria', new_callable=AsyncMock) as m_e, \
            patch('app.db.repository.repository.save_agent_event', new_callable=AsyncMock), \
            patch('app.db.repository.repository.save_evidence_records', new_callable=AsyncMock):
           m_s.return_value = {'success': True, 'candidates': [{'canonical_url': 'https://utoronto.ca', 'title': 'MScAC', 'university': 'UofT'}]}
           m_e.return_value = {
               'success': True, 'is_retrieval_successful': True, 'retrieval_status': 'URL_RETRIEVAL_STATUS_SUCCESS',
               'data': {'program_name': 'MScAC', 'university': 'UofT', 'admission_requirements': [{'criterion_type': 'ACADEMIC_GRADE', 'stated_requirement': 'Min 8.0 CGPA'}]}
           }
           opps = await agent.execute_discovery_and_audit('run-1', profile)
           assert len(opps) == 1
           assert 'deadline_status' in opps[0].model_dump()
           print('PASSED integration verification')

   asyncio.run(run())
   "
   ```

5. **Invalidation Conditions**:
   Remediation will be invalidated if:
   - `actionable_gaps` or `eligibility_reasons` remain uninitialized.
   - Any test in `tests/test_m1_challenger_stress.py` or `tests/test_m2_eligibility.py` fails.
   - Failing an optional scholarship criteria disqualifies a student who meets all admission criteria.
   - `opp.model_dump()` does not include `deadline_status`.
