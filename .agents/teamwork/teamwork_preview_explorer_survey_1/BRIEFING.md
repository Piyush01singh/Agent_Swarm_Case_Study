# BRIEFING — 2026-10-20T21:18:30Z

## Mission
Investigate ScholarSwarm backend codebase under `scholarswarm/` and project root for Requirements R1, R2, R3, R4 (hardcoded opportunities, Gemini grounding, URL context, eligibility logic, deadlines, official domains, and 5-agent workflow).

## 🔒 My Identity
- Archetype: explorer
- Roles: survey, synthesis
- Working directory: D:\Case_study_drive\TetraNoodle_AI_Hackathon\.agents\teamwork\teamwork_preview_explorer_survey_1
- Original parent: 6828b193-f5c1-4991-90e8-8c39694edfd6
- Milestone: survey_backend_and_grounding

## 🔒 Key Constraints
- Read-only investigation — do NOT implement
- Files for content delivery, Messages for coordination
- Report written to D:\Case_study_drive\TetraNoodle_AI_Hackathon\.agents\teamwork\teamwork_preview_explorer_survey_1\handoff.md
- Maintain progress.md with timestamp heartbeat

## Current Parent
- Conversation ID: 6828b193-f5c1-4991-90e8-8c39694edfd6
- Updated: 2026-10-20T21:18:30Z

## Investigation State
- **Explored paths**:
  - `backend/app/agents/research_eligibility.py`
  - `backend/app/agents/quality_reviewer.py`
  - `backend/app/agents/profile_intelligence.py`
  - `backend/app/agents/match_strategist.py`
  - `backend/app/agents/application_coach.py`
  - `backend/app/services/gemini_service.py`
  - `backend/app/services/scoring_service.py`
  - `backend/app/graph/workflow.py`
  - `backend/app/graph/state.py`
  - `backend/app/api/research.py`, `opportunities.py`, `profile.py`, `health.py`
  - `backend/app/models/opportunity.py`, `evidence.py`, `profile.py`
  - `backend/tests/` (all 7 test files)
  - `docs/EXPERIMENT.md`
- **Key findings**:
  - `REAL_OPPORTUNITIES_BASE` (lines 15-295 of `research_eligibility.py`) hardcodes 8 opportunities; live search results from Gemini are logged but never converted into Opportunity objects.
  - Gemini URL Context tool is completely missing (`types.Tool(url_context=types.UrlContext())` is never configured), and `analyze_url_and_extract_criteria` is dead uncalled code.
  - Synthetic f-strings are used instead of verbatim excerpts; generic country-level CGPA thresholds (Canada>=8.0, Germany>=7.5, Singapore>=8.0) replace program-specific criteria.
  - Expired 2025 deadlines are treated as verified active opportunities; official domain check is a loose substring matching `.ca`, `.de`, `.org`.
  - Application Coach is cleanly outside LangGraph (on-demand SOP generation), but Quality Reviewer loop does not pass feedback back to Research agent and overwrites previous opportunities.
  - `test_quality_reviewer.py` is referenced in `EXPERIMENT.md` but is missing; empirical metrics in `EXPERIMENT.md` are ungrounded; standalone `pytest` fails without `pytest.ini`.
- **Unexplored areas**: None within backend scope.

## Key Decisions Made
- Proceed to write comprehensive 5-component `handoff.md` covering all 6 focus areas with verbatim lines, file paths, and verification methods.

## Artifact Index
- D:\Case_study_drive\TetraNoodle_AI_Hackathon\.agents\teamwork\teamwork_preview_explorer_survey_1\BRIEFING.md — persistent working memory
- D:\Case_study_drive\TetraNoodle_AI_Hackathon\.agents\teamwork\teamwork_preview_explorer_survey_1\progress.md — liveness heartbeat
- D:\Case_study_drive\TetraNoodle_AI_Hackathon\.agents\teamwork\teamwork_preview_explorer_survey_1\handoff.md — 5-component handoff report
