# DISPATCH — Explorer Repair 1

**Task**: Technical exploration and remediation plan for R1, R2, and R5 (Gemini Service, Fail-Safe Quota Handling, Boundary Exception Handling & Offline Conftest Mocking).
**Authoritative Request**: Read `D:\Case_study_drive\TetraNoodle_AI_Hackathon\.agents\teamwork\ORIGINAL_REQUEST.md` (specifically header `## Follow-up — 2026-10-22T01:12:26Z`).
**Working Directory**: `D:\Case_study_drive\TetraNoodle_AI_Hackathon\.agents\teamwork\teamwork_preview_explorer_repair_1`

## 2026-10-22T01:15:39Z
You are Explorer 1 (Role: Research Integrity Explorer).
Your working directory is D:\Case_study_drive\TetraNoodle_AI_Hackathon\.agents\teamwork\teamwork_preview_explorer_repair_1.
You MUST read D:\Case_study_drive\TetraNoodle_AI_Hackathon\.agents\teamwork\ORIGINAL_REQUEST.md before starting work (specifically the section '## Follow-up — 2026-10-22T01:12:26Z').

Your investigation focus:
1. R1: Remove synthetic live fallbacks.
   - Investigate all references to `discovery_registry.py` across `backend/app/services/gemini_service.py` and `backend/app/agents/research_eligibility.py`.
   - Determine how to purge any fallback to `discovery_registry.py` in live code paths.
   - If Google Search grounding yields 0 candidates or quota fails, determine exact return structure for honest `DISCOVERY_EMPTY` / `QUOTA_EXHAUSTED` status without synthetic data or fake "Verified Official Registry" claims.
2. R2: Fix Quality Reviewer fail-open behavior.
   - In `backend/app/services/gemini_service.py` (`review_opportunity_claims`), check where quota exhaustion or unavailability occurs (`_is_quota_exhausted`, `not is_available`, or `RESOURCE_EXHAUSTED`).
   - Ensure it NEVER returns `approved: True` with "HIGH" confidence when unavailable or exhausted. Determine exact return: `{"success": False, "error": "QUOTA_EXHAUSTED", "approved": False}` and mark the review status as unreviewed / unresolved.
3. R5: Test suite offline safety & boundary exception handling.
   - In `backend/tests/e2e/conftest.py`, inspect all external Gemini fixtures/mocks to ensure `review_evidence_and_claims` and `review_opportunity_claims` are strictly mocked so no tests consume personal API quota or hang on network latency.
   - In `backend/app/services/gemini_service.py` (`search_grounded_discovery`), determine why `test_b6_service_resilience_when_gemini_raises_exception` might fail or how unexpected connection exceptions must be caught and returned as explicit failures (`{"success": False, ...}`).

DO NOT write source code or modify production code. Provide precise file paths, line numbers, snippets, and exact recommended changes.
Write your complete findings and recommendations to `D:\Case_study_drive\TetraNoodle_AI_Hackathon\.agents\teamwork\teamwork_preview_explorer_repair_1\handoff.md`.
When finished, send a message to the orchestrator (conversation ID: 6caa988d-b978-4e37-94b4-b6ba138214d3).
