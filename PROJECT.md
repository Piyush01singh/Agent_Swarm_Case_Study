# Project: ScholarSwarm Pipeline Audit & Grounding Repair

## Architecture
ScholarSwarm is a multi-agent system designed to discover international graduate scholarships, evaluate strict admission and funding eligibility from verified source documents, formulate application strategies, and generate tailored statements of purpose.

### System Architecture
```
                                 [Student Profile]
                                        │
                                        ▼
                           ┌─────────────────────────┐
                           │ 1. Profile Intelligence │
                           └────────────┬────────────┘
                                        │ (Normalized Profile)
                                        ▼
             ┌─────────────────────────────────────────────────────┐
             │            2. Research & Eligibility                │◄────────┐
             │  - Gemini Search Grounding (Live Discovery)         │         │
             │  - Google GenAI SDK URL Context (Live Extraction)   │         │
             │  - Criterion-Level Matching (Admission vs Funding)  │         │
             │  - Verbatim Excerpts & UNRESOLVED Classifications   │         │
             └──────────────────────────┬──────────────────────────┘         │
                                        │ (Candidates + Evidence)            │
                                        ▼                                    │
                           ┌─────────────────────────┐                       │
                           │   3. Match Strategist   │                       │
                           │  - Multi-factor Scoring │                       │
                           │  - Shortlist & Gaps     │                       │
                           └────────────┬────────────┘                       │ Re-research Loop
                                        │ (Scored Shortlist)                 │ (Max 2-3 rounds)
                                        ▼                                    │
                           ┌─────────────────────────┐                       │
                           │   5. Quality Reviewer   │                       │
                           │  - Domain Verification  │                       │
                           │  - Funding & Deadline   │───────────────────────┘
                           │  - Evidence Audit       │ (Flagged Issues)
                           └────────────┬────────────┘
                                        │ (Approved Shortlist)
                                        ▼
                                 [FastAPI / DB]
                                        │
                    ┌───────────────────┴───────────────────┐
                    ▼                                       ▼
        ┌───────────────────────┐               ┌────────────────────────┐
        │ 4. Application Coach  │               │   Frontend UI (React)  │
        │ - On-demand SOP Draft │               │ - Opportunity Cards    │
        │ - Grounded in Facts   │               │ - Evidence Drawer      │
        └───────────────────────┘               │ - Gap Planner & SOP    │
                                                └────────────────────────┘
```

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| F1 | Eliminate `REAL_OPPORTUNITIES_BASE` | Remove hardcoded opportunity fixtures from live code paths into `backend/tests/fixtures/opportunities.py`. | M1 | R1, Survey 1 |
| F2 | Gemini Search Grounding Discovery | Discover candidate opportunities via genuine Gemini Google Search grounding with student profile parameters, extract URLs and authentic source metadata, deduplicate candidates. | M1 | R1, Survey 1 |
| F3 | Google Gen AI SDK URL Context Tool | Retrieve official candidate pages using `types.Tool(url_context=types.UrlContext())` via `google-genai` SDK. | M1 | R1, Survey 1 |
| F4 | Retrieval Metadata Handling | Inspect `UrlContextMetadata` and distinguish `URL_RETRIEVAL_STATUS_SUCCESS` from `ERROR`, `PAYWALL`, `UNSAFE`. | M1 | R1, Survey 1 |
| F5 | Explicit API Configuration Errors | Raise explicit error on missing `GEMINI_API_KEY` in live pipeline without silent fallbacks to dummy records. | M1 | R1, Survey 1 |
| F6 | Program-Specific Criteria Matching | Remove generic country-level CGPA assumptions; compare student grades, degree prerequisites, and language scores directly against extracted published criteria. | M2 | R2, Survey 1 |
| F7 | Verbatim Quotes & `UNRESOLVED` Classification | Extract authentic excerpts verbatim; unverified or missing rules must be explicitly classified as `UNRESOLVED`. | M2 | R2, Survey 1 |
| F8 | Admission vs Scholarship Distinction | Distinctly separate university admission requirements from scholarship eligibility criteria in data models and evaluations. | M2 | R2, Survey 1 |
| F9 | Runtime Deadline Verification | Compare application deadlines against `datetime.now(timezone.utc).date()`. Flag historical or passed deadlines as `EXPIRED` / passed, distinguishing rolling/unannounced intakes. | M2 | R3, Survey 1 |
| F10 | Robust Official Domain Verification | Replace simplistic domain substring checks with parsed domain verification against an authoritative educational/official provider policy. | M2 | R3, Survey 1 |
| F11 | 5-Agent Architecture Alignment | Maintain the five distinct agent roles with clear operational boundaries. | M3 | R4, Survey 1 |
| F12 | Bounded Quality Reviewer Loop | Wire rejection loop to feed `reviewer_issues` back to Research & Eligibility; enforce termination within `max_research_rounds`. | M3 | R4, Survey 1 |
| F13 | Cross-Round Candidate Preservation | Preserve approved candidates across re-research iterations instead of overwriting `state.opportunities`. | M3 | R4, Survey 1 |
| F14 | Comprehensive Reviewer Audit | Review all shortlisted candidate opportunities, not only the top index. | M3 | R4, Survey 1 |
| F15 | On-Demand Application Coach SOP | Keep Application Coach exposed for selected opportunity SOP generation, operating cleanly on verified facts. | M3 | R4, Survey 1 |
| F16 | Database & Repository Consistency | Fix `repository.py` bugs: persist/retrieve `evidence_records` in Supabase; fix `get_opportunity_by_id` index `[0]` bug. | M3 | R4, Survey 3 |
| F17 | Pytest Discovery Configuration | Add `backend/pytest.ini` with `pythonpath = .` so `pytest` and `python -m pytest` execute cleanly. | M4 | R5, Survey 2 |
| F18 | Missing Test Suite `test_quality_reviewer.py` | Implement comprehensive unit and workflow integration tests for Quality Reviewer agent to fix documented test command. | M4 | R5, Survey 2 |
| F19 | Reproducible Evaluation Harness | Implement `backend/scripts/evaluate_harness.py` with 10 documented test cases, baseline vs self-correcting comparative runs, controlled failure injection, latency, source coverage, and eligibility accuracy metrics. | M4 | R5, Survey 2 |
| F20 | Evaluation Harness Automated Tests | Implement `backend/tests/test_evaluation_harness.py` to ensure CI coverage of harness. | M4 | R5, Survey 2 |
| F21 | Honest Experiment Documentation | Update `docs/EXPERIMENT.md` with true empirical measurements generated by the evaluation harness, replacing fabricated placeholders. | M4 | R5, Survey 2 |
| F22 | Frontend Rules of Hooks Fix | Fix React Rules of Hooks violation in `SopWorkspace.tsx` so `npm run lint` passes cleanly. | M5 | R6, Survey 3 |
| F23 | Remove Synthetic UI Fallbacks | Eliminate `|| 3` in `OpportunityCard.tsx`, `|| 'OFFICIAL'` in `EvidenceDrawer.tsx`, and silent `slice(0, 5)` in `GapPlanner.tsx`. | M5 | R6, Survey 3 |
| F24 | Frontend Evidence Fetching & Env Config | Ensure `App.tsx` fetches full opportunity details on demand; add `envDir: '../'` in `vite.config.ts`. | M5 | R6, Survey 3 |
| F25 | Full Test Suite & Build Verification | Pass 100% of backend pytest suite and frontend production build (`npm run build`). | M6 | R6, Sentinel |
| F26 | Live Gemini Smoke Test Runner | Implement and run live Gemini smoke test runner when credentials are present. | M6 | R6, Sentinel |
| F27 | Adversarial Coverage Hardening (Tier 5) | White-box adversarial testing with Challenger, Worker, Reviewer, and Forensic Auditor verification. | M6 | R6, Pattern |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| E2E | E2E Testing Track | Requirement-driven opaque-box test suites (Tiers 1-4) published to `TEST_READY.md`. Output: 55 tests passing in `backend/tests/e2e/`, `TEST_INFRA.md`. | none | DONE |
| M1 | Grounded Discovery & Real Extraction | F1, F2, F3, F4, F5: Live search grounding, URL context tool, remove hardcoded opportunities to test fixtures, explicit API config errors. Outputs: `gemini_service.py`, `research_eligibility.py`, `test_m1_grounding.py` (14 tests passed, 0 hardcoded opportunities, Gate PASS). | none | DONE |
| M2 | Strict Eligibility & Domain/Deadline Verification | F6, F7, F8, F9, F10: Program-specific criteria matching, verbatim quotes, UNRESOLVED markers, admission vs scholarship separation, runtime deadline validation, robust official domain policy. Output: 22 tests in `test_m2_eligibility.py`, 74 total regression tests passed, Gate PASS. | M1 | DONE |
| M3 | 5-Agent Workflow, Bounded Loop & Fault Recovery | F11, F12, F13, F14, F15, F16: LangGraph rejection feedback loop, candidate preservation across rounds, comprehensive reviewer audit, repository Supabase fixes. Outputs: `state.py`, `workflow.py`, `quality_reviewer.py`, `repository.py`, `test_m3_workflow.py` (8/8 tests passed, 45 regression tests passed, 139 full suite passed, Gate PASS). | M2 | DONE |
| M4 | Reproducible Experiment Harness & Docs | F17, F18, F19, F20, F21: `pytest.ini`, `test_quality_reviewer.py`, `evaluate_harness.py`, `test_evaluation_harness.py`, honest `docs/EXPERIMENT.md`. Outputs: `backend/pytest.ini`, `test_quality_reviewer.py` (9 tests), `evaluate_harness.py` (10 benchmark cases), `test_evaluation_harness.py` (3 tests), `artifacts/experiment_results.json`, honest `docs/EXPERIMENT.md` (102 regression tests pass, Gate PASS). | M3 | DONE |
| M5 | Frontend Real Data Audit & Deployability | F22, F23, F24: Rules of Hooks fix in `SopWorkspace.tsx`, remove UI fallbacks (`|| 3`, `|| 'OFFICIAL'`), full gap display, `envDir` config. Outputs: `SopWorkspace.tsx`, `OpportunityCard.tsx`, `EvidenceDrawer.tsx`, `GapPlanner.tsx`, `App.tsx`, `vite.config.ts` (oxlint 0 errors, npm run build exits 0, Gate PASS). | M3 | DONE |
| M6 | Final Verification & Adversarial Hardening | F25, F26, F27: 100% Pass of E2E test suite (Tiers 1-4), pytest pass, npm run build pass, live smoke test, Tier 5 adversarial testing, Forensic Audit CLEAN verdict. | M4, M5, E2E | IN_PROGRESS |

## Interface Contracts

### Research Discovery ↔ URL Extraction
- Input: `query: str`, `context_prompt: str`
- Tool: `types.Tool(google_search=types.GoogleSearch())`
- Output: `List[Dict[str, Any]]` containing canonical URL, title, snippet.
- Extraction: `types.Tool(url_context=types.UrlContext())`
- Retrieval Verification:
  ```python
  candidate.url_context_metadata.url_metadata[i].url_retrieval_status == types.UrlRetrievalStatus.URL_RETRIEVAL_STATUS_SUCCESS
  ```
- Error Handling: If status is `ERROR`, `PAYWALL`, or `UNSAFE`, classify as `SECONDARY` or `UNRESOLVED`; do not fabricate text or crash.

### Quality Reviewer ↔ Research Discovery Re-Research Loop
- `SwarmState`:
  ```python
  class SwarmState(BaseModel):
      run_id: str
      student_profile: StudentProfile
      research_round: int = 1
      max_research_rounds: int = 2
      opportunities: List[Opportunity] = []
      approved_opportunities: List[Opportunity] = []
      reviewer_issues: List[Dict[str, Any]] = []
      needs_re_research: bool = False
  ```
- Feedback Protocol:
  When `needs_re_research` is True and `research_round < max_research_rounds`, `route_after_review` returns `"research_discovery"`.
  `node_research_discovery` passes `state.reviewer_issues` into `ResearchEligibilityAgent`.
  `opportunities` combines preserved approved opportunities with newly resolved opportunities.

### Backend ↔ Frontend API Contract
- `GET /api/research/{run_id}/opportunities`: Returns `List[Opportunity]`
  - `evidence_records`: `List[EvidenceRecord]`
  - `evidence_quality`: `"OFFICIAL"` | `"SECONDARY"` | `"UNVERIFIED"`
  - `deadline`: `YYYY-MM-DD` | `None`
  - `deadline_status`: `"ACTIVE"` | `"EXPIRED"` | `"ROLLING"` | `"UNKNOWN"`
  - `actionable_gaps`: `List[str]`
- `POST /api/opportunities/{id}/sop`:
  - Request: `{"run_id": str, "user_notes": Optional[str]}`
  - Response: `ApplicationDraft`

## Code Layout
```
backend/
├── app/
│   ├── agents/
│   │   ├── application_coach.py
│   │   ├── match_strategist.py
│   │   ├── profile_intelligence.py
│   │   ├── quality_reviewer.py
│   │   └── research_eligibility.py
│   ├── api/
│   │   ├── health.py
│   │   ├── opportunities.py
│   │   ├── profile.py
│   │   └── research.py
│   ├── db/
│   │   ├── repository.py
│   │   └── supabase.py
│   ├── graph/
│   │   ├── state.py
│   │   └── workflow.py
│   ├── models/
│   │   ├── opportunity.py
│   │   └── profile.py
│   └── services/
│       ├── gemini_service.py
│       └── scoring_service.py
├── scripts/
│   ├── evaluate_harness.py
│   └── smoke_test_gemini.py
├── tests/
│   ├── e2e/
│   │   ├── conftest.py
│   │   ├── test_tier1_feature_coverage.py
│   │   ├── test_tier2_boundary_corner.py
│   │   ├── test_tier3_cross_feature.py
│   │   └── test_tier4_real_world.py
│   ├── fixtures/
│   │   └── opportunities.py
│   ├── test_api.py
│   ├── test_documents.py
│   ├── test_eligibility.py
│   ├── test_evaluation_harness.py
│   ├── test_github.py
│   ├── test_graph.py
│   ├── test_m1_grounding.py
│   ├── test_m1_challenger_stress.py
│   ├── test_profile.py
│   ├── test_quality_reviewer.py
│   └── test_scoring.py
├── pytest.ini
└── requirements.txt

frontend/
├── src/
│   ├── components/
│   │   ├── AgentWorkspace.tsx
│   │   ├── EvidenceDrawer.tsx
│   │   ├── GapPlanner.tsx
│   │   ├── Navbar.tsx
│   │   ├── OpportunityCard.tsx
│   │   ├── ProfileModal.tsx
│   │   └── SopWorkspace.tsx
│   ├── api/
│   │   └── client.ts
│   ├── types/
│   │   └── index.ts
│   ├── App.tsx
│   └── main.tsx
├── package.json
└── vite.config.ts

docs/
├── EXPERIMENT.md
└── SYSTEM_AUDIT.md
```
