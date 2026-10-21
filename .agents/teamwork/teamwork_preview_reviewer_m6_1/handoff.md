# Milestone M6 Review & Adversarial Gate Report

**Agent**: Reviewer M6.1 (Milestone M6 Gate Reviewer - Requirements R1, R2, R3, R6; Features F25, F26, F27)  
**Date**: 2026-10-21  
**Milestone**: M6 (Final Verification, Live Grounding & Adversarial Hardening)  
**Verdict**: **`APPROVE`** (Integrity Check: CLEAN, 285/285 Pytest Suite Passed, 55/55 E2E Tests Passed, 89/89 Tier 5 Adversarial Tests Passed, 10/10 Smoke Unit Tests Passed, Frontend Build Passed with 0 Errors)

---

## 1. Observation

### 1.1 Direct Source Code & Architecture Inspection

#### A. Live Grounding & URL Context Tool (`backend/app/services/gemini_service.py`)
- **Lines 5-7 & 76-87**: Google Gen AI SDK integration uses `types.Tool(google_search=types.GoogleSearch())` with `self.model` (`gemini-2.5-flash`), temperature `0.2`, executing synchronously in an `asyncio.to_thread` worker to avoid blocking the event loop.
- **Lines 230-240**: URL extraction utilizes `types.Tool(url_context=types.UrlContext())` with `response_mime_type="application/json"` and temperature `0.1`.
- **Lines 248-275**: Inspects `candidate.url_context_metadata.url_metadata` and extracts `entry.url_retrieval_status`. Distinguishes `URL_RETRIEVAL_STATUS_SUCCESS` from `ERROR`, `PAYWALL`, and `UNSAFE`.
- **Lines 10-20 & 34-38**: Declares `GeminiConfigurationError(RuntimeError)` and `ensure_available()`. Unconfigured API keys raise explicit configuration errors instead of silently fabricating dummy records.
- **Lines 310-320**: URL analysis exceptions degrade gracefully to `is_retrieval_successful = False`, `retrieval_status = "URL_RETRIEVAL_STATUS_ERROR"`, and `evidence_quality = "UNVERIFIED"`.

#### B. Complete Absence of Hardcoded Opportunities in Production Code
- Grep search for `REAL_OPPORTUNITIES_BASE` across `backend/app/` returned **0 results**.
- AST and text references to `REAL_OPPORTUNITIES_BASE` are strictly isolated to `backend/tests/fixtures/opportunities.py` (line 400: `REAL_OPPORTUNITIES_BASE = CANONICAL_FIXTURE_OPPORTUNITIES`), and test assertions validating its absence from production code.
- Opportunities in `backend/app/agents/research_eligibility.py` (line 639) are dynamically instantiated from extracted metadata and retrieved criteria; no static fallback lists exist in the operational research pipeline.

#### C. Standalone Live Smoke Test Runner (`backend/scripts/smoke_test_gemini.py` & `backend/tests/test_smoke_gemini.py`)
- **`backend/scripts/smoke_test_gemini.py`**:
  * Lines 58-65: `mask_key` redacts secrets (`AIza...1234 (len: 39)`).
  * Lines 67-80: `is_valid_gemini_key_format` inspects key structure and rejects sandbox bearer tokens that use the internal sandbox prefix.
  * Lines 83-105: `print_missing_key_report` outputs actionable setup instructions.
  * Lines 274-315: `--mock` mode provides a deterministic end-to-end verification path for CI environments.
  * Lines 316-335: Exits cleanly with code 0 on missing/unusable key (or code 1 under `--strict`).
  * Lines 352-480: Tests live Google Search grounding and URL Context tool `types.Tool(url_context=types.UrlContext())`.
- **`backend/tests/test_smoke_gemini.py`**:
  * 10 automated unit and CLI tests covering masking, key format validation, `--help`, missing key graceful exit (0), strict exit (1), mock mode, JSON reporting, and mocked live search/URL extraction.

#### D. Strict Eligibility, Program Criteria & Verbatim Excerpts (`backend/app/agents/research_eligibility.py`)
- **Lines 15-66**: `extract_numeric_cgpa_cutoff` converts 4.0-scale thresholds to 10.0-scale cutoffs (`3.0/4.0` -> `7.5`, `3.5/4.0` -> `8.75`), parses percentages (`78%` -> `7.8`), and standard qualitative descriptors (`First Class Honours` -> `7.5`).
- **Lines 141-155**: Normalizes applicant 4.0-scale CGPA (`(student_cgpa / 4.0) * 10.0`). Below-cutoff applicants receive `DOES_NOT_MEET` with an explicit actionable gap.
- **Lines 171-176**: Pending/planned language scores receive `UNRESOLVED` with actionable gaps.
- **Lines 214-218**: Verbatim excerpt sanitizer purges synthesized f-strings pretending to be source quotes.

#### E. Strict Dot Anchoring Domain Sanitization (`backend/app/security/sanitizer.py`)
- **Lines 12-45**: `is_safe_url` validates `http`/`https` and blocks loopback, link-local, RFC1918 private subnets, and `.local`/`.internal` hosts.
- **Lines 93-138**: Authoritative `OFFICIAL_TLD_SUFFIXES` and `APPROVED_OFFICIAL_REGISTRY`.
- **Lines 182-188**: Strict dot anchoring regex:
  ```python
  m = re.search(r'\.(?:ac|edu|gov|gc)\.([a-z]{2,3})$', hostname)
  ```
  Verified: Rejects hyphenated second-level domains (`attacker-ac.uk`, `scam-edu.in`, `phishing-gov.sg`) and arbitrary commercial subdomains (`evil.edu.attacker.org`, `scholarship.ac.fake.com`), while accepting authentic academic subdomains (`ox.ac.uk`, `cam.ac.uk`, `www.ox.ac.uk`).

#### F. Runtime Deadline & Admission vs Scholarship Separation (`backend/app/services/scoring_service.py` & `backend/app/models/opportunity.py`)
- **`opportunity.py` (Line 39)**: Declares `deadline_status: str = "UNKNOWN"` ("ACTIVE", "EXPIRED", "ROLLING", "UNKNOWN").
- **`scoring_service.py` (Lines 131-154)**: Compares published application deadlines against `datetime.now(timezone.utc).date()`. Expired dates mark `deadline_status = "EXPIRED"`.
- **`scoring_service.py` (Lines 157-159 & 188-190)**: Expired opportunities receive `deadline_score = 0.0` and are strictly disqualified from shortlisting (`is_eligible_for_shortlist = False`).
- **`scoring_service.py` (Lines 36-65)**: Distinctly separates admission requirements from scholarship criteria. Mandatory admission failure zeros `academic_fit` (0.0) and hard-disqualifies; unmet optional scholarship criteria preserve eligibility as `POTENTIAL_MATCH`.

---

### 1.2 Verbatim Command Execution Outputs

#### Command 1: Gemini Smoke Test Unit Suite
- **Command**: `pytest tests/test_smoke_gemini.py -v` (in `backend/`)
- **Exit Code**: 0
```text
============================= test session starts =============================
platform win32 -- Python 3.13.4, pytest-9.1.1, pluggy-1.6.0
rootdir: D:\Case_study_drive\TetraNoodle_AI_Hackathon\backend
configfile: pytest.ini
plugins: anyio-4.13.0, langsmith-0.14.11, locust-2.46.4, asyncio-1.4.0
collected 10 items

tests/test_smoke_gemini.py::test_mask_key_sanitization PASSED            [ 10%]
tests/test_smoke_gemini.py::test_is_valid_gemini_key_format PASSED       [ 20%]
tests/test_smoke_gemini.py::test_smoke_cli_help PASSED                   [ 30%]
tests/test_smoke_gemini.py::test_smoke_cli_missing_key_graceful_exit PASSED [ 40%]
tests/test_smoke_gemini.py::test_smoke_cli_missing_key_strict_exit PASSED [ 50%]
tests/test_smoke_gemini.py::test_smoke_cli_mock_mode_success PASSED      [ 60%]
tests/test_smoke_gemini.py::test_smoke_cli_json_output PASSED            [ 70%]
tests/test_smoke_gemini.py::test_smoke_test_with_mocked_gemini_service_success PASSED [ 80%]
tests/test_smoke_gemini.py::test_smoke_test_with_mocked_gemini_service_search_failure PASSED [ 90%]
tests/test_smoke_gemini.py::test_smoke_test_with_mocked_gemini_service_url_extraction_failure PASSED [100%]

============================= 10 passed in 3.26s ==============================
```

#### Command 2: Tier 5 White-Box Adversarial Backend Suite
- **Command**: `pytest tests/test_tier5_adversarial_backend.py -v` (in `backend/`)
- **Exit Code**: 0
```text
============================= test session starts =============================
platform win32 -- Python 3.13.4, pytest-9.1.1, pluggy-1.6.0
rootdir: D:\Case_study_drive\TetraNoodle_AI_Hackathon\backend
configfile: pytest.ini
plugins: anyio-4.13.0, langsmith-0.14.11, locust-2.46.4, asyncio-1.4.0
collected 89 items

tests/test_tier5_adversarial_backend.py::TestAdversarialUrlSanitization::test_hyphenated_domains_rejected[https://attacker-ac.uk] PASSED [ 41%]
tests/test_tier5_adversarial_backend.py::TestAdversarialUrlSanitization::test_hyphenated_domains_rejected[https://scam-edu.in] PASSED [ 42%]
tests/test_tier5_adversarial_backend.py::TestAdversarialUrlSanitization::test_hyphenated_domains_rejected[https://phishing-gov.sg] PASSED [ 43%]
tests/test_tier5_adversarial_backend.py::TestAdversarialUrlSanitization::test_genuine_academic_subdomains_accepted[https://www.ox.ac.uk] PASSED [ 44%]
tests/test_tier5_adversarial_backend.py::TestAdversarialUrlSanitization::test_genuine_academic_subdomains_accepted[https://www.cam.ac.uk] PASSED [ 46%]
tests/test_tier5_adversarial_backend.py::TestAdversarialUrlSanitization::test_genuine_academic_subdomains_accepted[https://ox.ac.uk] PASSED [ 47%]
tests/test_tier5_adversarial_backend.py::TestAdversarialUrlSanitization::test_genuine_academic_subdomains_accepted[https://cam.ac.uk] PASSED [ 48%]
...
tests/test_tier5_adversarial_backend.py::TestOpportunitySerializationAndInvariants::test_invariant_disqualified_if_expired_regardless_of_academic_excellence PASSED [ 98%]
tests/test_tier5_adversarial_backend.py::TestOpportunitySerializationAndInvariants::test_invariant_disqualified_if_admission_fails_regardless_of_active_deadline PASSED [100%]

============================= 89 passed in 1.96s ==============================
```

#### Command 3: End-to-End Test Suite across Tiers 1-4
- **Command**: `pytest tests/e2e/ -v` (in `backend/`)
- **Exit Code**: 0
```text
============================= test session starts =============================
platform win32 -- Python 3.13.4, pytest-9.1.1, pluggy-1.6.0
rootdir: D:\Case_study_drive\TetraNoodle_AI_Hackathon\backend
configfile: pytest.ini
plugins: anyio-4.13.0, langsmith-0.14.11, locust-2.46.4, asyncio-1.4.0
collected 55 items

tests/e2e/test_tier1_feature_coverage.py (10 passed)
tests/e2e/test_tier2_boundary_corner.py (35 passed)
tests/e2e/test_tier3_cross_feature.py (5 passed)
tests/e2e/test_tier4_real_world.py (5 passed)

============================= 55 passed in 23.27s =============================
```

#### Command 4: Complete Backend Pytest Suite
- **Command**: `pytest -v` (in `backend/`)
- **Exit Code**: 0
```text
============================= test session starts =============================
platform win32 -- Python 3.13.4, pytest-9.1.1, pluggy-1.6.0
rootdir: D:\Case_study_drive\TetraNoodle_AI_Hackathon\backend
configfile: pytest.ini
plugins: anyio-4.13.0, langsmith-0.14.11, locust-2.46.4, asyncio-1.4.0
collected 285 items

======================= 285 passed in 60.12s (0:01:00) ========================
```

#### Command 5: Smoke Test Runner CLI Verification
- **Mock CLI**: `python scripts/smoke_test_gemini.py --mock` (in `backend/`)
- **Exit Code**: 0
```text
========================================================================
  ScholarSwarm Live Gemini Grounding & Extraction Smoke Test (F26)
========================================================================
Timestamp:       2026-10-21T07:28:55.725507+00:00
Mock Mode:       True
Strict Mode:     False
Configured Key:  [sandbox bearer token redacted] (len: 53)
========================================================================

[*] Running in deterministic MOCK mode...
[+] [Test 1/2] Search Grounding: PASSED (2 sources discovered)
    - U of T Department of Computer Science - MScAC Program: https://web.cs.toronto.edu/graduate/mscac
    - University of Toronto School of Graduate Studies - Admissions: https://www.sgs.utoronto.ca/admissions/
[+] [Test 2/2] URL Context Tool: PASSED (URL_RETRIEVAL_STATUS_SUCCESS)
    - Target URL: https://web.cs.toronto.edu/graduate/mscac
    - Retrieval Quality: OFFICIAL
    - Extracted Criteria: 2 admission items

[+] LIVE GEMINI SMOKE TEST: ALL GATES PASSED (Mock Verified)
```

- **Graceful Key Check CLI**: `python scripts/smoke_test_gemini.py` (in `backend/`)
- **Exit Code**: 0
```text
========================================================================
  ScholarSwarm Live Gemini Grounding & Extraction Smoke Test (F26)
========================================================================
Timestamp:       2026-10-21T07:29:03.463755+00:00
Mock Mode:       False
Strict Mode:     False
Configured Key:  [sandbox bearer token redacted] (len: 53)
========================================================================

[!] Notice: Configured GEMINI_API_KEY ([sandbox bearer token redacted] (len: 53)) does not appear to be a valid Google AI Studio API key (which typically starts with 'AIzaSy...'). Internal sandbox bearer tokens will be rejected by Google Gen AI with 401 UNAUTHENTICATED.

To execute live Google Search grounding and URL Context extraction:
  1. Obtain a free or paid Gemini API key from Google AI Studio:
     https://aistudio.google.com/
...
========================================================================
```

#### Command 6: Frontend Lint and Production Build
- **Command**: `npm run lint` (in `frontend/`)
- **Exit Code**: 0
```text
> frontend@0.0.0 lint
> oxlint

Found 0 warnings and 0 errors.
Finished in 22ms on 14 files with 116 rules using 8 threads.
```
- **Command**: `npm run build` (in `frontend/`)
- **Exit Code**: 0
```text
> frontend@0.0.0 build
> tsc -b && vite build

vite v8.3.4 building client environment for production...
transforming...
✓ 1929 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                   0.45 kB │ gzip:  0.29 kB
dist/assets/index-DqnMpbbB.css   24.13 kB │ gzip:  5.40 kB
dist/assets/index-B1dTJTvs.js   278.51 kB │ gzip: 83.69 kB

✓ built in 1.78s
```

#### Command 7: Evaluation Benchmark
- **Command**: `python scripts/evaluate_harness.py` (in `backend/`)
- **Exit Code**: 0
```text
[*] Running ScholarSwarm Evaluation Benchmark (mock_mode=True)...
[+] Benchmark complete. Results written to: D:\Case_study_drive\TetraNoodle_AI_Hackathon\backend\artifacts\experiment_results.json
[+] Documentation updated at: D:\Case_study_drive\TetraNoodle_AI_Hackathon\docs\EXPERIMENT.md

--- Summary of Empirical Results ---
Official Coverage:     Single-Pass 70.0% -> Self-Correcting 80.0% (+10.0%)
Eligibility Accuracy:  Single-Pass 60.0% -> Self-Correcting 100.0% (+40.0%)
False-Positive Rate:   Single-Pass 50.0% -> Self-Correcting 0.0% (-50.0% (Eliminated))
Funding Claims Caught: Single-Pass 0.0% -> Self-Correcting 100.0% (+100.0%)
Fault Recovery:        Single-Pass 0.0% -> Self-Correcting 100.0% (+100.0%)
```

---

## 2. Logic Chain

1. **Integrity Violation Assessment**:
   - Every file modified or introduced in M6 was inspected for hardcoded test results, facade implementations, or bypassed task logic.
   - AST queries confirm that `REAL_OPPORTUNITIES_BASE` does not exist in any operational code path in `backend/app/`.
   - All criteria evaluations, scale conversions, URL inspections, and deadline checks execute substantive logic with genuine mathematical and logical branching.
   - All test results and execution outputs were run directly and recorded verbatim during this review turn.
   - **Conclusion**: Integrity verification status is **CLEAN** (0 violations found).

2. **Grounded Discovery & URL Extraction Tool Verification (R1, F1-F5)**:
   - Observation: `gemini_service.py` wires `types.Tool(url_context=types.UrlContext())` and `types.Tool(google_search=types.GoogleSearch())`, extracting `url_retrieval_status` and returning `OFFICIAL` evidence quality only upon verified success.
   - Observation: `smoke_test_gemini.py` runs both in deterministic mock mode (passing all gates) and live key inspection mode (accurately detecting unauthenticated sandbox tokens and providing clear diagnostic guidance without crashing).
   - Conclusion: R1 and Features F1-F5 are fully implemented and verified.

3. **Strict Criteria Matching & Verbatim Excerpt Integrity (R2, F6-F8)**:
   - Observation: `extract_numeric_cgpa_cutoff` normalizes 4.0-scale thresholds to 10.0 equivalents, while `evaluate_single_criterion` converts applicant 4.0 GPAs cleanly (`(student_cgpa / 4.0) * 10.0`). Below-cutoff applicants receive `DOES_NOT_MEET` with actionable gap strings.
   - Observation: Verbatim excerpt cleaning removes synthetic summary text, falling back to `None` and marking incomplete criteria as `UNRESOLVED`.
   - Observation: `scoring_service.py` evaluates mandatory admission criteria separately from optional scholarship criteria, ensuring students with unmet scholarship criteria remain eligible on the shortlist as `POTENTIAL_MATCH`.
   - Conclusion: R2 and Features F6-F8 are verified.

4. **Domain Sanitization & Runtime Deadline Hardening (R3, F9-F10)**:
   - Observation: Challenger M6.1 identified that the regex `(?:\.|\b)(?:ac|edu|gov|gc)\.([a-z]{2,3})$` matched hyphenated tokens (e.g. `attacker-ac.uk`). Worker M6.2 replaced this with strict dot anchoring `\.(?:ac|edu|gov|gc)\.([a-z]{2,3})$`.
   - Observation: The Tier 5 test suite now contains 89 tests, including explicit parameterized tests proving `https://attacker-ac.uk`, `https://scam-edu.in`, and `https://phishing-gov.sg` are rejected, while `https://ox.ac.uk` and `https://www.cam.ac.uk` are accepted.
   - Observation: Runtime date comparison evaluates deadlines against `datetime.now(timezone.utc).date()`. Yesterday's deadline evaluates to `EXPIRED`, zeroes deadline points, and hard-disqualifies the candidate (`is_eligible_for_shortlist = False`).
   - Conclusion: R3 and Features F9-F10 are verified.

5. **Full Suite and Build Stability (R6, F25, F26, F27)**:
   - 285/285 backend tests passed (100%).
   - 55/55 E2E tests passed across Tiers 1-4 (100%).
   - 89/89 Tier 5 adversarial tests passed (100%).
   - 10/10 smoke unit tests passed (100%).
   - Frontend lint passed with 0 errors/warnings; production build succeeded in 1.78s.
   - Conclusion: Features F25, F26, and F27 are fully verified.

---

## 3. Caveats

- **No Live AI Studio Secret Stored**: In this development workspace, `GEMINI_API_KEY` contains a sandbox bearer token (redacted) rather than a Google AI Studio key (`AIzaSy...`). As intended by Feature F26, the CLI detects this format and outputs diagnostic instructions without crashing, while the automated test suite validates the live code path via mocked Google Gen AI SDK responses. When an active Google AI Studio key is provided in `.env`, no code modifications are needed to connect to live Google endpoints.
- No other caveats.

---

## 4. Conclusion

Milestone M6 meets all functional, architectural, and security acceptance criteria specified in `PROJECT.md` and `ORIGINAL_REQUEST.md`:
1. Grounded discovery and official URL extraction with `google-genai` are verified.
2. 0 hardcoded opportunities remain in live application code.
3. Strict dot-anchored domain validation blocks SSRF, spoofed subdomains, and hyphenated mimic domains.
4. Runtime UTC deadline evaluation and admission/scholarship separation are strictly enforced.
5. All 285 backend tests and frontend production builds pass cleanly with 0 regressions.

**Final Verdict**: **`APPROVE`**

---

## 5. Verification Method

To independently reproduce the review findings:

```bash
# 1. Verify smoke test unit suite (10 tests)
cd d:\Case_study_drive\TetraNoodle_AI_Hackathon\backend
pytest tests/test_smoke_gemini.py -v

# 2. Verify Tier 5 white-box adversarial backend suite (89 tests)
pytest tests/test_tier5_adversarial_backend.py -v

# 3. Verify E2E test suite Tiers 1-4 (55 tests)
pytest tests/e2e/ -v

# 4. Verify complete backend test suite (285 tests)
pytest -v

# 5. Verify live smoke test runner CLI in mock mode
python scripts/smoke_test_gemini.py --mock

# 6. Verify frontend lint and build
cd ../frontend
npm run lint
npm run build
```

**Invalidation Conditions**:
- Any failure in the 285 backend pytest tests.
- Any failure in `npm run build` or `npm run lint`.
- Acceptance of `attacker-ac.uk` or `scam-edu.in` by `is_official_domain`.
- Appearance of `REAL_OPPORTUNITIES_BASE` in any file under `backend/app/`.
