## 2026-10-22T01:15:40Z
You are Explorer 2 (Role: Eligibility & Workflow Explorer).
Your working directory is D:\Case_study_drive\TetraNoodle_AI_Hackathon\.agents\teamwork\teamwork_preview_explorer_repair_2.
You MUST read D:\Case_study_drive\TetraNoodle_AI_Hackathon\.agents\teamwork\ORIGINAL_REQUEST.md before starting work (specifically the section '## Follow-up — 2026-10-22T01:12:26Z').

Your investigation focus:
1. R3: Remove invented universal grade conversion formulas.
   - In `backend/app/agents/research_eligibility.py` (`extract_numeric_cgpa_cutoff` and related helpers), find all linear 4.0-to-10.0 scaling, percentage-to-CGPA dividing formulas, and hardcoded qualitative mappings ("first class with distinction" -> 8.0, "b+ average" -> 7.5).
   - Determine how to eliminate these ungrounded heuristics unless supported by published institution equivalency guidance.
   - When a student's scale and requirement scale differ without published equivalency, specify how to flag status as `UNRESOLVED` with an actionable gap description.
2. R4: Fix reviewer feedback query construction.
   - In `backend/app/agents/research_eligibility.py`, during round 2 re-research, locate where raw reviewer error string concatenation appends student failure reasons to the search query.
   - Design short, targeted search queries derived specifically from the opportunity provider, program name, and the specific unresolved admission criterion.
3. R6: Clarify Agent 4 architecture & polish UI/templates.
   - In `backend/app/agents/application_coach.py`, find where applicant test type is hardcoded/defaulted rigidly to GRE, and show how to dynamically inject the applicant's actual test type from their profile into SOP fallback drafting.
   - In `frontend/index.html`, locate the document title and confirm the update to `ScholarSwarm — AI Scholarship Intelligence`.
   - In `docs/ARCHITECTURE.md` and `README.md`, locate descriptions of Agent 4 and plan clear documentation that Agent 4 operates as an on-demand application specialist rather than an autonomous looping node in LangGraph.

DO NOT write source code or modify production code. Provide precise file paths, line numbers, snippets, and exact recommended changes.
Write your complete findings and recommendations to `D:\Case_study_drive\TetraNoodle_AI_Hackathon\.agents\teamwork\teamwork_preview_explorer_repair_2\handoff.md`.
When finished, send a message to the orchestrator (conversation ID: 6caa988d-b978-4e37-94b4-b6ba138214d3).
