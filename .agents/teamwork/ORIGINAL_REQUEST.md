# Original User Request

## Initial Request — 2026-10-20T21:08:53Z

Audit and repair ScholarSwarm's research and eligibility pipeline, eliminating hardcoded opportunities, correctly wiring Gemini Search grounding and official URL Context, enforcing strict evidence integrity, creating a reproducible evaluation experiment, and verifying end-to-end frontend and backend behavior.

Working directory: D:\Case_study_drive\TetraNoodle_AI_Hackathon
Integrity mode: development

## Requirements

### R1. Live Grounded Discovery & Real Extraction Pipeline
- Remove hardcoded opportunities (`REAL_OPPORTUNITIES_BASE`) from the live research pipeline; move any useful fixtures exclusively into isolated test suites.
- Discover candidate opportunities via genuine Gemini Google Search grounding with student profile parameters, extract URLs and authentic source metadata, and deduplicate candidates.
- Retrieve official candidate pages using the official Gemini URL Context tool via the current Google Gen AI SDK (`google-genai`). Distinguish retrieved pages from failed, unsafe, or missing URLs using API retrieval metadata.
- Return only genuinely retrieved and evaluated opportunities without fabricating records to meet arbitrary quotas. Report verified count honestly.

### R2. Strict Eligibility Evaluation & Source Evidence Integrity
- Remove generic country-wide assumptions (e.g. universal CGPA cutoffs or treating any test status as passing). Compare student grades, degree prerequisites, and language scores directly against extracted published criteria.
- Extract verbatim evidence excerpts directly from retrieved source content; never synthesize or fabricate quotes. Unverified criteria or missing rules must be explicitly classified as `UNRESOLVED`.
- Apply mandatory eligibility checks before ranking. Distinctly separate university admission requirements from scholarship criteria.
- Record actual check and retrieval timestamps.

### R3. Current Deadline & Official Domain Verification
- Evaluate deadline status against the application runtime date. Distinguish passed deadlines from rolling or unannounced intakes. Historical or past-cycle deadlines must not be shown as current.
- Replace simplistic domain substring checks with a robust, verifiable official provider policy. Unverified funding amounts or deadlines must remain labelled as unknown.

### R4. Five-Agent Workflow Alignment & Fault Recovery
- Maintain the five agent roles (Profile Intelligence, Research & Eligibility, Match Strategist, Application Coach, Quality Reviewer).
- Ensure the Quality Reviewer can route specific validation failures back to Research & Eligibility with a bounded maximum loop count.
- Keep the Application Coach exposed for selected opportunity SOP generation, documenting the invocation boundary accurately without claiming it ran during research discovery.
- Ensure partial branch failures do not discard successfully retrieved opportunities.

### R5. Reproducible & Honest Experiment Harness
- Update `docs/EXPERIMENT.md` by removing unverified or fabricated performance claims.
- Provide a runnable Python evaluation harness with documented test cases comparing single-pass vs. Quality Reviewer correction loops, injecting controlled retrieval failures, and measuring latency, source coverage, and eligibility accuracy.
- Fix all missing test commands (including `test_quality_reviewer.py`) and write reproducible results to artifacts.

### R6. End-to-End Verification, Frontend Audit & Deployability
- Audit frontend components (Opportunity cards, Evidence Drawer, Gap Planner, SOP generator) to ensure they render real pipeline results and actual source links, without synthetic fallbacks.
- Provide comprehensive backend test suite (unit + mocked integration) and a live Gemini smoke test runner when credentials are present.
- Verify frontend production build (`npm run build`) and backend tests (`pytest`) pass cleanly.
- Preserve existing tech stack (React + Vite, FastAPI, Supabase schema, Cloudflare/Render deployment setup) without introducing extraneous dependencies.

## Acceptance Criteria

### Research & Verification Pipeline
- [ ] No hardcoded opportunities exist in live research code paths (`REAL_OPPORTUNITIES_BASE` removed or isolated in test fixtures).
- [ ] Gemini URL Context is configured with explicit tool enablement via official Gen AI SDK, and URL retrieval metadata is verified.
- [ ] Every verified opportunity has real citation URLs, accurate retrieval statuses, and genuine source quotes.
- [ ] CGPA and language requirements are checked against specific program criteria, marking unmet or unknown requirements as failed or unresolved.
- [ ] Expired application cycles are flagged as passed and never presented as active.
- [ ] Missing API keys trigger explicit configuration errors, never silent fallbacks to fabricated records.

### Workflow & Experiment Reproducibility
- [ ] Quality Reviewer rejection loop executes and terminates within the configured iteration limit.
- [ ] The experiment harness executes via a documented CLI command, runs reproducible test cases, and outputs honest empirical data to `docs/EXPERIMENT.md`.
- [ ] All test scripts referenced in documentation execute cleanly.

### System Verification & Build
- [ ] Full backend pytest suite passes cleanly.
- [ ] Frontend builds successfully (`npm run build`) without TypeScript or bundling errors.
- [ ] Application Coach SOP generation operates cleanly on selected opportunities with verified student facts.
- [ ] Final audit report details modified files, research data flow, test outputs, live verification status, and experiment findings.


## Follow-up — 2026-10-22T01:12:26Z

Execute the high-impact repairs on the ScholarSwarm scholarship intelligence platform to address the 7 critical evaluation findings with minimal changes, restoring research integrity, failure handling, eligibility accuracy, and offline test safety.

Working directory: d:/Case_study_drive/TetraNoodle_AI_Hackathon
Integrity mode: development

## Requirements

### R1. Remove Synthetic Live Fallbacks
Remove fallback to `discovery_registry.py` from live code paths in `backend/app/services/gemini_service.py` and `backend/app/agents/research_eligibility.py`. If Google Search grounding yields 0 candidates or quota fails, return an honest `DISCOVERY_EMPTY` / `QUOTA_EXHAUSTED` status without synthetic data or fake "Verified Official Registry" claims. Ensure the frontend gracefully displays an explicit error / empty-state message. Keep registry data strictly for test fixtures if needed.

### R2. Fix Quality Reviewer Fail-Open Behavior
In `backend/app/services/gemini_service.py` (`review_opportunity_claims`), when Gemini quota is exhausted or unavailable (`_is_quota_exhausted`, not `is_available`, or `RESOURCE_EXHAUSTED`), never return `approved: True` with "HIGH" confidence. Return `{"success": False, "error": "QUOTA_EXHAUSTED", "approved": False}` and mark the review status as unreviewed / unresolved.

### R3. Remove Invented Universal Grade Conversion Formulas
In `backend/app/agents/research_eligibility.py` (`extract_numeric_cgpa_cutoff` and related helpers), remove linear 4.0-to-10.0 scaling, percentage-to-CGPA dividing formulas, and hardcoded qualitative mappings ("first class with distinction" -> 8.0, "b+ average" -> 7.5) unless supported by the institution's published equivalency guidance. When a student's scale and requirement scale differ without published equivalency, flag status as `UNRESOLVED` with an actionable gap description.

### R4. Fix Reviewer Feedback Query Construction
In `backend/app/agents/research_eligibility.py`, during round 2 re-research, replace raw reviewer error string concatenation (which appends student failure reasons to the search query) with short, targeted search queries derived specifically from the opportunity provider, program name, and the specific unresolved admission criterion.

### R5. Test Suite Offline Safety & Boundary Exception Handling
In `backend/tests/e2e/conftest.py`, ensure all external Gemini calls—including `review_evidence_and_claims` and `review_opportunity_claims`—are strictly mocked so no tests consume personal API quota or hang on network latency. In `backend/app/services/gemini_service.py` (`search_grounded_discovery`), ensure unexpected connection exceptions propagate or return explicit failures (`{"success": False, ...}`) so that `test_b6_service_resilience_when_gemini_raises_exception` passes.

### R6. Clarify Agent 4 Architecture & Polish UI/Templates
In `docs/ARCHITECTURE.md` and `README.md`, document that Agent 4 (Application Coach) operates as an on-demand application specialist rather than an autonomous looping node in LangGraph. In `frontend/index.html`, set the title to `ScholarSwarm — AI Scholarship Intelligence`. In `backend/app/agents/application_coach.py`, dynamically inject the applicant's actual test type into SOP fallback drafting instead of defaulting rigidly to GRE.

### R7. Benchmark Transparency
Label mock-harness measurements in project documentation as deterministic simulated benchmarks rather than live Gemini API performance measurements.

## Acceptance Criteria

### Research Integrity & Fail-Safe Handling
- [ ] No import or invocation of `discovery_registry.py` exists in production runtime paths (`gemini_service.py`, `research_eligibility.py`).
- [ ] Exhausted quota or empty search produces explicit failure/empty responses rather than synthetic opportunities or false "HIGH" confidence ratings.
- [ ] Reviewer issue queries in round 2 re-research are clean targeted phrases without student failure notes concatenated.

### Eligibility Accuracy
- [ ] Incompatible grading scales without published institution equivalencies resolve to `UNRESOLVED` with specific actionable gap feedback instead of calculated conversion formulas.

### Test Suite & Offline Isolation
- [ ] `pytest` runs completely offline with zero network calls and zero quota consumption.
- [ ] `pytest backend/tests/e2e/test_tier2_boundary_corner.py` passes completely (including `test_b6`).
- [ ] Frontend production build (`npm run build` in `frontend/`) completes cleanly with zero errors.

### Documentation & UI Integrity
- [ ] `frontend/index.html` has title `ScholarSwarm — AI Scholarship Intelligence`.
- [ ] Architecture documentation accurately explains Agent 4's on-demand invocation pattern.
- [ ] No secrets, keys, or credentials modified or exposed.
