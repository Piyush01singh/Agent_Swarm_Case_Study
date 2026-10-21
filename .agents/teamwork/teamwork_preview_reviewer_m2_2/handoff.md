# Handoff Report: Review & Adversarial Stress-Test of Milestone M2

**Reviewer**: Reviewer M2.2 (`teamwork_preview_reviewer_m2_2`)  
**Target Agent Reviewed**: Worker M2 (`teamwork_preview_worker_m2`)  
**Milestone**: M2 (Strict Eligibility & Domain/Deadline Verification — Features F6 through F10)  
**Parent Orchestrator ID**: `6828b193-f5c1-4991-90e8-8c39694edfd6`  
**Date**: 2026-10-20T22:30:00Z  
**Explicit Verdict**: **`REQUEST_CHANGES`**

---

## 1. Observation

### 1.1 Test Command Executions & Results

1. **Requested Test Command 1: `pytest tests/test_m2_eligibility.py -v`**:
   - Command: `pytest tests/test_m2_eligibility.py -v` (Cwd: `backend`)
   - Output: `18 passed in 3.01s`
   - Direct Observation: All 18 isolated unit tests written by Worker M2 passed.

2. **Requested Test Command 2: `pytest tests/test_scoring.py -v`**:
   - Command: `pytest tests/test_scoring.py -v` (Cwd: `backend`)
   - Output: `3 passed in 0.14s`
   - Direct Observation: Tests `test_scoring_weights_and_dimensions`, `test_hard_disqualifier_excludes_from_shortlist`, and `test_potential_match_partial_score` passed cleanly.

3. **Requested Test Command 3: `pytest tests/test_eligibility.py -v`**:
   - Command: `pytest tests/test_eligibility.py -v` (Cwd: `backend`)
   - Output: `3 passed in 0.07s`
   - Direct Observation: Tests `test_url_normalization`, `test_safe_url_ssrf_protection`, and `test_evidence_record_integrity` passed cleanly.

4. **Tier 1 Feature Coverage: `pytest tests/e2e/test_tier1_feature_coverage.py -k "f6 or f7 or f8 or f9 or f10" -v`**:
   - Output: `5 passed, 5 deselected in 0.08s`
   - Direct Observation: Passing.

5. **Regression & Adversarial Harness Suite: `pytest tests/test_challenger_m1_stress.py tests/test_m1_challenger_stress.py -v`**:
   - Command: `pytest tests/test_challenger_m1_stress.py tests/test_m1_challenger_stress.py -v` (Cwd: `backend`)
   - Output: `10 failed, 15 passed in 9.08s`
   - Direct Observation: Failed with verbatim Python `NameError` exceptions inside `backend/app/agents/research_eligibility.py`:
     ```python
     E   NameError: name 'actionable_gaps' is not defined
     app\agents\research_eligibility.py:473: NameError
     ```
     and
     ```python
     E   NameError: name 'eligibility_reasons' is not defined
     app\agents\research_eligibility.py:533: NameError
     ```

---

### 1.2 Direct Code Observations & Evidence

#### Observation A: Uninitialized Variables in `ResearchEligibilityAgent.execute_discovery_and_audit`
In `backend/app/agents/research_eligibility.py`:
Lines 443–444 initialize only `evidence_records`:
```python
443: # Build authentic evidence records
444: evidence_records: List[EvidenceRecord] = []
```
`actionable_gaps: List[str] = []` and `eligibility_reasons: List[str] = []` are **never initialized** in this scope.
Subsequently:
- Line 473: `if eval_res["actionable_gap"] and eval_res["actionable_gap"] not in actionable_gaps:`
- Line 474: `actionable_gaps.append(eval_res["actionable_gap"])`
- Line 496: `if eval_res["actionable_gap"] and eval_res["actionable_gap"] not in actionable_gaps:`
- Line 497: `actionable_gaps.append(eval_res["actionable_gap"])`
- Line 525: `if "Does not meet mandatory program admission criteria." not in eligibility_reasons:`
- Line 526: `eligibility_reasons.append("Does not meet mandatory program admission criteria.")`
- Line 529: `if "Potential match; key criteria pending official document verification." not in eligibility_reasons:`
- Line 530: `eligibility_reasons.append("Potential match; key criteria pending official document verification.")`
- Line 533: `if "Meets published admission and scholarship criteria." not in eligibility_reasons:`
- Line 534: `eligibility_reasons.append("Meets published admission and scholarship criteria.")`
- Line 537: `actionable_gaps.append(f"Official portal at {cand_url} could not be retrieved ({retrieval_status}); verify requirements manually.")`
- Line 566: `actionable_gaps.append(f"Application deadline ({deadline}) has passed and is expired.")`
- Line 597: `eligibility_reasons=eligibility_reasons,`
- Line 598: `actionable_gaps=actionable_gaps,`

Whenever any candidate is evaluated (whether retrieval was successful or unsuccessful), execution reaches these lines and raises an uncaught `NameError`.

#### Observation B: Subdomain Exploitation in `sanitizer.py:is_official_domain`
In `backend/app/security/sanitizer.py`:
Lines 99–104 define:
```python
OFFICIAL_ACADEMIC_PARTS = (
    ".ac.",     # e.g. .ac.uk, .ac.jp, .ac.in, .ac.nz, .ac.za, .ac.kr, .ac.at, .ac.il, .ac.th
    ".edu.",    # e.g. .edu.sg, .edu.au, .edu.cn, .edu.hk, .edu.my, .edu.pk, .edu.tw, .edu.br
    ".gc.ca",   # Official Government of Canada
    ".gov.",    # e.g. .gov.uk, .gov.sg, .gov.au, .gov.in, .gov.ca
)
```
Lines 179–185 check:
```python
        # 3. Check official academic and government second-level domains
        for part in OFFICIAL_ACADEMIC_PARTS:
            if part in hostname:
                # Ensure the part acts as a domain component (not merely path or substring)
                # e.g., 'ox.ac.uk' has '.ac.' as a component, not 'mac.com'
                if hostname.endswith(part.rstrip(".")) or f"{part}" in hostname:
                    return True
```
Because `f"{part}" in hostname` is identical to the enclosing condition `part in hostname`, any domain containing `.ac.`, `.edu.`, `.gov.`, or `.gc.ca` anywhere in its hostname immediately returns `True`.
Verified in Python:
- `is_official_domain('https://scholarship.ac.fake.com')` -> `True`
- `is_official_domain('https://evil.edu.attacker.org')` -> `True`
- `is_official_domain('https://attacker.gov.scam.net')` -> `True`

#### Observation C: Missing `deadline_status` Field on Pydantic Model `Opportunity`
In `backend/app/models/opportunity.py`:
Lines 36–39 declare:
```python
    deadline: Optional[str] = None
    deadline_type: str = "Unknown" # "Fixed", "Rolling", "Priority", "Unknown"
    deadline_verified: bool = False
```
The field `deadline_status` is not declared.
In `backend/app/agents/quality_reviewer.py` (lines 101, 124), `backend/app/agents/research_eligibility.py` (line 603), and `backend/app/services/scoring_service.py` (line 127), the code uses:
```python
object.__setattr__(opp, "deadline_status", deadline_status)
```
Verified in Python:
```python
from app.models.opportunity import Opportunity
opp = Opportunity(id='t', run_id='r', canonical_url='https://utoronto.ca', title='U', program_name='P', university='U', country='C')
object.__setattr__(opp, 'deadline_status', 'EXPIRED')
print('deadline_status' in opp.model_dump()) # Prints: False
```
When serialized via Pydantic (`opp.model_dump()` or FastAPI endpoint `GET /api/research/{run_id}/opportunities`), `deadline_status` is omitted, violating the API Contract in `PROJECT.md` line 130.

---

## 2. Logic Chain

1. **Step 1: Test Command Verification**:
   - The three requested test suites (`test_m2_eligibility.py`, `test_scoring.py`, `test_eligibility.py`) pass cleanly in isolation.
   - However, `test_m2_eligibility.py` tests individual sub-functions (`evaluate_single_criterion`, `extract_numeric_cgpa_cutoff`, `extract_language_cutoff`, `QualityReviewerAgent.execute_audit`, `calculate_match_score`) in isolation with pre-constructed dictionaries and models.
   - It does not invoke `ResearchEligibilityAgent.execute_discovery_and_audit`.

2. **Step 2: Integration Failure Detection**:
   - When running the broader test harness (`test_challenger_m1_stress.py` and `test_m1_challenger_stress.py`), which invokes `ResearchEligibilityAgent.execute_discovery_and_audit`, 10 tests fail immediately with `NameError: name 'actionable_gaps' is not defined` and `NameError: name 'eligibility_reasons' is not defined`.
   - Inspection of `research_eligibility.py:443–600` confirms that neither `actionable_gaps` nor `eligibility_reasons` is initialized in the candidate loop, causing an unconditional crash on 100% of candidate evaluations during discovery.

3. **Step 3: Adversarial Vulnerability Analysis**:
   - Stress-testing `is_official_domain` reveals that while commercial blogs without `.ac.` or `.edu.` in the domain are rejected, an attacker or scammer can register any domain (e.g. `scam.com`) and configure subdomains `scholarship.ac.scam.com` or `portal.edu.scam.com`, completely bypassing domain validation because `f"{part}" in hostname` evaluates to `True`.

4. **Step 4: Contract Non-Conformance**:
   - `PROJECT.md` defines the backend-to-frontend contract including `deadline_status: "ACTIVE" | "EXPIRED" | "ROLLING" | "UNKNOWN"`.
   - Because `Opportunity` lacks `deadline_status: str = "UNKNOWN"`, dynamic monkey-patching via `object.__setattr__` does not survive Pydantic model serialization, stripping the field from API responses and database persistence.

5. **Step 5: Synthesizing Verdict**:
   - While features F6, F7, F8, and F9 logic functions are conceptually well-designed and pass unit tests, the discovery pipeline cannot execute without crashing (`NameError`), the domain security policy has a major subdomain spoofing loophole, and the API model drops `deadline_status`.
   - Therefore, the work product cannot be approved in its current state. The verdict is **`REQUEST_CHANGES`**.

---

## 3. Caveats

1. **Unit Test Quality**:
   - The unit tests written in `test_m2_eligibility.py` for F6 (program cutoffs), F7 (verbatim quotes), F8 (mandatory admission vs scholarship separation), and F9 (deadline checking in Quality Reviewer and Scoring) are thorough, rigorous, and well-structured.
2. **Mocking vs Live API**:
   - End-to-end tests requiring live Gemini API keys (`test_xf5_full_langgraph_workflow_execution`, `test_scenario_1` to `4`) remain unverified due to API key absence, as documented in M1/M2 caveats.
3. **No Intentional Malice / Integrity Violation**:
   - The issues detected are implementation bugs and security oversights (uninitialized variables, regex anchoring flaw, missing model attribute), not integrity violations or attempts to fabricate outputs.

---

## 4. Conclusion

Milestone M2 cannot be approved due to 1 Critical integration blocker and 2 Major defects:
1. **Critical**: Unconditional crash (`NameError: name 'actionable_gaps' is not defined`) in `ResearchEligibilityAgent.execute_discovery_and_audit` whenever candidate opportunities are evaluated.
2. **Major**: Subdomain spoofing loophole in `sanitizer.py:is_official_domain` (`evil.edu.attacker.org` and `scholarship.ac.fake.com` return `True`).
3. **Major**: Missing `deadline_status` field on Pydantic `Opportunity` model causing omission during serialization.

**Explicit Verdict**: **`REQUEST_CHANGES`**

---

## 5. Verification Method

### 5.1 Verification Commands

1. **Reproduce Critical NameError Crash**:
   ```powershell
   cd backend
   python -c "
   import asyncio
   from unittest.mock import AsyncMock, patch, PropertyMock
   from app.agents.research_eligibility import ResearchEligibilityAgent
   from app.models.profile import StudentProfile

   async def run():
       agent = ResearchEligibilityAgent()
       profile = StudentProfile(cgpa=8.2, target_countries=['Canada'])
       with patch('app.services.gemini_service.GeminiService.is_available', new_callable=PropertyMock, return_value=True), \
            patch('app.services.gemini_service.gemini_service.ensure_available'), \
            patch('app.services.gemini_service.gemini_service.search_grounded_discovery', new=AsyncMock(return_value={
                'success': True,
                'candidates': [{'canonical_url': 'https://utoronto.ca', 'title': 'UofT CS'}]
            })), \
            patch('app.services.gemini_service.gemini_service.analyze_url_and_extract_criteria', new=AsyncMock(return_value={
                'success': True,
                'is_retrieval_successful': True,
                'retrieval_status': 'URL_RETRIEVAL_STATUS_SUCCESS',
                'data': {
                    'program_name': 'MSc CS',
                    'university': 'University of Toronto',
                    'admission_requirements': [{'stated_requirement': 'Min 8.0 CGPA', 'criterion_type': 'ACADEMIC_GRADE'}]
                }
            })):
           await agent.execute_discovery_and_audit('run-1', profile)

   asyncio.run(run())
   "
   ```
   *Expected Output*: `NameError: name 'actionable_gaps' is not defined` at `app/agents/research_eligibility.py:473`.

2. **Reproduce Subdomain Bypass in `is_official_domain`**:
   ```powershell
   cd backend
   python -c "
   from app.security.sanitizer import is_official_domain
   print('scholarship.ac.fake.com:', is_official_domain('https://scholarship.ac.fake.com'))
   print('evil.edu.attacker.org:', is_official_domain('https://evil.edu.attacker.org'))
   "
   ```
   *Expected Output*: Both print `True` (should be `False`).

3. **Reproduce Missing `deadline_status` Serialization**:
   ```powershell
   cd backend
   python -c "
   from app.models.opportunity import Opportunity
   opp = Opportunity(id='t', run_id='r', canonical_url='https://utoronto.ca', title='U', program_name='P', university='U', country='C')
   object.__setattr__(opp, 'deadline_status', 'EXPIRED')
   print('deadline_status in model_dump():', 'deadline_status' in opp.model_dump())
   "
   ```
   *Expected Output*: `deadline_status in model_dump(): False` (should be `True`).

### 5.2 Invalidation Conditions
This `REQUEST_CHANGES` verdict will be satisfied and converted to `APPROVE` when:
1. `actionable_gaps: List[str] = []` and `eligibility_reasons: List[str] = []` are properly initialized in `backend/app/agents/research_eligibility.py` candidate loop, allowing `test_challenger_m1_stress.py` to pass without NameErrors.
2. `sanitizer.py:is_official_domain` anchors academic second-level domain suffixes to authoritative ccTLDs (e.g. `re.search(r'\.(?:ac|edu|gov|gc)\.[a-z]{2,3}$', hostname)`), rejecting arbitrary subdomains like `evil.edu.attacker.org`.
3. `Opportunity` model in `backend/app/models/opportunity.py` includes `deadline_status: str = "UNKNOWN"`, ensuring serialization in API responses.

---

## 6. Detailed Quality Review Report

### Review Summary
**Verdict**: **`REQUEST_CHANGES`**

### Findings

#### [Critical] Finding 1: Uninitialized `actionable_gaps` and `eligibility_reasons` in `ResearchEligibilityAgent`
- **What**: In `backend/app/agents/research_eligibility.py`, `actionable_gaps` and `eligibility_reasons` are referenced without initialization in the candidate loop of `execute_discovery_and_audit`.
- **Where**: `backend/app/agents/research_eligibility.py:444`, `473`, `525`, `533`, `566`, `597–598`.
- **Why**: Causes an unconditional `NameError` crash whenever any candidate page is extracted and evaluated, breaking discovery and failing 10 tests in the test suite.
- **Suggestion**: Add `actionable_gaps: List[str] = []` and `eligibility_reasons: List[str] = []` directly below line 444 (`evidence_records: List[EvidenceRecord] = []`).

#### [Major] Finding 2: Subdomain Bypass in `is_official_domain`
- **What**: `sanitizer.py:is_official_domain` permits any hostname containing `.ac.`, `.edu.`, `.gov.`, or `.gc.ca` anywhere in its domain name to pass as official.
- **Where**: `backend/app/security/sanitizer.py:179–185`.
- **Why**: Spammers and phishing operators can create arbitrary subdomains (e.g. `apply.edu.scamsite.com` or `grants.ac.phishing.org`) and bypass verification.
- **Suggestion**: Anchor academic ccTLD matching to the end of the hostname, e.g.:
  ```python
  if re.search(r'\.(?:ac|edu|gov|gc)\.[a-z]{2,3}$', hostname):
      return True
  ```

#### [Major] Finding 3: Missing `deadline_status` Field in `Opportunity` Model
- **What**: `deadline_status` is not declared on Pydantic `Opportunity` model.
- **Where**: `backend/app/models/opportunity.py:36–39`.
- **Why**: Using `object.__setattr__(opp, "deadline_status", ...)` causes the attribute to be discarded when serialized via `model_dump()` or returned by FastAPI endpoints, violating the API contract in `PROJECT.md`.
- **Suggestion**: Add `deadline_status: str = "UNKNOWN"` to the `Opportunity` class in `backend/app/models/opportunity.py`.

#### [Minor] Finding 4: Inline Redefinition of `is_official_domain` in Tier 1 Tests
- **What**: `tests/e2e/test_tier1_feature_coverage.py:291–301` defines its own local `is_official_domain` function instead of importing from `app.security.sanitizer`.
- **Where**: `backend/tests/e2e/test_tier1_feature_coverage.py:291`.
- **Why**: Reduces the value of Tier 1 tests by testing a local mock function rather than the production codebase.
- **Suggestion**: Import `from app.security.sanitizer import is_official_domain`.

### Verified Claims
- **F6 Program-Specific Criteria Matching**: Verified via `test_f6_extract_numeric_cgpa_cutoff_various_formats` and `test_f6_no_generic_country_assumptions_two_canadian_programs` -> **PASS**.
- **F7 Verbatim Quotes & UNRESOLVED**: Verified via `test_f7_verbatim_quotes_preserved_and_synthetic_quotes_purged` and `test_f7_pending_language_test_marked_unresolved_with_actionable_gap` -> **PASS**.
- **F8 Admission vs Scholarship Separation**: Verified via `test_f8_mandatory_admission_failure_disqualifies_before_ranking` -> **PASS**.
- **F9 Quality Reviewer Deadline Flagging**: Verified via `test_f9_quality_reviewer_flags_expired_deadlines` and boundary testing (today/tomorrow/yesterday) -> **PASS**.
- **F9 Scoring Disqualification & 0.0 Score**: Verified via `test_f9_scoring_service_zero_readiness_score_for_expired_deadline` -> **PASS**.
- **F9 Rolling & Unknown Deadlines**: Verified via `test_f9_rolling_and_unknown_deadlines_handled_correctly` -> **PASS**.
- **F10 Commercial Blog Rejection**: Verified via `test_f10_is_official_domain_rejects_commercial_blogs_and_substring_exploits` -> **PASS** (for base domains).

### Coverage Gaps
- Full integration discovery via `execute_discovery_and_audit` was not covered in `test_m2_eligibility.py`, masking the `NameError` regression. Risk: **HIGH**.

---

## 7. Adversarial Challenge Report

### Challenge Summary
**Overall Risk Assessment**: **HIGH**

### Challenges

#### [High] Challenge 1: Subdomain Injection in Academic Domain Policy
- **Assumption Challenged**: Checking if `".ac."` or `".edu."` is in `hostname` ensures the site is an official academic institution.
- **Attack Scenario**: Attacker registers `scam-scholarship.com` and configures DNS record `apply.edu.scam-scholarship.com`.
- **Blast Radius**: Quality Reviewer marks the scam URL as an official source (`evidence_quality = "OFFICIAL"`, `reviewer_status = "APPROVED"`), misleading students to apply on malicious sites.
- **Mitigation**: Require the academic segment to be in the penultimate position preceding a 2-3 letter ccTLD (`re.search(r'\.(?:ac|edu|gov|gc)\.[a-z]{2,3}$', hostname)`).

#### [High] Challenge 2: Discovery Pipeline Crash under Valid Retrieval
- **Assumption Challenged**: Newly refactored `research_eligibility.py` executes cleanly during discovery.
- **Attack Scenario**: Live or mocked Gemini discovery succeeds and returns a valid candidate page with admission requirements.
- **Blast Radius**: Entire research process terminates abruptly with `NameError`, preventing any opportunities from being saved or reviewed.
- **Mitigation**: Initialize `actionable_gaps` and `eligibility_reasons` lists before processing extracted requirements.

### Stress Test Results
- `today_utc` deadline: Evaluates as `ACTIVE`, verified=True, score 10.0 -> **PASS**
- `today_utc - 1 day` deadline: Evaluates as `EXPIRED`, verified=False, score 0.0, shortlisted=False -> **PASS**
- `today_utc + 1 day` deadline: Evaluates as `ACTIVE`, verified=True, score 10.0 -> **PASS**
- Malformed dates (`"2026/12/31"`, `"Fall 2026"`): Degrades gracefully to `UNKNOWN`, verified=False, score 2.0 -> **PASS**
- Rolling intake (`deadline_type="Rolling"` or `deadline="rolling"`): Evaluates as `ROLLING`, verified=True, score 10.0 -> **PASS**
- Arbitrary subdomains (`evil.edu.attacker.org`): Returns `True` -> **FAIL (Vulnerability)**
- Model serialization of `deadline_status`: Discarded from JSON -> **FAIL (API Defect)**
- `execute_discovery_and_audit`: Raises `NameError: name 'actionable_gaps' is not defined` -> **FAIL (Crash)**

### Unchallenged Areas
- Live network requests to Google GenAI endpoints (omitted due to development environment constraints).
