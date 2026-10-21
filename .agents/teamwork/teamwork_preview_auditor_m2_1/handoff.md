# Forensic Audit Report & Handoff: Milestone M2 (Features F6–F10)

**Auditor Agent**: Forensic Auditor M2.1 (`teamwork_preview_auditor_m2_1`)  
**Parent Orchestrator ID**: `6828b193-f5c1-4991-90e8-8c39694edfd6`  
**Target Work Product**: Milestone M2 (Features F6 through F10) Defect Remediation & Implementation  
**Integrity Mode**: `development` (per `ORIGINAL_REQUEST.md` line 8)  
**Profile**: General Project  
**Date**: 2026-10-20T22:53:00Z  
**Verdict**: **`CLEAN`**

---

## Forensic Audit Summary

| Check | Focus Area | Status | Key Evidence |
|---|---|:---:|---|
| **Check 1** | Genuine Implementation & Zero Cheating | **PASS** | Zero occurrences of `REAL_OPPORTUNITIES_BASE` in `backend/app`; zero hardcoded test outputs or dummy facades. |
| **Check 2** | Criteria Evaluation Honesty (`research_eligibility.py`) | **PASS** | Genuine regex extraction of CGPA (10.0 and 4.0 scales) and language scores (IELTS/TOEFL); 4.0 grading scale normalized to 10.0; pending tests marked `UNRESOLVED` with actionable gaps. |
| **Check 3** | Dynamic Runtime Deadline Evaluation (`scoring_service.py`) | **PASS** | Dynamic elapsed date comparison against `datetime.now(timezone.utc).date()`; expired deadlines strictly zeroed (`deadline_fit = 0.0`) and excluded from shortlist; rolling deadlines awarded full score. |
| **Check 4** | Official Domain Security & Anti-Spoofing (`sanitizer.py`) | **PASS** | Parsed hostname verification with ccTLD-anchored regex; commercial blogs, scrapers, and subdomain injection attacks (`scholarship.ac.fake.com`, `evil.edu.attacker.org`) strictly rejected. |
| **Check 5** | Data Model Contract & Serialization (`opportunity.py`) | **PASS** | `deadline_status: str = "UNKNOWN"` explicitly declared on `Opportunity` model; serializes cleanly in `opp.model_dump()` and `opp.model_dump_json()`. |
| **Check 6** | Empirical Test Suite Verification | **PASS** | 100% pass across all 4 suites: 22 passed in `test_m2_eligibility.py`, 17 passed in `test_m1_challenger_stress.py`, 10 passed in `test_tier1_feature_coverage.py`, 25 passed in regression suite. |

---

## 1. Observation

### 1.1 Empirical Observations of Production Code

1. **`backend/app/models/opportunity.py` (Line 39)**:
   - Verbatim declaration:
     ```python
     deadline_status: str = "UNKNOWN" # "ACTIVE", "EXPIRED", "ROLLING", "UNKNOWN"
     ```
   - Confirmed `deadline_status` is a first-class Pydantic model field, preventing serialization drop.
   - Separate list fields for admission and scholarship criteria:
     ```python
     admission_requirements: List[EligibilityCriterion] = Field(default_factory=list)
     scholarship_requirements: List[EligibilityCriterion] = Field(default_factory=list)
     ```

2. **`backend/app/security/sanitizer.py` (Lines 150–190)**:
   - Hostname is parsed with `urllib.parse.urlparse`, checked against SSRF and private IP ranges via `is_safe_url`.
   - Subdomain and exact matches checked against `APPROVED_OFFICIAL_REGISTRY`.
   - TLD suffixes checked against `OFFICIAL_TLD_SUFFIXES` (`.edu`, `.gov`, `.mil`).
   - Academic second-level ccTLD match is strictly anchored:
     ```python
     m = re.search(r'(?:\.|\b)(?:ac|edu|gov|gc)\.([a-z]{2,3})$', hostname)
     if m:
         tld = m.group(1).lower()
         if tld not in ("com", "org", "net", "biz", "info", "xyz", "io", "co"):
             return True
     ```
   - Subdomain spoofing exploits (`scholarship.ac.fake.com`, `evil.edu.attacker.org`, `attacker.gov.scam.net`, `phishing.ac.com`) terminate at commercial TLDs (`com`, `org`, `net`) and evaluate strictly to `False`.

3. **`backend/app/services/scoring_service.py` (Lines 24–65 & 131–174)**:
   - Admission vs scholarship decoupling:
     ```python
     for ev in opportunity.evidence_records:
         if ev.status == "DOES_NOT_MEET":
             is_scholarship = (
                 "scholarship" in (ev.criterion_name or "").lower()
                 or (ev.source_title and "scholarship" in ev.source_title.lower())
                 or any((sch.requirement_text in ev.stated_requirement or ev.stated_requirement in sch.requirement_text)
                        for sch in opportunity.scholarship_requirements)
             )
             if is_scholarship:
                 continue
     ```
     Failing competitive scholarship criteria does NOT trigger `has_mandatory_failure = True`.
   - Dynamic runtime deadline evaluation:
     ```python
     now_utc = as_of_date or datetime.now(timezone.utc).date()
     ```
     Parsed against `datetime.strptime(d_str, "%Y-%m-%d").date()`.
     If `parsed_d < now_utc`, sets `deadline_status = "EXPIRED"`, `deadline_score = 0.0`, and `is_eligible = not has_mandatory_failure and deadline_status != "EXPIRED"`.

4. **`backend/app/agents/research_eligibility.py` (Lines 15–202 & 458–572)**:
   - `extract_numeric_cgpa_cutoff`: parses X/10, X/4, qualitative descriptors (`first class with distinction` -> 8.0, `second upper` -> 7.5, `b average` -> 7.0).
   - `extract_language_cutoff`: parses IELTS (4.0–9.0) and TOEFL (50–120).
   - `evaluate_single_criterion`:
     - Normalizes 4.0 scale CGPA: `effective_student_cgpa = (student_cgpa / 4.0) * 10.0`.
     - Compares student CGPA against extracted cutoff without arbitrary country heuristics.
     - Planned language tests are classified as `UNRESOLVED` with explicit actionable gaps.
     - Synthetic excerpt templates are purged.
   - Candidate loop initializes tracking variables (`evidence_records`, `actionable_gaps`, `eligibility_reasons`, `admission_evidence_records`, `scholarship_evidence_records`) at the loop header, completely eliminating the previously reported `NameError`.

5. **`backend/tests/e2e/test_tier1_feature_coverage.py` (Line 15 & 280–300)**:
   - Imports `is_official_domain` directly from `app.security.sanitizer`.
   - Tests authoritative domains and anti-spoofing rejection without local reimplementations.

---

### 1.2 Raw Empirical Test Execution Outputs

#### Suite 1: `pytest tests/test_m2_eligibility.py -v` (22 passed)
```
tests/test_m2_eligibility.py::test_f6_extract_numeric_cgpa_cutoff_various_formats PASSED [  4%]
tests/test_m2_eligibility.py::test_f6_program_specific_criteria_matching_rahul_meets_and_fails PASSED [  9%]
tests/test_m2_eligibility.py::test_f6_no_generic_country_assumptions_two_canadian_programs PASSED [ 13%]
tests/test_m2_eligibility.py::test_f6_language_criteria_matching_specific_cutoffs PASSED [ 18%]
tests/test_m2_eligibility.py::test_f6_degree_prerequisites_matching_phd_requires_masters PASSED [ 22%]
tests/test_m2_eligibility.py::test_f7_verbatim_quotes_preserved_and_synthetic_quotes_purged PASSED [ 27%]
tests/test_m2_eligibility.py::test_f7_pending_language_test_marked_unresolved_with_actionable_gap PASSED [ 31%]
tests/test_m2_eligibility.py::test_f7_ambiguous_criteria_marked_unresolved PASSED [ 36%]
tests/test_m2_eligibility.py::test_f8_distinct_admission_and_scholarship_data_models PASSED [ 40%]
tests/test_m2_eligibility.py::test_f8_mandatory_admission_failure_disqualifies_before_ranking PASSED [ 45%]
tests/test_m2_eligibility.py::test_f8_admission_passed_with_unresolved_scholarship_remains_potential_match PASSED [ 50%]
tests/test_m2_eligibility.py::test_f9_quality_reviewer_flags_expired_deadlines PASSED [ 54%]
tests/test_m2_eligibility.py::test_f9_scoring_service_zero_readiness_score_for_expired_deadline PASSED [ 59%]
tests/test_m2_eligibility.py::test_f9_rolling_and_unknown_deadlines_handled_correctly PASSED [ 63%]
tests/test_m2_eligibility.py::test_f9_active_future_deadline_awarded_maximum_score PASSED [ 68%]
tests/test_m2_eligibility.py::test_f10_is_official_domain_authoritative_tlds_and_registries PASSED [ 72%]
tests/test_m2_eligibility.py::test_f10_is_official_domain_rejects_commercial_blogs_and_substring_exploits PASSED [ 77%]
tests/test_m2_eligibility.py::test_f10_quality_reviewer_flags_secondary_domain_and_triggers_reresearch PASSED [ 81%]
tests/test_m2_eligibility.py::test_f6_grading_scale_4_point_scale_normalized_to_10 PASSED [ 86%]
tests/test_m2_eligibility.py::test_f8_failing_optional_scholarship_remains_eligible_for_admission_shortlist PASSED [ 90%]
tests/test_m2_eligibility.py::test_f9_opportunity_model_dump_serializes_deadline_status PASSED [ 95%]
tests/test_m2_eligibility.py::test_discovery_and_audit_candidate_loop_integration_no_name_error PASSED [100%]
============================= 22 passed in 3.36s ==============================
```

#### Suite 2: `pytest tests/test_m1_challenger_stress.py -v` (17 passed)
```
tests/test_m1_challenger_stress.py::test_empirical_url_context_paywall_status_service_level PASSED [  5%]
tests/test_m1_challenger_stress.py::test_empirical_url_context_error_status_service_level PASSED [ 11%]
tests/test_m1_challenger_stress.py::test_empirical_url_context_unsafe_status_service_level PASSED [ 17%]
tests/test_m1_challenger_stress.py::test_empirical_url_context_mixed_statuses_service_level PASSED [ 23%]
tests/test_m1_challenger_stress.py::test_empirical_research_agent_paywall_graceful_degradation PASSED [ 29%]
tests/test_m1_challenger_stress.py::test_empirical_research_agent_network_failure_does_not_crash PASSED [ 35%]
tests/test_m1_challenger_stress.py::test_empirical_is_available_false_raises_configuration_error PASSED [ 41%]
tests/test_m1_challenger_stress.py::test_empirical_workflow_bubbles_configuration_error PASSED [ 47%]
tests/test_m1_challenger_stress.py::test_empirical_zero_candidate_discovery_returns_clean_empty_list PASSED [ 52%]
tests/test_m1_challenger_stress.py::test_empirical_zero_candidate_full_workflow_execution PASSED [ 58%]
tests/test_m1_challenger_stress.py::test_empirical_unsafe_and_ssrf_urls_rejected_before_extraction PASSED [ 64%]
tests/test_m1_challenger_stress.py::test_empirical_malformed_json_response_handling PASSED [ 70%]
tests/test_m1_challenger_stress.py::test_empirical_ast_inspection_no_hardcoded_lists_in_research_eligibility PASSED [ 76%]
tests/test_m1_challenger_stress.py::test_empirical_url_context_empty_urls_list PASSED [ 82%]
tests/test_m1_challenger_stress.py::test_empirical_url_context_unspecified_enum_defaults_to_unverified PASSED [ 88%]
tests/test_m1_challenger_stress.py::test_empirical_duplicate_url_deduplication_in_discovery PASSED [ 94%]
tests/test_m1_challenger_stress.py::test_empirical_candidate_bounding_to_max_configured PASSED [100%]
============================= 17 passed in 11.21s =============================
```

#### Suite 3: `pytest tests/e2e/test_tier1_feature_coverage.py -v` (10 passed)
```
tests/e2e/test_tier1_feature_coverage.py::test_f1_fixtures_are_isolated_and_conform_to_schema PASSED [ 10%]
tests/e2e/test_tier1_feature_coverage.py::test_f2_search_grounding_discovery_contract PASSED [ 20%]
tests/e2e/test_tier1_feature_coverage.py::test_f3_google_genai_sdk_url_context_tool_contract PASSED [ 30%]
tests/e2e/test_tier1_feature_coverage.py::test_f4_retrieval_metadata_handling_distinguishes_status PASSED [ 40%]
tests/e2e/test_tier1_feature_coverage.py::test_f5_missing_api_key_returns_explicit_error_without_fallback PASSED [ 50%]
tests/e2e/test_tier1_feature_coverage.py::test_f6_program_specific_criteria_matching PASSED [ 60%]
tests/e2e/test_tier1_feature_coverage.py::test_f7_verbatim_quotes_and_unresolved_classification PASSED [ 70%]
tests/e2e/test_tier1_feature_coverage.py::test_f8_admission_vs_scholarship_distinction PASSED [ 80%]
tests/e2e/test_tier1_feature_coverage.py::test_f9_runtime_deadline_verification_against_utc_date PASSED [ 90%]
tests/e2e/test_tier1_feature_coverage.py::test_f10_robust_official_domain_verification PASSED [100%]
============================= 10 passed in 1.26s ==============================
```

#### Suite 4: Regression Suite (25 passed)
```
tests/test_challenger_m1_stress.py::test_adversarial_ssrf_injection_filtered_by_discovery_pipeline PASSED [  4%]
tests/test_challenger_m1_stress.py::test_aggressive_url_deduplication_and_normalization PASSED [  8%]
tests/test_challenger_m1_stress.py::test_graceful_degradation_across_all_retrieval_statuses[URL_RETRIEVAL_STATUS_SUCCESS-True-OFFICIAL] PASSED [ 12%]
tests/test_challenger_m1_stress.py::test_graceful_degradation_across_all_retrieval_statuses[URL_RETRIEVAL_STATUS_PAYWALL-False-UNVERIFIED] PASSED [ 16%]
tests/test_challenger_m1_stress.py::test_graceful_degradation_across_all_retrieval_statuses[URL_RETRIEVAL_STATUS_UNSAFE-False-UNVERIFIED] PASSED [ 20%]
tests/test_challenger_m1_stress.py::test_graceful_degradation_across_all_retrieval_statuses[URL_RETRIEVAL_STATUS_ERROR-False-UNVERIFIED] PASSED [ 24%]
tests/test_challenger_m1_stress.py::test_missing_credentials_never_returns_canned_records PASSED [ 28%]
tests/test_challenger_m1_stress.py::test_static_ast_zero_real_opportunities_base_in_backend_app PASSED [ 32%]
tests/test_scoring.py::test_scoring_weights_and_dimensions PASSED        [ 36%]
tests/test_scoring.py::test_hard_disqualifier_excludes_from_shortlist PASSED [ 40%]
tests/test_scoring.py::test_potential_match_partial_score PASSED         [ 44%]
tests/test_m1_grounding.py::test_missing_api_key_ensure_available_raises_exception PASSED [ 48%]
tests/test_m1_grounding.py::test_search_grounded_discovery_missing_key_error PASSED [ 52%]
tests/test_m1_grounding.py::test_research_agent_missing_key_raises_error_without_dummy_fallback PASSED [ 56%]
tests/test_m1_grounding.py::test_gemini_configuration_error_returns_503_http_response PASSED [ 60%]
tests/test_m1_grounding.py::test_url_context_tool_structure PASSED       [ 64%]
tests/test_m1_grounding.py::test_google_search_grounding_tool_structure PASSED [ 68%]
tests/test_m1_grounding.py::test_analyze_url_and_extract_criteria_configures_url_context_tool PASSED [ 72%]
tests/test_m1_grounding.py::test_retrieval_status_enums_exist PASSED     [ 76%]
tests/test_m1_grounding.py::test_retrieval_status_policy_paywall_marks_unresolved PASSED [ 80%]
tests/test_m1_grounding.py::test_retrieval_status_policy_unsafe_marks_unresolved PASSED [ 84%]
tests/test_m1_grounding.py::test_retrieval_status_policy_error_marks_unresolved PASSED [ 88%]
tests/test_m1_grounding.py::test_partial_url_retrieval_failure_preservation PASSED [ 92%]
tests/test_m1_grounding.py::test_zero_hardcoded_opportunities_in_live_research_code PASSED [ 96%]
tests/test_m1_grounding.py::test_isolated_fixtures_conform_to_schema PASSED [100%]
============================= 25 passed in 7.16s ==============================
```

#### Independent Forensic Stress Test Execution Output
```
--- CHECK 1: DEADLINE STATUS SERIALIZATION ---
PASS: deadline_status field properly declared, typed, and serialized.
--- CHECK 2: OFFICIAL DOMAIN SECURITY AND ANCHORING ---
PASS: All malicious domains rejected and all authentic institutions verified.
--- CHECK 3: DYNAMIC RUNTIME DEADLINE CALCULATION AND SCORING ---
PASS: Runtime deadline calculations dynamically determine ACTIVE, EXPIRED, ROLLING, UNKNOWN.
--- CHECK 4: NUMERIC CGPA AND LANGUAGE EXTRACTION HONESTY ---
PASS: CGPA and Language extraction and grading scale normalization operate honestly.
--- CHECK 5: ADMISSION VS SCHOLARSHIP DECOUPLING ---
PASS: Admission vs Scholarship decoupling verified.
ALL 5 FORENSIC STRESS CHECKS PASSED EMPIRICALLY!
```

---

## 2. Logic Chain

1. **Verification of Non-Circumvention (Authentic Execution)**:
   - *Observation*: Static AST scans and grep searches for `REAL_OPPORTUNITIES_BASE` and hardcoded outputs in `backend/app/` produced 0 occurrences.
   - *Logic*: Opportunities and criteria evaluation are dynamically constructed from input parameters, search grounding results, and extracted evidence records. No pre-cooked results are delivered.
   - *Conclusion*: Satisfies Requirement R1 and Milestone M1/M2 non-circumvention mandate.

2. **Resolution of Reviewer Defect 1 (NameError Crashes)**:
   - *Observation*: `test_m1_challenger_stress.py` previously failed on 10 tests due to `NameError: name 'actionable_gaps' is not defined`.
   - *Logic*: Inspecting `research_eligibility.py:458–463` shows explicit initialization of `actionable_gaps: List[str] = []` and `eligibility_reasons: List[str] = []` before entering the criteria evaluation branches.
   - *Conclusion*: 17/17 tests in `test_m1_challenger_stress.py` execute cleanly to completion.

3. **Resolution of Reviewer Defect 2 (Admission vs Scholarship Conflation)**:
   - *Observation*: `scoring_service.py:36–47` explicitly detects scholarship evidence records and skips them during `has_mandatory_failure` evaluation.
   - *Logic*: Admission prerequisites are compulsory university conditions; scholarships are competitive awards. Disqualifying admission shortlist eligibility for an applicant meeting admission standards because of a competitive fellowship failure violated domain logic.
   - *Conclusion*: A student meeting admission requirements but failing scholarship criteria retains positive academic score (`>= 25.0`) and remains `is_eligible_for_shortlist = True`.

4. **Resolution of Reviewer Defect 3 (API Contract Schema Conformance)**:
   - *Observation*: `Opportunity` model in `opportunity.py:39` defines `deadline_status: str = "UNKNOWN"`.
   - *Logic*: Pydantic V2 drops attributes set on instances if they are not declared in `model_fields`. Declaring it on the model class guarantees retention through `model_dump()` and JSON serialization.
   - *Conclusion*: `opp.model_dump()` outputs `"deadline_status"` with values `"ACTIVE"`, `"EXPIRED"`, `"ROLLING"`, or `"UNKNOWN"`.

5. **Resolution of Reviewer Defect 4 (Subdomain Spoofing Vulnerability)**:
   - *Observation*: `is_official_domain` in `sanitizer.py:182` anchors academic ccTLDs to the end of the hostname preceding a 2-3 letter ccTLD (`r'(?:\.|\b)(?:ac|edu|gov|gc)\.([a-z]{2,3})$'`) and excludes commercial/untrusted TLDs (`com`, `org`, `net`, `biz`, `info`, `xyz`, `io`, `co`).
   - *Logic*: Attackers attempting to spoof `.ac.` or `.edu.` in commercial subdomains (e.g. `scholarship.ac.fake.com`, `evil.edu.attacker.org`) terminate in excluded generic TLDs and are rejected. Authentic institutions (`cs.stanford.edu`, `ox.ac.uk`, `nus.edu.sg`, `canada.ca`) match approved registry, TLD suffixes, or valid ccTLD structures.
   - *Conclusion*: Subdomain spoofing vulnerability is eliminated.

6. **Resolution of Reviewer Defect 5 (Grading Scale Normalization)**:
   - *Observation*: `research_eligibility.py:119–122` normalizes 4.0 scale CGPA via `(student_cgpa / 4.0) * 10.0`.
   - *Logic*: Without normalization, a 3.8/4.0 GPA (top-tier student) was directly compared against 8.0/10.0 cutoffs and falsely failed (`3.8 >= 8.0` evaluated to `False`).
   - *Conclusion*: 4.0-scale students are evaluated fairly and accurately.

---

## 3. Caveats

1. **No Caveats on Implementation Integrity**:
   - Zero hardcoding, facades, or synthetic cheating exist in live operational code.
2. **Environment & Live API Constraints**:
   - Unit and contract tests utilize mock responses for Google GenAI SDK calls because live production Gemini API keys are omitted in offline CI environments (as anticipated in `PROJECT.md` line 80 and line 123). Live smoke testing is designated for Milestone M6 (F26).

---

## 4. Conclusion

**Verdict: `CLEAN`**

Milestone M2 (Features F6, F7, F8, F9, F10) demonstrates authentic, rigorous, and verified implementation. All 6 defects previously flagged by Reviewers M2.1 and M2.2 have been completely resolved and empirically validated across all relevant unit, contract, stress, and regression test suites.

Milestone M2 is officially cleared for progression to Milestone M3 (5-Agent Workflow & Fault Recovery).

---

## 5. Verification Method

To independently reproduce and verify this audit:

```powershell
# 1. Verify M2 unit and contract test suite
cd d:\Case_study_drive\TetraNoodle_AI_Hackathon\backend
pytest tests/test_m2_eligibility.py -v

# 2. Verify Challenger M1 stress suite (confirming zero NameErrors)
pytest tests/test_m1_challenger_stress.py -v

# 3. Verify Tier 1 feature coverage
pytest tests/e2e/test_tier1_feature_coverage.py -v

# 4. Verify regression test suites
pytest tests/test_challenger_m1_stress.py tests/test_scoring.py tests/test_m1_grounding.py -v

# 5. Execute independent adversarial stress checks
python -c @"
from app.security.sanitizer import is_official_domain
assert is_official_domain('https://scholarship.ac.fake.com') is False
assert is_official_domain('https://evil.edu.attacker.org') is False
assert is_official_domain('https://web.cs.toronto.edu/mscac') is True

from app.models.opportunity import Opportunity
opp = Opportunity(id='t', run_id='r', canonical_url='https://utoronto.ca', title='U', program_name='P', university='U', country='C')
opp.deadline_status = 'EXPIRED'
assert opp.model_dump()['deadline_status'] == 'EXPIRED'
print('INDEPENDENT VERIFICATION SUCCESSFUL')
"@
```

### Invalidation Conditions
This clean verdict would be invalidated if:
1. `pytest tests/test_m2_eligibility.py` or `pytest tests/test_m1_challenger_stress.py` produces any failure or uncaught `NameError`.
2. Any spoofed domain (e.g. `https://scholarship.ac.fake.com`) returns `True` from `is_official_domain`.
3. An expired application cycle is ever marked active or awarded deadline points.
4. An applicant meeting all mandatory admission requirements is disqualified from the shortlist due to an optional scholarship criterion.
