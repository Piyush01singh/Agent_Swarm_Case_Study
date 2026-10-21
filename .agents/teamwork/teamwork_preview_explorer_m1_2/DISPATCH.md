# Dispatch Task: Explorer M1.2 (Research Agent Extraction & Fixture Isolation)

- **Target Directory**: D:\Case_study_drive\TetraNoodle_AI_Hackathon\.agents\teamwork\teamwork_preview_explorer_m1_2
- **Original Request**: D:\Case_study_drive\TetraNoodle_AI_Hackathon\.agents\teamwork\ORIGINAL_REQUEST.md
- **Project Scope**: D:\Case_study_drive\TetraNoodle_AI_Hackathon\PROJECT.md
- **Role**: Plan the extraction of `REAL_OPPORTUNITIES_BASE` into `backend/tests/fixtures/opportunities.py` and constructing real `Opportunity` records from live web discovery.

## 2026-10-20T21:21:20Z
Sender: 6828b193-f5c1-4991-90e8-8c39694edfd6
Message:
Your identity is: Explorer M1.2 (Research Agent Extraction & Fixture Isolation).
Your working directory is: D:\Case_study_drive\TetraNoodle_AI_Hackathon\.agents\teamwork\teamwork_preview_explorer_m1_2
Original request file path: D:\Case_study_drive\TetraNoodle_AI_Hackathon\.agents\teamwork\ORIGINAL_REQUEST.md
Project plan file path: D:\Case_study_drive\TetraNoodle_AI_Hackathon\PROJECT.md

You MUST read ORIGINAL_REQUEST.md and PROJECT.md first before starting work.

Your mission:
Deeply investigate `backend/app/agents/research_eligibility.py` to plan the exact refactor for Milestone M1:
1. Extract `REAL_OPPORTUNITIES_BASE` (lines 15-295) into `backend/tests/fixtures/opportunities.py`. Ensure ZERO hardcoded opportunity fixtures remain in live research code paths.
2. In `execute_discovery_and_audit`, eliminate lines 364-379 iterating `REAL_OPPORTUNITIES_BASE`.
3. Plan how `Opportunity` models will be instantiated dynamically from the Gemini search grounding and URL Context extraction results.
4. Provide exact code diffs and step-by-step instructions for the Worker.
Write your report to:
`D:\Case_study_drive\TetraNoodle_AI_Hackathon\.agents\teamwork\teamwork_preview_explorer_m1_2\handoff.md`.
Maintain `progress.md` and send a message upon completion.
