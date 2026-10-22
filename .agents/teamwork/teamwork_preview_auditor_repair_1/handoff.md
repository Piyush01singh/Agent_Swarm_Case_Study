# Forensic Integrity Audit Report

**Work Product**: TetraNoodle AI Hackathon (`backend/` & `frontend/`)  
**Profile**: General Project (Integrity Forensics)  
**Integrity Mode**: Development (`ORIGINAL_REQUEST.md`)  
**Auditor**: `teamwork_preview_auditor_repair_1` (forensic_auditor)  
**Parent**: `6caa988d-b978-4e37-94b4-b6ba138214d3`  
**Date**: 2026-10-22  
**Verdict**: **`CLEAN`**

---

## 1. Observation

### Check 1 & Check 2: Zero Synthetic Fallbacks or `discovery_registry` in Production Codepaths
- **Command**:
  ```powershell
  Get-ChildItem -Path 'backend\app' -Recurse -File -Include *.py | Select-String -Pattern 'discovery_registry|get_precomputed_discovery_results|REAL_OPPORTUNITIES_BASE'
  ```
- **Result**: Exactly 0 matches found across `backend/app/` (outside `discovery_registry.py` itself).
- In `backend/app/services/gemini_service.py` (lines 120-130 and lines 239-251):
  - On missing API key or quota exhaustion in `search_grounded_discovery`:
    ```python
    if self._is_quota_exhausted or not self.is_available:
        return {
            "success": False,
            "error": "GEMINI_API_KEY is not configured or quota is exhausted.",
            "candidates": [],
            "sources": [],
            "citations": [],
            "search_queries": [query],
            "model_used": self.model
        }
    ```
  - In `analyze_url_and_extract_criteria` (lines 239-251):
    ```python
    if self._is_quota_exhausted or not self.is_available:
        err_msg = "QUOTA_EXHAUSTED" if self._is_quota_exhausted else "GEMINI_API_KEY is not configured."
        return {
            "success": False,
            "error": err_msg,
            "status": "QUOTA_EXHAUSTED" if self._is_quota_exhausted else "NOT_CONFIGURED",
            "data": None,
            "retrieval_metadata": [],
            "url_retrieval_statuses": {u: "URL_RETRIEVAL_STATUS_ERROR" for u in urls},
            "is_retrieval_successful": False,
            "retrieval_status": "URL_RETRIEVAL_STATUS_ERROR",
            "evidence_quality": "UNVERIFIED"
        }
    ```
- In `backend/app/agents/research_eligibility.py` (lines 411-430):
  ```python
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
  ```
  Zero synthetic opportunities returned; returns clean empty list `[]`.

### Check 3: Authentic Fail-Closed Behavior on Quota Exhaustion
- In `backend/app/services/gemini_service.py` (lines 485-503 and lines 547-568):
  - When quota is exhausted (`self._is_quota_exhausted = True`) or service unavailable, `review_evidence_and_claims` returns:
    ```python
    {"success": False, "error": err_code, "approved": False, "data": {"approved": False, "confidence_rating": "LOW", ...}}
    ```
  - Exception handler explicitly catches 429/`RESOURCE_EXHAUSTED` and sets:
    ```python
    return {"success": False, "error": "QUOTA_EXHAUSTED", "approved": False, "data": {"approved": False, "confidence_rating": "LOW", ...}}
    ```
  - At no point is `approved: True` or `"HIGH"` confidence fabricated.
- In `backend/app/agents/quality_reviewer.py` (lines 251-256):
  ```python
  else:
      # R2: If quota exhausted or audit uncompleted, mark status UNRESOLVED (fail-closed)
      candidate.reviewer_status = "UNRESOLVED"
      err_code = audit_res.get("error", "QUOTA_EXHAUSTED")
      candidate.reviewer_notes = f"Quality review unreviewed / unresolved ({err_code})."
  ```
- In `frontend/src/App.tsx` (lines 342-371):
  - Renders explicit alert card with `429 RESOURCE_EXHAUSTED` badge, title "Gemini API Quota Exhausted", and actionable guidance instead of an infinite spinner or fake results.

### Check 4: Genuine Removal of Ungrounded Grade Conversion Formulas
- In `backend/app/agents/research_eligibility.py`:
  - `extract_numeric_cgpa_cutoff` (lines 15-48): Linear formula `(val / 4.0) * 10.0`, percentage division `/ 10.0`, and qualitative mappings (`first class with distinction -> 8.0`, `b+ average -> 7.5`) are completely absent. Only explicit `/10` ratios or standalone CGPAs > 4.0 are parsed.
  - `evaluate_single_criterion` (lines 159-191):
    - Matching scales (`student_scale == req_scale`) are compared directly.
    - Differing scales without official equivalency evaluate strictly to:
      ```python
      status = "UNRESOLVED"
      uncertainty_note = f"Program requirement specifies {raw_cutoff}/{req_scale} while applicant credentials are on {student_scale} scale. No published institutional equivalency provided."
      actionable_gap = f"Verify institutional grade conversion for {profile.institution} ({student_scale} scale) with admissions office ({req_text})."
      ```

### Check 5: Clean Reviewer Feedback Query Construction
- In `backend/app/agents/research_eligibility.py` (lines 317-344):
  - In round 2 re-research, query formulation strictly tokenizes institution and program names:
    - `SECONDARY_SOURCE`: `"{univ}" official portal admission {country}`
    - `EXPIRED_DEADLINE`: `"{univ}" admissions deadline current intake {country}`
    - `MANDATORY_CRITERIA_FAILED`: `"{univ}" degree admission requirements {country}`
  - No student failure reasons or subjective notes are concatenated into search queries.

### Check 6: Offline Test Execution and Frontend Production Build
- **Backend Test Suite**:
  - Full suite:
    ```powershell
    pytest backend/tests/ -v
    ```
    Output: `356 passed in 13.24s` (100% passed, 0 failures, 0 warnings).
  - Corner and boundary suite:
    ```powershell
    pytest backend/tests/e2e/test_tier2_boundary_corner.py -v
    ```
    Output: `35 passed in 0.53s` (including `test_b6_service_resilience_when_gemini_raises_exception`).
  - Adversarial & scale suite:
    ```powershell
    pytest backend/tests/test_challenger2_eligibility_and_queries.py -v
    ```
    Output: `65 passed in 0.67s`.
  - Resilience suite:
    ```powershell
    pytest backend/tests/test_challenger_resilience.py -v
    ```
    Output: `4 passed in 1.63s`.
- **Frontend Build**:
  - Command: `cd frontend; npm run build`
  - Output: `tsc -b && vite build` completed in 1.71s with 0 errors.

### Check 7: Secrets and Credentials Safety Scan
- Ran repository-wide scan for API key patterns (`AIzaSy*`, `AQ*`), secret tokens, and `.env` leaks.
- All actual `.env` files are gitignored.
- `.env.example` contains only empty placeholder keys.
- References in `smoke_test_gemini.py` and `test_smoke_gemini.py` are strictly dummy test format strings or key mask sanitizers.
- Git working tree diff contains zero exposed secrets or credentials.

### Check 8: UI & Documentation Compliance
- `frontend/index.html` title verified: `<title>ScholarSwarm — AI Scholarship Intelligence</title>`.
- `backend/app/agents/application_coach.py` dynamically extracts applicant's test type (`actual_test`) from `profile.language_tests` rather than hardcoding GRE/IELTS.
- `docs/ARCHITECTURE.md` and `README.md` document Agent 4 as an on-demand application specialist.
- `docs/EXPERIMENT.md` transparently labels in-memory harness measurements as deterministic simulated benchmarks.

---

## 2. Logic Chain

1. **Discovery Integrity (Checks 1 & 2)**: The primary integrity risk was live operational paths silently falling back to canned precomputed fixtures in `discovery_registry.py` under quota exhaustion. The empirical audit verified 0 imports and 0 calls to `discovery_registry` in `backend/app/`. When discovery produces 0 results or encounters quota limits, the system raises explicit `QUOTA_EXHAUSTED` / `DISCOVERY_EMPTY` events and returns an empty list `[]`. The UI renders dedicated, transparent error cards. Hence, research integrity is fully preserved.
2. **Safety & Fail-Closed Review (Check 3)**: A system that returns `approved: True` with high confidence during reviewer downtime constitutes a critical safety defect. Empirical inspection confirmed that both `gemini_service.py` and `quality_reviewer.py` enforce fail-closed behavior: `approved: False`, `confidence_rating: "LOW"`, and `candidate.reviewer_status = "UNRESOLVED"`. No false confidence is ever emitted.
3. **Scientific Grading Accuracy (Check 4)**: Linear interpolation between disparate grading scales (e.g. 4.0 to 10.0) lacks academic validity. Code analysis verified that ungrounded conversion multipliers and hardcoded qualitative thresholds have been completely excised. When scale mismatch occurs without published equivalency, the platform honestly classifies criteria as `UNRESOLVED` with actionable gap guidance to contact admissions.
4. **Query Integrity (Check 5)**: Appending applicant rejection text into search engine queries corrupts query intent. The verified implementation constructs clean, institution-targeted search queries, ensuring search grounding targets official admission portals rather than forum threads.
5. **Hermetic Offline Testing & Build (Check 6)**: All 356 automated backend tests pass cleanly in 13.24 seconds with zero network calls and zero quota consumption. The frontend builds without bundling or TypeScript errors.
6. **Credential Security (Check 7)**: Zero secrets or live API keys are committed or exposed in code or git.

---

## 3. Caveats

- **Test Fixture Retention**: `discovery_registry.py` remains in `backend/app/services/` but is completely unreferenced by production code.
- **No Other Caveats**: All 8 audit requirements have been empirically verified and found cleanly compliant.

---

## 4. Conclusion

**Verdict: `CLEAN`**

The codebase strictly adheres to all requirements in `ORIGINAL_REQUEST.md` (including the follow-up requirements R1 through R7). There are no hardcoded test results, mock shortcuts, dummy facade implementations, fabricated ratings, ungrounded grading conversions, or secret exposures.

---

## 5. Verification Method

To independently reproduce the forensic verification:

1. **Verify Full Backend Test Suite**:
   ```bash
   pytest backend/tests/ -v
   ```
   *Expected*: 356 passed in ~13s, 0 failures.

2. **Verify Frontend Build**:
   ```bash
   cd frontend && npm run build
   ```
   *Expected*: `vite build` completed in ~2s with 0 errors.

3. **Verify Zero Registry Invocations in Live Codepaths**:
   ```powershell
   Get-ChildItem -Path 'backend\app' -Recurse -File -Include *.py | Select-String -Pattern 'discovery_registry|get_precomputed_discovery_results|REAL_OPPORTUNITIES_BASE'
   ```
   *Expected*: 0 matches outside `discovery_registry.py`.

4. **Verify Boundary Test `test_b6`**:
   ```bash
   pytest backend/tests/e2e/test_tier2_boundary_corner.py -k "test_b6" -v
   ```
   *Expected*: 2 passed in ~0.5s.
