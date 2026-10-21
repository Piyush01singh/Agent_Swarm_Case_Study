# Survey 2 Handoff Report: Requirement R5 & Testing Infrastructure

**Author**: Survey Explorer 2 (Testing, Experiment Harness & Docs)  
**Date**: 2026-10-20  
**Target Directory**: `D:\Case_study_drive\TetraNoodle_AI_Hackathon\.agents\teamwork\teamwork_preview_explorer_survey_2`  
**Handoff Type**: Hard (Investigation & Blueprint Complete)

---

## 1. Observation

### 1.1 Documentation Claims in `docs/EXPERIMENT.md`
Direct observation of `docs/EXPERIMENT.md`:
- **Line 11**:
  > `Target Candidate Sample: 10 distinct international graduate scholarship opportunities across Canada, Germany, and Singapore (e.g., Vector Institute AI Master's, TUM DAAD Informatics, NUS Research Scholarship, NTU MSAI, UBC Global Leadership Fellowship).`
- **Lines 12–15**:
  > `Test Profiles Tested: 1. Rahul Sharma (B.Tech CS, 8.2 CGPA...)... 2. Profile B (B.Sc Biotech, 6.8 CGPA...)... 3. Profile C (M.Sc Mathematics, 8.6 CGPA...)`
- **Lines 24–33 (Table of Empirical Measurements & Results)**:
  > | Metric | Single Pass (Baseline) | Self-Correcting (ScholarSwarm) | Delta / Improvement |
  > |---|---:|---:|---:|
  > | **Critical Claims Grounded in Official Sources** | 78.4% | **94.2%** | **+15.8%** |
  > | **Eligibility Classification Accuracy (vs Ground Truth)** | 84.0% | **96.0%** | **+12.0%** |
  > | **False-Positive Admissions Pass Rate** | 12.0% | **0.0%** | **-12.0% (Eliminated)** |
  > | **Unsupported Funding Claims Flagged & Rectified** | 0/4 | **4/4 (100%)** | **100% Detected** |
  > | **Fault Recovery under Injected Network/URL Block** | 30.0% | **90.0%** | **+60.0%** |
  > | **Mean End-to-End Latency** | 3.4s | 5.8s | +2.4s |
  > | **Mean Additional API Calls per Cycle** | 0 calls | 1.8 calls | +1.8 calls |
- **Lines 38–44**: Claims that "Agent 5 flagged instances where universal conversion was inferred without published equivalency evidence, forcing the criterion into `UNRESOLVED`..." and "The self-correction loop added only 1.8 additional calls and 2.4 seconds of latency...".
- **Lines 50–55 (Reproducibility Command)**:
  ```bash
  # Run the automated graph and quality reviewer test suite
  cd backend
  python -m pytest tests/test_graph.py tests/test_scoring.py tests/test_quality_reviewer.py -v
  ```

### 1.2 Verbatim Test Execution Failure
Executing the documented experiment command:
- **Command**: `python -m pytest tests/test_graph.py tests/test_scoring.py tests/test_quality_reviewer.py -v` (in `D:\Case_study_drive\TetraNoodle_AI_Hackathon\backend`)
- **Result**:
  ```
  ERROR: file or directory not found: tests/test_quality_reviewer.py
  collected 0 items
  ============================ no tests ran in 0.01s ============================
  ```
  Exit code: `1`. The test file `tests/test_quality_reviewer.py` **does not exist** anywhere in the repository.

### 1.3 Verbatim Plain `pytest` Command Failure
Executing plain `pytest -v` in `D:\Case_study_drive\TetraNoodle_AI_Hackathon\backend`:
- **Command**: `pytest -v`
- **Result**:
  ```
  collecting ... collected 0 items / 7 errors
  ERROR collecting tests/test_api.py: ModuleNotFoundError: No module named 'app'
  ERROR collecting tests/test_documents.py: ModuleNotFoundError: No module named 'app'
  ERROR collecting tests/test_eligibility.py: ModuleNotFoundError: No module named 'app'
  ERROR collecting tests/test_github.py: ModuleNotFoundError: No module named 'app'
  ERROR collecting tests/test_graph.py: ModuleNotFoundError: No module named 'app'
  ERROR collecting tests/test_profile.py: ModuleNotFoundError: No module named 'app'
  ERROR collecting tests/test_scoring.py: ModuleNotFoundError: No module named 'app'
  ============================== 7 errors in 4.36s ==============================
  ```
  Exit code: `1`. No `pytest.ini` or `pyproject.toml` exists configuring `pythonpath = .`.

### 1.4 Test Suite Inventory (`backend/tests/`)
When run via `python -m pytest -v` (which implicitly adds current working directory to `sys.path`), 21 tests collected and passed across 7 files:
1. `backend/tests/test_api.py` (68 lines): 3 tests (`test_health_endpoint`, `test_profile_adaptability_three_profiles`, `test_reset_endpoint`).
2. `backend/tests/test_documents.py` (59 lines): 4 tests (`test_pdf_extraction_success`, `test_pdf_extraction_empty_failure`, `test_docx_extraction_success`, `test_parse_profile_facts_from_text`).
3. `backend/tests/test_eligibility.py` (38 lines): 3 tests (`test_url_normalization`, `test_safe_url_ssrf_protection`, `test_evidence_record_integrity`).
4. `backend/tests/test_github.py` (22 lines): 3 tests (`test_extract_username_formats`, `test_validate_github_username`, `test_fetch_github_invalid_username`).
5. `backend/tests/test_graph.py` (42 lines): 2 tests (`test_route_after_review_conditional_logic`, `test_full_graph_workflow_execution`).
6. `backend/tests/test_profile.py` (38 lines): 3 tests (`test_student_profile_defaults`, `test_student_profile_custom_validation`, `test_project_achievement_provenance`).
7. `backend/tests/test_scoring.py` (88 lines): 3 tests (`test_scoring_weights_and_dimensions`, `test_hard_disqualifier_excludes_from_shortlist`, `test_potential_match_partial_score`).
- Noticeably absent:
  - `test_quality_reviewer.py` (completely missing).
  - Any evaluation harness script or test (`evaluate_harness.py`, `test_evaluation_harness.py`).
  - `conftest.py` (no shared fixtures).
  - Any live Gemini API smoke test.

### 1.5 Quality Reviewer Implementation (`backend/app/agents/quality_reviewer.py`)
Direct observation of `QualityReviewerAgent`:
- **Lines 38–62**: Checks domain substrings (`.edu`, `.ac.`, `.ca`, `.de`, `.sg`, `.gov`, `.org`, `vectorinstitute.ai`, `daad.de`, `a-star.edu.sg`). If unverified, sets `opp.evidence_quality = "SECONDARY"`, `opp.reviewer_status = "FLAGGED"`, and sets `needs_re_research = True`.
- **Lines 64–70**: If `funding_type == "Fully Funded"` and not `coverage_description`, sets `opp.reviewer_status = "FLAGGED"`.
- **Lines 72–76**: If not `opp.deadline`, sets `opp.deadline_type = "Unknown"`, `opp.deadline_verified = False`.
- **Lines 82–94**: Calls `gemini_service.review_evidence_and_claims` if `gemini_service.is_available` is True.
- **Lines 105–106**: Returns `(opportunities, needs_re_research, issues)`.
- **Note on Claim vs Reality**: The agent does *not* audit CGPA conversions as claimed in `docs/EXPERIMENT.md:38–41`. It only checks domain suffixes, fully-funded coverage text, and missing deadlines.

### 1.6 Hardcoded Data in Live Research (`backend/app/agents/research_eligibility.py`)
- **Lines 15–295**: Defines `REAL_OPPORTUNITIES_BASE` (10 hardcoded dictionaries).
- **Lines 363–380**: Iterates over `REAL_OPPORTUNITIES_BASE` and builds opportunities directly from it, ignoring live web extraction.
- **Lines 393–415**: Hardcodes country-based CGPA cutoffs (e.g., `raw_opp["country"] == "Canada" and student_cgpa >= 8.0`).

### 1.7 Frontend Build (`frontend/package.json`)
- Running `npm run build` in `d:\Case_study_drive\TetraNoodle_AI_Hackathon\frontend` exited with code 0 (`tsc -b && vite build` built cleanly in 2.31s).

---

## 2. Logic Chain

1. **Premise**: `docs/EXPERIMENT.md` presents exact empirical percentages (78.4% -> 94.2%, 84.0% -> 96.0%, 0/4 -> 4/4 rectified, 30% -> 90% fault recovery, 3.4s -> 5.8s latency) and claims these results were derived from testing 10 candidate opportunities across 3 student profiles.
2. **Finding**: A workspace-wide search for any script containing benchmark harnesses, evaluation routines, or experiment metric calculation returned 0 matches.
3. **Finding**: The single test command documented in `docs/EXPERIMENT.md` (`python -m pytest tests/test_graph.py tests/test_scoring.py tests/test_quality_reviewer.py -v`) fails immediately with code 1 because `tests/test_quality_reviewer.py` does not exist.
4. **Finding**: The live discovery code in `backend/app/agents/research_eligibility.py` actually bypassed live search and loaded hardcoded records from `REAL_OPPORTUNITIES_BASE`.
5. **Inference**: The empirical numbers and comparative claims in `docs/EXPERIMENT.md` are unverified placeholder fabrications. They were not produced by an executable evaluation harness.
6. **Premise**: Requirement R5 requires:
   - Updating `docs/EXPERIMENT.md` by removing unverified or fabricated claims.
   - Providing a runnable Python evaluation harness with documented test cases comparing single-pass vs. Quality Reviewer correction loops, injecting controlled retrieval failures, and measuring latency, source coverage, and eligibility accuracy.
   - Fixing all missing test commands (including `test_quality_reviewer.py`) and writing reproducible results to artifacts.
7. **Inference**: Fulfilling R5 requires four concrete technical deliverables:
   a. Implementing `backend/tests/test_quality_reviewer.py` to fix the broken documented command.
   b. Adding `backend/pytest.ini` with `pythonpath = .` so both `pytest` and `python -m pytest` execute reliably without module import errors.
   c. Creating a standalone runnable evaluation script (`backend/scripts/evaluate_harness.py`) and companion test (`backend/tests/test_evaluation_harness.py`) with 10 documented test cases, controlled failure injection, latency measurement, and JSON/Markdown output.
   d. Rewriting `docs/EXPERIMENT.md` with true empirical measurements generated directly by the harness.

---

## 3. Caveats

- **Gemini API Key Availability**: While `.env` in the workspace root contains a Gemini API key (`GEMINI_API_KEY`), running tests from `backend/` does not load root `.env` unless configured or explicitly passed. The evaluation harness must support an **offline / mock mode** that produces deterministic, reproducible evaluation metrics without external network calls, alongside an optional `--live` mode when API keys are available.
- **Frontend Scope**: The frontend builds successfully (`npm run build`), but its Opportunity Cards, Evidence Drawer, and Gap Planner components must be audited by Survey Explorer 3 / implementers to ensure UI rendering consumes live pipeline data rather than static fallbacks.
- **Scope Boundary**: As Survey Explorer 2, this investigation is strictly read-only. No project source files have been modified.

---

## 4. Conclusion

1. **Documented Claims**: `docs/EXPERIMENT.md` contains completely fabricated metrics (78.4% -> 94.2% source grounding, 84% -> 96% accuracy, 12% -> 0% false positives, 30% -> 90% fault recovery). No test harness or empirical log exists to support them.
2. **Broken Commands**: The documented command `python -m pytest tests/test_graph.py tests/test_scoring.py tests/test_quality_reviewer.py -v` is broken because `test_quality_reviewer.py` is absent.
3. **Environment Execution Bug**: Plain `pytest` fails across all 7 test files due to missing `pytest.ini` (`pythonpath = .`).
4. **R5 Blueprint Prepared**: An exact architecture for `test_quality_reviewer.py`, `backend/pytest.ini`, and `backend/scripts/evaluate_harness.py` is defined below to enable immediate implementation.

---

## 5. Blueprint for Fulfilling Requirement R5

### 5.1 New File: `backend/pytest.ini`
Creates standard pytest discovery configuration:
```ini
[pytest]
pythonpath = .
asyncio_mode = auto
testpaths = tests
filterwarnings =
    ignore::DeprecationWarning
    ignore::pydantic.warnings.PydanticDeprecatedSince20
```

### 5.2 New File: `backend/tests/test_quality_reviewer.py`
Fulfills missing test command and validates Agent 5:
- **Test 1: `test_official_domain_approval`**:
  - Input: Opportunity with official university domain (`https://web.cs.toronto.edu`).
  - Expectation: `evidence_quality == "OFFICIAL"`, `reviewer_status == "APPROVED"`, `needs_re_research == False`.
- **Test 2: `test_secondary_domain_flagged_for_reresearch`**:
  - Input: Opportunity with secondary aggregator domain (`https://scholarship-positions.com/toronto-award`).
  - Expectation: `evidence_quality == "SECONDARY"`, `reviewer_status == "FLAGGED"`, `needs_re_research == True`, `issues` contains `"Only secondary sources found"`.
- **Test 3: `test_unsupported_fully_funded_flagged`**:
  - Input: Opportunity claiming `funding_type == "Fully Funded"` but `coverage_description == ""`.
  - Expectation: `reviewer_status == "FLAGGED"`, `needs_re_research == False` (flagged for review/rectification), issue recorded in `issues`.
- **Test 4: `test_supported_funding_approved`**:
  - Input: Opportunity with `funding_type == "Fully Funded"` and `coverage_description == "$17,500 CAD scholarship + research internship"`.
  - Expectation: `reviewer_status == "APPROVED"`.
- **Test 5: `test_missing_deadline_marked_unknown`**:
  - Input: Opportunity with `deadline == None` or empty string.
  - Expectation: `deadline_type == "Unknown"`, `deadline_verified == False`, note records unannounced/undocumented status.
- **Test 6: `test_reviewer_node_state_update_in_graph`**:
  - Input: `SwarmState` with `research_round = 1`, `max_research_rounds = 2`, flagged opportunities.
  - Call: `await node_quality_reviewer(state)`.
  - Expectation: Returned dictionary contains `research_round == 2`, `needs_re_research == True`, `current_phase == "RE_RESEARCH"`.
- **Test 7: `test_re_research_loop_bounded_termination`**:
  - Input: `SwarmState` where `research_round = 3`, `max_research_rounds = 2`, `needs_re_research = True`.
  - Call: `route_after_review(state)`.
  - Expectation: Returns `"__end__"` (workflow does not loop infinitely).
- **Test 8: `test_gemini_reviewer_audit_mocked_failure_handling`**:
  - Mock `gemini_service.review_evidence_and_claims` returning `approved=False` with issues.
  - Call: `reviewer_agent.execute_audit(...)`.
  - Expectation: Reviewer incorporates detected LLM issues into the issue list.
- **Test 9: `test_reviewer_handles_gemini_service_unavailable`**:
  - Set `gemini_service.is_available = False`.
  - Expectation: `execute_audit` completes rule-based audits without error.

### 5.3 New File: `backend/scripts/evaluate_harness.py`
A standalone, runnable evaluation harness.
- **CLI Usage**:
  ```bash
  cd backend
  python scripts/evaluate_harness.py [--output artifacts/experiment_results.json] [--markdown docs/EXPERIMENT.md]
  ```
- **Structure**:
  1. **Documented Dataset (`BENCHMARK_CASES`)**: 10 curated test cases:
     - Case 1: University of Toronto MScAC / Vector AI (Official domain, Fully Funded, valid deadline, Rahul 8.2 CGPA -> MEETS).
     - Case 2: TUM Informatics DAAD (Official domain, Fully Funded, Student B 6.8 CGPA vs 7.5 cutoff -> DOES_NOT_MEET).
     - Case 3: NUS Research Scholarship (Official domain, PhD track, Student C 8.5 CGPA, missing GRE/TOEFL -> POTENTIAL_MATCH / UNRESOLVED).
     - Case 4: Secondary Aggregator Blog URL (`scholarshipsads.com`) -> In single-pass: accepted as candidate. In self-correcting: flagged by Reviewer, re-research round triggered, resolves official domain.
     - Case 5: Unsupported Funding Claim ("Fully Funded" without coverage) -> In single-pass: unflagged. In self-correcting: caught and rectified.
     - Case 6: Unannounced / Missing Deadline -> In single-pass: left blank. In self-correcting: tagged `deadline_type="Unknown"`, `deadline_verified=False`.
     - Case 7: Injected Retrieval Failure (HTTP 404 / connection timeout) -> Controlled failure injection; measures fault recovery without pipeline crash.
     - Case 8: Injected SSRF / Unsafe Host (`http://169.254.169.254`) -> Intercepted by sanitizer; measures safety containment.
     - Case 9: Expired / Past-Cycle Deadline (e.g. `2024-01-15`) -> Evaluated against current runtime; flagged as passed.
     - Case 10: Non-standard CGPA scale / Ambiguous conversion -> Flagged as `UNRESOLVED` with actionable transcript verification gap.
  2. **Comparative Runner**:
     - Runs **Pass 1: Baseline Single-Pass** (no Quality Reviewer feedback, 1 round).
     - Runs **Pass 2: Self-Correcting Pass** (Agent 5 active, targeted re-research, max 2 rounds).
     - Records wall-clock latency via `time.perf_counter()`.
     - Records tool / round counts.
  3. **Metrics Computation**:
     - `official_source_coverage`: % official vs secondary domains.
     - `eligibility_accuracy`: % match against ground truth labels.
     - `false_positive_pass_rate`: % failing candidates incorrectly admitted.
     - `unsupported_claims_rectified`: count of caught funding/deadline anomalies.
     - `fault_recovery_rate`: % injected failures handled gracefully.
     - `mean_latency_seconds`: baseline vs self-correcting latency.
  4. **Output Artifacts**:
     - Writes `backend/artifacts/experiment_results.json`.
     - Formats Markdown summary table and writes/updates `docs/EXPERIMENT.md`.

### 5.4 New File: `backend/tests/test_evaluation_harness.py`
Ensures CI test coverage for the evaluation harness:
```python
import pytest
from scripts.evaluate_harness import run_evaluation_benchmark

@pytest.mark.asyncio
async def test_evaluation_harness_execution():
    results = await run_evaluation_benchmark(mock_mode=True)
    assert "single_pass" in results
    assert "self_correcting" in results
    assert results["self_correcting"]["false_positive_rate"] == 0.0
    assert results["self_correcting"]["official_coverage"] >= results["single_pass"]["official_coverage"]
```

### 5.5 Updating `docs/EXPERIMENT.md`
Replace fabricated data with the exact empirical results produced by `evaluate_harness.py`. Explicitly state:
- Exact methodology and test cases used.
- Actual measured numbers from `artifacts/experiment_results.json`.
- Reproducibility commands that actually work:
  ```bash
  cd backend
  python -m pytest tests/test_graph.py tests/test_scoring.py tests/test_quality_reviewer.py -v
  python scripts/evaluate_harness.py
  ```

---

## 6. Verification Method

To independently verify the observations and conclusions in this report:

1. **Verify Broken Documented Test Command**:
   ```bash
   cd D:\Case_study_drive\TetraNoodle_AI_Hackathon\backend
   python -m pytest tests/test_graph.py tests/test_scoring.py tests/test_quality_reviewer.py -v
   ```
   *Expected Result*: Exits with code 1, `ERROR: file or directory not found: tests/test_quality_reviewer.py`.

2. **Verify Plain `pytest` Module Import Failure**:
   ```bash
   cd D:\Case_study_drive\TetraNoodle_AI_Hackathon\backend
   pytest -v
   ```
   *Expected Result*: Exits with code 1, `ModuleNotFoundError: No module named 'app'`.

3. **Verify Existing Tests Pass with `python -m`**:
   ```bash
   cd D:\Case_study_drive\TetraNoodle_AI_Hackathon\backend
   python -m pytest tests -v
   ```
   *Expected Result*: 21 passed.

4. **Verify Frontend Build**:
   ```bash
   cd D:\Case_study_drive\TetraNoodle_AI_Hackathon\frontend
   npm run build
   ```
   *Expected Result*: Exits with code 0.

5. **Invalidation Conditions**:
   - If `tests/test_quality_reviewer.py` exists before this implementation, Observation 1.2 is invalidated.
   - If a script already generates the numbers in `docs/EXPERIMENT.md`, Observation 1.1 is invalidated.
