# Handoff Report: Explorer M1.2 (Research Agent Extraction & Fixture Isolation)

**Agent**: Explorer M1.2  
**Date**: 2026-10-20T21:30:00Z  
**Target File**: `D:\Case_study_drive\TetraNoodle_AI_Hackathon\.agents\teamwork\teamwork_preview_explorer_m1_2\handoff.md`  
**Reference Documents**:
- `D:\Case_study_drive\TetraNoodle_AI_Hackathon\.agents\teamwork\ORIGINAL_REQUEST.md` (R1, R2, R3, R6)
- `D:\Case_study_drive\TetraNoodle_AI_Hackathon\PROJECT.md` (F1, F2, F3, F4, F5, Milestone M1)

---

## 1. Observation

### 1.1 Hardcoded Fixtures in Production Agent Code
In `backend/app/agents/research_eligibility.py`:
- **Lines 15–295**: Define `REAL_OPPORTUNITIES_BASE`, a hardcoded list of 10 opportunity dictionary records (University of Toronto, TUM, NUS, NTU, UBC, McGill, KIT, SFU, Waterloo, and A*STAR SINGA).
- **Line 15**:
  ```python
  # Verified Real Academic Opportunities for fallback / baseline ground truth
  # Curated from official university & government portals (Canada, Germany, Singapore)
  REAL_OPPORTUNITIES_BASE = [
      {
          "title": "Vector Institute Scholarship in Artificial Intelligence (VSAI) & Master's",
  ...
  ```
- **Lines 364–379**:
  ```python
  # Augment with verified official scholarship opportunities matching target criteria
  for raw_opp in REAL_OPPORTUNITIES_BASE:
      # Check country match
      if raw_opp["country"] not in profile.target_countries:
          continue
          
      norm_url = normalize_url(raw_opp["canonical_url"])
      if norm_url in seen_canonical_urls:
          await repository.save_agent_event(AgentEvent(
              run_id=run_id,
              agent_role=self.role_name,
              event_type="DUPLICATE_REMOVED",
              title="Duplicate Candidate Filtered",
              description=f"Merged duplicate instance of {raw_opp['title']} ({norm_url})."
          ))
          continue
      seen_canonical_urls.add(norm_url)
  ```

### 1.2 Discarding Live Discovered Candidates
In `backend/app/agents/research_eligibility.py`:
- **Lines 344–362**:
  When `gemini_service.is_available` is True, `gemini_service.search_grounded_discovery` is executed for each country. Sources discovered from Google Search Grounding (`discovery_res.get("sources", [])`) are validated and added to `seen_canonical_urls`. An event with `event_type="CANDIDATE_FOUND"` is emitted.
- However, **no Opportunity model is ever instantiated from discovered sources**.
- Instead, execution immediately flows into line 364 (`for raw_opp in REAL_OPPORTUNITIES_BASE:`). If a live candidate URL matches a `REAL_OPPORTUNITIES_BASE` entry, line 370 skips it as duplicate; if it does not match, the live candidate is discarded without creation.
- The returned list `opportunities` contains **only** models constructed from `REAL_OPPORTUNITIES_BASE`.

### 1.3 Fabricated Criteria & Generic Country-Wide Assumptions
In `backend/app/agents/research_eligibility.py`:
- **Lines 391–415**: CGPA evaluation uses broad country-level rules (`if raw_opp["country"] == "Canada" and student_cgpa >= 8.0:`) rather than verifying criteria published by the specific institution.
- **Lines 395, 399, 403, 407, 438, 454, 479**: `evidence_excerpt` values are synthesized with Python f-strings (e.g. `f"Student's {student_cgpa}/10.0 CGPA from Indian institution meets B+ minimum admission requirement."`), rather than quoting verbatim text from live retrieved web pages.
- **Lines 433–444**: Any language test score present is marked `MEETS`, ignoring whether the score fulfills the institution's specific published cutoff.

### 1.4 Uncalled Dead Code in `gemini_service.py`
In `backend/app/services/gemini_service.py`:
- **Lines 104–185**: `analyze_url_and_extract_criteria` exists but is never invoked anywhere in the codebase.
- In addition, line 171 configures `types.GenerateContentConfig` without passing `tools=[types.Tool(url_context=types.UrlContext())]`.

### 1.5 Deprecation Warnings in Python 3.13 Runtime
- In `backend/app/agents/research_eligibility.py` (lines 428, 458, 483, 518), calls to `datetime.utcnow()` trigger deprecation warnings:
  `DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).`

### 1.6 Existing Test Fixtures Status
- `backend/tests/fixtures/opportunities.py` has been created with `CANONICAL_FIXTURE_OPPORTUNITIES` (5 items) used by `tests/e2e/test_tier1_feature_coverage.py`.
- Running `pytest` in `backend` currently passes all 31 tests.
- `REAL_OPPORTUNITIES_BASE` is currently only referenced in `backend/app/agents/research_eligibility.py`.

---

## 2. Logic Chain

1. **Observations 1.1 & 1.2** show that ScholarSwarm's research agent currently displays hardcoded opportunities exclusively from `REAL_OPPORTUNITIES_BASE`, bypassing all live Google Search discoveries.
2. To satisfy Requirement **R1** and Feature **F1**, `REAL_OPPORTUNITIES_BASE` must be eliminated completely from `backend/app/agents/research_eligibility.py` and isolated inside `backend/tests/fixtures/opportunities.py`. Live code paths must contain zero opportunity fixtures.
3. **Observation 1.4** demonstrates that `gemini_service.analyze_url_and_extract_criteria` must be activated and integrated into `execute_discovery_and_audit`. When candidate URLs are discovered via `search_grounded_discovery`, they must be fed directly into `analyze_url_and_extract_criteria`.
4. **Observation 1.3** demonstrates that criteria matching and evidence generation cannot rely on hardcoded Python rules or synthesized f-strings. Instead, Gemini URL Context must retrieve official page content, extract published admission and scholarship criteria, and produce verbatim evidence excerpts with real citation URLs.
5. In Phase C of `execute_discovery_and_audit`, `Opportunity` models must be instantiated dynamically using the payload returned by `analyze_url_and_extract_criteria`, populated with authentic `EligibilityCriterion`, `FundingDetails`, `EvidenceRecord`, and retrieval timestamps.
6. If `gemini_service.is_available` is False, `execute_discovery_and_audit` must raise an explicit `GeminiConfigurationError` rather than silently skipping search and falling back to dummy records, satisfying Requirement **R1** and Feature **F5**.
7. Partial branch failures (e.g. a paywalled or errored URL) must be logged as `EXTRACTION_SKIPPED` without crashing the loop, ensuring successfully extracted opportunities are preserved (satisfying Requirement **R4**).
8. Replacing `datetime.utcnow()` with `datetime.now(timezone.utc)` removes all deprecation warnings in the test runner.

---

## 3. Caveats

1. **Coordination with Explorer M1.1**: Explorer M1.1 is specifying the exact changes inside `backend/app/services/gemini_service.py` to enable `types.Tool(url_context=types.UrlContext())` and return `retrieval_status` alongside JSON data. The interface designed here matches M1.1's return contract:
   `{"success": bool, "retrieval_status": str, "evidence_quality": str, "data": dict}`.
2. **Offline CI Testing**: Without a live `GEMINI_API_KEY`, end-to-end tests calling `execute_discovery_and_audit` directly must patch `gemini_service` using fixture helpers in `backend/tests/fixtures/opportunities.py`.
3. **Search Grounding Yield**: If Google Search Grounding discovers 0 opportunities for an obscure search query, the pipeline returns `[]` honestly. The system must never synthesize fake opportunities to satisfy an arbitrary quota.

---

## 4. Conclusion & Implementation Plan

### 4.1 Plan Summary
1. **Fixture Isolation**: Update `backend/tests/fixtures/opportunities.py` to export both `CANONICAL_FIXTURE_OPPORTUNITIES` and `REAL_OPPORTUNITIES_BASE` (with full 10-item list), plus helper functions `get_fixture_opportunity_models()`, `get_mock_discovery_response()`, and `get_mock_url_analysis_response()`.
2. **Clean Agent Module**: Remove lines 13–295 (`REAL_OPPORTUNITIES_BASE`) from `backend/app/agents/research_eligibility.py`.
3. **Missing Key Policy**: In `execute_discovery_and_audit`, check `gemini_service.is_available`. If False, raise `GeminiConfigurationError`.
4. **Candidate Discovery**: Collect real, sanitized, unique candidate URLs from `gemini_service.search_grounded_discovery(query, context_prompt)`.
5. **URL Context Audit**: For each candidate URL, invoke `gemini_service.analyze_url_and_extract_criteria`.
6. **Dynamic Instantiation**: Construct `Opportunity` instances dynamically using extracted fields, authentic `EligibilityCriterion` entries, and verbatim `EvidenceRecord` instances. Save evidence records to `repository`.
7. **Deprecation Fixes**: Use `datetime.now(timezone.utc)` for all timestamps.

---

## 5. Worker Implementation Instructions & Exact Code Diffs

### Step 1: Update `backend/tests/fixtures/opportunities.py`
Ensure `backend/tests/fixtures/opportunities.py` contains the complete canonical fixture list, aliases `REAL_OPPORTUNITIES_BASE = CANONICAL_FIXTURE_OPPORTUNITIES`, and provides model factory helpers.

#### Target File: `backend/tests/fixtures/opportunities.py`
Add the following exports at the bottom of the file (or merge cleanly):
```python
import uuid
from datetime import datetime, timezone
from app.models.opportunity import Opportunity, FundingDetails, EligibilityCriterion
from app.models.evidence import EvidenceRecord

# Backwards-compatible alias for existing tests and harnesses
REAL_OPPORTUNITIES_BASE = CANONICAL_FIXTURE_OPPORTUNITIES

def get_fixture_raw_opportunities(countries: list[str] | None = None) -> list[dict]:
    """Returns a copy of canonical fixture dictionaries, optionally filtered by country."""
    if not countries:
        return [dict(item) for item in CANONICAL_FIXTURE_OPPORTUNITIES]
    return [dict(item) for item in CANONICAL_FIXTURE_OPPORTUNITIES if item.get("country") in countries]

def get_fixture_opportunity_models(run_id: str = "fixture-run", countries: list[str] | None = None) -> list[Opportunity]:
    """Builds and returns genuine Opportunity pydantic model instances from test fixtures."""
    raw_list = get_fixture_raw_opportunities(countries)
    models: list[Opportunity] = []
    now_dt = datetime.now(timezone.utc)
    now_iso = now_dt.isoformat()

    for raw in raw_list:
        opp_id = raw.get("id") or str(uuid.uuid4())
        funding_data = raw.get("funding", {})
        funding = FundingDetails(
            funding_type=funding_data.get("funding_type", "Unknown"),
            coverage_description=funding_data.get("coverage_description", "Unspecified"),
            amount=funding_data.get("amount"),
            currency=funding_data.get("currency"),
            tuition_covered=funding_data.get("tuition_covered", False)
        )

        adm_reqs = [
            EligibilityCriterion(
                criterion_type=req.get("criterion_type", "PREREQUISITE"),
                is_mandatory=req.get("is_mandatory", True),
                requirement_text=req.get("requirement_text", ""),
                official_equivalency_note=req.get("official_equivalency_note")
            )
            for req in raw.get("admission_requirements", [])
        ]

        sch_reqs = [
            EligibilityCriterion(
                criterion_type=req.get("criterion_type", "PREREQUISITE"),
                is_mandatory=req.get("is_mandatory", False),
                requirement_text=req.get("requirement_text", ""),
                official_equivalency_note=req.get("official_equivalency_note")
            )
            for req in raw.get("scholarship_requirements", [])
        ]

        evidence_records = [
            EvidenceRecord(
                id=str(uuid.uuid4()),
                opportunity_id=opp_id,
                run_id=run_id,
                criterion_name=req.criterion_type,
                stated_requirement=req.requirement_text,
                student_value="Satisfies published requirements",
                status="MEETS",
                evidence_excerpt=f"Requirement verified: {req.requirement_text}",
                source_title=f"{raw.get('university')} Official Admissions",
                source_url=raw.get("canonical_url", ""),
                source_category="OFFICIAL",
                checked_at=now_dt
            )
            for req in adm_reqs + sch_reqs
        ]

        opp = Opportunity(
            id=opp_id,
            run_id=run_id,
            canonical_url=raw.get("canonical_url", ""),
            title=raw.get("title", ""),
            program_name=raw.get("program_name", ""),
            university=raw.get("university", ""),
            country=raw.get("country", ""),
            degree_level=raw.get("degree_level", "Master's"),
            field=raw.get("field", "Computer Science"),
            intake=raw.get("intake"),
            admission_requirements=adm_reqs,
            scholarship_requirements=sch_reqs,
            funding_details=funding,
            deadline=raw.get("deadline"),
            deadline_type=raw.get("deadline_type", "Fixed"),
            deadline_verified=raw.get("deadline_verified", True),
            official_application_url=raw.get("canonical_url"),
            official_source_urls=raw.get("official_source_urls", [raw.get("canonical_url")]),
            source_retrieval_timestamps={u: now_iso for u in raw.get("official_source_urls", [raw.get("canonical_url")])},
            evidence_quality="OFFICIAL",
            eligibility_status="MEETS_STATED_CRITERIA",
            eligibility_reasons=["Meets academic requirements based on official fixture."],
            actionable_gaps=[],
            evidence_records=evidence_records,
            created_at=now_dt
        )
        models.append(opp)

    return models

def get_mock_discovery_response(countries: list[str] | None = None) -> dict:
    """Mock Gemini Search Grounding discovery response."""
    fixtures = get_fixture_raw_opportunities(countries)
    sources = [{"title": f["title"], "url": f["canonical_url"]} for f in fixtures]
    return {
        "success": True,
        "text": "Discovered accredited university programs matching query.",
        "sources": sources,
        "search_queries": [f"official graduate scholarships {c}" for c in (countries or ["Canada"])],
        "model_used": "gemini-2.5-flash"
    }
```

---

### Step 2: Refactor `backend/app/agents/research_eligibility.py`
Replace the entirety of `backend/app/agents/research_eligibility.py` with the following clean, fixture-free implementation:

```python
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from app.models.profile import StudentProfile
from app.models.opportunity import Opportunity, FundingDetails, EligibilityCriterion
from app.models.evidence import EvidenceRecord
from app.models.events import AgentEvent
from app.services.gemini_service import gemini_service
from app.security.sanitizer import normalize_url, is_safe_url
from app.db.repository import repository
from app.config import settings

# Graceful configuration error import
try:
    from app.services.gemini_service import GeminiConfigurationError
except ImportError:
    class GeminiConfigurationError(Exception):
        """Raised when GEMINI_API_KEY is not configured for live operations."""
        pass


class ResearchEligibilityAgent:
    """
    Agent 2: Research & Eligibility Agent
    Coordinates live discovery via Gemini Google Search Grounding and page evaluation
    via URL context, extracting evidence records and determining criterion-level status.
    """
    def __init__(self):
        self.role_name = "Research & Eligibility Agent"

    async def execute_discovery_and_audit(
        self,
        run_id: str,
        profile: StudentProfile,
        research_round: int = 1,
        reviewer_issues: Optional[List[Dict[str, Any]]] = None
    ) -> List[Opportunity]:
        """
        Executes live grounded discovery and official URL extraction.

        1. Validates Gemini API key availability (raises explicit error if unconfigured).
        2. Formulates search queries targeting profile degree, field, and countries.
        3. Discovers real academic candidate URLs using Gemini Google Search Grounding.
        4. Retrieves and analyzes official page content via Gemini URL Context tool.
        5. Dynamically instantiates Opportunity and EvidenceRecord models from authentic page data.
        6. Strictly avoids synthetic or hardcoded fixtures in live execution.
        """
        # Validate Gemini API key availability - live discovery MUST NOT silently fall back
        if not gemini_service.is_available:
            raise GeminiConfigurationError(
                "GEMINI_API_KEY is not configured. Live research discovery requires a valid Gemini API key. "
                "Configure GEMINI_API_KEY in backend/.env to run live discovery."
            )

        # Phase A: Opportunity Discovery
        await repository.save_agent_event(AgentEvent(
            run_id=run_id,
            agent_role=self.role_name,
            event_type="SEARCH_QUERY",
            title=f"Opportunity Discovery (Round {research_round})",
            description=f"Formulating profile-targeted search queries for {profile.target_degree} in {profile.target_field} across {', '.join(profile.target_countries)}.",
            metadata={"countries": profile.target_countries, "degree": profile.target_degree}
        ))

        candidate_sources: List[Dict[str, Any]] = []
        seen_canonical_urls = set()

        student_context = (
            f"Student has CGPA {profile.cgpa}/{profile.grading_scale} from {profile.institution}, "
            f"current degree {profile.current_degree}, seeking {profile.target_degree} in {profile.target_field}."
        )

        # Phase A.1: Live Gemini Search Grounding per target country
        for country in profile.target_countries:
            query = (
                f"official site:edu OR site:gov OR site:ac scholarship fully funded "
                f"{profile.target_degree} in {profile.target_field} in {country} "
                f"admission requirements CGPA deadline"
            )

            if reviewer_issues and research_round > 1:
                issue_text = " ".join([str(issue.get("issue", issue)) if isinstance(issue, dict) else str(issue) for issue in reviewer_issues])
                if issue_text:
                    query += f" official admissions {issue_text[:80]}"

            await repository.save_agent_event(AgentEvent(
                run_id=run_id,
                agent_role=self.role_name,
                event_type="SEARCH_QUERY",
                title=f"Querying Google Search Grounding: {country}",
                description=f"Query: '{query}'",
                metadata={"query": query, "country": country}
            ))

            discovery_res = await gemini_service.search_grounded_discovery(
                query=query,
                context_prompt=student_context
            )

            if discovery_res.get("success"):
                for src in discovery_res.get("sources", []):
                    raw_url = src.get("url")
                    if not raw_url or not is_safe_url(raw_url):
                        continue
                    norm_url = normalize_url(raw_url)
                    if norm_url in seen_canonical_urls:
                        continue
                    seen_canonical_urls.add(norm_url)

                    candidate_title = src.get("title", "Official Degree / Scholarship Page")
                    candidate_sources.append({
                        "url": norm_url,
                        "title": candidate_title,
                        "country": country
                    })

                    await repository.save_agent_event(AgentEvent(
                        run_id=run_id,
                        agent_role=self.role_name,
                        event_type="CANDIDATE_FOUND",
                        title=f"Discovered Live Candidate in {country}",
                        description=f"Source: {candidate_title} ({norm_url})",
                        metadata={"url": norm_url, "country": country}
                    ))
            else:
                await repository.save_agent_event(AgentEvent(
                    run_id=run_id,
                    agent_role=self.role_name,
                    event_type="SEARCH_WARNING",
                    title=f"Search Grounding Warning: {country}",
                    description=discovery_res.get("error", "No search results returned."),
                    metadata={"country": country}
                ))

        # Check if any candidates were discovered
        if not candidate_sources:
            await repository.save_agent_event(AgentEvent(
                run_id=run_id,
                agent_role=self.role_name,
                event_type="DISCOVERY_EMPTY",
                title="No Candidates Found",
                description="Live search grounding did not return candidate URLs for the specified criteria.",
                metadata={"countries": profile.target_countries}
            ))
            return []

        # Bound candidates to settings limit
        max_candidates = getattr(settings, "MAX_RESEARCH_CANDIDATES", 30)
        candidates_to_evaluate = candidate_sources[:max_candidates]

        opportunities: List[Opportunity] = []
        student_summary = (
            f"Name: {profile.full_name}, Degree: {profile.current_degree}, Institution: {profile.institution}, "
            f"CGPA: {profile.cgpa}/{profile.grading_scale}, Target Degree: {profile.target_degree}, "
            f"Target Field: {profile.target_field}, Target Countries: {', '.join(profile.target_countries)}, "
            f"Language Tests: {profile.language_tests or 'None'}"
        )

        # Phase B & C: Extract criteria & evaluate against student profile via URL Context
        for cand in candidates_to_evaluate:
            cand_url = cand["url"]
            cand_title = cand["title"]
            cand_country = cand["country"]

            await repository.save_agent_event(AgentEvent(
                run_id=run_id,
                agent_role=self.role_name,
                event_type="ANALYZING_PAGE",
                title=f"Evaluating Page Content: {cand_title[:40]}",
                description=f"Retrieving official page via Gemini URL Context tool: {cand_url}",
                metadata={"url": cand_url, "country": cand_country}
            ))

            try:
                extraction_res = await gemini_service.analyze_url_and_extract_criteria(
                    urls=[cand_url],
                    program_name=cand_title,
                    university=cand_title,
                    student_profile_summary=student_summary
                )
            except Exception as exc:
                await repository.save_agent_event(AgentEvent(
                    run_id=run_id,
                    agent_role=self.role_name,
                    event_type="EXTRACTION_FAILED",
                    title=f"URL Extraction Error: {cand_title[:40]}",
                    description=f"Failed to extract criteria from {cand_url}: {str(exc)}",
                    metadata={"url": cand_url, "error": str(exc)}
                ))
                continue

            if not extraction_res.get("success"):
                error_msg = extraction_res.get("error", "URL extraction unsuccessful.")
                retrieval_status = extraction_res.get("retrieval_status", "URL_RETRIEVAL_STATUS_ERROR")
                await repository.save_agent_event(AgentEvent(
                    run_id=run_id,
                    agent_role=self.role_name,
                    event_type="EXTRACTION_SKIPPED",
                    title=f"Skipped Candidate ({retrieval_status})",
                    description=f"Could not retrieve authentic content for {cand_url}: {error_msg}",
                    metadata={"url": cand_url, "retrieval_status": retrieval_status}
                ))
                continue

            extracted_data = extraction_res.get("data", {})
            if not extracted_data:
                continue

            # Phase C: Dynamic Opportunity Model Instantiation
            opp_id = str(uuid.uuid4())
            now_dt = datetime.now(timezone.utc)
            now_iso = now_dt.isoformat()

            program_name = extracted_data.get("program_name") or cand_title
            university = extracted_data.get("university") or "Official University / Provider"
            country = extracted_data.get("country") or cand_country
            degree_level = extracted_data.get("degree_level") or profile.target_degree
            field = extracted_data.get("field") or profile.target_field
            intake = extracted_data.get("intake")
            title = extracted_data.get("title") or f"{program_name} - {university}"

            raw_funding = extracted_data.get("funding_details", {})
            funding = FundingDetails(
                funding_type=raw_funding.get("funding_type", "Unknown"),
                coverage_description=raw_funding.get("coverage_description", "Unspecified"),
                amount=raw_funding.get("amount"),
                currency=raw_funding.get("currency"),
                stipend_amount=raw_funding.get("stipend_amount"),
                tuition_covered=raw_funding.get("tuition_covered", False)
            )

            evidence_quality = extraction_res.get("evidence_quality", "OFFICIAL")
            retrieval_status = extraction_res.get("retrieval_status", "URL_RETRIEVAL_STATUS_SUCCESS")
            if retrieval_status != "URL_RETRIEVAL_STATUS_SUCCESS":
                evidence_quality = "UNVERIFIED"

            # Parse admission requirements
            raw_adm_reqs = extracted_data.get("admission_requirements", [])
            admission_requirements: List[EligibilityCriterion] = []
            for req in raw_adm_reqs:
                req_text = req.get("stated_requirement") or req.get("requirement_text") or ""
                if req_text:
                    admission_requirements.append(EligibilityCriterion(
                        criterion_type=req.get("criterion_type", "PREREQUISITE"),
                        is_mandatory=req.get("is_mandatory", True),
                        requirement_text=req_text,
                        official_equivalency_note=req.get("official_equivalency_note")
                    ))

            # Parse scholarship requirements
            raw_sch_reqs = extracted_data.get("scholarship_requirements", [])
            scholarship_requirements: List[EligibilityCriterion] = []
            for req in raw_sch_reqs:
                req_text = req.get("stated_requirement") or req.get("requirement_text") or ""
                if req_text:
                    scholarship_requirements.append(EligibilityCriterion(
                        criterion_type=req.get("criterion_type", "PREREQUISITE"),
                        is_mandatory=req.get("is_mandatory", False),
                        requirement_text=req_text,
                        official_equivalency_note=req.get("official_equivalency_note")
                    ))

            # Build authentic evidence records
            evidence_records: List[EvidenceRecord] = []
            for req in raw_adm_reqs + raw_sch_reqs:
                req_text = req.get("stated_requirement") or req.get("requirement_text") or ""
                if not req_text:
                    continue
                ev = EvidenceRecord(
                    id=str(uuid.uuid4()),
                    opportunity_id=opp_id,
                    run_id=run_id,
                    criterion_name=req.get("criterion_name", "Academic Criterion"),
                    stated_requirement=req_text,
                    student_value=req.get("student_value"),
                    status=req.get("status", "UNRESOLVED"),
                    evidence_excerpt=req.get("evidence_excerpt"),
                    source_title=f"{university} Official Regulations",
                    source_url=req.get("source_url") or cand_url,
                    source_category=evidence_quality,
                    checked_at=now_dt
                )
                evidence_records.append(ev)

            overall_status = extracted_data.get("overall_eligibility_status", "INSUFFICIENT_EVIDENCE")
            eligibility_reasons = extracted_data.get("eligibility_reasons", [])
            actionable_gaps = extracted_data.get("actionable_gaps", [])

            official_source_urls = [cand_url]
            if extracted_data.get("official_source_urls"):
                for u in extracted_data["official_source_urls"]:
                    if u not in official_source_urls and is_safe_url(u):
                        official_source_urls.append(normalize_url(u))

            deadline = extracted_data.get("deadline")
            deadline_type = extracted_data.get("deadline_type", "Unknown")
            deadline_verified = extracted_data.get("deadline_verified", False)

            opp = Opportunity(
                id=opp_id,
                run_id=run_id,
                canonical_url=cand_url,
                title=title,
                program_name=program_name,
                university=university,
                country=country,
                degree_level=degree_level,
                field=field,
                intake=intake,
                admission_requirements=admission_requirements,
                scholarship_requirements=scholarship_requirements,
                funding_details=funding,
                deadline=deadline,
                deadline_type=deadline_type,
                deadline_verified=deadline_verified,
                official_application_url=extracted_data.get("official_application_url") or cand_url,
                official_source_urls=official_source_urls,
                source_retrieval_timestamps={u: now_iso for u in official_source_urls},
                evidence_quality=evidence_quality,
                eligibility_status=overall_status,
                eligibility_reasons=eligibility_reasons,
                actionable_gaps=actionable_gaps,
                evidence_records=evidence_records,
                created_at=now_dt
            )

            if evidence_records:
                await repository.save_evidence_records(evidence_records)

            opportunities.append(opp)

            await repository.save_agent_event(AgentEvent(
                run_id=run_id,
                agent_role=self.role_name,
                event_type="ELIGIBILITY_EVALUATED",
                title=f"Evaluated: {opp.program_name}",
                description=f"Status: {overall_status} at {opp.university} ({opp.country}). Verified against {len(evidence_records)} official criteria.",
                metadata={"status": overall_status, "opportunity_id": opp.id}
            ))

        return opportunities
```

---

### Step 3: Exact Unified Diff for `backend/app/agents/research_eligibility.py`

```diff
--- a/backend/app/agents/research_eligibility.py
+++ b/backend/app/agents/research_eligibility.py
@@ -1,300 +1,24 @@
 import uuid
-import asyncio
 from typing import List, Dict, Any, Optional
-from datetime import datetime
+from datetime import datetime, timezone
 from app.models.profile import StudentProfile
 from app.models.opportunity import Opportunity, FundingDetails, EligibilityCriterion
 from app.models.evidence import EvidenceRecord
 from app.models.events import AgentEvent
-from app.services.gemini_service import gemini_service
+from app.services.gemini_service import gemini_service
 from app.security.sanitizer import normalize_url, is_safe_url
 from app.db.repository import repository
-
-# Verified Real Academic Opportunities for fallback / baseline ground truth
-# Curated from official university & government portals (Canada, Germany, Singapore)
-REAL_OPPORTUNITIES_BASE = [
-    ... (280 lines of hardcoded fixture records removed) ...
-]
+from app.config import settings
+
+try:
+    from app.services.gemini_service import GeminiConfigurationError
+except ImportError:
+    class GeminiConfigurationError(Exception):
+        """Raised when GEMINI_API_KEY is not configured for live operations."""
+        pass
 
 class ResearchEligibilityAgent:
     """
@@ -306,238 +30,229 @@ class ResearchEligibilityAgent:
     async def execute_discovery_and_audit(
         self,
         run_id: str,
         profile: StudentProfile,
-        research_round: int = 1
+        research_round: int = 1,
+        reviewer_issues: Optional[List[Dict[str, Any]]] = None
     ) -> List[Opportunity]:
+        if not gemini_service.is_available:
+            raise GeminiConfigurationError(
+                "GEMINI_API_KEY is not configured. Live research discovery requires a valid Gemini API key. "
+                "Configure GEMINI_API_KEY in backend/.env to run live discovery."
+            )
+
         # Phase A: Opportunity Discovery
         await repository.save_agent_event(AgentEvent(
             run_id=run_id,
             agent_role=self.role_name,
             event_type="SEARCH_QUERY",
             title=f"Opportunity Discovery (Round {research_round})",
             description=f"Formulating profile-targeted search queries for {profile.target_degree} in {profile.target_field} across {', '.join(profile.target_countries)}.",
             metadata={"countries": profile.target_countries, "degree": profile.target_degree}
         ))
 
-        opportunities: List[Opportunity] = []
+        candidate_sources: List[Dict[str, Any]] = []
         seen_canonical_urls = set()
+        student_context = (
+            f"Student has CGPA {profile.cgpa}/{profile.grading_scale} from {profile.institution}, "
+            f"current degree {profile.current_degree}, seeking {profile.target_degree} in {profile.target_field}."
+        )
 
-        # Try live Gemini Search Grounding if API is configured
-        if gemini_service.is_available:
-            for country in profile.target_countries:
-                query = f"official site:edu OR site:gov OR site:ac scholarship fully funded {profile.target_degree} in {profile.target_field} in {country} admission requirements CGPA deadline"
-                
+        for country in profile.target_countries:
+            query = (
+                f"official site:edu OR site:gov OR site:ac scholarship fully funded "
+                f"{profile.target_degree} in {profile.target_field} in {country} "
+                f"admission requirements CGPA deadline"
+            )
+            if reviewer_issues and research_round > 1:
+                issue_text = " ".join([str(issue.get("issue", issue)) if isinstance(issue, dict) else str(issue) for issue in reviewer_issues])
+                if issue_text:
+                    query += f" official admissions {issue_text[:80]}"
+
+            await repository.save_agent_event(AgentEvent(
+                run_id=run_id,
+                agent_role=self.role_name,
+                event_type="SEARCH_QUERY",
+                title=f"Querying Google Search Grounding: {country}",
+                description=f"Query: '{query}'",
+                metadata={"query": query, "country": country}
+            ))
+
+            discovery_res = await gemini_service.search_grounded_discovery(
+                query=query,
+                context_prompt=student_context
+            )
+
+            if discovery_res.get("success"):
+                for src in discovery_res.get("sources", []):
+                    raw_url = src.get("url")
+                    if not raw_url or not is_safe_url(raw_url):
+                        continue
+                    norm_url = normalize_url(raw_url)
+                    if norm_url in seen_canonical_urls:
+                        continue
+                    seen_canonical_urls.add(norm_url)
+                    candidate_title = src.get("title", "Official Degree / Scholarship Page")
+                    candidate_sources.append({
+                        "url": norm_url,
+                        "title": candidate_title,
+                        "country": country
+                    })
+                    await repository.save_agent_event(AgentEvent(
+                        run_id=run_id,
+                        agent_role=self.role_name,
+                        event_type="CANDIDATE_FOUND",
+                        title=f"Discovered Live Candidate in {country}",
+                        description=f"Source: {candidate_title} ({norm_url})",
+                        metadata={"url": norm_url, "country": country}
+                    ))
+
+        if not candidate_sources:
+            return []
+
+        max_candidates = getattr(settings, "MAX_RESEARCH_CANDIDATES", 30)
+        candidates_to_evaluate = candidate_sources[:max_candidates]
+        opportunities: List[Opportunity] = []
+        student_summary = (
+            f"Name: {profile.full_name}, Degree: {profile.current_degree}, Institution: {profile.institution}, "
+            f"CGPA: {profile.cgpa}/{profile.grading_scale}, Target Degree: {profile.target_degree}, "
+            f"Target Field: {profile.target_field}, Target Countries: {', '.join(profile.target_countries)}, "
+            f"Language Tests: {profile.language_tests or 'None'}"
+        )
+
+        # Phase B & C: Extract criteria & evaluate via URL Context
+        for cand in candidates_to_evaluate:
+            cand_url = cand["url"]
+            cand_title = cand["title"]
+            cand_country = cand["country"]
+
+            try:
+                extraction_res = await gemini_service.analyze_url_and_extract_criteria(
+                    urls=[cand_url],
+                    program_name=cand_title,
+                    university=cand_title,
+                    student_profile_summary=student_summary
+                )
+            except Exception as exc:
+                continue
+
+            if not extraction_res.get("success"):
+                continue
+
+            extracted_data = extraction_res.get("data", {})
+            if not extracted_data:
+                continue
+
+            opp_id = str(uuid.uuid4())
+            now_dt = datetime.now(timezone.utc)
+            now_iso = now_dt.isoformat()
+
+            program_name = extracted_data.get("program_name") or cand_title
+            university = extracted_data.get("university") or "Official University / Provider"
+            country = extracted_data.get("country") or cand_country
+            degree_level = extracted_data.get("degree_level") or profile.target_degree
+            field = extracted_data.get("field") or profile.target_field
+            intake = extracted_data.get("intake")
+            title = extracted_data.get("title") or f"{program_name} - {university}"
+
+            raw_funding = extracted_data.get("funding_details", {})
+            funding = FundingDetails(
+                funding_type=raw_funding.get("funding_type", "Unknown"),
+                coverage_description=raw_funding.get("coverage_description", "Unspecified"),
+                amount=raw_funding.get("amount"),
+                currency=raw_funding.get("currency"),
+                stipend_amount=raw_funding.get("stipend_amount"),
+                tuition_covered=raw_funding.get("tuition_covered", False)
+            )
+
+            evidence_quality = extraction_res.get("evidence_quality", "OFFICIAL")
+            retrieval_status = extraction_res.get("retrieval_status", "URL_RETRIEVAL_STATUS_SUCCESS")
+            if retrieval_status != "URL_RETRIEVAL_STATUS_SUCCESS":
+                evidence_quality = "UNVERIFIED"
+
+            raw_adm_reqs = extracted_data.get("admission_requirements", [])
+            admission_requirements = [
+                EligibilityCriterion(
+                    criterion_type=req.get("criterion_type", "PREREQUISITE"),
+                    is_mandatory=req.get("is_mandatory", True),
+                    requirement_text=req.get("stated_requirement", req.get("requirement_text", "")),
+                    official_equivalency_note=req.get("official_equivalency_note")
+                )
+                for req in raw_adm_reqs if req.get("stated_requirement") or req.get("requirement_text")
+            ]
+
+            raw_sch_reqs = extracted_data.get("scholarship_requirements", [])
+            scholarship_requirements = [
+                EligibilityCriterion(
+                    criterion_type=req.get("criterion_type", "PREREQUISITE"),
+                    is_mandatory=req.get("is_mandatory", False),
+                    requirement_text=req.get("stated_requirement", req.get("requirement_text", "")),
+                    official_equivalency_note=req.get("official_equivalency_note")
+                )
+                for req in raw_sch_reqs if req.get("stated_requirement") or req.get("requirement_text")
+            ]
+
+            evidence_records = [
+                EvidenceRecord(
+                    id=str(uuid.uuid4()),
+                    opportunity_id=opp_id,
+                    run_id=run_id,
+                    criterion_name=req.get("criterion_name", "Academic Criterion"),
+                    stated_requirement=req.get("stated_requirement", req.get("requirement_text", "")),
+                    student_value=req.get("student_value"),
+                    status=req.get("status", "UNRESOLVED"),
+                    evidence_excerpt=req.get("evidence_excerpt"),
+                    source_title=f"{university} Official Regulations",
+                    source_url=req.get("source_url") or cand_url,
+                    source_category=evidence_quality,
+                    checked_at=now_dt
+                )
+                for req in raw_adm_reqs + raw_sch_reqs if req.get("stated_requirement") or req.get("requirement_text")
+            ]
+
+            opp = Opportunity(
+                id=opp_id,
+                run_id=run_id,
+                canonical_url=cand_url,
+                title=title,
+                program_name=program_name,
+                university=university,
+                country=country,
+                degree_level=degree_level,
+                field=field,
+                intake=intake,
+                admission_requirements=admission_requirements,
+                scholarship_requirements=scholarship_requirements,
+                funding_details=funding,
+                deadline=extracted_data.get("deadline"),
+                deadline_type=extracted_data.get("deadline_type", "Unknown"),
+                deadline_verified=extracted_data.get("deadline_verified", False),
+                official_application_url=extracted_data.get("official_application_url") or cand_url,
+                official_source_urls=[cand_url],
+                source_retrieval_timestamps={cand_url: now_iso},
+                evidence_quality=evidence_quality,
+                eligibility_status=extracted_data.get("overall_eligibility_status", "INSUFFICIENT_EVIDENCE"),
+                eligibility_reasons=extracted_data.get("eligibility_reasons", []),
+                actionable_gaps=extracted_data.get("actionable_gaps", []),
+                evidence_records=evidence_records,
+                created_at=now_dt
+            )
+
+            if evidence_records:
+                await repository.save_evidence_records(evidence_records)
+            opportunities.append(opp)
+
+        return opportunities
```

---

## 6. Verification Method

1. **Schema and Test Suite Verification**:
   Execute `pytest` in `backend`:
   ```bash
   cd backend
   pytest
   ```
   **Expected**: All 31+ tests pass cleanly without errors or `DeprecationWarning` from `research_eligibility.py`.

2. **Zero Hardcoded Fixtures Inspection**:
   Run grep across the entire `backend/app/` tree:
   ```bash
   grep -rn "REAL_OPPORTUNITIES_BASE" backend/app/
   ```
   **Expected**: 0 results returned.

3. **URL Context Pipeline Integration Check**:
   Verify that `backend/app/agents/research_eligibility.py` invokes `analyze_url_and_extract_criteria` directly with candidate URLs discovered from `gemini_service.search_grounded_discovery`.

4. **Missing Key Policy Enforcement**:
   Verify that running `execute_discovery_and_audit` with `gemini_service.api_key = ""` raises `GeminiConfigurationError`.
