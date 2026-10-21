## 2026-10-20T23:43:24Z
Your identity is: Worker M5 (Frontend Real Data Audit & Deployability).
Your working directory is: D:\Case_study_drive\TetraNoodle_AI_Hackathon\.agents\teamwork\teamwork_preview_worker_m5
Original request file path: D:\Case_study_drive\TetraNoodle_AI_Hackathon\.agents\teamwork\ORIGINAL_REQUEST.md
Project plan file path: D:\Case_study_drive\TetraNoodle_AI_Hackathon\PROJECT.md
Survey Explorer 3 report path: D:\Case_study_drive\TetraNoodle_AI_Hackathon\.agents\teamwork\teamwork_preview_explorer_survey_3\handoff.md

You MUST read ORIGINAL_REQUEST.md, PROJECT.md, and the Survey Explorer 3 report first before starting work.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Your exclusive write ownership:
- `frontend/src/components/SopWorkspace.tsx`
- `frontend/src/components/OpportunityCard.tsx`
- `frontend/src/components/EvidenceDrawer.tsx`
- `frontend/src/components/GapPlanner.tsx`
- `frontend/src/App.tsx`
- `frontend/vite.config.ts`

Your tasks:
1. Feature F22 (Frontend Rules of Hooks Fix):
   In `frontend/src/components/SopWorkspace.tsx`:
   - Move `if (!opportunity) return null;` below hook declarations (`useState`, `useEffect`) so React Rules of Hooks are strictly respected.
   - Inside `useEffect`, check `if (!opportunity) return;` safely.
   - Verify with `npm run lint` in `frontend/` that 0 errors remain.
2. Feature F23 (Remove Synthetic UI Fallbacks):
   - In `frontend/src/components/OpportunityCard.tsx`: replace line 144 `opportunity.evidence_records?.length || 3` with `opportunity.evidence_records?.length ?? 0`.
   - In `frontend/src/components/EvidenceDrawer.tsx`: replace line 46-47 default `'OFFICIAL'` with `opportunity.evidence_quality || 'UNVERIFIED'`.
   - In `frontend/src/components/GapPlanner.tsx`: remove `slice(0, 5)` so all actionable gaps are rendered without truncation, matching `{allGaps.length} Actionable Items`.
3. Feature F24 (Frontend Evidence Fetching & Env Config):
   - In `frontend/src/App.tsx`: in `handleViewEvidence` / `onViewEvidence`, if `opportunity.evidence_records` is empty or undefined, call `getOpportunityDetails(opportunity.id)` to fetch complete opportunity details and update `selectedEvidenceOpp`.
   - In `frontend/vite.config.ts`: add `envDir: '../'` so Vite loads root `.env`.
4. Verification:
   - Run `npm run lint` in `frontend/` (must exit 0 with 0 errors).
   - Run `npm run build` in `frontend/` (`tsc -b && vite build` must exit 0 cleanly).

Deliver your complete report to:
`D:\Case_study_drive\TetraNoodle_AI_Hackathon\.agents\teamwork\teamwork_preview_worker_m5\handoff.md`.
Maintain `progress.md` in your directory and send a message when done.
