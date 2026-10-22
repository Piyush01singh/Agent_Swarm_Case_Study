# Explorer 3 Handoff Report: Frontend, Benchmark Transparency & Test Suite Offline Impact Analysis

## 1. Observation

### Focus 1: Frontend Error & Empty Handling (R1 & R6)
1. **`frontend/src/App.tsx` (Lines 88–140)**:
   - In `handleStartResearch`:
     ```typescript
     try {
       const run = await startResearch(updatedProfile);
       ...
     } catch (err: any) {
       alert(`Research cycle initiation failed: ${err.message}`);
       setCurrentPhase("ERROR");
     }
     ```
   - In the JSX rendering (lines 331–357):
     ```tsx
     {opportunities.length === 0 && (
       <div className="p-12 text-center rounded-2xl bg-slate-900/40 border border-slate-800 space-y-4">
         {currentPhase !== "STANDBY" && !isCompleted ? (
           <>
             <RefreshCw className="h-10 w-10 text-emerald-400 mx-auto animate-spin" />
             <h3 className="text-base font-bold text-white">ScholarSwarm Research Cycle in Progress</h3>
             ...
           </>
         ) : (
           <>
             <GraduationCap className="h-10 w-10 text-emerald-400 mx-auto" />
             <h3 className="text-base font-bold text-white">No research results in current session</h3>
             ...
           </>
         )}
       </div>
     )}
     ```
   - **Bug A (Infinite Spinner on Error)**: When `startResearch` throws an exception, `currentPhase` becomes `"ERROR"` and `isCompleted` remains `false`. Because `currentPhase !== "STANDBY"` is true and `!isCompleted` is true, the UI continuously renders the spinning icon `<RefreshCw className="... animate-spin" />` with *"ScholarSwarm Research Cycle in Progress"*, hanging indefinitely.
   - **Bug B (Silent Standby Masking `DISCOVERY_EMPTY` & `QUOTA_EXHAUSTED`)**: When the backend emits `event_type="DISCOVERY_EMPTY"` or `event_type="QUOTA_EXHAUSTED"`, the SSE handler in `App.tsx` (line 100) tests:
     ```typescript
     if (event.event_type.includes("SEARCH") || event.event_type.includes("DISCOVERY") || event.event_type.includes("CANDIDATE")) {
       setCurrentPhase("DISCOVERY");
     }
     ```
     `"DISCOVERY_EMPTY".includes("DISCOVERY")` evaluates to true, keeping `currentPhase` as `"DISCOVERY"`. When the run completes with zero opportunities, `onDone` is invoked, setting `isCompleted = true` and `currentPhase = "COMPLETED"`. The UI falls into `currentPhase === "COMPLETED"` with `opportunities.length === 0` and renders:
     *"No research results in current session. Launch the 5-agent research cycle to discover live scholarships across Canada, Germany, and Singapore tailored to your profile. [Start Research Now]"*.
     The user is never told that discovery ran and returned 0 results (`DISCOVERY_EMPTY`), or that Gemini quota failed (`QUOTA_EXHAUSTED`). It appears as an un-run blank session.
2. **`frontend/src/components/AgentWorkspace.tsx` (Line 147)**:
   - Terminal styling only checks:
     ```typescript
     const isFlag = ev.event_type.includes("FLAG") || ev.event_type.includes("ERROR");
     const isRetry = ev.event_type.includes("RETRY");
     ```
   - Events with `QUOTA_EXHAUSTED`, `DISCOVERY_EMPTY`, or `SEARCH_WARNING` default to neutral grey styling (`bg-slate-900/50`) without rose/amber alert badges.
3. **`frontend/index.html` (Line 7)**:
   - Current title: `<title>frontend</title>`.
   - Requirement R6 requires: `<title>ScholarSwarm — AI Scholarship Intelligence</title>`.
4. **`frontend/src/components/SopWorkspace.tsx` (Lines 27–42)**:
   - When `generateSopDraft` fails in `.catch((err) => { ... })`, `draft` remains `null` and `content` remains empty without displaying an actionable error banner.

---

### Focus 2: Benchmark Transparency (R7)
1. **`docs/EXPERIMENT.md` (Lines 27–40, 58–59)**:
   ```markdown
   ### 3. Empirical Measurements & Results
   *Benchmark Execution Mode: `deterministic_mock` | Test Cases: `10` | Generated: `2026-10-21T07:40:09.344902+00:00`*

   | Metric | Single Pass (Baseline) | Self-Correcting (ScholarSwarm) | Delta / Improvement |
   |---|---:|---:|---:|
   | **Critical Claims Grounded in Official Sources** | 70.0% | **80.0%** | **+10.0%** |
   | **Eligibility Classification Accuracy (vs Ground Truth)** | 60.0% | **100.0%** | **+40.0%** |
   | **False-Positive Admissions Pass Rate** | 50.0% | **0.0%** | **-50.0% (Eliminated)** |
   | **Unsupported Funding Claims Flagged & Rectified** | 0/1 (0.0%) | **1/1 (100.0%)** | **+100.0%** |
   | **Fault Recovery under Injected Network/URL Block** | 0.0% | **100.0%** | **+100.0%** |
   | **Mean End-to-End Latency** | 4e-05s | 0.000195s | +0.000155s |
   | **Mean Additional Pipeline Rounds** | 1.0 rounds | 1.3 rounds | +0.3 rounds |
   ...
   5. **Bounded Latency Trade-Off**:
      - The self-correction loop added only ~+0.3 rounds and modest latency overhead (+0.000155s), satisfying responsive user interaction standards.
   ```
2. **`README.md` (Lines 141–143, 194)**:
   - Line 141-143 claims `Test Results: 21 passed in ~8 seconds (100% pass rate)` without clarifying that the harness executes in mock mode.
   - Line 194 lists `- [Self-Correction Empirical Experiment](docs/EXPERIMENT.md)` without simulation disclosures.
3. **`backend/artifacts/experiment_results.json`**:
   - Stores `"mean_latency_seconds": 4e-05` (40 microseconds) and `"mean_latency_seconds": 0.000195` (195 microseconds). These are pure in-memory Python mock CPU benchmarks, NOT live Gemini API calls (which take 1–5 seconds per call).

---

### Focus 3: Test Suite Regression & Offline Impact Analysis
1. **`test_b6_service_resilience_when_gemini_raises_exception` Failure**:
   - Command: `pytest backend/tests/e2e/test_tier2_boundary_corner.py`
   - Result: **FAILED** at line 222:
     ```
     FAILED backend/tests/e2e/test_tier2_boundary_corner.py::test_b6_service_resilience_when_gemini_raises_exception
     assert res_discovery["success"] is False
     AssertionError: assert True is False
     ```
   - Verbatim code in `backend/app/services/gemini_service.py` (lines 210–233):
     ```python
     except Exception as e:
         err_str = str(e)
         if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "quota" in err_str.lower():
             self._is_quota_exhausted = True
         # If rate-limited, quota exhausted (429), or unavailable, gracefully fall back to verified official discovery
         try:
             from app.services.discovery_registry import get_verified_candidates_for_countries
             detected_country = "Canada"
             ...
             candidates_raw = get_verified_candidates_for_countries([detected_country])
             sources = [{"title": c["title"], "url": c["url"]} for c in candidates_raw]
             return {
                 "success": True,
                 "text": f"Grounded discovery of official university degree and scholarship portals in {detected_country}.",
                 "candidates": [c["raw_data"] for c in candidates_raw],
                 "sources": sources,
                 "citations": sources,
                 "search_queries": [query],
                 "model_used": f"{self.model} (Verified Official Registry Fallback)"
             }
         except Exception:
             ...
     ```
   - When `service._client.models.generate_content.side_effect = RuntimeError(...)` is raised, `search_grounded_discovery` catches it and returns `"success": True` with data from `discovery_registry.py`! Thus, `res_discovery["success"]` is `True`, causing `assert res_discovery["success"] is False` to fail.
   - Similarly, in `analyze_url_and_extract_criteria` (lines 429–447), exceptions fall back to `discovery_registry.get_criteria_for_url_or_program` and return `"success": True`.

2. **Case Mismatch Failures in `test_f5` & `test_search_grounded_discovery_missing_key_error`**:
   - Files:
     - `backend/tests/e2e/test_tier1_feature_coverage.py:151` (`test_f5`)
     - `backend/tests/test_m1_grounding.py:48` (`test_search_grounded_discovery_missing_key_error`)
   - Verbatim failure:
     ```
     AssertionError: assert 'GEMINI_API_KEY is not configured' in 'Gemini API key is not configured or quota is exhausted.'
     ```
   - In `backend/app/services/gemini_service.py:122`:
     `"error": "Gemini API key is not configured or quota is exhausted."`
   - The string uses `"Gemini API key"` instead of `"GEMINI_API_KEY"`. In contrast, line 274 uses `"GEMINI_API_KEY is not configured."`.

3. **Offline Safety: Missing Mocks and Quota Leaks**:
   - `backend/tests/conftest.py` **does not exist**. Only `backend/tests/e2e/conftest.py` exists.
   - Pytest does NOT load `backend/tests/e2e/conftest.py` for tests located directly in `backend/tests/` (e.g. `test_graph.py`, `test_m3_workflow.py`, `test_m1_challenger_stress.py`).
   - Even in `backend/tests/e2e/conftest.py` (lines 28–48), the fixture only mocked `search_grounded_discovery` and `analyze_url_and_extract_criteria` on `re_agent_mod.gemini_service`.
   - Neither `conftest.py` nor the tests mocked `gemini_service.review_evidence_and_claims` or `gemini_service.generate_sop_draft`.
   - When `QualityReviewerAgent.execute_audit` ran (lines 214–220 in `backend/app/agents/quality_reviewer.py`):
     ```python
     if gemini_service.is_available and opportunities:
         candidates_to_audit = [o for o in opportunities if o.is_top_five] or opportunities[:5]
         for candidate in candidates_to_audit:
             audit_res = await gemini_service.review_evidence_and_claims(...)
     ```
     Because `gemini_service.is_available` was True (due to `GEMINI_API_KEY` in environment), it executed 5 sequential LIVE HTTPS calls to Google Gemini for every top-5 candidate. This caused `test_tier3_cross_feature.py`, `test_tier4_real_world.py`, `test_graph.py`, and `test_m3_workflow.py` to hang on network latency and consume personal API quota.

4. **Tests Directly Impacted by R3 Grade Conversion Removal**:
   - In `backend/tests/test_m2_eligibility.py`:
     - Line 44: `assert extract_numeric_cgpa_cutoff("Minimum 3.2/4.0 GPA in Computer Science") == 8.0 # scaled to 10`
     - Line 47: `assert extract_numeric_cgpa_cutoff("Requires Second Upper Class Honours / B+ average") == 7.5`
   - In `backend/tests/test_tier5_adversarial_backend.py`:
     - Lines 146–151:
       ```python
       ("78% overall standing", 7.8),          # Percentage converted to 10 scale
       ("First class honours", 7.5),           # Qualitative benchmark
       ("First Class with Distinction", 8.0),  # Qualitative benchmark
       ("Second class upper", 7.5),            # Qualitative benchmark
       ("B+ average", 7.5),                    # Qualitative benchmark
       ("B average", 7.0),                     # Qualitative benchmark
       ```
   - When R3 removes linear scaling `(val / 4.0) * 10.0`, percentage division `(pct / 10.0)`, and hardcoded qualitative benchmarks, these functions will return `None` (or 3.2 on a 4.0 scale). These test assertions will fail unless updated to reflect that ungrounded conversions return `None` and result in `UNRESOLVED` criteria.

5. **Round 2 Re-research Reviewer Feedback Query Bug (R4)**:
   - In `backend/app/agents/research_eligibility.py` (lines 288–292):
     ```python
     if reviewer_issues and research_round > 1:
         issue_text = " ".join([str(issue.get("issue", issue)) if isinstance(issue, dict) else str(issue) for issue in reviewer_issues])
         if issue_text:
             query += f" official admissions {issue_text[:80]}"
     ```
   - Because `issue` strings from `quality_reviewer.py` contain student failure messages like `"Technical University of Munich: Student fails published mandatory admission criteria."`, the search query literally concatenated the student's personal failure reason into the Google Search query string.

---

## 2. Logic Chain

1. **Frontend Empty & Error States**:
   - *Observation*: `App.tsx` has only two visual outcomes for `opportunities.length === 0`: spinning wheel (if `!isCompleted` and not standby) or initial blank session prompt (if `isCompleted`).
   - *Logic*: An error in `startResearch` leaves `currentPhase = "ERROR"` and `isCompleted = false`, trapping the UI in the spinner. A run that completes with zero results (`DISCOVERY_EMPTY` or `QUOTA_EXHAUSTED`) sets `isCompleted = true`, trapping the UI in the blank "No research results in current session" state.
   - *Conclusion*: Explicit UI branches for `currentPhase === "ERROR"`, `currentPhase === "QUOTA_EXHAUSTED"` (or event received), and `currentPhase === "DISCOVERY_EMPTY"` (or event received) must be added to `App.tsx` to display distinct, actionable cards.

2. **Benchmark Transparency**:
   - *Observation*: `docs/EXPERIMENT.md` reports latencies of `4e-05s` and `0.000195s` under the header "Empirical Measurements & Results".
   - *Logic*: A human reader or evaluator can easily mistake these microsecond values for live Gemini API calls, creating an ungrounded or deceptive impression of LLM speed.
   - *Conclusion*: Project documentation must prominently label these figures as deterministic simulated in-memory benchmark harness measurements that isolate internal routing logic from external internet latency.

3. **`test_b6` Fix & Research Integrity (R1 & R5)**:
   - *Observation*: `search_grounded_discovery` catches `Exception` and returns `"success": True` with data from `discovery_registry.py`.
   - *Logic*: `test_b6` injects a `RuntimeError` into `models.generate_content` and asserts `res["success"] is False`. Because of the `discovery_registry.py` fallback, `res["success"]` is `True`, causing the test to fail.
   - *Conclusion*: Removing the fallback to `discovery_registry.py` in `gemini_service.py` ensures that exceptions and empty discovery return `"success": False` with explicit error descriptions, fixing `test_b6` and satisfying R1 and R5.

4. **Offline Test Safety**:
   - *Observation*: `QualityReviewerAgent.execute_audit` calls `gemini_service.review_evidence_and_claims` on all top-5 candidates. `conftest.py` only existed in `e2e/` and only mocked discovery/extraction, leaving review and SOP generation unmocked.
   - *Logic*: Running tests that invoke LangGraph or the quality reviewer executes live HTTP requests against the Gemini API whenever an API key is present, burning user quota and hanging indefinitely on network latency.
   - *Conclusion*: A root `backend/tests/conftest.py` must be created (or `backend/tests/e2e/conftest.py` expanded and placed at root) with an `autouse=True` fixture strictly mocking `search_grounded_discovery`, `analyze_url_and_extract_criteria`, `review_evidence_and_claims`, `generate_sop_draft`, and `check_connection`.

---

## 3. Caveats

- **Live Mode Testing**: `scripts/smoke_test_gemini.py` supports a `--live` flag for testing real Gemini credentials. The test mocking recommendations must be scoped to automated test suites (`pytest backend/tests`), ensuring CLI smoke test scripts remain able to test real API connectivity when explicitly invoked with `--live`.
- **Institution Equivalency Data**: Under R3, removing invented qualitative mappings ("First Class with Distinction" -> 8.0) means that unless the institution's published criteria text explicitly mentions the equivalency (e.g. *"B+ average, equivalent to 8.0/10 from Indian universities"*), the criterion will resolve to `UNRESOLVED` with an actionable gap. This is the intended behavior of R3, and test suites must be updated to expect `UNRESOLVED` instead of synthetic `MEETS`.
- No caveats regarding unexplored files; all assigned areas were thoroughly examined and verified with running commands.

---

## 4. Conclusion & Precise Recommended Changes

### A. Frontend Updates (`frontend/src/App.tsx`, `AgentWorkspace.tsx`, `index.html`)

#### 1. `frontend/index.html` (Line 7)
```html
<!-- BEFORE -->
<title>frontend</title>

<!-- AFTER -->
<title>ScholarSwarm — AI Scholarship Intelligence</title>
```

#### 2. `frontend/src/App.tsx`
- **State & Event Detection**: Add state variables or derived getters from `events`:
  ```typescript
  const quotaExhaustedEvent = events.find(
    (e) => e.event_type === "QUOTA_EXHAUSTED" || e.metadata?.status === "QUOTA_EXHAUSTED"
  );
  const discoveryEmptyEvent = events.find(
    (e) => e.event_type === "DISCOVERY_EMPTY"
  );
  const workflowErrorEvent = events.find(
    (e) => e.event_type === "ERROR"
  );
  ```
- **In `subscribeToEvents` (around line 100)**:
  Update phase tracking to avoid treating `DISCOVERY_EMPTY` as active `"DISCOVERY"`:
  ```typescript
  if (event.event_type === "QUOTA_EXHAUSTED") {
    setCurrentPhase("QUOTA_EXHAUSTED");
  } else if (event.event_type === "DISCOVERY_EMPTY") {
    setCurrentPhase("DISCOVERY_EMPTY");
  } else if (event.event_type === "ERROR") {
    setCurrentPhase("ERROR");
  } else if (event.event_type.includes("SEARCH") || event.event_type === "DISCOVERY_STARTED" || event.event_type.includes("CANDIDATE")) {
    setCurrentPhase("DISCOVERY");
  }
  ```
- **Empty & Error UI Branch in `App.tsx` (Replace lines 331–357)**:
  ```tsx
  {opportunities.length === 0 && (
    <div className="p-8 sm:p-12 text-center rounded-2xl bg-slate-900/60 border border-slate-800 space-y-4 shadow-xl">
      {/* 1. API Quota Exhausted State */}
      {currentPhase === "QUOTA_EXHAUSTED" || quotaExhaustedEvent ? (
        <>
          <div className="h-12 w-12 rounded-2xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-center text-rose-400 mx-auto">
            <AlertTriangle className="h-6 w-6" />
          </div>
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs font-semibold">
            429 RESOURCE_EXHAUSTED
          </div>
          <h3 className="text-lg font-bold text-white">Gemini API Quota Exhausted</h3>
          <p className="text-xs text-slate-300 max-w-lg mx-auto leading-relaxed">
            Live Google Search grounding and official URL Context extraction could not proceed because the Google Gen AI API quota limit has been reached. ScholarSwarm enforces strict research integrity and will not fabricate synthetic opportunities.
          </p>
          <div className="pt-2 flex items-center justify-center gap-3">
            <button
              onClick={() => setIsProfileModalOpen(true)}
              className="px-5 py-2 rounded-xl text-xs font-bold text-white bg-slate-800 hover:bg-slate-700 border border-slate-700 transition"
            >
              Configure Profile
            </button>
            <button
              onClick={() => handleStartResearch(profile)}
              className="px-5 py-2 rounded-xl text-xs font-bold text-white bg-emerald-600 hover:bg-emerald-500 shadow-lg shadow-emerald-700/20 transition inline-flex items-center gap-1.5"
            >
              <RefreshCw className="h-3.5 w-3.5" /> Retry Research
            </button>
          </div>
        </>
      ) : currentPhase === "DISCOVERY_EMPTY" || discoveryEmptyEvent ? (
        /* 2. Honest Empty Discovery State */
        <>
          <div className="h-12 w-12 rounded-2xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400 mx-auto">
            <Search className="h-6 w-6" />
          </div>
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-400 text-xs font-semibold">
            0 Programs Found
          </div>
          <h3 className="text-lg font-bold text-white">No Matching Programs Discovered</h3>
          <p className="text-xs text-slate-300 max-w-lg mx-auto leading-relaxed">
            Live Gemini Google Search grounding returned zero candidate degree programs matching your criteria across {profile.target_countries.join(', ')}. In accordance with our research integrity policy, no dummy or synthetic records were substituted.
          </p>
          <div className="pt-2 flex items-center justify-center gap-3">
            <button
              onClick={() => setIsProfileModalOpen(true)}
              className="px-5 py-2 rounded-xl text-xs font-bold text-white bg-emerald-600 hover:bg-emerald-500 shadow-lg shadow-emerald-700/20 transition"
            >
              Adjust Target Countries / Field
            </button>
          </div>
        </>
      ) : currentPhase === "ERROR" || workflowErrorEvent ? (
        /* 3. Explicit Workflow Error State (Fixes Infinite Spinner) */
        <>
          <div className="h-12 w-12 rounded-2xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-center text-rose-400 mx-auto">
            <AlertCircle className="h-6 w-6" />
          </div>
          <h3 className="text-lg font-bold text-white">Research Workflow Interrupted</h3>
          <p className="text-xs text-slate-400 max-w-lg mx-auto leading-relaxed">
            {workflowErrorEvent?.description || "An unexpected error occurred while executing the multi-agent research swarm."}
          </p>
          <div className="pt-2">
            <button
              onClick={() => handleStartResearch(profile)}
              className="px-5 py-2 rounded-xl text-xs font-bold text-white bg-emerald-600 hover:bg-emerald-500 shadow-lg shadow-emerald-700/20 transition inline-flex items-center gap-1.5"
            >
              <RefreshCw className="h-3.5 w-3.5" /> Restart Research
            </button>
          </div>
        </>
      ) : currentPhase !== "STANDBY" && !isCompleted ? (
        /* 4. Active In-Progress Execution */
        <>
          <RefreshCw className="h-10 w-10 text-emerald-400 mx-auto animate-spin" />
          <h3 className="text-base font-bold text-white">ScholarSwarm Research Cycle in Progress</h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto">
            The 5-agent research swarm is currently discovering opportunities, verifying official admissions criteria, and calculating match rankings...
          </p>
        </>
      ) : (
        /* 5. Initial Standby State */
        <>
          <GraduationCap className="h-10 w-10 text-emerald-400 mx-auto" />
          <h3 className="text-base font-bold text-white">Ready to Discover Scholarships</h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto">
            Launch the 5-agent research cycle to discover live scholarships across Canada, Germany, and Singapore tailored to your profile.
          </p>
          <button
            onClick={() => setIsProfileModalOpen(true)}
            className="px-5 py-2 rounded-xl text-xs font-bold text-white bg-emerald-600 hover:bg-emerald-500 shadow-lg shadow-emerald-700/20 transition inline-flex items-center gap-2"
          >
            Start Research Now
          </button>
        </>
      )}
    </div>
  )}
  ```

#### 3. `frontend/src/components/AgentWorkspace.tsx` (Line 147)
Update event styling:
```typescript
const isFlag = ev.event_type.includes("FLAG") || ev.event_type.includes("ERROR") || ev.event_type.includes("EXHAUSTED");
const isRetry = ev.event_type.includes("RETRY") || ev.event_type.includes("WARNING") || ev.event_type.includes("EMPTY");
```

---

### B. Benchmark Transparency Documentation Updates (`docs/EXPERIMENT.md` & `README.md`)

#### 1. `docs/EXPERIMENT.md`
- **Add Disclosure Banner in Section 2 & Section 3**:
  ```markdown
  > **Benchmark Transparency & Simulation Disclaimer**:
  > All latency metrics and performance results reported in this document were measured using the automated in-memory evaluation harness (`backend/scripts/evaluate_harness.py`). They represent deterministic simulated benchmark execution designed to evaluate agent routing, self-correction logic, and classification accuracy in an isolated, reproducible offline environment without consuming API quotas.
  > 
  > These numbers do **NOT** reflect live Google Gemini API network latency or live web scraping turnaround times, which typically range from 1 to 5 seconds per round in production.
  ```
- **Update Table Row in Section 3**:
  Change:
  `| **Mean End-to-End Latency** | 4e-05s | 0.000195s | +0.000155s |`
  To:
  `| **Mean Simulated Routing Latency (In-Memory Harness)** * | 4e-05s | 0.000195s | +0.000155s |`
  `\n* Deterministic mock harness execution measuring CPU routing overhead without external network latency.`
- **Update Section 4.5**:
  Change *"Bounded Latency Trade-Off"* to *"Bounded Algorithmic Routing Overhead (Simulated In-Memory)"*, clarifying that the +0.000155s represents internal agent routing and rule evaluation overhead in Python, and that production runs are bounded by the 2-round iteration ceiling.

#### 2. `README.md`
- Under `## 🧪 Automated Testing`:
  Add a clear note:
  ```markdown
  *Note on Performance Benchmarks*: The empirical evaluation harness (`backend/scripts/evaluate_harness.py`) executes in deterministic simulated benchmark mode to provide reproducible, offline verification of agent routing, classification accuracy, and fault recovery without consuming personal Gemini API quota.
  ```
- Under `## 📚 Deliverables & Documentation Index`:
  Change link label to:
  `- [Self-Correction Empirical Experiment (Deterministic Simulated Benchmarks)](docs/EXPERIMENT.md)`

---

### C. Backend & Test Suite Fixes

#### 1. Fix `test_b6` and Remove `discovery_registry.py` from `backend/app/services/gemini_service.py`
In `search_grounded_discovery` (lines 210–241), replace the fallback block:
```python
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "quota" in err_str.lower():
                self._is_quota_exhausted = True
            return {
                "success": False,
                "error": f"Gemini Search Grounding error: {err_str}",
                "candidates": [],
                "sources": [],
                "citations": [],
                "model_used": self.model
            }
```
In `analyze_url_and_extract_criteria` (lines 425–455), remove the `discovery_registry` try/except fallback and return:
```python
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "quota" in err_str.lower():
                self._is_quota_exhausted = True
            return {
                "success": False,
                "error": f"URL analysis error: {err_str}",
                "data": None,
                "retrieval_metadata": [],
                "url_retrieval_statuses": {},
                "is_retrieval_successful": False,
                "retrieval_status": "URL_RETRIEVAL_STATUS_ERROR",
                "evidence_quality": "UNVERIFIED"
            }
```

#### 2. Fix Case Mismatch in `backend/app/services/gemini_service.py` (Line 122)
Change:
```python
            return {
                "success": False,
                "error": "Gemini API key is not configured or quota is exhausted.",
                ...
            }
```
To:
```python
            return {
                "success": False,
                "error": "GEMINI_API_KEY is not configured or quota is exhausted.",
                ...
            }
```
This immediately resolves the failure in `test_tier1_feature_coverage.py::test_f5` and `test_m1_grounding.py::test_search_grounded_discovery_missing_key_error`.

#### 3. Root Test Suite Offline Isolation (`backend/tests/conftest.py`)
Create or promote a root `backend/tests/conftest.py` containing an autouse fixture so that all unit, workflow, and e2e tests run 100% offline without live calls or quota usage:
```python
import pytest
from unittest.mock import AsyncMock

@pytest.fixture(autouse=True)
def mock_all_gemini_calls_offline(monkeypatch):
    """
    Ensures zero external network calls or personal API quota consumption
    across the entire test suite.
    """
    from app.services.gemini_service import gemini_service
    from tests.fixtures.opportunities import get_mock_discovery_response, get_mock_url_analysis_response

    async def _mock_discovery(query: str, context_prompt: str):
        countries = [c for c in ["Canada", "Germany", "Singapore"] if c.lower() in query.lower()]
        return get_mock_discovery_response(countries=countries or None)

    async def _mock_extract(urls, program_name="", university="", student_profile_summary=""):
        url = urls[0] if urls else ""
        return get_mock_url_analysis_response(url)

    async def _mock_review(opportunity_data, student_data):
        return {
            "success": True,
            "data": {
                "approved": True,
                "confidence_rating": "HIGH",
                "issues_detected": [],
                "reviewer_notes": "Official university sources and evidence verified."
            }
        }

    async def _mock_sop(student_profile_dict, opportunity_dict, user_notes=None):
        return {
            "success": True,
            "data": {
                "title": f"Statement of Purpose - {opportunity_dict.get('program_name')}",
                "sop_content": f"Statement of purpose for {student_profile_dict.get('full_name')} at {opportunity_dict.get('university')}.",
                "unconfirmed_claims": [],
                "word_count": 200
            }
        }

    monkeypatch.setattr(gemini_service, "search_grounded_discovery", _mock_discovery)
    monkeypatch.setattr(gemini_service, "analyze_url_and_extract_criteria", _mock_extract)
    monkeypatch.setattr(gemini_service, "review_evidence_and_claims", _mock_review)
    monkeypatch.setattr(gemini_service, "generate_sop_draft", _mock_sop)
```

#### 4. Adjustments for Tests Impacted by R3 (Grade Conversion Removal)
- In `backend/tests/test_m2_eligibility.py`:
  - Update line 44: When 3.2/4.0 is not scaled to 10.0, assert `extract_numeric_cgpa_cutoff("Minimum 3.2/4.0 GPA in Computer Science") == 3.2` (or None if scale mismatch is strictly handled).
  - Update line 47: When qualitative requirement has no published numeric cutoff, assert `extract_numeric_cgpa_cutoff("Requires Second Upper Class Honours / B+ average") is None`.
- In `backend/tests/test_tier5_adversarial_backend.py` (lines 146–151):
  - Change expected values for un-equivalent qualitative and percentage phrases (`"78% overall standing"`, `"First class honours"`, `"First Class with Distinction"`, `"Second class upper"`, `"B+ average"`, `"B average"`) from `7.8`, `7.5`, `8.0`, etc. to `None`.
  - Add test asserting that when `profile.grading_scale != requirement_scale` without published equivalency, `evaluate_single_criterion` marks status as `UNRESOLVED` with an actionable gap.

#### 5. Dynamic Test Type in Application Coach (`backend/app/agents/application_coach.py:95`)
Change:
```python
f"Ensure planned language proficiency test (IELTS) is scheduled prior to {opportunity.deadline or 'application deadline'}."
```
To:
```python
test_name = (profile.language_tests.get("test") if isinstance(profile.language_tests, dict) else None) or "standardized language proficiency test"
...
f"Ensure planned {test_name} is scheduled prior to {opportunity.deadline or 'application deadline'}."
```

---

## 5. Verification Method

To independently verify all findings and test suite behavior:

1. **Verify `test_b6` Failure & Fix**:
   - Run: `pytest backend/tests/e2e/test_tier2_boundary_corner.py::test_b6_service_resilience_when_gemini_raises_exception -v`
   - Current result: Fails with `AssertionError: assert True is False`.
   - Invalidation condition: Passes once lines 215–233 in `gemini_service.py` are replaced with explicit error return.

2. **Verify Case Mismatch in Error Handling**:
   - Run: `pytest backend/tests/e2e/test_tier1_feature_coverage.py::test_f5_missing_api_key_returns_explicit_error_without_fallback -v`
   - Run: `pytest backend/tests/test_m1_grounding.py::test_search_grounded_discovery_missing_key_error -v`
   - Current result: Fails on line 122 casing.
   - Invalidation condition: Passes once line 122 contains `"GEMINI_API_KEY is not configured"`.

3. **Verify Frontend Build**:
   - Run: `npm run build` in `frontend/`
   - Current result: Passes cleanly in 5.25s with 0 errors.

4. **Verify Offline Test Execution**:
   - Run: `pytest backend/tests/test_scoring.py backend/tests/test_documents.py backend/tests/test_github.py backend/tests/test_api.py backend/tests/test_profile.py backend/tests/test_smoke_gemini.py -v`
   - Current result: All 31 tests pass cleanly in under 10 seconds.
