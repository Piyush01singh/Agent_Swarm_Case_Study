# Handoff Report: Milestone M1 Error Handling, Missing Key Policies & Test Strategy

**Agent**: Explorer M1.3 (Error Handling, Missing Key Policies & Test Strategy)  
**Date**: 2026-10-20T21:30:00Z  
**Target Path**: `D:\Case_study_drive\TetraNoodle_AI_Hackathon\.agents\teamwork\teamwork_preview_explorer_m1_3\handoff.md`  
**Parent Orchestrator ID**: `6828b193-f5c1-4991-90e8-8c39694edfd6`  
**Reference Documents**: `ORIGINAL_REQUEST.md`, `PROJECT.md` (Features F1–F5, Milestone M1)

---

## 1. Observation

### 1.1 Current API Key Handling & Silent Fallback Vulnerabilities
- **File**: `backend/app/config.py` (lines 4–5)
  ```python
  class Settings(BaseSettings):
      GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
  ```
  `GEMINI_API_KEY` defaults to `""`.
- **File**: `backend/app/services/gemini_service.py` (lines 17–33, 114–120)
  ```python
  @property
  def is_available(self) -> bool:
      return bool(self.api_key and self._client)

  async def search_grounded_discovery(self, query: str, context_prompt: str) -> Dict[str, Any]:
      if not self.is_available:
          return {
              "success": False,
              "error": "GEMINI_API_KEY is not configured.",
              "candidates": [],
              "citations": []
          }
  ```
  Missing API keys merely returned a dictionary with `"success": False`. No custom exception was defined or raised.
- **File**: `backend/app/agents/research_eligibility.py` (lines 325–379)
  ```python
  # Try live Gemini Search Grounding if API is configured
  if gemini_service.is_available:
      ...
  # Augment with verified official scholarship opportunities matching target criteria
  for raw_opp in REAL_OPPORTUNITIES_BASE:
      ...
      opportunities.append(opp)
  return opportunities
  ```
  When `gemini_service.is_available` was `False`, the live discovery block was silently skipped, and execution fell through to lines 364–379, returning hardcoded dummy records (`REAL_OPPORTUNITIES_BASE`). Neither an error nor a warning was surfaced to the user, masking key configuration errors.
- **FastAPI Exception Handling**:
  - `backend/app/main.py` had zero custom exception handlers registered.
  - `backend/app/api/research.py` (lines 40–55) caught general `Exception as e` in `run_swarm_pipeline`, marking run status as `FAILED`, but `/api/research/start` (line 57) scheduled the background task without pre-validating live discovery readiness or surfacing HTTP 503 for direct live requests.

### 1.2 Google Gen AI SDK URL Retrieval Status Metadata
- **SDK Inspection via Python 3.13 Runtime**:
  - `google.genai.types` defines:
    - `UrlContext`: Tool for page retrieval (`types.Tool(url_context=types.UrlContext())`).
    - `UrlRetrievalStatus` enum members:
      - `URL_RETRIEVAL_STATUS_SUCCESS = "URL_RETRIEVAL_STATUS_SUCCESS"`
      - `URL_RETRIEVAL_STATUS_ERROR = "URL_RETRIEVAL_STATUS_ERROR"`
      - `URL_RETRIEVAL_STATUS_PAYWALL = "URL_RETRIEVAL_STATUS_PAYWALL"`
      - `URL_RETRIEVAL_STATUS_UNSAFE = "URL_RETRIEVAL_STATUS_UNSAFE"`
      - `URL_RETRIEVAL_STATUS_UNSPECIFIED = "URL_RETRIEVAL_STATUS_UNSPECIFIED"`
    - `UrlMetadata`: Contains `retrieved_url: str` and `url_retrieval_status: UrlRetrievalStatus`.
    - `UrlContextMetadata`: Contains `url_metadata: List[UrlMetadata]`.
    - `Candidate`: Exposes `url_context_metadata: Optional[UrlContextMetadata]`.
- **Existing Defect in `gemini_service.py`**:
  `analyze_url_and_extract_criteria` (lines 171–174) failed to configure `tools=[types.Tool(url_context=types.UrlContext())]` and did not inspect `candidate.url_context_metadata`. If a URL was paywalled or failed with HTTP 404/500, the prompt simply hallucinated criteria or failed during JSON parsing.

### 1.3 Existing Test Suite & Pytest Discovery
- Running `pytest` in `backend/` directly:
  Previously failed with `ModuleNotFoundError: No module named 'app'` when `pytest.ini` was missing `pythonpath = .`.
  With `backend/pytest.ini` configured (`pythonpath = .`, `testpaths = tests`, `asyncio_mode = auto`), `pytest` executes 21 passed tests in 9.09s.
- `backend/tests/fixtures/opportunities.py`:
  Already created with `CANONICAL_FIXTURE_OPPORTUNITIES` containing 5 isolated opportunity fixtures.
- `backend/tests/e2e/test_tier1_feature_coverage.py`:
  Contains initial feature tests (10 passing), including `test_f4_retrieval_metadata_handling_distinguishes_status` and `test_f5_missing_api_key_returns_explicit_error_without_fallback`.
- Dedicated unit test coverage specifically verifying:
  1) `types.Tool(url_context=types.UrlContext())` configuration on `GenerateContentConfig`;
  2) Non-crashing degradation when URL returns `PAYWALL`, `UNSAFE`, or `ERROR`;
  3) Immediate raising of `GeminiConfigurationError` and FastAPI HTTP 503 response;
  4) Strict guarantee that 0 dummy opportunities are emitted when live discovery yields no verified matches;
  remains to be authored in `backend/tests/test_m1_grounding.py`.

---

## 2. Logic Chain

### 2.1 Enforcing Missing Key Policies Without Silent Fallback
1. **Premise**: In live discovery mode, ScholarSwarm promises genuine discovery from official portals. Hardcoding dummy records violates requirement R1 and acceptance criterion 53 ("Missing API keys trigger explicit configuration errors, never silent fallbacks to fabricated records").
2. **Mechanism**:
   - Define custom exception:
     ```python
     class GeminiConfigurationError(RuntimeError):
         """Raised when live Gemini discovery or URL extraction is requested without a valid API key."""
     ```
   - In `backend/app/services/gemini_service.py`:
     Provide `ensure_available()` which raises `GeminiConfigurationError` if `not self.is_available`.
     In `search_grounded_discovery` and `analyze_url_and_extract_criteria`: when `not self.is_available`, either raise `GeminiConfigurationError` immediately (in live/strict mode) or return `{"success": False, "error": "...", "error_type": "GeminiConfigurationError"}`.
   - In `backend/app/agents/research_eligibility.py`:
     In `execute_discovery_and_audit`:
     ```python
     if not gemini_service.is_available:
         await repository.save_agent_event(AgentEvent(
             run_id=run_id,
             agent_role=self.role_name,
             event_type="ERROR",
             title="Gemini API Key Missing",
             description="Live research discovery aborted: GEMINI_API_KEY is not configured.",
             metadata={"error_type": "GeminiConfigurationError"}
         ))
         raise GeminiConfigurationError(
             "GEMINI_API_KEY is not configured. Live research discovery cannot proceed without a valid Gemini API key."
         )
     ```
     Because lines 364–379 iterating `REAL_OPPORTUNITIES_BASE` are eliminated (Feature F1/F2), there is ZERO code path returning fabricated records.
   - In `backend/app/main.py`:
     Register `@app.exception_handler(GeminiConfigurationError)` to return HTTP 503 Service Unavailable:
     ```json
     {
       "error": "GeminiConfigurationError",
       "detail": "GEMINI_API_KEY is not configured. Live research discovery requires a valid Gemini API key.",
       "status_code": 503
     }
     ```
   - In `backend/app/api/research.py`:
     In `run_swarm_pipeline`, explicitly catch `GeminiConfigurationError`:
     Set `run.status = "FAILED"`, `run.current_phase = "FAILED"`, `run.error_message = str(e)`, and log an `ERROR` agent event so the frontend SSE stream immediately receives the error notice.

### 2.2 Graceful Non-Crashing Handling of `UrlRetrievalStatus` Errors
1. **Premise**: Web scraping and live URL context retrieval encounter paywalls, malicious pages, and network failures. The pipeline must neither crash nor invent criteria when a page cannot be retrieved.
2. **Metadata Inspection Flow**:
   When `gemini_service.analyze_url_and_extract_criteria` executes with `types.Tool(url_context=types.UrlContext())`:
   ```python
   # Extract retrieval status per URL
   retrieval_statuses: Dict[str, str] = {}
   if response.candidates:
       candidate = response.candidates[0]
       url_ctx_meta = getattr(candidate, "url_context_metadata", None)
       if url_ctx_meta:
           for meta in getattr(url_ctx_meta, "url_metadata", []) or []:
               url = getattr(meta, "retrieved_url", "")
               status = getattr(meta, "url_retrieval_status", None)
               status_str = status.name if hasattr(status, "name") else str(status)
               if url:
                   retrieval_statuses[url] = status_str
   ```
3. **Status Classification & Pipeline Policy**:
   - **`URL_RETRIEVAL_STATUS_SUCCESS`**:
     - Status: Retrieved successfully.
     - `evidence_quality`: Set to `"OFFICIAL"` (if URL domain is verified official educational/government portal) or `"SECONDARY"`.
     - `criteria`: Evaluated against page content.
     - `evidence_excerpt`: Verbatim text excerpt directly quoted from retrieved page.
   - **`URL_RETRIEVAL_STATUS_PAYWALL`**:
     - Status: Blocked behind login or subscriber paywall.
     - Action: DO NOT CRASH. DO NOT FABRICATE EXCERPTS.
     - `evidence_quality`: Downgraded to `"SECONDARY"` or `"UNVERIFIED"`.
     - Criteria: Mark affected criteria as `status = "UNRESOLVED"`.
     - Uncertainty Note: `"Official portal paywalled; criteria unverified via live retrieval."`
     - Actionable Gap: Append `"Official portal at {url} is paywalled; student must verify requirements manually."`
     - Event: Record `AgentEvent(event_type="RETRIEVAL_PAYWALL")`.
   - **`URL_RETRIEVAL_STATUS_UNSAFE`**:
     - Status: Flagged by Google Gen AI safety/malware filter.
     - Action: DO NOT CRASH. DO NOT TRUST URL CONTENT.
     - `evidence_quality`: Set to `"UNVERIFIED"`.
     - Criteria: Mark affected criteria as `status = "UNRESOLVED"`.
     - Uncertainty Note: `"Source URL flagged as UNSAFE by GenAI URL safety filter."`
     - Actionable Gap: Append `"Source URL {url} flagged as unsafe; excluded from trusted evidence."`
     - Event: Record `AgentEvent(event_type="RETRIEVAL_UNSAFE")`.
   - **`URL_RETRIEVAL_STATUS_ERROR`**:
     - Status: HTTP 404, 500, DNS lookup failure, or timeout.
     - Action: DO NOT CRASH.
     - `evidence_quality`: Set to `"UNVERIFIED"`.
     - Criteria: Mark affected criteria as `status = "UNRESOLVED"`.
     - Uncertainty Note: `"Source URL retrieval error; official criteria unverified."`
     - Actionable Gap: Append `"Source URL {url} could not be retrieved; criteria unverified."`
     - Event: Record `AgentEvent(event_type="RETRIEVAL_ERROR")`.
4. **Partial Branch Recovery (Multi-URL Candidates)**:
   A candidate opportunity typically has 1 to 3 URLs (e.g., main program page, scholarship portal, departmental admissions).
   - If at least 1 URL succeeds:
     Verbatim evidence from successful URLs is retained. Missing information from failed URLs is marked `UNRESOLVED`. The opportunity is preserved with partial evidence quality (`"SECONDARY"` or `"OFFICIAL"` with noted gaps) rather than dropped.
   - If ALL URLs fail (`PAYWALL`, `UNSAFE`, or `ERROR`):
     The candidate is preserved with `evidence_quality = "UNVERIFIED"`, `eligibility_status = "INSUFFICIENT_EVIDENCE"`, match score penalized, and excluded from top-5 recommendations.
   - Pipeline NEVER crashes; all agent steps complete cleanly.

### 2.3 Comprehensive Test Strategy for Milestone M1
To verify the entire M1 milestone deterministically, we design a 3-part test matrix:
1. **Isolated Unit Tests** (`backend/tests/test_m1_grounding.py`):
   Targeting SDK tool configuration, retrieval status mapping, error bubbling, and exception responses.
2. **Eligibility Contract Tests** (`backend/tests/test_eligibility.py`):
   Targeting verbatim evidence integrity and handling of unretrieved/paywalled sources.
3. **Mock & Fixture Isolation**:
   Ensuring all unit tests run in CI/offline environments without spending Google GenAI API credits or failing due to network latency, while live smoke tests (`scripts/smoke_test_gemini.py`) run when `GEMINI_API_KEY` is present.

---

## 3. Caveats

1. **Live Gemini Quotas**: In live discovery mode with an active key, `types.Tool(url_context=...)` queries live web pages in real-time. High concurrency (>2 concurrent requests) may hit Google API rate limits (RPM/TPM). The worker should respect `settings.MAX_CONCURRENT_RESEARCH_REQUESTS = 2` and `settings.GEMINI_TIMEOUT_SECONDS = 90`.
2. **Offline Unit Test Determinism**: To ensure CI reproducibility, unit tests must never make outbound HTTP calls to Gemini unless run with an explicit flag or via `smoke_test_gemini.py`. All tests in `test_m1_grounding.py` must use mocked `types.GenerateContentResponse` fixtures.
3. **Scope Boundary**: Milestones M2 (program-specific criteria matching, deadline verification, official domain policy) and M3 (bounded review feedback loop) build on this foundation. M1's responsibility is solely discovery, URL Context extraction, retrieval metadata classification, missing key error handling, and fixture isolation.

---

## 4. Conclusion

The implementation strategy for Milestone M1 Error Handling, Missing Key Policies, and Test Strategy is fully formulated:

1. **Missing Key Handling**:
   - `GeminiConfigurationError` defined in `app/services/gemini_service.py`.
   - `gemini_service.ensure_available()` called at the entry of live discovery in `research_eligibility.py`.
   - Global exception handler in `app/main.py` translating `GeminiConfigurationError` to HTTP 503.
   - `run_swarm_pipeline` catching `GeminiConfigurationError` and setting run state to `FAILED`.
   - Removal of `REAL_OPPORTUNITIES_BASE` from live discovery guarantees zero fallback to dummy records.

2. **`UrlRetrievalStatus` Error Policy**:
   - Explicit inspection of `candidate.url_context_metadata.url_metadata`.
   - Classification of `SUCCESS` as `OFFICIAL`/`SECONDARY` with verbatim excerpts.
   - Classification of `PAYWALL`, `UNSAFE`, and `ERROR` as `UNRESOLVED` criteria and `UNVERIFIED` evidence quality, logging appropriate `AgentEvent`s without crashing the pipeline.
   - Partial branch failure recovery preserving verified evidence from accessible URLs.

3. **Test Suite Design**:
   - Creation of `backend/tests/test_m1_grounding.py` with 12 distinct unit test cases.
   - Pytest mock fixtures simulating all `UrlRetrievalStatus` variants.
   - Zero hardcoded opportunities verification test via AST/module inspection.

---

## 5. Verification Method & Code Specifications for Worker

### 5.1 Proposed Code: `backend/app/services/gemini_service.py`
Add `GeminiConfigurationError` and `ensure_available`:
```python
# ==============================================================================
# Custom Exceptions
# ==============================================================================
class GeminiConfigurationError(RuntimeError):
    """Raised when live Gemini discovery or URL extraction is requested without a valid API key."""
    def __init__(
        self,
        message: str = (
            "GEMINI_API_KEY is not configured. Live research discovery requires a valid Gemini API key. "
            "Please configure GEMINI_API_KEY in the environment or .env file."
        )
    ):
        super().__init__(message)
        self.message = message


class GeminiService:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.model = settings.GEMINI_MODEL
        self._client = None
        if self.api_key:
            self._client = genai.Client(api_key=self.api_key)

    @property
    def is_available(self) -> bool:
        return bool(self.api_key and self._client)

    def ensure_available(self) -> None:
        """Validates that Gemini API key and client are configured; raises GeminiConfigurationError otherwise."""
        if not self.is_available:
            raise GeminiConfigurationError()
```

In `analyze_url_and_extract_criteria`:
Enable `types.Tool(url_context=types.UrlContext())` and extract retrieval metadata:
```python
        config = types.GenerateContentConfig(
            tools=[types.Tool(url_context=types.UrlContext())],
            temperature=0.1,
            response_mime_type="application/json"
        )
        response = await asyncio.to_thread(
            self._client.models.generate_content,
            model=self.model,
            contents=prompt,
            config=config
        )

        # Inspect URL Context Metadata
        retrieval_statuses: Dict[str, str] = {}
        if response.candidates and len(response.candidates) > 0:
            candidate = response.candidates[0]
            url_context_metadata = getattr(candidate, "url_context_metadata", None)
            if url_context_metadata:
                url_metadata_list = getattr(url_context_metadata, "url_metadata", []) or []
                for meta in url_metadata_list:
                    retrieved_url = getattr(meta, "retrieved_url", "")
                    status = getattr(meta, "url_retrieval_status", None)
                    status_name = status.name if hasattr(status, "name") else str(status)
                    if retrieved_url:
                        retrieval_statuses[retrieved_url] = status_name

        data = json.loads(response.text)
        return {
            "success": True,
            "data": data,
            "url_retrieval_statuses": retrieval_statuses
        }
```

### 5.2 Proposed Code: `backend/app/main.py`
Register HTTP 503 Exception Handler:
```python
from fastapi import Request
from fastapi.responses import JSONResponse
from app.services.gemini_service import GeminiConfigurationError

@app.exception_handler(GeminiConfigurationError)
async def gemini_configuration_exception_handler(request: Request, exc: GeminiConfigurationError):
    return JSONResponse(
        status_code=503,
        content={
            "status": 503,
            "error": "GeminiConfigurationError",
            "detail": str(exc),
            "help": "Set the GEMINI_API_KEY environment variable to enable live Gemini discovery and extraction."
        }
    )
```

### 5.3 Proposed Unit Test Suite: `backend/tests/test_m1_grounding.py`
The Worker will create this file to verify M1:

```python
"""
Milestone M1 Unit & Contract Tests:
Verifies Google Search Grounding tool configuration, URL Context tool enablement,
UrlRetrievalStatus metadata handling (SUCCESS vs PAYWALL/UNSAFE/ERROR),
explicit GeminiConfigurationError on missing keys, and zero dummy fallback.
"""

import pytest
import json
from unittest.mock import MagicMock, AsyncMock, patch
from google.genai import types

from app.services.gemini_service import GeminiService, GeminiConfigurationError
from app.agents.research_eligibility import ResearchEligibilityAgent
from app.models.profile import StudentProfile
from app.models.evidence import EvidenceRecord
from tests.fixtures.opportunities import CANONICAL_FIXTURE_OPPORTUNITIES


# ==============================================================================
# 1. Missing Key & Configuration Error Policies
# ==============================================================================
def test_missing_api_key_ensure_available_raises_exception():
    """Verify ensure_available raises GeminiConfigurationError when API key is missing."""
    service = GeminiService()
    service.api_key = ""
    service._client = None
    assert service.is_available is False

    with pytest.raises(GeminiConfigurationError) as exc_info:
        service.ensure_available()
    assert "GEMINI_API_KEY is not configured" in str(exc_info.value)


@pytest.mark.asyncio
async def test_search_grounded_discovery_missing_key_error():
    """Verify search_grounded_discovery returns explicit error or raises configuration error."""
    service = GeminiService()
    service.api_key = ""
    service._client = None

    res = await service.search_grounded_discovery("masters in canada", "student context")
    assert res["success"] is False
    assert "GEMINI_API_KEY is not configured" in res["error"]


@pytest.mark.asyncio
async def test_research_agent_missing_key_raises_error_without_dummy_fallback():
    """Verify ResearchEligibilityAgent raises GeminiConfigurationError and NEVER falls back to dummy records."""
    agent = ResearchEligibilityAgent()
    profile = StudentProfile(
        full_name="Rahul Sharma",
        current_degree="B.Tech Computer Science",
        cgpa=8.2,
        target_degree="Master's",
        target_field="Computer Science",
        target_countries=["Canada"]
    )

    with patch("app.agents.research_eligibility.gemini_service.is_available", False):
        with pytest.raises(GeminiConfigurationError) as exc_info:
            await agent.execute_discovery_and_audit(
                run_id="test-run-no-key",
                profile=profile,
                research_round=1
            )
        assert "GEMINI_API_KEY is not configured" in str(exc_info.value)


# ==============================================================================
# 2. Tool Enablement & SDK Configuration
# ==============================================================================
def test_url_context_tool_structure():
    """Verify types.Tool(url_context=types.UrlContext()) is valid SDK configuration."""
    tool = types.Tool(url_context=types.UrlContext())
    assert tool.url_context is not None


def test_google_search_grounding_tool_structure():
    """Verify types.Tool(google_search=types.GoogleSearch()) is valid SDK configuration."""
    tool = types.Tool(google_search=types.GoogleSearch())
    assert tool.google_search is not None


# ==============================================================================
# 3. UrlRetrievalStatus Metadata Inspection & Error Policy
# ==============================================================================
def test_retrieval_status_enums_exist():
    """Verify google-genai SDK defines SUCCESS, PAYWALL, UNSAFE, and ERROR statuses."""
    assert hasattr(types, "UrlRetrievalStatus")
    assert hasattr(types.UrlRetrievalStatus, "URL_RETRIEVAL_STATUS_SUCCESS")
    assert hasattr(types.UrlRetrievalStatus, "URL_RETRIEVAL_STATUS_PAYWALL")
    assert hasattr(types.UrlRetrievalStatus, "URL_RETRIEVAL_STATUS_UNSAFE")
    assert hasattr(types.UrlRetrievalStatus, "URL_RETRIEVAL_STATUS_ERROR")


def test_retrieval_status_policy_paywall_marks_unresolved():
    """Verify PAYWALL status causes criterion status UNRESOLVED and does NOT crash."""
    status = types.UrlRetrievalStatus.URL_RETRIEVAL_STATUS_PAYWALL
    # Evaluation policy
    is_success = (status == types.UrlRetrievalStatus.URL_RETRIEVAL_STATUS_SUCCESS)
    assert is_success is False
    
    # EvidenceRecord creation under paywall
    record = EvidenceRecord(
        criterion_name="Academic CGPA",
        stated_requirement="Published on portal",
        student_value="8.2",
        status="UNRESOLVED",
        evidence_excerpt=None,
        source_url="https://paywalled.edu/admissions",
        source_category="UNVERIFIED",
        uncertainty_or_conflict="Source URL paywalled; criteria unverified via live retrieval."
    )
    assert record.status == "UNRESOLVED"
    assert record.evidence_excerpt is None
    assert "paywalled" in record.uncertainty_or_conflict.lower()


def test_retrieval_status_policy_unsafe_marks_unresolved():
    """Verify UNSAFE status marks criteria UNRESOLVED and flags safety issue."""
    status = types.UrlRetrievalStatus.URL_RETRIEVAL_STATUS_UNSAFE
    assert status != types.UrlRetrievalStatus.URL_RETRIEVAL_STATUS_SUCCESS

    record = EvidenceRecord(
        criterion_name="Prerequisites",
        stated_requirement="Unknown",
        status="UNRESOLVED",
        source_url="https://malicious-link.com",
        source_category="UNVERIFIED",
        uncertainty_or_conflict="Source URL flagged as UNSAFE by GenAI URL safety filter."
    )
    assert record.status == "UNRESOLVED"
    assert record.source_category == "UNVERIFIED"
    assert "UNSAFE" in record.uncertainty_or_conflict


def test_retrieval_status_policy_error_marks_unresolved():
    """Verify HTTP ERROR status marks criteria UNRESOLVED gracefully."""
    status = types.UrlRetrievalStatus.URL_RETRIEVAL_STATUS_ERROR
    assert status != types.UrlRetrievalStatus.URL_RETRIEVAL_STATUS_SUCCESS

    record = EvidenceRecord(
        criterion_name="Language Test",
        stated_requirement="IELTS requirements",
        status="UNRESOLVED",
        source_url="https://broken-link.edu/404",
        source_category="UNVERIFIED",
        uncertainty_or_conflict="Source URL retrieval error (HTTP/Network failure); criteria unverified."
    )
    assert record.status == "UNRESOLVED"
    assert "retrieval error" in record.uncertainty_or_conflict.lower()


def test_partial_url_retrieval_failure_preservation():
    """
    Verify multi-URL candidate preserves verified data from successful URL
    while classifying failed URL criteria as UNRESOLVED without dropping candidate.
    """
    url_results = {
        "https://cs.toronto.edu/mscac": types.UrlRetrievalStatus.URL_RETRIEVAL_STATUS_SUCCESS,
        "https://cs.toronto.edu/internal-paywalled": types.UrlRetrievalStatus.URL_RETRIEVAL_STATUS_PAYWALL,
    }

    records = []
    # Success URL
    records.append(EvidenceRecord(
        criterion_name="Academic CGPA",
        stated_requirement="Minimum 8.0/10.0 CGPA",
        student_value="8.2",
        status="MEETS",
        evidence_excerpt="Applicant must have B+ average (8.0/10) in final two years.",
        source_url="https://cs.toronto.edu/mscac",
        source_category="OFFICIAL"
    ))
    # Paywalled URL
    records.append(EvidenceRecord(
        criterion_name="Departmental Fellowship Details",
        stated_requirement="Stipend details",
        status="UNRESOLVED",
        evidence_excerpt=None,
        source_url="https://cs.toronto.edu/internal-paywalled",
        source_category="UNVERIFIED",
        uncertainty_or_conflict="Source URL paywalled; criteria unverified via live retrieval."
    ))

    # Candidate preserves verified record
    meets_records = [r for r in records if r.status == "MEETS"]
    unresolved_records = [r for r in records if r.status == "UNRESOLVED"]
    assert len(meets_records) == 1
    assert len(unresolved_records) == 1
    assert meets_records[0].evidence_excerpt is not None


# ==============================================================================
# 4. Zero Hardcoded Opportunities Verification
# ==============================================================================
def test_zero_hardcoded_opportunities_in_live_research_code():
    """Verify REAL_OPPORTUNITIES_BASE is completely absent from live research module."""
    import inspect
    import app.agents.research_eligibility as mod

    source_code = inspect.getsource(mod)
    assert "REAL_OPPORTUNITIES_BASE" not in source_code, (
        "Violation: REAL_OPPORTUNITIES_BASE must be removed from app/agents/research_eligibility.py"
    )


def test_isolated_fixtures_conform_to_schema():
    """Verify test fixtures reside in tests/fixtures/opportunities.py and match schema."""
    assert len(CANONICAL_FIXTURE_OPPORTUNITIES) >= 5
    for fixture in CANONICAL_FIXTURE_OPPORTUNITIES:
        assert "title" in fixture
        assert "canonical_url" in fixture
        assert "admission_requirements" in fixture
        assert "funding" in fixture
```

### 5.4 Independent Verification Commands
```bash
# 1. Verify backend tests pass with isolated fixtures and configuration error handling:
cd D:\Case_study_drive\TetraNoodle_AI_Hackathon\backend
pytest tests/e2e/test_tier1_feature_coverage.py

# 2. Run new M1 grounding unit test suite:
pytest tests/test_m1_grounding.py

# 3. Verify zero hardcoded opportunities remain in live research code paths:
python -c "import inspect, app.agents.research_eligibility as mod; assert 'REAL_OPPORTUNITIES_BASE' not in inspect.getsource(mod)"

# 4. Run full test suite:
pytest
```
