# Plan — ScholarSwarm Project Orchestrator

## Objective
Coordinate the complete audit, repair, and verification of ScholarSwarm's research and eligibility pipeline, eliminating hardcoded fixtures, wiring genuine Gemini Search grounding & Google Gen AI URL Context, enforcing strict evidence integrity, creating a reproducible evaluation experiment harness, and verifying end-to-end frontend and backend behavior.

## Workflow Plan
1. **Phase 0: Survey (Top-Level Discovery)**
   - Dispatch 3 parallel Explorers:
     - `teamwork_preview_explorer_survey_1`: Focus on backend research pipeline, agents (`scholarswarm/agents/`), `REAL_OPPORTUNITIES_BASE`, Gemini search grounding, URL context implementation (`google-genai`), schemas, and eligibility logic.
     - `teamwork_preview_explorer_survey_2`: Focus on evaluation harness, tests, `docs/EXPERIMENT.md`, `test_quality_reviewer.py`, pytest suite, and CI/scripts.
     - `teamwork_preview_explorer_survey_3`: Focus on frontend components (`frontend/src/components/`, Opportunity cards, Evidence Drawer, Gap Planner, SOP generator, build setup `npm run build`), Supabase integration, and end-to-end API contracts.
   - Set safety timer and wait for surveys.

2. **Phase 1: Synthesize into PROJECT.md**
   - Synthesize findings into `PROJECT.md` at project root: Architecture, Feature Inventory (R1-R6 mapped to milestones), Milestones decomposition, Interface Contracts, and Code Layout.

3. **Phase 2: Dual Track Execution**
   - **E2E Testing Track**: Build comprehensive opaque-box test suites (Tier 1 Feature, Tier 2 Boundary/Corner, Tier 3 Cross-feature, Tier 4 Real-world scenarios) -> `TEST_READY.md`.
   - **Implementation Track**: Decompose R1-R4 into sequential/parallel milestones:
     - M1: Grounded Discovery & Real Extraction (R1, R3)
     - M2: Strict Eligibility Evaluation & Evidence Integrity (R2)
     - M3: 5-Agent Workflow, Bounded Quality Reviewer Loop & Fault Recovery (R4)
     - M4: Experiment Harness, Documented CLI & Empirical Data (R5)
     - M5: Frontend Real Data Rendering & Production Build (R6 frontend)

4. **Phase 3: Final Milestone (Tiers 1-4 Verification + Tier 5 Adversarial Hardening)**
   - Phase 1: 100% Pass of all E2E tests (Tiers 1-4)
   - Phase 2: Tier 5 White-box adversarial testing with Challenger -> Worker -> Reviewer -> Forensic Auditor.

5. **Phase 4: Final Synthesis & Reporting**
   - Synthesize final reports, verify all gates, verify Forensic Auditor report is CLEAN.
   - Send completion message to Sentinel with full details.
