# Forensic Audit Report: Milestone M5 — Frontend Real Data Audit & Deployability

**Work Product**: Milestone M5 (Features F22, F23, F24) — `frontend/src/components/OpportunityCard.tsx`, `EvidenceDrawer.tsx`, `GapPlanner.tsx`, `SopWorkspace.tsx`, `App.tsx`, `vite.config.ts`  
**Profile**: General Project (Anti-Mock & Integrity Forensics)  
**Integrity Mode**: `development` (per `ORIGINAL_REQUEST.md`)  
**Verdict**: CLEAN

---

## 1. Observation

Direct forensic observations, code AST analysis, and execution outputs:

### 1.1 Anti-Mock & Synthetic Data Forensics

1. **`frontend/src/components/OpportunityCard.tsx`**:
   - Line 144:
     ```tsx
     <ShieldCheck className="h-3.5 w-3.5 text-cyan-400" />
     Evidence ({opportunity.evidence_records?.length ?? 0})
     ```
   - Verbatim check: The previous hardcoded mock number `|| 3` has been completely eliminated. If an opportunity has 0 evidence records or undefined records, it evaluates strictly to `0` via nullish coalescing `?? 0`, preventing synthetic fabrication of 3 evidence records.
   - Grep search for `|| 3` across `frontend/src` returned 0 matches.

2. **`frontend/src/components/EvidenceDrawer.tsx`**:
   - Line 46:
     ```tsx
     <ShieldCheck className="h-3.5 w-3.5" />
     {opportunity.evidence_quality || 'UNVERIFIED'}
     ```
   - Verbatim check: The previous synthetic default status `|| 'OFFICIAL'` has been eliminated. Unverified or missing evidence qualities correctly fallback to `'UNVERIFIED'`.
   - Grep search for `'OFFICIAL'` defaults across `frontend/src` confirmed zero mock defaults.

3. **`frontend/src/components/GapPlanner.tsx`**:
   - Line 41:
     ```tsx
     allGaps.map((item, idx) => (
     ```
   - Verbatim check: Artificial truncation (`allGaps.slice(0, 5)`) has been eliminated. The header badge renders `{allGaps.length} Actionable Items` and the list maps every item without truncation.
   - Grep search for `slice` across `frontend/src` returned 0 matches.

4. **`frontend/src/components/SopWorkspace.tsx`**:
   - Lines 17–21 & 23–46:
     ```tsx
     const [draft, setDraft] = useState<ApplicationDraft | null>(null);
     const [content, setContent] = useState<string>("");
     const [isLoading, setIsLoading] = useState<boolean>(true);
     const [isCopied, setIsCopied] = useState<boolean>(false);
     const userNotes = "";

     useEffect(() => {
       if (!opportunity) return;
       let cancelled = false;

       generateSopDraft(opportunity.id, runId, userNotes)
         .then((generated) => {
           if (!cancelled) {
             setDraft(generated);
             setContent(generated.sop_content);
           }
         })
         .catch((err) => {
           console.error("Failed to generate SOP draft:", err);
         })
         .finally(() => {
           if (!cancelled) {
             setIsLoading(false);
           }
         });

       return () => {
         cancelled = true;
       };
     }, [opportunity, runId]);

     if (!opportunity) return null;
     ```
   - Verbatim check: The React Rules of Hooks violation (`if (!opportunity) return null;` preceding hook declarations) is fully resolved. All hooks are declared unconditionally at the top level of the component. An async cancellation token (`cancelled = true`) prevents memory leaks and unmounted state updates.

5. **`frontend/src/App.tsx` & Data Flow**:
   - Lines 120–130:
     ```tsx
     const handleViewEvidence = async (opportunity: Opportunity) => {
       setSelectedEvidenceOpp(opportunity);
       if (!opportunity.evidence_records || opportunity.evidence_records.length === 0) {
         try {
           const fullDetails = await getOpportunityDetails(opportunity.id);
           setSelectedEvidenceOpp(fullDetails);
         } catch (err) {
           console.error("Failed to fetch full opportunity evidence details:", err);
         }
       }
     };
     ```
   - Lines 282 & 301: Passed `onViewEvidence={handleViewEvidence}` to both Top 5 and additional opportunity cards. Ensures detailed evidence records are fetched on-demand from `/api/opportunities/{id}` without dummy facades.

6. **`frontend/vite.config.ts`**:
   - Line 7: `envDir: '../'` correctly configured to load root `.env` variables in Vite.

7. **Codebase-Wide Search for Mock / Dummy State**:
   - Search for `mock`: 0 matches in `frontend/src/`.
   - Search for `dummy`: 0 matches in `frontend/src/`.
   - Search for `fake`: 0 matches in `frontend/src/`.
   - Search for pre-populated synthetic artifacts: None present.

---

### 1.2 Execution Validation Outputs

1. **`npm run lint`** in `frontend/`:
   - Command: `npm run lint` (`oxlint`)
   - Exit Code: **0**
   - Raw Output:
     ```
     > frontend@0.0.0 lint
     > oxlint

     Found 0 warnings and 0 errors.
     Finished in 70ms on 14 files with 116 rules using 8 threads.
     ```

2. **`npm run build`** in `frontend/`:
   - Command: `npm run build` (`tsc -b && vite build`)
   - Exit Code: **0**
   - Raw Output:
     ```
     > frontend@0.0.0 build
     > tsc -b && vite build

     vite v8.3.4 building client environment for production...
     transforming...
     ✓ 1929 modules transformed.
     rendering chunks...
     computing gzip size...
     dist/index.html                   0.45 kB │ gzip:  0.29 kB
     dist/assets/index-DqnMpbbB.css   24.13 kB │ gzip:  5.40 kB
     dist/assets/index-B1dTJTvs.js   278.51 kB │ gzip: 83.69 kB
     ✓ built in 1.88s
     ```

3. **Independent TypeScript Verification (`npx tsc --noEmit`)**:
   - Command: `npx tsc --noEmit`
   - Exit Code: **0**
   - Output: 0 type errors, 0 warnings.

---

## 2. Logic Chain

1. **Anti-Mock / Facade Invalidation Hypothesis**:
   - If UI components relied on `|| 3` or `|| 'OFFICIAL'`, a zero-evidence or unverified record would deceive the student by fabricating confidence and official verification tiers.
   - Observation confirms replacing `|| 3` with `?? 0` in `OpportunityCard.tsx` preserves authentic counts (e.g. 0 remains 0). Replacing `|| 'OFFICIAL'` with `|| 'UNVERIFIED'` in `EvidenceDrawer.tsx` guarantees unverified criteria are never promoted to official status.
2. **Data Presentation Transparency**:
   - Slicing `allGaps.slice(0, 5)` while displaying `{allGaps.length} Actionable Items` hid critical application blockers from the applicant. Removing `.slice(0, 5)` restores full integrity between header counters and displayed content.
3. **Execution Correctness & React Architecture**:
   - Placing conditional returns before hooks violated the React execution invariant where hooks must be called in identical sequence across renders. Moving `useState` and `useEffect` above the conditional return resolves this, directly verified by `oxlint` passing with 0 warnings/errors.
   - Production compilation via `tsc -b && vite build` completed in 1.88s with clean bundle generation in `dist/`.

---

## 3. Caveats

- **No Caveats**: The audit covered 100% of the files modified in Milestone M5 (`OpportunityCard.tsx`, `EvidenceDrawer.tsx`, `GapPlanner.tsx`, `SopWorkspace.tsx`, `App.tsx`, and `vite.config.ts`), as well as full lint, typecheck, and build execution.
- No modifications were made by the auditor, adhering strictly to the audit-only constraint.

---

## 4. Conclusion

**Verdict: CLEAN**

Milestone M5 satisfies all integrity, anti-mock, and build criteria:
- **Zero hardcoded mock numbers**: `|| 3` eliminated; replaced with `?? 0`.
- **Zero synthetic default statuses**: `|| 'OFFICIAL'` eliminated; replaced with `|| 'UNVERIFIED'`.
- **Zero artificial truncation**: `.slice(0, 5)` removed from `GapPlanner.tsx`.
- **Zero React hook violations**: `SopWorkspace.tsx` hook order fixed; clean lifecycle with cancellation.
- **Genuine API integration**: `App.tsx` fetches full evidence details via `getOpportunityDetails`.
- **Execution validation**: `npm run lint` exits 0 (0 warnings, 0 errors); `npm run build` exits 0 (successful Vite production bundle); `tsc` exits 0.

---

## 5. Verification Method

To independently reproduce the forensic audit results:

```powershell
# 1. Lint validation
cd D:\Case_study_drive\TetraNoodle_AI_Hackathon\frontend
npm run lint
# Verify: Exit code 0, 0 warnings, 0 errors

# 2. Production build validation
npm run build
# Verify: Exit code 0, dist/index.html and assets successfully generated

# 3. Type check validation
npx tsc --noEmit
# Verify: Exit code 0

# 4. Anti-mock code verification
# Verify ?? 0 in OpportunityCard
Select-String -Path src\components\OpportunityCard.tsx -Pattern "\?\? 0"
# Verify UNVERIFIED fallback in EvidenceDrawer
Select-String -Path src\components\EvidenceDrawer.tsx -Pattern "UNVERIFIED"
# Verify no slice in GapPlanner
Select-String -Path src\components\GapPlanner.tsx -Pattern "slice"
```
