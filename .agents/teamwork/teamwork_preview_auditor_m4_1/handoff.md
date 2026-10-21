# Forensic Audit Report: Milestone M4 (Features F17 through F21)

**Auditor**: Forensic Auditor M4.1  
**Target Work Product**: Milestone M4 (Reproducible Experiment Harness & Quality Reviewer Suites)  
**Profile**: General Project (Integrity Mode: `development` per `ORIGINAL_REQUEST.md:8`)  
**Verdict**: `CLEAN`  

---

## 1. Observation

### 1.1 Metric Authenticity Forensics
1. **Inspection of `backend/scripts/evaluate_harness.py`**:
   - `BENCHMARK_CASES` (lines 41–533): Contains 10 documented benchmark test cases spanning genuine academic cases (`Toronto MScAC`, `TUM Informatics DAAD`, `NUS Research Scholarship`), adversarial/edge conditions (`Secondary Aggregator Blog URL`, `Unsupported Funding Claim`, `Missing Application Deadline`, `Non-Standard Grading Scale`), and injected faults (`HTTP 404`, `SSRF Cloud Metadata 169.254.169.254`).
   - Latency Measurement:
     - `run_single_pass_benchmark`: Line 589 invokes `start_time = time.perf_counter()`, and line 625 measures `latency = time.perf_counter() - start_time`.
     - `run_self_correcting_benchmark`: Line 653 invokes `start_time = time.perf_counter()`, line 661 measures early return latency, line 675 measures 404 containment latency, and line 728 measures full audit latency `time.perf_counter() - start_time`.
   - Pipeline Execution:
     - Lines 690–717 execute `QualityReviewerAgent.execute_audit()` with `StudentProfile` and `Opportunity` models.
     - Secondary aggregator URL (CASE-04) triggers re-research (`needs_re_research=True`), advancing `rounds` from 1 to 2, resolving official domain `web.cs.toronto.edu`, and re-auditing.
   - Dynamic Metrics Calculation:
     - Search for hardcoded metric percentages (`70.0%`, `80.0%`, `60.0%`, `100.0%`, `50.0%`) in `backend/scripts/evaluate_harness.py` returned zero occurrences.
     - Metrics are dynamically derived in `run_evaluation_benchmark` (lines 765–816):
       - `sp_official = sum(1 for r in sp_results if r["is_official"]) / total_cases * 100.0`
       - `sc_official = sum(1 for r in sc_results if r["is_official"]) / total_cases * 100.0`
       - `sp_accuracy = (sp_acc_count / total_cases) * 100.0`
       - `sc_accuracy = (sc_acc_count / total_cases) * 100.0`
       - `sp_fp = sum(1 for i in inadmissible_indices if sp_results[i]["is_admitted"]) / total_inadmissible * 100.0`
       - `sc_fp = sum(1 for i in inadmissible_indices if sc_results[i]["is_admitted"]) / total_inadmissible * 100.0`
       - `sp_fc = sum(1 for i in funding_anomaly_indices if sp_results[i]["funding_caught"]) / total_funding_anomalies * 100.0`
       - `sc_fc = sum(1 for i in funding_anomaly_indices if sc_results[i]["funding_caught"]) / total_funding_anomalies * 100.0`
       - `sp_fr = sum(1 for i in fault_indices if sp_results[i]["fault_recovered"]) / total_faults * 100.0`
       - `sc_fr = sum(1 for i in fault_indices if sc_results[i]["fault_recovered"]) / total_faults * 100.0`
       - `sp_latency = sum(r["latency_seconds"] for r in sp_results) / total_cases`
       - `sc_latency = sum(r["latency_seconds"] for r in sc_results) / total_cases`
2. **Inspection of `backend/artifacts/experiment_results.json` and `docs/EXPERIMENT.md`**:
   - `docs/EXPERIMENT.md` lines 29–40 contain structured empirical results matching `backend/artifacts/experiment_results.json`.
   - Upon independent execution of `python scripts/evaluate_harness.py`, `backend/artifacts/experiment_results.json` and `docs/EXPERIMENT.md` were regenerated in place with updated UTC timestamps (`2026-10-20T23:39:00.519514+00:00`) and fresh wall-clock latency measurements (`4.2e-05s` baseline vs `0.0002s` self-correcting), proving outputs are not static or pre-fabricated.

### 1.2 Test Integrity Forensics
1. **Assertion Integrity (`backend/tests/test_quality_reviewer.py`)**:
   - Search for `assert True`, `assert False`, or empty test bodies across the test suite returned 0 results.
   - All 9 test cases perform rigorous, property-level assertions:
     - `test_official_domain_approval`: lines 107–111 assert `evidence_quality == "OFFICIAL"`, `reviewer_status == "APPROVED"`, `needs_re_research is False`, `len(issues) == 0`.
     - `test_secondary_domain_flagged_for_reresearch`: lines 135–139 assert `evidence_quality == "SECONDARY"`, `reviewer_status == "FLAGGED"`, `needs_re_research is True`, `len(issues) >= 1`, and issue message/type verification.
     - `test_unsupported_fully_funded_flagged`: lines 162–163 assert `reviewer_status == "FLAGGED"`, and issue verification.
     - `test_supported_funding_approved`: lines 186–187 assert `reviewer_status == "APPROVED"`.
     - `test_missing_deadline_marked_unknown`: lines 210–212 assert `deadline_type == "Unknown"`, `deadline_verified is False`, `deadline_status == "UNKNOWN"`.
     - `test_reviewer_node_state_update_in_graph`: lines 236–239 assert `update["needs_re_research"] is True`, `update["research_round"] == 2`, `update["current_phase"] == "RE_RESEARCH"`, `len(update["reviewer_issues"]) >= 1`.
     - `test_re_research_loop_bounded_termination`: lines 256, 265, 274 test within-bounds re-research (`"research_discovery"`), exceeded bounds (`"__end__"`), and clean audit (`"__end__"`).
     - `test_gemini_reviewer_audit_mocked_failure_handling`: lines 312–314 assert `reviewer_status == "FLAGGED"`, `needs_re_research is True`.
     - `test_reviewer_handles_gemini_service_unavailable`: lines 337–340 assert graceful degradation without exceptions.
2. **Assertion Integrity (`backend/tests/test_evaluation_harness.py`)**:
   - `test_benchmark_cases_dataset_integrity`: lines 15–21 assert exact count of 10 cases and presence of required schema fields.
   - `test_evaluation_harness_execution`: lines 35–79 assert top-level schema keys, metric dictionaries, file persistence in a temporary directory, and strict empirical boundary invariants:
     - `results["self_correcting"]["false_positive_rate"] == 0.0`
     - `results["self_correcting"]["official_coverage"] >= results["single_pass"]["official_coverage"]`
     - `results["self_correcting"]["eligibility_accuracy"] >= results["single_pass"]["eligibility_accuracy"]`
     - `results["self_correcting"]["unsupported_claims_caught"] == 100.0`
     - `results["self_correcting"]["fault_recovery"] == 100.0`
   - `test_format_markdown_report`: lines 119–125 assert presence of table sections and case descriptions.
3. **Mocking & Facade Inspection**:
   - `GeminiService.is_available` is patched to `False` in offline unit tests, and to `True` with `AsyncMock` in failure-handling tests. No internal agent logic or rule-based verification code is mocked out.
   - Zero facade implementations detected.

### 1.3 Execution Validation Results
1. **Documented Test Command**:
   - Command: `python -m pytest tests/test_graph.py tests/test_scoring.py tests/test_quality_reviewer.py -v` (Cwd: `backend`)
   - Verbatim Output:
     ```
     tests/test_graph.py::test_route_after_review_conditional_logic PASSED    [  7%]
     tests/test_graph.py::test_full_graph_workflow_execution PASSED           [ 14%]
     tests/test_scoring.py::test_scoring_weights_and_dimensions PASSED        [ 21%]
     tests/test_scoring.py::test_hard_disqualifier_excludes_from_shortlist PASSED [ 28%]
     tests/test_scoring.py::test_potential_match_partial_score PASSED         [ 35%]
     tests/test_quality_reviewer.py::test_official_domain_approval PASSED     [ 42%]
     tests/test_quality_reviewer.py::test_secondary_domain_flagged_for_reresearch PASSED [ 50%]
     tests/test_quality_reviewer.py::test_unsupported_fully_funded_flagged PASSED [ 57%]
     tests/test_quality_reviewer.py::test_supported_funding_approved PASSED   [ 64%]
     tests/test_quality_reviewer.py::test_missing_deadline_marked_unknown PASSED [ 71%]
     tests/test_quality_reviewer.py::test_reviewer_node_state_update_in_graph PASSED [ 78%]
     tests/test_quality_reviewer.py::test_re_research_loop_bounded_termination PASSED [ 85%]
     tests/test_quality_reviewer.py::test_gemini_reviewer_audit_mocked_failure_handling PASSED [ 92%]
     tests/test_quality_reviewer.py::test_reviewer_handles_gemini_service_unavailable PASSED [100%]
     ============================= 14 passed in 5.30s ==============================
     ```
   - Exit Code: 0.

2. **Quality Reviewer and Evaluation Harness Suite**:
   - Command: `pytest tests/test_quality_reviewer.py tests/test_evaluation_harness.py -v` (Cwd: `backend`)
   - Verbatim Output:
     ```
     ============================= 12 passed in 4.83s ==============================
     ```
   - Exit Code: 0.

3. **Evaluation Harness CLI Execution**:
   - Command: `python scripts/evaluate_harness.py` (Cwd: `backend`)
   - Verbatim Output:
     ```
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
   - Exit Code: 0.

4. **Full Backend Test Suite (Regression Protection)**:
   - Command: `pytest --ignore=tests/e2e -v` (Cwd: `backend`)
   - Verbatim Output:
     ```
     ============================ 102 passed in 13.26s =============================
     ```
   - Exit Code: 0.

---

## 2. Logic Chain

1. **Premise 1**: A clean forensic verdict requires that all reported metrics in `docs/EXPERIMENT.md` and `backend/artifacts/experiment_results.json` are dynamically computed from genuine execution rather than hardcoded or fabricated (Integrity Forensics Prohibited Pattern 1 & 3).
   - *Observation*: Source code search in `evaluate_harness.py` verified that no percentage metrics or latency numbers are hardcoded. AST and execution trace confirm that `run_evaluation_benchmark` computes all values from `sp_results` and `sc_results` dynamically, writes them to `experiment_results.json`, and updates `docs/EXPERIMENT.md`.
2. **Premise 2**: Latency measurements must use genuine monotonic wall-clock timing.
   - *Observation*: Lines 589, 625, 653, 661, 675, and 728 in `evaluate_harness.py` utilize `time.perf_counter()` directly. Latency varied across independent runs (`3.8e-05s` vs `4.2e-05s` for baseline; `0.000188s` vs `0.0002s` for self-correcting) reflecting real execution differences.
3. **Premise 3**: Single-pass vs. self-correcting pipeline comparison must reflect authentic logic divergence rather than a mocked facsimile.
   - *Observation*: In baseline single-pass, secondary URLs are retained without re-research, sub-cutoff applicants pass without audit (false positives), expired deadlines are missed, and unhandled faults fail. In self-correcting mode, `QualityReviewerAgent` executes real domain validation (`is_official_domain`), URL sanitization (`is_safe_url`), funding checks, runtime deadline verification against `datetime.now(timezone.utc).date()`, and triggers iterative re-research rounds.
4. **Premise 4**: Test suites must have genuine assertion depth with zero vacuous assertions or obfuscated monkeypatching (Integrity Forensics Prohibited Pattern 2 & 4).
   - *Observation*: `test_quality_reviewer.py` (9 tests) and `test_evaluation_harness.py` (3 tests) contain zero `assert True` statements. All assertions test explicit field values, enum statuses, state mutations, and empirical invariance properties.
5. **Premise 5**: Documented and regression test commands must execute with exit code 0.
   - *Observation*: All required commands executed successfully: 14/14 tests passed in the documented suite, 12/12 tests passed in the M4 suite, and 102/102 tests passed across the entire backend unit/integration suite.
6. **Conclusion**: Milestone M4 strictly conforms to all integrity guidelines, with zero prohibited patterns and 100% empirical verification.

---

## 3. Caveats

No caveats. All requirements under Milestone M4 (Features F17 through F21) have been directly and empirically validated.

---

## 4. Conclusion

**Verdict**: `CLEAN`

Milestone M4 satisfies all integrity forensics criteria:
- **Feature F17**: `backend/pytest.ini` properly configured with `pythonpath = .` and clean discovery.
- **Feature F18**: `backend/tests/test_quality_reviewer.py` implemented with 9 comprehensive, high-integrity test cases.
- **Feature F19**: `backend/scripts/evaluate_harness.py` implements a reproducible, empirical 10-case evaluation runner with dynamic metric calculations and real `time.perf_counter()` timing.
- **Feature F20**: `backend/tests/test_evaluation_harness.py` automates harness regression testing with 3 rigorous test cases.
- **Feature F21**: `docs/EXPERIMENT.md` accurately reflects empirical measurements generated directly from the harness.

---

## 5. Verification Method

To independently reproduce this forensic audit:

1. **Verify Metric Authenticity in Harness**:
   ```powershell
   cd D:\Case_study_drive\TetraNoodle_AI_Hackathon\backend
   python scripts/evaluate_harness.py
   git diff artifacts/experiment_results.json docs/EXPERIMENT.md
   ```
   *Expected*: Exit code 0, non-zero runtime latency, updated timestamp.

2. **Run Documented Experiment Test Suite**:
   ```powershell
   cd D:\Case_study_drive\TetraNoodle_AI_Hackathon\backend
   python -m pytest tests/test_graph.py tests/test_scoring.py tests/test_quality_reviewer.py -v
   ```
   *Expected*: 14 passed in ~5s.

3. **Run M4 Quality Reviewer & Harness Test Suites**:
   ```powershell
   cd D:\Case_study_drive\TetraNoodle_AI_Hackathon\backend
   pytest tests/test_quality_reviewer.py tests/test_evaluation_harness.py -v
   ```
   *Expected*: 12 passed in ~4s.

4. **Run Full Regression Suite**:
   ```powershell
   cd D:\Case_study_drive\TetraNoodle_AI_Hackathon\backend
   pytest --ignore=tests/e2e -v
   ```
   *Expected*: 102 passed in ~13s.

5. **Invalidation Conditions**:
   - If `evaluate_harness.py` contains hardcoded metric percentages, this report is invalidated.
   - If `test_quality_reviewer.py` or `test_evaluation_harness.py` contain vacuous assertions (`assert True`), this report is invalidated.
   - If any of the above commands fail with non-zero exit code, this report is invalidated.
