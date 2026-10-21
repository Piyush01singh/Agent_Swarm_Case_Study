# Dispatch Task: Survey Explorer 1 (Backend Pipeline & Gemini Grounding)

- **Target Directory**: D:\Case_study_drive\TetraNoodle_AI_Hackathon\.agents\teamwork\teamwork_preview_explorer_survey_1
- **Original Request**: D:\Case_study_drive\TetraNoodle_AI_Hackathon\.agents\teamwork\ORIGINAL_REQUEST.md
- **Role**: Survey backend codebase (`scholarswarm/`), research & eligibility pipeline, Gemini grounding, URL context, agent workflow, and eligibility logic.
- **Output Report**: D:\Case_study_drive\TetraNoodle_AI_Hackathon\.agents\teamwork\teamwork_preview_explorer_survey_1\handoff.md

## 2026-10-20T21:11:11Z
From: 6828b193-f5c1-4991-90e8-8c39694edfd6
Content:
Your identity is: Survey Explorer 1 (Backend Pipeline & Gemini Grounding).
Your working directory is: D:\Case_study_drive\TetraNoodle_AI_Hackathon\.agents\teamwork\teamwork_preview_explorer_survey_1
Original request file path: D:\Case_study_drive\TetraNoodle_AI_Hackathon\.agents\teamwork\ORIGINAL_REQUEST.md

You MUST read ORIGINAL_REQUEST.md first before starting your investigation.

Your mission:
Investigate the authoritative source of truth in the ScholarSwarm backend codebase (located under `scholarswarm/` and project root) regarding Requirements R1, R2, R3, and R4.
Specifically analyze and document:
1. Hardcoded opportunities: Search for `REAL_OPPORTUNITIES_BASE`, hardcoded opportunity lists, dummy fallback records, mock data dictionaries in `scholarswarm/agents/` or elsewhere in backend pipelines.
2. Gemini Grounding & URL Context: Check how Google Search grounding is currently implemented, how `google-genai` SDK is used, whether URL context tool is enabled/configured, how URLs are retrieved, and how retrieval metadata (failures, unsafe, missing) is handled.
3. Eligibility Evaluation & Source Evidence: Check current eligibility logic (CGPA cutoffs, language tests, degree prerequisites), whether generic country-wide assumptions are made, how quotes/excerpts are extracted, whether UNRESOLVED markers exist, and how university admission vs scholarship criteria are separated.
4. Deadlines & Official Domains: How application runtime dates are checked against deadlines, how passed cycles are handled, and how official provider domains are verified.
5. 5-Agent Workflow & Fault Recovery: Check the 5 agent roles (Profile Intelligence, Research & Eligibility, Match Strategist, Application Coach, Quality Reviewer). Check the rejection loop between Quality Reviewer and Research & Eligibility, loop bounding, partial branch failure handling, and Application Coach invocation boundaries.
6. Provide concrete file paths, line numbers, function definitions, data models/schemas, and architectural gaps against R1-R4 requirements.

Deliver your complete findings by writing a structured handoff report to:
`D:\Case_study_drive\TetraNoodle_AI_Hackathon\.agents\teamwork\teamwork_preview_explorer_survey_1\handoff.md`.
Also maintain your `progress.md` in your directory.
When finished, send a message to the orchestrator confirming completion and referencing the handoff path.
