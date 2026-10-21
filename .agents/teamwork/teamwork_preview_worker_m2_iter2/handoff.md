# Handoff Report: Milestone M2 Iteration 2 (Defect Remediation & Verification)

**Agent**: Worker M2 Iteration 2 (`teamwork_preview_worker_m2_iter2`)  
**Target Milestone**: M2 Rework & Defect Remediation (Features F6, F7, F8, F9, F10)  
**Parent Orchestrator ID**: `6828b193-f5c1-4991-90e8-8c39694edfd6`  
**Date**: 2026-10-20T22:47:00Z  

---

## 1. Observation

### 1.1 Pre-Remediation Defects Identified
1. **Runtime Crash (NameError in Candidate Loop)**:
   - In `backend/app/agents/research_eligibility.py:444`, `actionable_gaps` and `eligibility_reasons` were uninitialized in `ResearchEligibilityAgent.execute_discovery_and_audit`, causing uncaught `NameError: name 'actionable_gaps' is not defined` and `NameError: name 'eligibility_reasons' is not defined`.
   - Running `pytest tests/test_m1_challenger_stress.py tests/test_challenger_m1_stress.py -v` failed 10 tests with verbatim:
     ```
     FAILED tests/test_m1_challenger_stress.py::test_empirical_research_agent_paywall_graceful_degradation
     FAILED tests/test_m1_challenger_stress.py::test_empirical_unsafe_and_ssrf_urls_rejected_before_extraction
     FAILED tests/test_m1_challenger_stress.py::test_empirical_duplicate_url_deduplication_in_discovery
     FAILED tests/test_m1_challenger_stress.py::test_empirical_candidate_bounding_to_max_configured
     ...
     E   NameError: name 'eligibility_reasons' is not defined
     app\agents\research_eligibility.py:533: NameError
     ```
2. **F8 Admission vs Scholarship Conflation**:
   - In `backend/app/agents/research_eligibility.py:517–519` and `backend/app/services/scoring_service.py:36–39`, any criterion failure in `opportunity.evidence_records` (including optional, competitive scholarships) flagged `has_mandatory_failure = True`, zeroing `academic_fit = 0.0` and setting `is_eligible_for_shortlist = False`.
3. **F9 API Schema Contract (`deadline_status`)**:
   - In `backend/app/models/opportunity.py`, `deadline_status` was not declared on the `Opportunity` model. Dynamic monkey-patching via `object.__setattr__(opp, "deadline_status", ...)` was discarded upon Pydantic serialization (`opp.model_dump()`), violating the API contract specified in `PROJECT.md` line 130.
4. **F10 Subdomain Regex Anchor Vulnerability (`is_official_domain`)**:
   - In `backend/app/security/sanitizer.py:183`, `f"{part}" in hostname` permitted any domain containing `.ac.` or `.edu.` anywhere in the hostname to pass as official (e.g. `scholarship.ac.fake.com` -> `True`, `evil.edu.attacker.org` -> `True`).
5. **F6 Grading Scale Normalization**:
   - In `backend/app/agents/research_eligibility.py:104–112`, student profiles with `profile.grading_scale == "4.0"` (e.g. CGPA 3.8/4.0) were compared directly against cutoffs scaled to 10.0 (e.g. 8.0/10.0) without conversion, falsely failing qualified 4.0-scale applicants (`3.8 >= 8.0` evaluated to `False`).
6. **Tier 1 Feature Coverage Test Redefinition**:
   - In `backend/tests/e2e/test_tier1_feature_coverage.py:291–301`, `is_official_domain` was redefined locally with naive logic rather than imported from `app.security.sanitizer`.

---

### 1.2 Implemented Changes & Code Adjustments

1. **`backend/app/models/opportunity.py`**:
   - Added `deadline_status: str = "UNKNOWN" # "ACTIVE", "EXPIRED", "ROLLING", "UNKNOWN"` to the `Opportunity` model definition.
   - Verified that `opp.model_dump()` preserves `"deadline_status"` with full Pydantic V2 schema serialization.

2. **`backend/app/security/sanitizer.py`**:
   - Replaced substring matching in `is_official_domain` with ccTLD-anchored regex:
     ```python
     m = re.search(r'(?:\.|\b)(?:ac|edu|gov|gc)\.([a-z]{2,3})$', hostname)
     if m:
         tld = m.group(1).lower()
         if tld not in ("com", "org", "net", "biz", "info", "xyz", "io", "co"):
             return True
     ```
   - Confirmed that spoofed subdomains (`scholarship.ac.fake.com`, `evil.edu.attacker.org`, `attacker.gov.scam.net`, `phishing.ac.com`) strictly return `False`, while authoritative institutional domains (`web.cs.toronto.edu`, `cs.stanford.edu`, `ox.ac.uk`, `cam.ac.uk`, `u-tokyo.ac.jp`, `nus.edu.sg`, `nserc-crsng.gc.ca`) return `True`.

3. **`backend/app/agents/research_eligibility.py`**:
   - Declared and initialized `evidence_records`, `actionable_gaps`, `eligibility_reasons`, `admission_evidence_records`, and `scholarship_evidence_records` immediately at the top of the candidate evaluation loop.
   - Separated admission and scholarship evaluation:
     - Admission requirements are tracked in `admission_evidence_records`; only mandatory admission prerequisite failures trigger `has_mandatory_failure = True`.
     - Scholarship requirements are tracked in `scholarship_evidence_records`; competitive scholarship failures set status to `POTENTIAL_MATCH` without setting `has_mandatory_failure = True`.
     - When retrieval fails (`not is_retrieval_successful`), `overall_status` is explicitly set to `"INSUFFICIENT_EVIDENCE"` with actionable gap warnings.
   - Implemented 4.0 grading scale normalization in `evaluate_single_criterion`:
     ```python
     if str(getattr(profile, "grading_scale", "")).strip() == "4.0" and student_cgpa is not None:
         effective_student_cgpa = (student_cgpa / 4.0) * 10.0
     ```
   - Added criterion type inference in `evaluate_single_criterion` when `criterion_type` is omitted in extraction dictionaries, preventing degree prerequisites from being incorrectly processed as academic grades.
   - Passed `deadline_status=deadline_status` directly into `Opportunity(...)` constructor.

4. **`backend/app/services/scoring_service.py`**:
   - Refactored mandatory failure checking so that competitive scholarship criteria (`is_scholarship = True`) never set `has_mandatory_failure = True`.
   - Updated deadline evaluation: when `deadline_status` is not provided or defaults to `"UNKNOWN"`, dynamically evaluates date and type against runtime UTC date and sets `opp.deadline_status`.

5. **`backend/tests/e2e/test_tier1_feature_coverage.py`**:
   - Removed local redefinition of `is_official_domain` and replaced with `from app.security.sanitizer import is_official_domain`.
   - Added test assertions verifying rejection of spoofed subdomains.

6. **`backend/tests/test_m2_eligibility.py`**:
   - Added `test_f6_grading_scale_4_point_scale_normalized_to_10`: verifies 4.0 scale CGPA conversion and threshold matching.
   - Added `test_f8_failing_optional_scholarship_remains_eligible_for_admission_shortlist`: verifies that a student meeting admission requirements but failing scholarship requirements remains shortlisted.
   - Added `test_f9_opportunity_model_dump_serializes_deadline_status`: verifies `opp.model_dump()` serialization.
   - Added `test_discovery_and_audit_candidate_loop_integration_no_name_error`: integration test confirming clean execution with zero NameErrors.
   - Added subdomain spoofing assertions in `test_f10_is_official_domain_rejects_commercial_blogs_and_substring_exploits`.

---

## 2. Logic Chain

1. **Step 1 (Root Cause Resolution for NameError)**:
   - *Observation*: Predecessor Worker M2 wrote lines referencing `actionable_gaps` and `eligibility_reasons` inside `execute_discovery_and_audit` without initializing them in that scope.
   - *Reasoning*: Python raises `NameError` whenever an unbound local variable is referenced in conditional expressions or append calls.
   - *Remediation*: Explicitly initializing `actionable_gaps: List[str] = []` and `eligibility_reasons: List[str] = []` alongside `evidence_records` ensures all conditional branches find bound list instances.
   - *Result*: Zero NameErrors in candidate loop; challenger tests pass.

2. **Step 2 (Admission vs Scholarship Decoupling)**:
   - *Observation*: `scoring_service.py:36–39` and `research_eligibility.py:517–520` checked all evidence records without checking whether the record belonged to admission or scholarship.
   - *Reasoning*: A university admission prerequisite (e.g. minimum GPA, bachelor's degree) is mandatory for program entry. A scholarship requirement (e.g. top 1% rank, fellowship nomination) is competitive financial aid. Disqualifying admission for failing an optional scholarship criterion violates the domain model and user intent.
   - *Remediation*: Partition evidence records into admission and scholarship subsets; only mandatory admission failures trigger `has_mandatory_failure = True`.
   - *Result*: Students failing competitive scholarships remain shortlisted as `POTENTIAL_MATCH` with positive academic scores.

3. **Step 3 (API Contract Schema Conformance)**:
   - *Observation*: `deadline_status` was set via `object.__setattr__` on an `Opportunity` model that lacked the field definition, causing Pydantic's `model_dump()` to drop the field.
   - *Reasoning*: Pydantic models only serialize fields declared on the model class.
   - *Remediation*: Declared `deadline_status: str = "UNKNOWN"` on `Opportunity` in `app/models/opportunity.py`.
   - *Result*: `opp.model_dump()` preserves `"deadline_status"` with `"ACTIVE"`, `"EXPIRED"`, `"ROLLING"`, or `"UNKNOWN"`.

4. **Step 4 (Regex Anchoring Against Subdomain Spoofing)**:
   - *Observation*: `is_official_domain` checked `if part in hostname` with `".ac."` and `".edu."`, allowing `scholarship.ac.fake.com` and `evil.edu.attacker.org` to return `True`.
   - *Reasoning*: Genuine academic second-level domains occur immediately before a country-code top-level domain (`.ac.uk`, `.edu.sg`, `.gc.ca`).
   - *Remediation*: Applied `re.search(r'(?:\.|\b)(?:ac|edu|gov|gc)\.([a-z]{2,3})$', hostname)` and excluded generic commercial TLDs (`com`, `org`, `net`, `biz`, `info`, `xyz`, `io`, `co`).
   - *Result*: All spoofed subdomains are rejected while official institutions pass.

5. **Step 5 (Grading Scale Normalization)**:
   - *Observation*: Cutoffs were extracted on a 10.0 scale, but 4.0-scale profiles were compared without conversion.
   - *Reasoning*: A student with 3.8/4.0 represents 95% academic achievement, exceeding typical 8.0/10.0 cutoffs. Direct comparison (`3.8 >= 8.0`) produced false rejections.
   - *Remediation*: When `profile.grading_scale == "4.0"`, CGPA is normalized to 10.0 scale (`(cgpa / 4.0) * 10.0`) prior to cutoff comparison.
   - *Result*: 4.0 scale applicants are accurately evaluated without bias.

---

## 3. Caveats

1. **Live Gemini SDK Credentials**:
   - Tests were executed using local mocks and contract-level test harnesses, as live Google GenAI credentials are not configured in this test environment.
2. **Milestone M3/M6 Integration**:
   - Unmocked end-to-end tests (`tests/e2e/test_tier3_cross_feature.py` and `tests/e2e/test_tier4_real_world.py`) invoke live external network calls slated for Milestone M3 and M6 test harness integration per `PROJECT.md`.

---

## 4. Conclusion

All 6 defects highlighted in Reviewer M2.1 and Reviewer M2.2 handoff reports have been resolved and verified with 100% test pass rates across all 6 targeted test suites:
- **Zero NameErrors**: Discovery and candidate evaluation loops execute cleanly without uninitialized variable crashes.
- **Strict F8 Decoupling**: Mandatory university admission is verified independently from competitive scholarships. Failing an optional scholarship preserves admission eligibility.
- **Full F9 Schema Conformance**: `Opportunity.deadline_status` is declared and serialized in `model_dump()`.
- **Airtight F10 Domain Security**: Subdomain injection exploits are rejected; academic ccTLDs and approved registries are enforced.
- **Fair F6 Scale Normalization**: 4.0 grading scales are normalized to 10.0 before evaluating minimum cutoffs.
- **Production Import Cleanliness**: Tier 1 tests import `is_official_domain` from `app.security.sanitizer`.

---

## 5. Verification Method

### 5.1 Verification Commands and Results

1. **Verify M2 Eligibility Suite (22 passed)**:
   ```powershell
   cd backend
   pytest tests/test_m2_eligibility.py -v
   ```
   *Result*: `============================= 22 passed in 2.39s ==============================`

2. **Verify Challenger M1 Stress Suite (17 passed)**:
   ```powershell
   cd backend
   pytest tests/test_m1_challenger_stress.py -v
   ```
   *Result*: `============================= 17 passed in 6.01s ==============================`

3. **Verify Challenger M1 Additional Suite (8 passed)**:
   ```powershell
   cd backend
   pytest tests/test_challenger_m1_stress.py -v
   ```
   *Result*: `============================== 8 passed in 2.15s ==============================`

4. **Verify Scoring Suite (3 passed)**:
   ```powershell
   cd backend
   pytest tests/test_scoring.py -v
   ```
   *Result*: `============================== 3 passed in 0.06s ==============================`

5. **Verify Tier 1 Feature Coverage (10 passed)**:
   ```powershell
   cd backend
   pytest tests/e2e/test_tier1_feature_coverage.py -v
   ```
   *Result*: `============================= 10 passed in 0.97s ==============================`

6. **Verify M1 Grounding Regression Suite (14 passed)**:
   ```powershell
   cd backend
   pytest tests/test_m1_grounding.py -v
   ```
   *Result*: `============================= 14 passed in 5.45s ==============================`

7. **Verify Combined Regression Suite (64 passed in 9.72s)**:
   ```powershell
   cd backend
   pytest tests/test_m2_eligibility.py tests/test_m1_challenger_stress.py tests/test_challenger_m1_stress.py tests/test_scoring.py tests/test_m1_grounding.py -v
   ```
   *Result*: `============================= 64 passed in 9.72s ==============================`

8. **Verify Subdomain Rejection and Model Dump Serialization**:
   ```powershell
   cd backend
   python -c "
   from app.security.sanitizer import is_official_domain
   assert is_official_domain('https://scholarship.ac.fake.com') is False
   assert is_official_domain('https://evil.edu.attacker.org') is False

   from app.models.opportunity import Opportunity
   opp = Opportunity(id='t', run_id='r', canonical_url='https://utoronto.ca', title='U', program_name='P', university='U', country='C')
   opp.deadline_status = 'EXPIRED'
   assert 'deadline_status' in opp.model_dump()
   assert opp.model_dump()['deadline_status'] == 'EXPIRED'
   print('ALL INDEPENDENT CHECKS PASSED')
   "
   ```
   *Result*: `ALL INDEPENDENT CHECKS PASSED`

### 5.2 Invalidation Conditions
This remediation would be invalidated if:
1. Any test in `tests/test_m2_eligibility.py`, `tests/test_m1_challenger_stress.py`, or `tests/test_challenger_m1_stress.py` raises `NameError`.
2. `is_official_domain("https://scholarship.ac.fake.com")` or `is_official_domain("https://evil.edu.attacker.org")` evaluates to `True`.
3. `Opportunity.model_dump()` omits the `"deadline_status"` field.
4. Failing a competitive scholarship disqualifies a student who meets all mandatory admission prerequisites.
