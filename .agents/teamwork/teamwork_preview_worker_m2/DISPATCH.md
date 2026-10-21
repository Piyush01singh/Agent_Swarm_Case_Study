## 2026-10-20T22:01:47Z
Your identity is: Worker M2 (Strict Eligibility & Domain/Deadline Verification).
Your working directory is: D:\Case_study_drive\TetraNoodle_AI_Hackathon\.agents\teamwork\teamwork_preview_worker_m2
Original request file path: D:\Case_study_drive\TetraNoodle_AI_Hackathon\.agents\teamwork\ORIGINAL_REQUEST.md
Project plan file path: D:\Case_study_drive\TetraNoodle_AI_Hackathon\PROJECT.md
Survey 1 report path: D:\Case_study_drive\TetraNoodle_AI_Hackathon\.agents\teamwork\teamwork_preview_explorer_survey_1\handoff.md

You MUST read ORIGINAL_REQUEST.md and PROJECT.md first before starting work.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Your exclusive write ownership:
- `backend/app/agents/research_eligibility.py`
- `backend/app/agents/quality_reviewer.py`
- `backend/app/services/scoring_service.py`
- `backend/app/security/sanitizer.py`
- `backend/tests/test_m2_eligibility.py`

Your tasks:
1. Feature F6 (Program-Specific Criteria Matching):
   In `backend/app/agents/research_eligibility.py`, eliminate generic country-level CGPA assumptions. Compare student grades, degree prerequisites, and language scores directly against extracted program-specific criteria.
2. Feature F7 (Verbatim Quotes & UNRESOLVED Classification):
   Ensure extracted evidence excerpts are authentic verbatim quotes from retrieved official content; never synthesize or fabricate quotes. Unverified criteria or missing rules must be explicitly classified as `UNRESOLVED` with clear uncertainty notes and actionable gaps.
3. Feature F8 (Admission vs Scholarship Distinction):
   Distinctly separate university admission requirements from scholarship criteria in data models and evaluation. Apply mandatory admission checks before ranking.
4. Feature F9 (Runtime Deadline Verification):
   In `backend/app/agents/quality_reviewer.py` and `backend/app/services/scoring_service.py`, compare deadlines against `datetime.now(timezone.utc).date()`. Flag historical or passed deadlines as `EXPIRED` / passed and never present them as active. Distinguish rolling or unannounced intakes (`ROLLING` / `UNKNOWN`). Do NOT award deadline readiness score to expired deadlines.
5. Feature F10 (Robust Official Domain Verification):
   In `backend/app/security/sanitizer.py` and `backend/app/agents/quality_reviewer.py`, replace simplistic domain substring checks (e.g. searching for '.org' or '.ca') with parsed hostname verification against an authoritative educational and official scholarship provider policy (`.edu`, `.ac.*`, and verified official registry).
6. Create `backend/tests/test_m2_eligibility.py`:
   Write unit and contract tests verifying F6, F7, F8, F9, and F10.
7. Run tests:
   - `pytest tests/test_m2_eligibility.py -v`
   - `pytest tests/e2e/test_tier1_feature_coverage.py -k "f6 or f7 or f8 or f9 or f10" -v`
   - `pytest tests/test_m1_grounding.py -v`
   Ensure all tests pass cleanly without regressions.

Deliver your complete report to:
`D:\Case_study_drive\TetraNoodle_AI_Hackathon\.agents\teamwork\teamwork_preview_worker_m2\handoff.md`.
Maintain `progress.md` in your directory and send a message when done.
