# BRIEFING — 2026-10-20T23:05:00Z

## Mission
Deeply investigate the codebase and design the exact refactoring plan for Milestone M3 (Features F11 through F16 — 5-Agent Workflow, Bounded Loop & Fault Recovery).

## 🔒 My Identity
- Archetype: explorer
- Roles: codebase investigation, synthesis, architecture & refactoring plan
- Working directory: D:\Case_study_drive\TetraNoodle_AI_Hackathon\.agents\teamwork\teamwork_preview_explorer_m3_1
- Original parent: 6828b193-f5c1-4991-90e8-8c39694edfd6
- Milestone: M3 (Features F11-F16)

## 🔒 Key Constraints
- Read-only investigation — do NOT implement directly in backend source code (write findings, patches, and plan in working directory)
- Deliver complete findings in handoff.md following 5-component handoff protocol
- Guarantee bounded loop termination after max_research_rounds
- Detail exact code diffs, function signatures, and step-by-step instructions for worker

## Current Parent
- Conversation ID: 6828b193-f5c1-4991-90e8-8c39694edfd6
- Updated: not yet

## Investigation State
- **Explored paths**:
  - `backend/app/graph/state.py`: identified missing `approved_opportunities` field and type update for `reviewer_issues: List[Dict[str, Any]]`.
  - `backend/app/graph/workflow.py`: verified nodes, identified missing `node_application_coaching`, missing preservation of `approved_opportunities` in `node_research_discovery`, missing parameter pass of `reviewer_issues`, and conditional edge routing logic.
  - `backend/app/agents/quality_reviewer.py`: designed dual-compatible `ReviewerIssue(dict)` satisfying both structured dict access and string method compatibility with existing tests; verified audit loop over all top-5 opportunities (F14).
  - `backend/app/agents/research_eligibility.py`: traced query formulation with `reviewer_issues`.
  - `backend/app/db/repository.py`: identified critical `IndexError` bug in `get_opportunity_by_id`, missing Supabase persistence in `save_evidence_records` and `get_evidence_for_opportunity`, and missing `get_evidence_records` method.
  - Test suites: verified 132 passing tests; designed 12 targeted unit/integration tests in `test_m3_workflow.py`.
- **Key findings**:
  - `ReviewerIssue(dict)` dual subclass satisfies Pydantic validation and avoids breaking existing tests (`test_m2_eligibility.py` line 400 `issue.lower()`, line 589 `"..." in issue`, `test_tier3_cross_feature.py` line 131).
  - Cross-round preservation requires `node_research_discovery` to merge `state.approved_opportunities` with new candidates, and `node_quality_reviewer` to update `state.approved_opportunities`.
  - Bounded loop counter in `node_quality_reviewer` (`new_round = state.research_round + 1`) paired with `route_after_review` (`state.research_round <= state.max_research_rounds`) correctly bounds iterations to `max_research_rounds`.
  - `get_opportunity_by_id` index crash occurs when `get_opportunities()` returns empty or returns non-matching opportunity; resolved via explicit ID lookup and direct deserialization fallback.
- **Unexplored areas**: none (all M3 files and contracts analyzed).

## Key Decisions Made
- Use `ReviewerIssue(dict)` for structured issues to maintain 100% backward compatibility with existing tests while satisfying the structured issue requirement.
- Support both `research_discovery` and `match_strategy` in `route_after_review` conditional edge routing table.
- Add `get_evidence_records(run_id, opportunity_id)` alongside `get_evidence_for_opportunity(opportunity_id)` in repository.

## Artifact Index
- `DISPATCH.md` — record of initial dispatch message
- `progress.md` — liveness and step progress tracker
- `handoff.md` — final 5-component report
