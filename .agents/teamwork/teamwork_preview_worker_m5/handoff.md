# Handoff Report: Milestone M5 — Frontend Real Data Audit & Deployability

## 1. Observation

Direct code inspections and tool execution outputs before and after implementation:

### 1.1 Pre-Modification Baseline
- `frontend/src/components/SopWorkspace.tsx:17`:
  ```tsx
  if (!opportunity) return null;
  const [draft, setDraft] = useState<ApplicationDraft | null>(null);
  ...
  useEffect(() => {
    loadDraft();
  }, [opportunity.id]);
  ```
  `npm run lint` (`oxlint`) failed with exit code 1:
  - 5 errors: `react-hooks(rules-of-hooks): React Hook "useState" / "useEffect" is called conditionally.`
  - 2 warnings: `react(set-state-in-effect)` and `react-hooks(exhaustive-deps)`.
- `frontend/src/components/OpportunityCard.tsx:144`:
  ```tsx
  Evidence ({opportunity.evidence_records?.length || 3})
  ```
  Evaluated `0 || 3` to `3`, fabricating 3 evidence items when 0 were present.
- `frontend/src/components/EvidenceDrawer.tsx:46-47`:
  ```tsx
  {opportunity.evidence_quality || 'OFFICIAL'}
  ```
  Defaulted unverified or missing evidence tiers to `'OFFICIAL'`.
- `frontend/src/components/GapPlanner.tsx:41`:
  ```tsx
  allGaps.slice(0, 5).map((item, idx) => (
  ```
  Truncated actionable gaps to at most 5 items despite header badge displaying `{allGaps.length} Actionable Items`.
- `frontend/src/App.tsx:270, 289`:
  ```tsx
  onViewEvidence={(o) => setSelectedEvidenceOpp(o)}
  ```
  Passed shallow opportunity objects to `EvidenceDrawer` without querying `getOpportunityDetails` when detailed evidence records were absent.
- `frontend/vite.config.ts`:
  Lacked `envDir: '../'`, preventing Vite from loading root `.env` values during development.

### 1.2 Implemented Changes
- In `frontend/src/components/SopWorkspace.tsx`:
  - Moved `useState` and `useEffect` hook declarations to the top of `SopWorkspace`.
  - Added safe guard `if (!opportunity) return;` inside `useEffect`.
  - Moved `if (!opportunity) return null;` below all hook invocations.
  - Handled async loading with cancellation cleanup, resolving `set-state-in-effect` and `exhaustive-deps`.
- In `frontend/src/components/OpportunityCard.tsx:144`:
  - Replaced `|| 3` with `?? 0` (`opportunity.evidence_records?.length ?? 0`).
- In `frontend/src/components/EvidenceDrawer.tsx:46`:
  - Replaced default fallback `'OFFICIAL'` with `'UNVERIFIED'` (`opportunity.evidence_quality || 'UNVERIFIED'`).
- In `frontend/src/components/GapPlanner.tsx:41`:
  - Removed `.slice(0, 5)` so `allGaps.map((item, idx) => ...)` renders every actionable item without truncation.
- In `frontend/src/App.tsx`:
  - Imported `getOpportunityDetails` from `./api/client`.
  - Implemented `handleViewEvidence`: if `opportunity.evidence_records` is empty or undefined, asynchronously fetches full opportunity details via `getOpportunityDetails(opportunity.id)` and updates `selectedEvidenceOpp`.
  - Passed `onViewEvidence={handleViewEvidence}` to both `topFiveList` and `otherOpportunities` card renderers.
- In `frontend/vite.config.ts`:
  - Added `envDir: '../'` to `defineConfig`.

### 1.3 Post-Modification Tool Execution Results
- `npm run lint` in `frontend/`:
  - Command: `oxlint`
  - Output: `Found 0 warnings and 0 errors. Finished in 18ms on 14 files with 116 rules using 8 threads.`
  - Exit code: 0
- `npm run build` in `frontend/`:
  - Command: `tsc -b && vite build`
  - Output:
    ```
    vite v8.3.4 building client environment for production...
    transforming...
    ✓ 1929 modules transformed.
    rendering chunks...
    computing gzip size...
    dist/index.html                   0.45 kB │ gzip:  0.29 kB
    dist/assets/index-DqnMpbbB.css   24.13 kB │ gzip:  5.40 kB
    dist/assets/index-B1dTJTvs.js   278.51 kB │ gzip: 83.69 kB
    ✓ built in 1.62s
    ```
  - Exit code: 0

---

## 2. Logic Chain

1. **Rules of Hooks**: React requires that hooks are called unconditionally in the exact same sequence on every render. Because `SopWorkspace.tsx` returned early at line 17 before `useState` and `useEffect`, any render where `opportunity` was null bypassed hook registrations. Placing `useState` and `useEffect` above `if (!opportunity) return null;` guarantees identical hook invocation on every render, satisfying the React Rules of Hooks.
2. **Honest Metric Reporting**: Using `|| 3` on array lengths coerced legitimate `0` values (falsy) to `3`. Using nullish coalescing `?? 0` guarantees that if an opportunity has `0` evidence records, the badge renders `Evidence (0)` rather than a fabricated `3`.
3. **Evidence Tier Authenticity**: Missing evidence tier should never masquerade as `'OFFICIAL'`. Defaulting to `'UNVERIFIED'` accurately reflects ungrounded records.
4. **Gap Transparency**: Slicing the gap array at 5 while advertising `N Actionable Items` misled the user. Removing `slice(0, 5)` ensures visual alignment between badge counter and item list.
5. **Real-Data Fetching**: When opportunities are initially listed from a shallow or persisted endpoint, evidence records may not be loaded. `handleViewEvidence` checks if `evidence_records` is empty/undefined and queries `getOpportunityDetails(id)` to retrieve verified source quotes and criteria checks.
6. **Deployability**: Adding `envDir: '../'` enables Vite to discover root configuration files (`.env`) for local development and build pipelines.

---

## 3. Caveats

- **No Caveats**: All edits were restricted to the 6 designated files within Worker M5 write ownership. No extraneous dependencies or alterations to API contracts were made.
- Backend API endpoints (`/api/opportunities/{id}`) were verified against existing routes in `backend/app/api/opportunities.py`.

---

## 4. Conclusion

Milestone M5 (Features F22, F23, F24) is fully satisfied:
- React Rules of Hooks violation in `SopWorkspace.tsx` is resolved.
- Synthetic fallbacks in `OpportunityCard.tsx`, `EvidenceDrawer.tsx`, and `GapPlanner.tsx` have been eliminated.
- On-demand evidence fetching via `getOpportunityDetails` is wired in `App.tsx`.
- Root environment configuration is enabled in `vite.config.ts`.
- `npm run lint` passes with 0 errors and 0 warnings.
- `npm run build` compiles with 0 errors, generating production assets in `frontend/dist/`.

---

## 5. Verification Method

To independently reproduce and verify this work:

1. **Lint Check**:
   ```bash
   cd frontend
   npm run lint
   ```
   *Expected Result*: Exits with code 0. Reports 0 warnings and 0 errors across 14 files.

2. **Build Check**:
   ```bash
   cd frontend
   npm run build
   ```
   *Expected Result*: Exits with code 0. TypeScript compilation succeeds and Vite bundles production assets in `frontend/dist/`.

3. **Code Inspection**:
   - `frontend/src/components/SopWorkspace.tsx`: Check that `useState` and `useEffect` precede `if (!opportunity) return null;`.
   - `frontend/src/components/OpportunityCard.tsx`: Check line with `opportunity.evidence_records?.length ?? 0`.
   - `frontend/src/components/EvidenceDrawer.tsx`: Check line with `opportunity.evidence_quality || 'UNVERIFIED'`.
   - `frontend/src/components/GapPlanner.tsx`: Check line with `allGaps.map((item, idx) => (` (no `slice(0, 5)`).
   - `frontend/src/App.tsx`: Check definition and usage of `handleViewEvidence` calling `getOpportunityDetails`.
   - `frontend/vite.config.ts`: Check `envDir: '../'`.
