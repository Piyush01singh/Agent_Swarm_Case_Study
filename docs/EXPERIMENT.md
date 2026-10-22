# Experiment: Self-Correcting Scholarship Research
## TetraNoodle AI Hackathon 2026

### 1. Objective
Evaluate whether an independent **Quality Reviewer Agent** (Agent 5) routing targeted issues back to the **Research & Eligibility Agent** (Agent 2) improves official source evidence grounding, eliminates false-positive admissions, detects unsupported funding claims, and recovers safely from injected faults.

---

### 2. Experimental Setup & Benchmark Methodology

The evaluation harness executes a comparative empirical benchmark across 10 documented real-world and adversarial test cases comparing **Single-Pass (Baseline)** against **Self-Correcting (ScholarSwarm 5-Agent Loop)**.

#### 10 Documented Benchmark Cases:
1. **CASE-01: Toronto MScAC / Vector AI** — Official domain, fully funded, valid deadline, student 8.2 CGPA -> MEETS.
2. **CASE-02: TUM Informatics DAAD** — Strict 7.5 CGPA entrance threshold vs Maria Santos 6.8 CGPA -> DOES_NOT_MEET (tests false-positive prevention).
3. **CASE-03: NUS Research Scholarship** — PhD track, Wei Chen 8.5 CGPA, missing language score -> POTENTIAL_MATCH with UNRESOLVED prerequisite gap.
4. **CASE-04: Secondary Aggregator Blog URL** — Ingests secondary blog domain; Reviewer flags SECONDARY_SOURCE and triggers re-research to retrieve official domain.
5. **CASE-05: Unsupported Funding Claim** — Opportunity claims "Fully Funded" with missing coverage breakdown; Reviewer flags MISSING_COVERAGE.
6. **CASE-06: Unannounced / Missing Deadline** — No deadline published; Reviewer marks `deadline_type: "Unknown"` and `deadline_verified: False`.
7. **CASE-07: Injected Retrieval Failure (HTTP 404 / Connection Timeout)** — Injected network failure; evaluates safe containment without pipeline crash.
8. **CASE-08: Injected SSRF / Unsafe Host** — Injected cloud metadata IP (`169.254.169.254`); intercepted by URL sanitizer.
9. **CASE-09: Expired Application Cycle** — Past-cycle deadline (`2024-01-15`); evaluated against runtime UTC date and flagged as EXPIRED.
10. **CASE-10: Non-Standard CGPA Scale / Ambiguous Conversion** — Ambiguous scale conversion without published formula; flagged as UNRESOLVED with actionable gap.

---

### 3. Empirical Measurements & Results

*Benchmark Execution Mode: `deterministic_mock` | Test Cases: `10` | Generated: `2026-10-21T07:40:09.344902+00:00`*

> **Benchmark Transparency & Simulation Disclaimer**:
> All latency metrics and performance results reported in this document were measured using the automated in-memory evaluation harness (`backend/scripts/evaluate_harness.py`). They represent **deterministic simulated benchmark execution** designed to evaluate agent routing, self-correction logic, and classification accuracy in an isolated, reproducible offline environment without consuming API quotas.
> 
> These numbers do **NOT** reflect live Google Gemini API network latency or live web scraping turnaround times, which typically range from 1 to 5 seconds per round in production.

| Metric | Single Pass (Baseline) | Self-Correcting (ScholarSwarm) | Delta / Improvement |
|---|---:|---:|---:|
| **Critical Claims Grounded in Official Sources** | 70.0% | **80.0%** | **+10.0%** |
| **Eligibility Classification Accuracy (vs Ground Truth)** | 60.0% | **100.0%** | **+40.0%** |
| **False-Positive Admissions Pass Rate** | 50.0% | **0.0%** | **-50.0% (Eliminated)** |
| **Unsupported Funding Claims Flagged & Rectified** | 0/1 (0.0%) | **1/1 (100.0%)** | **+100.0%** |
| **Fault Recovery under Injected Network/URL Block** | 0.0% | **100.0%** | **+100.0%** |
| **Mean Simulated Routing Latency (In-Memory Harness)** * | 4e-05s | 0.000195s | +0.000155s |
| **Mean Additional Pipeline Rounds** | 1.0 rounds | 1.3 rounds | +0.3 rounds |

*\* Deterministic mock harness execution measuring CPU routing overhead without external network latency.*

---

### 4. Key Observations & Findings

1. **Elimination of False-Positive Admissions**:
   - In baseline single-pass extraction, candidates with sub-cutoff grades (e.g., CASE-02 Maria Santos with 6.8 CGPA against TUM's strict 7.5 requirement) were admitted under generic country-level or lenient heuristics.
   - The Quality Reviewer evaluated the exact published criteria excerpt, flagging `MANDATORY_CRITERIA_FAILED` and reducing the false-positive pass rate from **50.0%** to **0.0%**.

2. **Official Domain Re-Research Escalation**:
   - In CASE-04, an initial candidate opportunity retrieved from an aggregator blog (`scholarship-positions.com`) was flagged with `evidence_quality: "SECONDARY"`. The bounded re-research loop resolved the official department portal (`web.cs.toronto.edu`), elevating official source grounding from **70.0%** to **80.0%**.

3. **Catching Funding Discrepancies**:
   - When opportunities claim "Fully Funded" without stating what is covered (CASE-05), single-pass accepts the headline claim. Agent 5 caught 100% of missing coverage descriptions, preventing misleading funding guidance.

4. **Fault Recovery & Safety Containment**:
   - Injected network faults (HTTP 404 in CASE-07) and SSRF exploit URLs (CASE-08 `http://169.254.169.254`) caused failures in baseline passes, whereas the self-correcting pipeline achieved **100% fault recovery** through proactive URL sanitization and graceful error states.

5. **Bounded Algorithmic Routing Overhead (Simulated In-Memory)**:
   - The self-correction loop added only ~+0.3 rounds and negligible CPU routing overhead (+0.000155s in-memory), demonstrating efficient state transition mechanics. In live production execution, total duration is bounded strictly by the 2-round iteration ceiling.

---

### 5. Reproducibility Instructions

To replicate this experiment and run all test suites locally:

```bash
# 1. Run the evaluation harness (generates backend/artifacts/experiment_results.json)
cd backend
python scripts/evaluate_harness.py

# 2. Run the automated quality reviewer and workflow test suites
python -m pytest tests/test_graph.py tests/test_scoring.py tests/test_quality_reviewer.py -v

# 3. Run the evaluation harness test
pytest tests/test_evaluation_harness.py -v

# 4. Run the complete pytest test suite
pytest -v
```
