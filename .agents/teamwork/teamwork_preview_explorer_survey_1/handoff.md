# Handoff Report: Backend Pipeline & Gemini Grounding Survey (R1–R4)

**Agent**: Survey Explorer 1 (Backend Pipeline & Gemini Grounding)  
**Date**: 2026-10-20T21:20:00Z  
**Target File**: `D:\Case_study_drive\TetraNoodle_AI_Hackathon\.agents\teamwork\teamwork_preview_explorer_survey_1\handoff.md`  
**Reference Document**: `D:\Case_study_drive\TetraNoodle_AI_Hackathon\.agents\teamwork\ORIGINAL_REQUEST.md`

---

## 1. Observation

### 1.1 Hardcoded Opportunities & Candidate Bypassing
- **File**: `backend/app/agents/research_eligibility.py`
  - **Lines 15–295**: Definition of `REAL_OPPORTUNITIES_BASE`, a hardcoded list of 8 dictionary records containing University of Toronto, TUM, NUS, NTU, UBC, McGill, KIT, SFU, Waterloo, and A*STAR SINGA.
  - **Lines 326–362**:
    ```python
    if gemini_service.is_available:
        for country in profile.target_countries:
            query = f"official site:edu OR site:gov OR site:ac scholarship fully funded {profile.target_degree} in {profile.target_field} in {country} admission requirements CGPA deadline"
            ...
            discovery_res = await gemini_service.search_grounded_discovery(
                query=query,
                context_prompt=f"Student has CGPA {profile.cgpa}/{profile.grading_scale} from {profile.institution}, degree {profile.current_degree}, seeking {profile.target_degree}."
            )
            if discovery_res.get("success"):
                for src in discovery_res.get("sources", []):
                    ...
                    norm_url = normalize_url(raw_url)
                    if norm_url in seen_canonical_urls:
                        continue
                    seen_canonical_urls.add(norm_url)
                    await repository.save_agent_event(AgentEvent(
                        ...
                        event_type="CANDIDATE_FOUND",
                        ...
                    ))
    ```
    Live discovered candidates are only logged to `repository.save_agent_event` with event type `CANDIDATE_FOUND` and their URLs added to `seen_canonical_urls`. No `Opportunity` model instances are ever constructed from them.
  - **Lines 364–379**:
    ```python
    for raw_opp in REAL_OPPORTUNITIES_BASE:
        if raw_opp["country"] not in profile.target_countries:
            continue
        norm_url = normalize_url(raw_opp["canonical_url"])
        if norm_url in seen_canonical_urls:
            ...
            continue
        seen_canonical_urls.add(norm_url)
    ```
    The only opportunities instantiated into `Opportunity` models and returned in `opportunities: List[Opportunity]` originate exclusively from `REAL_OPPORTUNITIES_BASE`. If a live candidate URL matches a `REAL_OPPORTUNITIES_BASE` entry, line 370 skips it as a duplicate; if it does not match, the live candidate is discarded without creation.
- **File**: `backend/app/models/profile.py`
  - **Lines 23–48**: `StudentProfile` model defines hardcoded defaults:
    `full_name: str = "Rahul Sharma"`, `current_degree: str = "B.Tech Computer Science"`, `institution: str = "Punjab Technical University / NIT Jalandhar"`, `cgpa: float = 8.2`, `skills = ["Python", "PyTorch", "FastAPI", "Machine Learning", "NLP"]`.
- **File**: `backend/app/agents/profile_intelligence.py` (lines 35–46) & `backend/app/api/profile.py` (lines 101–118): Fallback defaults replicate the hardcoded "Rahul Sharma" / 8.2 CGPA values if form parameters are null.

### 1.2 Gemini Grounding, URL Context & SDK Implementation
- **SDK & Version**: `backend/requirements.txt` specifies `google-genai>=1.0.0`. Python runtime inspection of `google.genai.types` confirms:
  - `types.Tool` supports fields: `['retrieval', 'computer_use', 'file_search', 'google_search', 'google_maps', 'code_execution', 'enterprise_web_search', 'function_declarations', 'google_search_retrieval', 'parallel_ai_search', 'url_context', 'mcp_servers', 'exa_ai_search']`.
  - `types.UrlContext` exists.
  - `types.Candidate` exposes `url_context_metadata: Optional[UrlContextMetadata]`.
  - `types.UrlContextMetadata` contains `url_metadata: List[UrlMetadata]`.
  - `types.UrlMetadata` exposes `retrieved_url: str` and `url_retrieval_status: UrlRetrievalStatus`.
  - `types.UrlRetrievalStatus` enums: `URL_RETRIEVAL_STATUS_SUCCESS`, `URL_RETRIEVAL_STATUS_ERROR`, `URL_RETRIEVAL_STATUS_PAYWALL`, `URL_RETRIEVAL_STATUS_UNSAFE`, `URL_RETRIEVAL_STATUS_UNSPECIFIED`.
- **File**: `backend/app/services/gemini_service.py`
  - **Lines 21–95 (`search_grounded_discovery`)**:
    Uses `types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearch())], temperature=0.2)`. It retrieves grounding chunks (`grounding_metadata.grounding_chunks`), extracting web URI and title into `sources`. However, it does not extract structured opportunity records or program parameters from the model response text.
  - **Lines 104–184 (`analyze_url_and_extract_criteria`)**:
    - Lines 171–174:
      ```python
      config = types.GenerateContentConfig(
          temperature=0.1,
          response_mime_type="application/json"
      )
      ```
      **URL Context tool is not enabled**. No `tools=[types.Tool(url_context=types.UrlContext())]` is passed. The method merely interpolates URL strings as text into the prompt (`urls_formatted = "\n".join([f"- {u}" for u in urls[:settings.MAX_URLS_PER_REQUEST]])`).
    - **Dead Code**: Grep search across the entire project for `analyze_url_and_extract_criteria` yields exactly 1 match (its definition at line 104 of `gemini_service.py`). It is never invoked anywhere in the codebase.
  - **Missing API Key Behavior**:
    Lines 26–32, 114–119, 196–202, 259–265: When `GEMINI_API_KEY` is empty, methods return `{"success": False, "error": "GEMINI_API_KEY is not configured."}`. In `research_eligibility.py` line 326 (`if gemini_service.is_available:`), missing keys trigger a silent skip of Google Search, followed by silent emission of the hardcoded `REAL_OPPORTUNITIES_BASE`. No explicit configuration error is raised to the user or caller.

### 1.3 Eligibility Evaluation & Source Evidence Integrity
- **File**: `backend/app/agents/research_eligibility.py`
  - **Generic country-wide CGPA rules (Lines 391–415)**:
    ```python
    student_cgpa = profile.cgpa
    if raw_opp["country"] == "Canada" and student_cgpa >= 8.0:
        grade_status = "MEETS"
        excerpt = f"Student's {student_cgpa}/10.0 CGPA from Indian institution meets B+ minimum admission requirement."
    elif raw_opp["country"] == "Germany" and student_cgpa >= 7.5:
        grade_status = "MEETS"
        excerpt = f"Student's {student_cgpa}/10.0 CGPA satisfies German 2.0 conversion threshold."
    elif raw_opp["country"] == "Singapore" and student_cgpa >= 8.0:
        grade_status = "MEETS"
        excerpt = f"Student's {student_cgpa}/10.0 CGPA meets Singapore university second upper / honours requirement."
    elif student_cgpa < 7.0:
        grade_status = "DOES_NOT_MEET"
        excerpt = f"Student's {student_cgpa} CGPA is below the published minimum entrance cutoff."
        has_mandatory_failure = True
    else:
        grade_status = "UNRESOLVED"
        excerpt = "Specific institution-to-institution equivalency table must be officially verified."
        has_unresolved = True
    ```
    Academic evaluation uses broad country-level rules rather than checking each specific university's published admission requirement.
  - **Synthesized / Fabricated Evidence Excerpts**:
    In lines 395, 399, 403, 407, 438, 454, 479: `evidence_excerpt` is fabricated using Python f-strings rather than extracting verbatim quotes from live retrieved official web pages.
  - **Language Evaluation (Lines 433–444)**:
    ```python
    lang_info = profile.language_tests or {}
    score = lang_info.get("score")
    if score:
        lang_status = "MEETS"
        lang_excerpt = f"Recorded test score: {lang_info.get('test')} {score} meets university requirement."
    else:
        lang_status = "UNRESOLVED"
    ```
    Any presence of a score is automatically marked as `MEETS`, regardless of whether the score satisfies the specific institution's cutoff (e.g. Waterloo requiring IELTS 7.5 vs McGill requiring 6.5).
  - **Degree Prerequisites (Lines 463–470)**:
    Only tests if `raw_opp["degree_level"] == "PhD"` and `profile.target_degree != "PhD"`. Curricular requirements (e.g. 30 ECTS in mathematics, algorithms, linear algebra) are not verified against student course history.
  - **Admission vs Scholarship Separation**:
    In `backend/app/models/opportunity.py` (lines 32–33), `admission_requirements` and `scholarship_requirements` are separate fields. However, in `REAL_OPPORTUNITIES_BASE`, `scholarship_requirements` is not defined for any item (defaults to `[]`). No scholarship eligibility criteria are evaluated or recorded in `evidence_records`.

### 1.4 Deadlines & Official Domain Verification
- **Application Runtime vs Deadlines**:
  - `REAL_OPPORTUNITIES_BASE` contains expired deadlines:
    - University of Toronto: `2025-12-01` (Line 36)
    - UBC: `2025-12-15` (Line 149)
    - McGill: `2026-01-01` (Line 177)
    - University of Waterloo: `2025-12-15` (Line 260)
  - `research_eligibility.py` line 515 hardcodes `deadline_verified=raw_opp["deadline_verified"]` (which is `True` in all fixtures).
  - **File**: `backend/app/agents/quality_reviewer.py` (lines 72–77):
    ```python
    if not opp.deadline:
        opp.deadline_type = "Unknown"
        opp.deadline_verified = False
        opp.reviewer_notes = "Application deadline is not explicitly documented on published page."
    opp.reviewer_status = "APPROVED"
    ```
    The reviewer only checks if `opp.deadline` is non-empty. It never compares the date against runtime/current date (`datetime.now(timezone.utc)`). Consequently, expired 2025 deadlines are marked `APPROVED` and `deadline_verified = True`.
  - **File**: `backend/app/services/scoring_service.py` (lines 90–103):
    Because `deadline_verified` is True, expired deadlines are awarded the maximum +10.0 points for Deadline Readiness.
- **Simplistic Domain Substring Matching**:
  - **File**: `backend/app/agents/quality_reviewer.py` (lines 41–44):
    ```python
    has_official_domain = any(
        u.startswith("https://") and any(dom in u for dom in [".edu", ".ac.", ".ca", ".de", ".sg", ".gov", ".org", "vectorinstitute.ai", "daad.de", "a-star.edu.sg"])
        for u in official_urls
    )
    ```
    Any URL containing `.ca`, `.de`, `.org`, or `.sg` anywhere in the string matches as official (e.g., `spamsite.org`, `fake-agent.ca`, `unrelated-news.de`). There is no parsed hostname validation or authoritative provider domain registry.

### 1.5 5-Agent Workflow & Fault Recovery
- **Agent Roles**:
  1. `ProfileIntelligenceAgent` (`app/agents/profile_intelligence.py`)
  2. `ResearchEligibilityAgent` (`app/agents/research_eligibility.py`)
  3. `MatchStrategistAgent` (`app/agents/match_strategist.py`)
  4. `ApplicationCoachAgent` (`app/agents/application_coach.py`)
  5. `QualityReviewerAgent` (`app/agents/quality_reviewer.py`)
- **Workflow Architecture (`backend/app/graph/workflow.py`)**:
  - LangGraph compiles 4 nodes: `profile_intelligence` -> `research_discovery` -> `match_strategist` -> `quality_reviewer`.
  - `ApplicationCoachAgent` is not in the LangGraph graph. It is called on-demand via `app/api/opportunities.py` (lines 30–58, `generate_sop_for_opportunity`). This boundary is clean and intentional (SOP generation is an interactive user choice per opportunity).
- **Quality Reviewer Rejection Loop**:
  - `workflow.py` lines 72–76:
    ```python
    def route_after_review(state: SwarmState) -> Literal["research_discovery", "__end__"]:
        if state.needs_re_research and state.research_round <= state.max_research_rounds:
            return "research_discovery"
        return "__end__"
    ```
  - `node_research_discovery` (lines 27–38):
    Calls `research_agent.execute_discovery_and_audit(run_id=state.run_id, profile=state.student_profile, research_round=state.research_round)`.
  - **Defect 1**: `execute_discovery_and_audit` does not take or inspect `state.reviewer_issues`. It repeats the exact same search and loop without addressing flagged issues.
  - **Defect 2**: `node_research_discovery` returns `{"opportunities": opps}`, completely overwriting `state.opportunities`. Any opportunities that passed review in round 1 are replaced, and new UUIDs are generated.
  - **Defect 3**: `SwarmState` (in `app/graph/state.py` line 19) hardcodes `max_research_rounds: int = 2`, whereas `backend/app/config.py` specifies `MAX_RESEARCH_ROUNDS: int = 3`.
- **Quality Reviewer Scope Limitation**:
  - In `quality_reviewer.py` line 84:
    `if gemini_service.is_available and opportunities: top_opp = opportunities[0]`
    Only the first ranked opportunity is reviewed with Gemini LLM; opportunities 2 through N are skipped.
- **Partial Branch Failure**:
  - In `research_eligibility.py` line 344, if `gemini_service.search_grounded_discovery` fails for one country, the error is swallowed and the loop continues, but because only `REAL_OPPORTUNITIES_BASE` is returned, true partial candidate preservation from live search was never implemented.

### 1.6 Tests, Build & Experiment Discrepancies
- **Command Results**:
  - `pytest -v` from `backend` exited with code 1 and 7 collection errors:
    `ImportError: No module named 'app'`. Root cause: missing `pytest.ini` configuring `pythonpath = .`.
  - `python -m pytest -v` from `backend` executed 21 tests and passed all 21 (due to `sys.path` injection by `-m`), but all tests pass because they assert hardcoded values (e.g. `test_full_graph_workflow_execution` asserting `len(final_state["opportunities"]) > 0` populated by `REAL_OPPORTUNITIES_BASE`).
  - Missing test file: `backend/tests/test_quality_reviewer.py` does not exist, despite being explicitly instructed to run in `docs/EXPERIMENT.md` (lines 50–55: `python -m pytest tests/test_graph.py tests/test_scoring.py tests/test_quality_reviewer.py -v`).
  - `docs/EXPERIMENT.md`: The metrics table (lines 24–33) claims specific precision numbers (78.4% -> 94.2%, 84.0% -> 96.0%, 0/4 -> 4/4 rectified) which are fabricated; no runnable evaluation harness exists in the repository.
  - `npm run build` from `frontend` completed cleanly with exit code 0 in 2.03s.

---

## 2. Logic Chain

1. **Hardcoded opportunities prevent live grounded discovery (R1)**:
   - *Observation*: `REAL_OPPORTUNITIES_BASE` defines 8 static opportunities in `research_eligibility.py:15-295`. Line 364 iterates over this list, and line 540 returns them. Discovered URLs from live search (lines 344–362) are only logged to `AgentEvent` and never instantiated.
   - *Reasoning*: Because the code never parses Gemini search output into `Opportunity` instances, the backend cannot function as a dynamic scholarship finder. Any change in student parameters (e.g., target degree, different countries) still results in the same 8 hardcoded opportunities.
   - *Conclusion*: `REAL_OPPORTUNITIES_BASE` must be extracted out of `research_eligibility.py` into isolated test fixtures (`tests/fixtures/opportunities.py`). Live candidates from Gemini Search Grounding must be parsed and stored.

2. **Absence of URL Context Tool breaks evidence grounding (R1, R2)**:
   - *Observation*: `GeminiService.analyze_url_and_extract_criteria` does not pass `tools=[types.Tool(url_context=types.UrlContext())]` to `types.GenerateContentConfig`. Furthermore, the function is never called in the backend pipeline.
   - *Reasoning*: Without `UrlContext`, Gemini cannot read live webpage DOM/text at the candidate URLs. The prompt text interpolation only allows the model to guess from training weights or URL strings.
   - *Conclusion*: `GeminiService` must configure `types.Tool(url_context=types.UrlContext())` via `google-genai` SDK, inspect `candidate.url_context_metadata.url_metadata`, distinguish `URL_RETRIEVAL_STATUS_SUCCESS` from `URL_RETRIEVAL_STATUS_ERROR` / `PAYWALL` / `UNSAFE`, and call this tool in Phase B of `ResearchEligibilityAgent`.

3. **Generic country rules and fabricated quotes violate evidence integrity (R2)**:
   - *Observation*: Lines 393–415 evaluate CGPA via `if raw_opp["country"] == "Canada" and student_cgpa >= 8.0` and synthesize quotes via `f"Student's {student_cgpa}/10.0 CGPA from Indian institution meets B+ minimum admission requirement."`. Language check only verifies `if score:`.
   - *Reasoning*: Universities within the same country have widely differing criteria (e.g., Waterloo requires IELTS 7.5; McGill requires 6.5; TUM requires specific Curricular Analysis). Synthesizing quotes misrepresents model summaries as authoritative source text.
   - *Conclusion*: Extraction must parse specific criteria from the retrieved page. Criteria with unverified equivalencies or unstated rules must be classified as `UNRESOLVED`. Evidence excerpts must be verbatim passages from the retrieved text or labeled as unquoted summaries.

4. **Lack of runtime date checking exposes expired application cycles (R3)**:
   - *Observation*: Fixtures list deadlines of `2025-12-01` and `2025-12-15`. The reviewer only tests `if not opp.deadline:`. Scoring awards +10.0 points when `deadline_verified` is True.
   - *Reasoning*: In 2026, a 2025 deadline is in the past. Presenting an expired deadline as verified and awarding maximum readiness points misleads students into applying for closed cycles.
   - *Conclusion*: Deadlines must be parsed into dates and checked against `datetime.now(timezone.utc).date()`. Deadlines prior to current date must be flagged as `EXPIRED` / passed, preventing active shortlist inclusion unless rolling intake is confirmed.

5. **Rejection loop lacks state memory and feedback consumption (R4)**:
   - *Observation*: `node_research_discovery` in `workflow.py` ignores `state.reviewer_issues` and replaces `state.opportunities` with fresh instances.
   - *Reasoning*: When Quality Reviewer rejects an opportunity and routes back to `research_discovery`, the re-research node cannot correct issues because it has no access to the feedback. Furthermore, replacing `state.opportunities` loses all previously approved opportunities.
   - *Conclusion*: `ResearchEligibilityAgent` must accept `reviewer_issues` and target re-research specifically to flagged criteria or missing official domains. Approved opportunities must be retained across rounds.

---

## 3. Caveats

1. **Live Gemini API Key Quota**: Live Google Search grounding and URL Context queries require a valid `GEMINI_API_KEY`. In development environments without an active key, the system must fail gracefully with explicit configuration errors rather than fabricating live results or falling back silently to mock data.
2. **URL Context Site Restrictions**: Certain university pages block automated crawlers (e.g., Cloudflare bot management, robots.txt, or paywalls). In those cases, `UrlRetrievalStatus` will return `URL_RETRIEVAL_STATUS_ERROR` or `URL_RETRIEVAL_STATUS_PAYWALL`. The system must handle these by marking evidence as `SECONDARY` or `UNRESOLVED` rather than failing the entire run.
3. **Frontend Compatibility**: Frontend components (`OpportunityCard.tsx`, `EvidenceDrawer.tsx`, `AgentWorkspace.tsx`) expect specific fields on `Opportunity` and `EvidenceRecord` (such as `evidence_records`, `eligibility_reasons`, `actionable_gaps`). Any schema refinements to support R1–R4 must remain backward-compatible with frontend TypeScript interfaces (`frontend/src/types/index.ts`).

---

## 4. Conclusion

The ScholarSwarm backend currently functions on a simulated baseline:
- Real live search results are logged as events but discarded from the opportunity pipeline.
- 100% of shortlisted opportunities are drawn from the hardcoded `REAL_OPPORTUNITIES_BASE`.
- The official Gemini URL Context tool is not enabled or invoked.
- Eligibility is evaluated using coarse country-level CGPA heuristics and fabricated quote strings.
- Historical (2025) deadlines are presented as active, verified opportunities.
- The Quality Reviewer loop re-executes without passing feedback to the research agent and overwrites valid opportunities.
- Test documentation refers to a nonexistent `test_quality_reviewer.py`, and `docs/EXPERIMENT.md` contains unverified performance metrics.

To satisfy Requirements R1 through R4, the backend must be refactored to:
1. Isolate `REAL_OPPORTUNITIES_BASE` into `tests/fixtures/opportunities.py` and implement real extraction from Gemini Search Grounding.
2. Wire `types.Tool(url_context=types.UrlContext())` into `GeminiService`, parse retrieval metadata (`UrlRetrievalStatus`), and inspect official DOM content.
3. Replace country heuristics with criterion-level checks against extracted program requirements, marking unknown items as `UNRESOLVED`.
4. Validate deadlines against `datetime.now(timezone.utc)` and replace substring domain checks with authoritative domain verification.
5. Pass `reviewer_issues` to `ResearchEligibilityAgent` in the LangGraph loop, retaining approved candidates and bounding execution to `settings.MAX_RESEARCH_ROUNDS`.

---

## 5. Verification Method

### 5.1 Commands to Verify Current State
1. **Pytest Import Error Reproduction**:
   ```powershell
   cd D:\Case_study_drive\TetraNoodle_AI_Hackathon\backend
   pytest -v
   ```
   *Expected Current Result*: Fails with 7 collection errors (`ModuleNotFoundError: No module named 'app'`).
2. **Pytest via Python Module**:
   ```powershell
   cd D:\Case_study_drive\TetraNoodle_AI_Hackathon\backend
   python -m pytest -v
   ```
   *Expected Current Result*: Passes 21 tests, confirming tests currently validate hardcoded fixtures.
3. **Missing Test Verification**:
   ```powershell
   python -m pytest tests/test_quality_reviewer.py -v
   ```
   *Expected Current Result*: `ERROR: file or directory not found: tests/test_quality_reviewer.py`.
4. **Frontend Production Build**:
   ```powershell
   cd D:\Case_study_drive\TetraNoodle_AI_Hackathon\frontend
   npm run build
   ```
   *Expected Current Result*: Builds cleanly in ~2s (`dist/index.html` created).

### 5.2 Key Code Locations to Inspect
- `backend/app/agents/research_eligibility.py`: Lines 15–295 (`REAL_OPPORTUNITIES_BASE`), Lines 344–362 (discarded search results), Lines 393–415 (country-level CGPA rules).
- `backend/app/services/gemini_service.py`: Lines 104–184 (unwired URL context and uncalled function).
- `backend/app/agents/quality_reviewer.py`: Lines 41–44 (domain substring checks), Lines 72–77 (missing deadline date validation), Line 84 (only checks top opportunity).
- `backend/app/graph/workflow.py`: Lines 27–38 and 72–76 (rejection loop and state overwriting).
- `docs/EXPERIMENT.md`: Lines 24–33 (unsubstantiated metric tables), Lines 50–55 (missing test command).

### 5.3 Invalidation Conditions
This survey report would be invalidated if:
1. A separate dynamic discovery pipeline exists outside `research_eligibility.py` that populates `Opportunity` objects from live web pages (verified false: only `research_eligibility.py` creates `Opportunity` objects).
2. `types.Tool(url_context=...)` is already invoked in another service (verified false: grep confirms `url_context` is never referenced in `backend/app/`).
3. Deadlines are verified against runtime dates elsewhere (verified false: no date comparison with `datetime` exists in `quality_reviewer.py` or `scoring_service.py`).
