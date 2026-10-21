# Forensic Audit Report: Milestone M1 (Grounded Discovery & Real Extraction)

**Auditor**: Forensic Auditor M1.1 (`teamwork_preview_auditor_m1_1`)  
**Parent Orchestrator ID**: `6828b193-f5c1-4991-90e8-8c39694edfd6`  
**Date**: 2026-10-20T22:00:00Z  
**Work Product**: Milestone M1 (Features F1, F2, F3, F4, F5)  
**Profile**: General Project  
**Integrity Mode**: Development (from `ORIGINAL_REQUEST.md`)  
**Verdict**: **CLEAN**

---

## 1. Observation

Direct empirical observations across all audited files and runtime execution:

### 1.1 Complete Absence of `REAL_OPPORTUNITIES_BASE` in `backend/app/`
- **Audit Target**: `D:\Case_study_drive\TetraNoodle_AI_Hackathon\backend\app`
- **Method**: Ripgrep search and recursive file tree walk.
- **Empirical Execution Command**:
  ```bash
  python -c "import os; hits = [os.path.join(r, f) for r, _, fs in os.walk('backend/app') for f in fs if 'REAL_OPPORTUNITIES_BASE' in open(os.path.join(r, f), encoding='utf-8', errors='ignore').read()]; print('HITS:', hits); assert len(hits) == 0"
  ```
- **Raw Tool Output**:
  ```
  HITS: []
  ```
- **Finding**: 0 occurrences found across all files in `backend/app/`. Hardcoded opportunities have been completely eliminated from operational code paths. All fixture data is strictly confined to `backend/tests/fixtures/opportunities.py` (lines 14–400).

### 1.2 Official Google Gen AI SDK URL Context Tool Configuration
- **Audit Target**: `backend/app/services/gemini_service.py` (lines 5–6, 230–234)
- **Code Observation**:
  ```python
  5: from google import genai
  6: from google.genai import types
  ...
  230: config = types.GenerateContentConfig(
  231:     tools=[types.Tool(url_context=types.UrlContext())],
  232:     temperature=0.1,
  233:     response_mime_type="application/json"
  234: )
  ```
- **Empirical AST Verification**:
  ```bash
  python -c "import inspect; from app.services.gemini_service import GeminiService; from google.genai import types; src = inspect.getsource(GeminiService.analyze_url_and_extract_criteria); assert 'types.Tool(url_context=types.UrlContext())' in src; assert 'config = types.GenerateContentConfig(' in src; print('URL Context tool is genuinely configured on GenerateContentConfig')"
  ```
- **Raw Tool Output**:
  ```
  URL Context tool is genuinely configured on GenerateContentConfig
  ```
- **Finding**: Genuine `google-genai` SDK `types.Tool(url_context=types.UrlContext())` is instantiated and passed to `generate_content`. No fake or mocked imports exist in production code.

### 1.3 `url_retrieval_status` Metadata Inspection & Graceful Degradation
- **Audit Target**: `backend/app/services/gemini_service.py` (lines 248–287) and `backend/app/agents/research_eligibility.py` (lines 198–211, 269–289)
- **Code Observation**:
  `gemini_service.py` inspects `candidate.url_context_metadata.url_metadata` and records `entry.url_retrieval_status`:
  ```python
  255: status_enum = getattr(entry, "url_retrieval_status", None)
  256: status_str = status_enum.name if hasattr(status_enum, "name") else (
  257:     status_enum.value if hasattr(status_enum, "value") else str(status_enum or "URL_RETRIEVAL_STATUS_UNSPECIFIED")
  258: )
  259: is_success = (
  260:     status_str == "URL_RETRIEVAL_STATUS_SUCCESS"
  261:     or status_enum == types.UrlRetrievalStatus.URL_RETRIEVAL_STATUS_SUCCESS
  262: )
  ```
  `research_eligibility.py` maps non-successful statuses (`URL_RETRIEVAL_STATUS_PAYWALL`, `URL_RETRIEVAL_STATUS_UNSAFE`, `URL_RETRIEVAL_STATUS_ERROR`) to `UNRESOLVED` criteria and `UNVERIFIED` evidence without synthesizing fake quotes or crashing:
  ```python
  270: if not is_retrieval_successful or retrieval_status in ("URL_RETRIEVAL_STATUS_PAYWALL", "URL_RETRIEVAL_STATUS_UNSAFE", "URL_RETRIEVAL_STATUS_ERROR"):
  271:     uncertainty_msg = (
  272:         f"Official portal at {cand_url} returned retrieval status {retrieval_status}. "
  273:         "Published criteria cannot be verified via live retrieval."
  274:     )
  ...
  282:     status="UNRESOLVED",
  283:     evidence_excerpt=None,
  ```
- **Empirical Execution Command**:
  ```bash
  python -c "
  import asyncio, json
  from unittest.mock import MagicMock
  from google.genai import types
  from app.services.gemini_service import GeminiService

  async def test_metadata():
      service = GeminiService()
      service.api_key = 'test-key'
      mock_client = MagicMock()
      service._client = mock_client

      entry_paywall = MagicMock()
      entry_paywall.retrieved_url = 'https://example.com/paywall'
      entry_paywall.url_retrieval_status = types.UrlRetrievalStatus.URL_RETRIEVAL_STATUS_PAYWALL
      cand_paywall = MagicMock()
      cand_paywall.url_context_metadata.url_metadata = [entry_paywall]
      resp_paywall = MagicMock()
      resp_paywall.candidates = [cand_paywall]
      resp_paywall.text = json.dumps({'admission_requirements': [], 'funding_details': {}})
      mock_client.models.generate_content.return_value = resp_paywall

      res = await service.analyze_url_and_extract_criteria(['https://example.com/paywall'], 'Prog', 'Univ', 'Profile')
      assert res['is_retrieval_successful'] is False
      assert res['retrieval_status'] == 'URL_RETRIEVAL_STATUS_PAYWALL'
      assert res['evidence_quality'] == 'UNVERIFIED'
      print('Metadata check PAYWALL passed successfully')

  asyncio.run(test_metadata())
  "
  ```
- **Raw Tool Output**:
  ```
  Metadata check PAYWALL passed successfully
  ```

### 1.4 Strict Missing API Key Policy & HTTP 503 Translation
- **Audit Target**: `backend/app/services/gemini_service.py` (lines 10–21, 34–37), `backend/app/agents/research_eligibility.py` (line 42), `backend/app/main.py` (lines 18–28)
- **Code Observation**:
  - `GeminiConfigurationError` is defined as a `RuntimeError` subclass.
  - `gemini_service.ensure_available()` raises `GeminiConfigurationError` when `GEMINI_API_KEY` is not present or client is uninitialized.
  - `research_eligibility.py` calls `gemini_service.ensure_available()` at line 42 as the entry-point precondition before performing any research.
  - `main.py` registers an exception handler for `GeminiConfigurationError` returning HTTP 503 JSON:
    ```python
    18: @app.exception_handler(GeminiConfigurationError)
    19: async def gemini_configuration_exception_handler(request: Request, exc: GeminiConfigurationError):
    20:     return JSONResponse(
    21:         status_code=503,
    22:         content={
    23:             "status": 503,
    24:             "error": "GeminiConfigurationError",
    25:             "detail": str(exc),
    26:             "help": "Set the GEMINI_API_KEY environment variable to enable live Gemini discovery and extraction."
    27:         }
    28:     )
    ```
- **Empirical Execution Command**:
  Executed test validating `ensure_available()` raises error, `execute_discovery_and_audit` does not produce fake records, and FastAPI endpoint returns HTTP 503.
- **Raw Tool Output**:
  ```
  All missing key checks passed: explicit GeminiConfigurationError, zero fallback records, HTTP 503 status code.
  ```

### 1.5 Unit and Stress Test Execution Results
- **M1 Grounding Test Suite (`tests/test_m1_grounding.py`)**:
  - Command: `pytest tests/test_m1_grounding.py -v`
  - Output: `14 passed in 5.94s`
  - Verified tests:
    - `test_missing_api_key_ensure_available_raises_exception`: PASSED
    - `test_search_grounded_discovery_missing_key_error`: PASSED
    - `test_research_agent_missing_key_raises_error_without_dummy_fallback`: PASSED
    - `test_gemini_configuration_error_returns_503_http_response`: PASSED
    - `test_url_context_tool_structure`: PASSED
    - `test_google_search_grounding_tool_structure`: PASSED
    - `test_analyze_url_and_extract_criteria_configures_url_context_tool`: PASSED
    - `test_retrieval_status_enums_exist`: PASSED
    - `test_retrieval_status_policy_paywall_marks_unresolved`: PASSED
    - `test_retrieval_status_policy_unsafe_marks_unresolved`: PASSED
    - `test_retrieval_status_policy_error_marks_unresolved`: PASSED
    - `test_partial_url_retrieval_failure_preservation`: PASSED
    - `test_zero_hardcoded_opportunities_in_live_research_code`: PASSED
    - `test_isolated_fixtures_conform_to_schema`: PASSED
- **Challenger Adversarial Stress Suite (`tests/test_m1_challenger_stress.py`)**:
  - Command: `pytest tests/test_m1_challenger_stress.py -v`
  - Output: `17 passed in 6.23s`
  - All 17 stress tests (SSRF candidate rejection, paywall degradation, malformed JSON recovery, workflow exception propagation) PASSED.
- **Full Backend Regression Suite**:
  - Command: `pytest tests/test_m1_grounding.py tests/test_m1_challenger_stress.py tests/test_graph.py tests/test_eligibility.py tests/test_api.py tests/test_documents.py tests/test_github.py tests/test_profile.py tests/test_scoring.py tests/e2e/test_tier1_feature_coverage.py tests/e2e/test_tier2_boundary_corner.py`
  - Output: `97 passed in 13.74s`

---

## 2. Logic Chain

1. **Elimination of Synthetic Opportunities (F1)**:
   - *Observation*: AST walk and string search over all files in `backend/app` confirmed 0 hits for `REAL_OPPORTUNITIES_BASE`.
   - *Logic*: Because `REAL_OPPORTUNITIES_BASE` is only imported and defined in `backend/tests/fixtures/opportunities.py`, live operational code paths cannot draw upon canned scholarship records. When zero opportunities are discovered or retrieval fails, empty or unresolved states are returned honestly.

2. **Genuine SDK Tool Enablement & Metadata Parsing (F3, F4)**:
   - *Observation*: `types.Tool(url_context=types.UrlContext())` is passed directly in `types.GenerateContentConfig` in `analyze_url_and_extract_criteria`. Inspection logic evaluates `candidate.url_context_metadata.url_metadata[i].url_retrieval_status`.
   - *Logic*: The implementation adheres strictly to the official `google-genai` SDK contract. When a URL retrieval succeeds, verbatim quotes are accepted and evidence is marked `OFFICIAL`. When the URL is blocked by paywall or unsafe filters, `is_retrieval_successful` is set to `False`, evidence is marked `UNVERIFIED`, and criteria are recorded as `UNRESOLVED` with explicit uncertainty notes.

3. **No Silent Fallbacks on Missing Credentials (F5)**:
   - *Observation*: `gemini_service.ensure_available()` raises `GeminiConfigurationError`. `research_eligibility.py` invokes this check before issuing any discovery queries.
   - *Logic*: If `GEMINI_API_KEY` is not configured, the pipeline will never silently substitute fake fixtures. In FastAPI, this raises an uncaught exception converted by the dedicated `@app.exception_handler` to HTTP 503 Service Unavailable with clear remediation guidance.

4. **Absence of Prohibited Patterns**:
   - *Hardcoded test results*: None. Return dictionaries are populated dynamically from GenAI responses and Pydantic models.
   - *Facade implementations*: None. Methods perform full processing, error inspection, and event logging.
   - *Fabricated outputs*: None. No pre-existing test results or artificial logs.
   - *Self-certifying tests*: None. Tests construct realistic inputs and assert behavior against mock boundaries or real contracts.

---

## 3. Caveats

1. **Downstream Unmocked E2E Tests in `tests/e2e/`**:
   - Tests in `backend/tests/e2e/test_tier3_cross_feature.py` and `backend/tests/e2e/test_tier4_real_world.py` invoke `swarm_app.ainvoke(state)` without mocking the Gemini service or providing live API credentials. Prior to M1, those tests relied on the synthetic `REAL_OPPORTUNITIES_BASE` fallback in `research_eligibility.py`. Because M1 completely eradicated that fallback, unmocked workflow tests without live API keys will raise `GeminiConfigurationError`. Milestone E2E / M6 is scoped to align these downstream suites with fixture model helpers (`get_fixture_opportunity_models()`).
2. **Scratch File `tests/test_challenger_m1_stress.py`**:
   - A scratch test file `test_challenger_m1_stress.py` left by an earlier challenger attempt uses `patch.object(agent.gemini_service, ...)` (attribute not on instance). The authoritative adversarial suite `test_m1_challenger_stress.py` patches correctly and passes 17/17 tests cleanly. Per auditor constraints, implementation code was not modified.

---

## 4. Conclusion

Milestone M1 (Grounded Discovery & Real Extraction Implementation) achieves a verdict of **CLEAN**:
- Zero hardcoded scholarship fixtures exist in `backend/app/`.
- Official `google-genai` SDK `types.Tool(url_context=types.UrlContext())` is genuinely configured.
- `url_retrieval_status` metadata is inspected and correctly categorized.
- Missing credentials explicitly raise `GeminiConfigurationError` mapped to HTTP 503.
- All 14 tests in `tests/test_m1_grounding.py` and 97 total regression/stress tests pass cleanly.

---

## 5. Verification Method

To independently reproduce this forensic audit:

1. **Verify Zero `REAL_OPPORTUNITIES_BASE` in `backend/app/`**:
   ```bash
   python -c "import os; hits = [os.path.join(r, f) for r, _, fs in os.walk('backend/app') for f in fs if 'REAL_OPPORTUNITIES_BASE' in open(os.path.join(r, f), encoding='utf-8', errors='ignore').read()]; print('HITS:', hits); assert len(hits) == 0"
   ```

2. **Verify URL Context Tool Configuration in `gemini_service.py`**:
   ```bash
   python -c "import inspect; from app.services.gemini_service import GeminiService; from google.genai import types; src = inspect.getsource(GeminiService.analyze_url_and_extract_criteria); assert 'types.Tool(url_context=types.UrlContext())' in src; assert 'config = types.GenerateContentConfig(' in src; print('URL Context Tool Verified')"
   ```

3. **Verify M1 Grounding Test Suite (14 passed)**:
   ```bash
   cd backend
   pytest tests/test_m1_grounding.py -v
   ```

4. **Verify Challenger Adversarial Stress Suite (17 passed)**:
   ```bash
   cd backend
   pytest tests/test_m1_challenger_stress.py -v
   ```

5. **Verify Combined 97-Test Regression Suite**:
   ```bash
   cd backend
   pytest tests/test_m1_grounding.py tests/test_m1_challenger_stress.py tests/test_graph.py tests/test_eligibility.py tests/test_api.py tests/test_documents.py tests/test_github.py tests/test_profile.py tests/test_scoring.py tests/e2e/test_tier1_feature_coverage.py tests/e2e/test_tier2_boundary_corner.py
   ```

### Invalidation Conditions
- Any reintroduction of `REAL_OPPORTUNITIES_BASE` or synthetic scholarship lists into `backend/app/`.
- Removal of `types.Tool(url_context=types.UrlContext())` from `GenerateContentConfig`.
- Bypassing `candidate.url_context_metadata` inspection.
- Replacing `GeminiConfigurationError` with silent dummy fallback records.
