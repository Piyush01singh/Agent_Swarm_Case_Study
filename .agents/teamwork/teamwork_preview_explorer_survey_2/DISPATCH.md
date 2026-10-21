# Dispatch Task: Survey Explorer 2 (Testing, Experiment Harness & Docs)

- **Target Directory**: D:\Case_study_drive\TetraNoodle_AI_Hackathon\.agents\teamwork\teamwork_preview_explorer_survey_2
- **Original Request**: D:\Case_study_drive\TetraNoodle_AI_Hackathon\.agents\teamwork\ORIGINAL_REQUEST.md
- **Role**: Survey testing infrastructure, `docs/EXPERIMENT.md`, evaluation harness, test scripts, pytest configuration, and CLI commands.
- **Output Report**: D:\Case_study_drive\TetraNoodle_AI_Hackathon\.agents\teamwork\teamwork_preview_explorer_survey_2\handoff.md
## 2026-10-20T21:11:11Z

Your identity is: Survey Explorer 2 (Testing, Experiment Harness & Docs).
Your working directory is: D:\Case_study_drive\TetraNoodle_AI_Hackathon\.agents\teamwork\teamwork_preview_explorer_survey_2
Original request file path: D:\Case_study_drive\TetraNoodle_AI_Hackathon\.agents\teamwork\ORIGINAL_REQUEST.md

You MUST read ORIGINAL_REQUEST.md first before starting your investigation.

Your mission:
Investigate the authoritative source of truth regarding Requirement R5 and the testing infrastructure:
1. Examine `docs/EXPERIMENT.md` and all documentation discussing experiment results, benchmarks, or accuracy claims. Identify unverified, fabricated, or placeholder claims.
2. Examine `tests/` and any existing test scripts across the codebase. Test runner configuration, pytest setup, fixtures, mock vs live test harnesses.
3. Specifically investigate `test_quality_reviewer.py` and any missing/broken test commands mentioned in R5.
4. Assess what is required to build a runnable Python evaluation harness with documented test cases comparing single-pass vs Quality Reviewer correction loops, injecting controlled retrieval failures, measuring latency, source coverage, and eligibility accuracy.
5. Identify all test execution commands, environment variables (e.g. GEMINI_API_KEY), and dependencies in `pyproject.toml` or `requirements.txt`.
6. Provide concrete file paths, line numbers, existing test coverage gaps, and an exact blueprint for fulfilling R5.

Deliver your complete findings by writing a structured handoff report to:
`D:\Case_study_drive\TetraNoodle_AI_Hackathon\.agents\teamwork\teamwork_preview_explorer_survey_2\handoff.md`.
Also maintain your `progress.md` in your directory.
When finished, send a message to the orchestrator confirming completion and referencing the handoff path.
