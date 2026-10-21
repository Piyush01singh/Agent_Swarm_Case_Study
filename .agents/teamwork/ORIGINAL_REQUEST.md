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
