# Handoff Report: Milestone M2 (Strict Eligibility & Domain/Deadline Verification)

**Agent**: Worker M2 (`teamwork_preview_worker_m2`)  
**Target Milestone**: M2 (Features F6, F7, F8, F9, F10)  
**Parent Orchestrator ID**: `6828b193-f5c1-4991-90e8-8c39694edfd6`  
**Date**: 2026-10-20T22:20:00Z  

---

## 1. Observation

### 1.1 Previous State Deficiencies
1. **Generic Country-Level Heuristics in Eligibility (Feature F6)**:
   - In `backend/app/agents/research_eligibility.py`, criteria matching historically relied on broad country rules (e.g. `if raw_opp["country"] == "Canada" and student_cgpa >= 8.0`) rather than extracting and comparing directly against program-specific cutoffs.
   - Distinct institutions within the same country (e.g., University of Waterloo requiring IELTS 7.5 and strict 8.0 CGPA vs McGill requiring IELTS 6.5) could not be evaluated accurately.
2. **Fabricated Excerpts & Lack of UNRESOLVED Handling (Feature F7)**:
   - Excerpts were previously generated with synthetic f-strings like `Student's 8.2/10.0 CGPA satisfies German 2.0 conversion threshold`, rather than preserving authentic quotes from retrieved official page content.
   - Missing or planned language test scores (`status == "planned"`) or unverified equivalencies were not explicitly marked as `UNRESOLVED` with actionable gaps.
3. **Lack of Admission vs Scholarship Separation (Feature F8)**:
   - While `Opportunity` possessed fields for `admission_requirements` and `scholarship_requirements`, mandatory admission requirements were not distinguished or verified before candidate ranking.
4. **Historical/Expired Deadlines Awarded Maximum Readiness (Feature F9)**:
   - In `backend/app/agents/quality_reviewer.py`, line 73 merely checked `if not opp.deadline:`, never comparing deadline strings against runtime UTC dates (`datetime.now(timezone.utc).date()`). Consequently, passed deadlines (such as 2025 deadlines in 2026) were approved and marked `deadline_verified = True`.
   - In `backend/app/services/scoring_service.py`, lines 91–96 awarded +10.0 points for `deadline_fit` to expired deadlines because `deadline_verified` was True.
5. **Simplistic Domain Substring Checks (Feature F10)**:
   - In `backend/app/agents/quality_reviewer.py`, lines 41–44 checked:
     ```python
     any(u.startswith("https://") and any(dom in u for dom in [".edu", ".ac.", ".ca", ".de", ".sg", ".gov", ".org", "vectorinstitute.ai", "daad.de", "a-star.edu.sg"]) for u in official_urls)
     ```
   - This naive substring search permitted commercial scrapers and phishing links (e.g., `https://fake-scholarships.org`, `https://visa-agent.ca`, `https://spamblog.com/about-canada.html`) because `.org`, `.ca`, or `.de` appeared anywhere in the URL string.

---

### 1.2 Implemented Changes Across Exclusive Write Scope

1. **`backend/app/security/sanitizer.py` (Feature F10)**:
   - Implemented `is_official_domain(url: str) -> bool`.
   - Parses URLs via `urlparse(url)` to extract canonical `hostname`.
   - Blocks raw IP addresses and unparsed schemes.
   - Validates against authoritative educational and governmental TLDs: `.edu`, `.gov`, `.mil`.
   - Validates against authentic second-level academic domains: `.ac.uk`, `.ac.jp`, `.ac.in`, `.ac.nz`, `.ac.za`, `.ac.kr`, `.ac.at`, `.edu.sg`, `.edu.au`, `.edu.cn`, `.edu.hk`, `.gc.ca`, etc.
   - Validates against `APPROVED_OFFICIAL_REGISTRY` covering recognized institutions and scholarship providers (e.g., `utoronto.ca`, `ubc.ca`, `tum.de`, `daad.de`, `vectorinstitute.ai`, `a-star.edu.sg`, `ox.ac.uk`, `mitacs.ca`, etc.) including their subdomains (e.g., `web.cs.toronto.edu`, `www.tum.de`).
   - Rejects commercial scrapers (`scholarship-tips-blog.com`, `free-student-aid-fast.biz`, `random-medium-post.io`) and deceptive substring matches (`fake-agent.ca`, `scamsite.org`).

2. **`backend/app/agents/quality_reviewer.py` (Features F9, F10, F8)**:
   - Check 1: Replaced naive substring matching with `is_safe_url(u) and is_official_domain(u)`. Flaggable secondary sources set `evidence_quality = "SECONDARY"`, `reviewer_status = "FLAGGED"`, and trigger re-research.
   - Check 3: Implemented runtime deadline verification against `datetime.now(timezone.utc).date()`.
     - Flagged passed dates as `deadline_status = "EXPIRED"`, set `deadline_verified = False`, set `reviewer_status = "FLAGGED"`, and logged `REVIEWER_FLAGGED` event.
     - Distinguished `ROLLING` intakes (`deadline_status = "ROLLING"`, `deadline_verified = True`) and `UNKNOWN` unannounced intakes (`deadline_status = "UNKNOWN"`, `deadline_verified = False`).
   - Check 4: Enforced mandatory criteria check; flagged any candidate with `status == "DOES_NOT_MEET"` on mandatory admission criteria.

3. **`backend/app/services/scoring_service.py` (Features F9, F8)**:
   - Check 0: Mandatory admission criteria checks enforce that any mandatory admission failure flags `has_mandatory_failure = True`, zeroing `academic_fit = 0.0` and setting `is_eligible_for_shortlist = False`.
   - Dimension 4: Compares deadlines against runtime UTC date (`datetime.now(timezone.utc).date()`).
     - Expired deadlines (`deadline_status == "EXPIRED"`) receive `deadline_score = 0.0` and set `is_eligible_for_shortlist = False`.
     - Verified active deadlines receive full +10.0 points.
     - Rolling deadlines receive active verified readiness (+10.0 if verified, +8.0 if unverified).
     - Unknown/unannounced deadlines receive baseline (+2.0).

4. **`backend/app/agents/research_eligibility.py` (Features F6, F7, F8, F9)**:
   - Implemented `extract_numeric_cgpa_cutoff(text: str)` and `extract_language_cutoff(text: str, test_type: str)`.
   - Implemented `evaluate_single_criterion(criterion_dict, profile, is_admission)`:
     - Directly compares student CGPA, scale, and institution against extracted program cutoff (no generic country-level heuristics).
     - Directly compares student IELTS/TOEFL scores against program thresholds.
     - Planned/unsubmitted language tests are explicitly marked `UNRESOLVED` with uncertainty notes and actionable gaps.
     - Curricular/doctoral prerequisites check student degree level (e.g. PhD requiring Master's rejects Bachelor's degree).
     - Purged synthetic template strings (`satisfies German`, `meets B+`, `from Indian institution meets`). Authentic excerpts are preserved verbatim or set to `None`.
   - Distinctly separated `raw_adm_reqs` from `raw_sch_reqs`, applying mandatory admission failure checks before ranking.
   - Evaluates deadline status at extraction time and sets `opp.deadline_status`.

5. **`backend/tests/test_m2_eligibility.py`**:
   - Created comprehensive 18-test suite covering:
     - F6: Program-specific criteria matching for diverse student personas (Rahul Sharma, Maria Santos), cross-program evaluation in the same country, language cutoffs, and doctoral prerequisites.
     - F7: Verbatim quote preservation, synthetic quote purging, planned language test UNRESOLVED classification with actionable gaps, and ambiguous criteria handling.
     - F8: Distinct admission and scholarship models, mandatory admission failure disqualification before ranking, and passed admission with unresolved scholarship remaining eligible.
     - F9: Quality Reviewer flagging expired deadlines, Scoring Service zeroing deadline score for expired deadlines, rolling intake recognition, unknown deadline baseline score, and active future deadline maximum readiness score.
     - F10: `is_official_domain` authoritative TLDs, approved registry hosts and subdomains, rejection of commercial blogs/scrapers/substring exploits, and Quality Reviewer flagging secondary domains.

6. **`backend/tests/test_scoring.py`**:
   - Updated legacy fixture date in `test_scoring_weights_and_dimensions` from `"2025-12-01"` to active `"2026-12-01"`, matching the canonical fixture updates from Worker M1.

---

## 2. Logic Chain

1. **Elimination of Country-Level Assumptions (F6)**:
   - *Observation*: Previously, students were evaluated using static country-level rules (e.g. all German programs requiring 7.5, all Canadian programs requiring 8.0).
   - *Reasoning*: Universities within the same country have distinct entry thresholds (e.g. Waterloo CS requires 8.0 and IELTS 7.5; Toronto Applied Computing requires 8.0; Calgary requires 7.5).
   - *Implementation*: `evaluate_single_criterion` parses specific numeric cutoffs and qualitative descriptors directly from the program's published requirement text and compares the student's actual CGPA and language scores against those program-specific values.
2. **Evidence Integrity & Verbatim Excerpts (F7)**:
   - *Observation*: Excerpts were previously generated using Python f-strings rather than extracting authentic text from web pages.
   - *Reasoning*: Synthesizing quotes presents artificial assertions as university policy, violating grounding integrity.
   - *Implementation*: `evaluate_single_criterion` only retains excerpts when provided directly from retrieved page content, purging any synthesized summary strings. Requirements with missing data (e.g. planned IELTS) are explicitly classified as `UNRESOLVED` with actionable gaps.
3. **Admission vs Scholarship Separation (F8)**:
   - *Observation*: Admission requirements and funding criteria were previously conflated.
   - *Reasoning*: University admission is a prerequisite for scholarship eligibility. Students failing mandatory admission criteria cannot be admitted, regardless of funding availability.
   - *Implementation*: Mandatory admission criteria are evaluated independently. If any mandatory admission criterion fails (`DOES_NOT_MEET`), the candidate is disqualified (`academic_fit = 0.0`, `is_eligible_for_shortlist = False`). Candidates with passed admission but unverified scholarship criteria remain eligible as `POTENTIAL_MATCH`.
4. **Runtime Deadline Evaluation (F9)**:
   - *Observation*: In 2026, 2025 deadlines are historical and closed. Quality Reviewer previously marked them approved and Scoring awarded +10.0 points.
   - *Reasoning*: Recommending expired scholarship deadlines misleads students into applying for closed intake cycles.
   - *Implementation*: Deadlines are parsed and compared against `datetime.now(timezone.utc).date()`. Dates in the past are marked `EXPIRED`, given `0.0` points for `deadline_fit`, flagged by Quality Reviewer, and excluded from active shortlists. Rolling intakes are explicitly recognized as `ROLLING` and receive active readiness scores.
5. **Robust Hostname Verification (F10)**:
   - *Observation*: Checking `any(dom in url for dom in [".edu", ".ca", ".org"])` permitted commercial blogs and scam sites containing `.org` or `.ca`.
   - *Reasoning*: Substring matching does not inspect URI authority components.
   - *Implementation*: `is_official_domain` extracts the parsed hostname and verifies it against authoritative educational TLDs (`.edu`, `.gov`, `.mil`), recognized academic second-level suffixes (`.ac.*`, `.edu.*`, `.gc.ca`), and an approved institutional registry (`APPROVED_OFFICIAL_REGISTRY`), strictly rejecting commercial blog domains and substring exploits.

---

## 3. Caveats

1. **Unmocked E2E Tests in `tests/e2e/`**:
   - `test_xf5_full_langgraph_workflow_execution` and `test_scenario_1` through `test_scenario_4` in `tests/e2e/` invoke live Gemini discovery without credentials or mocks. As documented by Worker M1 and Survey 1, these tests depend on Milestone M3/M6 test harness mocking.
2. **Dynamic Webpage Language Variations**:
   - While `extract_numeric_cgpa_cutoff` and `extract_language_cutoff` handle standard academic formats (X/10, X/4, percentages, IELTS, TOEFL), unusual qualitative criteria without documented conversion tables appropriately fall back to `UNRESOLVED` with an actionable gap directing the applicant to admissions.

---

## 4. Conclusion

Milestone M2 (Strict Eligibility & Domain/Deadline Verification) is **100% complete**:
- **F6**: Program-specific criteria matching is implemented; country-wide heuristics are eliminated.
- **F7**: Verbatim quotes are enforced; synthesized template quotes are purged; unverified criteria and pending tests are classified as `UNRESOLVED` with actionable gaps.
- **F8**: University admission requirements are distinctly separated from scholarship criteria; mandatory admission failure hard-disqualifies candidates before ranking.
- **F9**: Deadlines are verified against runtime UTC date (`datetime.now(timezone.utc).date()`); expired deadlines are flagged as `EXPIRED` with zero readiness score; rolling intakes are recognized.
- **F10**: Naive substring domain matching is replaced with parsed hostname verification against authoritative TLDs, academic suffixes, and verified official institutional registries.
- **Tests**: All 18 tests in `backend/tests/test_m2_eligibility.py`, all 5 tests in `tests/e2e/test_tier1_feature_coverage.py -k "f6 or f7 or f8 or f9 or f10"`, all 14 tests in `tests/test_m1_grounding.py`, and all 98 backend unit tests pass cleanly with **zero regressions**.

---

## 5. Verification Method

### 5.1 Verification Commands & Results

1. **Verify M2 Eligibility Test Suite (18 passed)**:
   ```powershell
   cd backend
   pytest tests/test_m2_eligibility.py -v
   ```
   *Result*: `============================= 18 passed in 2.75s ==============================`

2. **Verify Tier 1 Feature Coverage F6–F10 (5 passed)**:
   ```powershell
   cd backend
   pytest tests/e2e/test_tier1_feature_coverage.py -k "f6 or f7 or f8 or f9 or f10" -v
   ```
   *Result*: `======================= 5 passed, 5 deselected in 0.05s =======================`

3. **Verify M1 Grounding Regression Suite (14 passed)**:
   ```powershell
   cd backend
   pytest tests/test_m1_grounding.py -v
   ```
   *Result*: `============================= 14 passed in 5.33s ==============================`

4. **Verify Combined Test Suite (98 passed, zero regressions)**:
   ```powershell
   cd backend
   pytest tests/test_m1_grounding.py tests/test_m2_eligibility.py tests/test_scoring.py tests/test_eligibility.py tests/test_graph.py tests/test_api.py tests/test_documents.py tests/test_github.py tests/test_profile.py tests/e2e/test_tier1_feature_coverage.py tests/e2e/test_tier2_boundary_corner.py -v
   ```
   *Result*: `============================= 98 passed in 5.25s ==============================`

### 5.2 Invalidation Conditions
This milestone implementation would be invalidated if:
1. Academic eligibility reverts to generic country-level CGPA rules (`if country == "Canada"`).
2. Synthetic f-string quotes (`Student's 8.2 satisfies German...`) are reintroduced into `EvidenceRecord.evidence_excerpt`.
3. Expired deadlines are awarded positive readiness score or presented as active.
4. Commercial blogs or scrapers (`scholarship-tips-blog.com`, `fake-agent.ca`) pass `is_official_domain`.
5. Candidates failing mandatory admission criteria are shortlisted or ranked for scholarships.
