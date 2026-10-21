## 2026-10-20T22:32:49Z
Your identity is: Worker M2 Iteration 2 (Milestone M2 Rework & Defect Remediation).
Your working directory is: D:\Case_study_drive\TetraNoodle_AI_Hackathon\.agents\teamwork\teamwork_preview_worker_m2_iter2
Original request file path: D:\Case_study_drive\TetraNoodle_AI_Hackathon\.agents\teamwork\ORIGINAL_REQUEST.md
Project plan file path: D:\Case_study_drive\TetraNoodle_AI_Hackathon\PROJECT.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Input Handoff Reports to study and follow:
- Reviewer M2.1 Report: D:\Case_study_drive\TetraNoodle_AI_Hackathon\.agents\teamwork\teamwork_preview_reviewer_m2_1\handoff.md
- Reviewer M2.2 Report: D:\Case_study_drive\TetraNoodle_AI_Hackathon\.agents\teamwork\teamwork_preview_reviewer_m2_2\handoff.md
- Predecessor Worker M2 Report: D:\Case_study_drive\TetraNoodle_AI_Hackathon\.agents\teamwork\teamwork_preview_worker_m2\handoff.md

Your exclusive write ownership:
- `backend/app/agents/research_eligibility.py`
- `backend/app/services/scoring_service.py`
- `backend/app/security/sanitizer.py`
- `backend/app/models/opportunity.py`
- `backend/tests/test_m2_eligibility.py`
- `backend/tests/e2e/test_tier1_feature_coverage.py`

Your tasks:
1. Fix Critical Runtime Crash (NameError in candidate loop):
   In `backend/app/agents/research_eligibility.py`: inside the candidate evaluation loop of `execute_discovery_and_audit`, declare and initialize `actionable_gaps: List[str] = []` and `eligibility_reasons: List[str] = []` immediately alongside `evidence_records: List[EvidenceRecord] = []` (around line 444). Ensure all subsequent references append to these initialized lists.
2. Fix F8 Admission vs Scholarship Conflation:
   In `backend/app/agents/research_eligibility.py` (lines 515–522) and `backend/app/services/scoring_service.py` (lines 36–39):
   Ensure that failing an optional, competitive scholarship criterion does NOT flag `has_mandatory_failure = True`. Only criteria that are strictly mandatory university admission prerequisites (e.g. minimum degree, minimum GPA for entrance, language test for admission) should trigger `has_mandatory_failure = True`. If a student meets admission criteria but fails a scholarship criterion, they remain eligible for admission with partial funding / admission shortlist.
3. Fix F9 API Schema Contract (`deadline_status`):
   In `backend/app/models/opportunity.py`: Add `deadline_status: str = "UNKNOWN"` to the `Opportunity` class so that `opp.model_dump()` and FastAPI endpoints serialize `deadline_status` ("ACTIVE", "EXPIRED", "ROLLING", "UNKNOWN") per `PROJECT.md` API contract.
4. Fix F10 Domain Verification Regex Anchor (`is_official_domain`):
   In `backend/app/security/sanitizer.py`: Fix `is_official_domain` so that arbitrary subdomains containing `.ac.` or `.edu.` in untrusted domains (e.g. `evil.edu.attacker.org`, `scholarship.ac.fake.com`) are REJECTED. Anchor academic and governmental second-level domains to the end of the hostname preceding a 2-3 letter ccTLD using regex `re.search(r'\.(?:ac|edu|gov|gc)\.[a-z]{2,3}$', hostname)`.
5. Fix F6 Grading Scale Normalization:
   In `backend/app/agents/research_eligibility.py`: When evaluating student CGPA against extracted cutoffs scaled to 10.0, check `profile.grading_scale`. If `profile.grading_scale == "4.0"`, convert student CGPA to 10.0 scale (`(profile.cgpa / 4.0) * 10.0`) before comparing.
6. Clean up test import:
   In `backend/tests/e2e/test_tier1_feature_coverage.py`: Import `from app.security.sanitizer import is_official_domain` instead of using a locally defined function.
7. Run and verify the test suites:
   - `pytest tests/test_m2_eligibility.py -v`
   - `pytest tests/test_m1_challenger_stress.py -v`
   - `pytest tests/test_challenger_m1_stress.py -v`
   - `pytest tests/test_scoring.py -v`
   - `pytest tests/e2e/test_tier1_feature_coverage.py -k "f6 or f7 or f8 or f9 or f10" -v`
   - `pytest tests/test_m1_grounding.py -v`
   Confirm that all tests execute cleanly with 0 NameErrors and 0 regressions.

Deliver your complete handoff report to:
`D:\Case_study_drive\TetraNoodle_AI_Hackathon\.agents\teamwork\teamwork_preview_worker_m2_iter2\handoff.md`.
Maintain `progress.md` in your directory and send a message when done.
