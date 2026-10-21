# Handoff Report: Gemini URL Context & Grounding Service (Milestone M1)

**Agent**: Explorer M1.1 (Gemini URL Context & Grounding Service)  
**Target Milestone**: M1 (Grounded Discovery & Real Extraction — Features F1, F2, F3, F4, F5)  
**Target Files**:
- `backend/app/services/gemini_service.py`
- `backend/app/agents/research_eligibility.py`
- `backend/tests/fixtures/opportunities.py` (New fixture module)
- `backend/tests/test_graph.py` (Mock alignment)

---

## 1. Observation

### 1.1 Current State of `backend/app/services/gemini_service.py`
1. **`analyze_url_and_extract_criteria` lacks URL Context Tool**:
   - In lines 171-174 of `gemini_service.py`:
     ```python
     config = types.GenerateContentConfig(
         temperature=0.1,
         response_mime_type="application/json"
     )
     ```
     `tools=[types.Tool(url_context=types.UrlContext())]` is **completely absent**. The model is prompted with URLs in text but cannot fetch or read webpage contents through Gemini's official URL Context tool.
2. **Missing `UrlContextMetadata` Inspection**:
   - Lines 175-184:
     ```python
     response = await asyncio.to_thread(
         self._client.models.generate_content,
         model=self.model,
         contents=prompt,
         config=config
     )
     data = json.loads(response.text)
     return {"success": True, "data": data}
     ```
     The method completely ignores `candidate.url_context_metadata`. It does not inspect `url_metadata`, does not evaluate `url_retrieval_status`, and returns raw parsed JSON without retrieval verification.
3. **`analyze_url_and_extract_criteria` is Never Called**:
   - Global grep across `backend/` confirmed that `analyze_url_and_extract_criteria` is defined only at line 104 of `gemini_service.py` and has **zero invocations anywhere in the codebase**.

### 1.2 SDK Capabilities Verified (`google-genai` v1.0.0+)
Direct inspection of `google.genai.types` via Python runtime confirmed the exact types:
- **`types.Tool`**: Contains field `url_context: Optional[UrlContext]`. Initialized as `types.Tool(url_context=types.UrlContext())`.
- **`types.UrlContext`**: Parameterless initialization `types.UrlContext()`.
- **`types.Candidate`**: Contains field `url_context_metadata: Optional[UrlContextMetadata]`.
- **`types.UrlContextMetadata`**: Contains field `url_metadata: Optional[list[UrlMetadata]]`.
- **`types.UrlMetadata`**: Contains fields:
  - `retrieved_url: Optional[str]`
  - `url_retrieval_status: Optional[UrlRetrievalStatus]`
- **`types.UrlRetrievalStatus`**: StrEnum with exact values:
  - `URL_RETRIEVAL_STATUS_SUCCESS`
  - `URL_RETRIEVAL_STATUS_ERROR`
  - `URL_RETRIEVAL_STATUS_PAYWALL`
  - `URL_RETRIEVAL_STATUS_UNSAFE`
  - `URL_RETRIEVAL_STATUS_UNSPECIFIED`

### 1.3 Current State of `backend/app/agents/research_eligibility.py`
1. **Hardcoded Opportunities in Live Code Path**:
   - Lines 15-100 define `REAL_OPPORTUNITIES_BASE` (3 hardcoded scholarships: Toronto, TUM, NUS).
   - Lines 364-540 loop over `REAL_OPPORTUNITIES_BASE` directly during live execution in `execute_discovery_and_audit`.
2. **Search Grounding Output Discarded**:
   - Lines 339-361 execute `gemini_service.search_grounded_discovery`, extract URLs, log `CANDIDATE_FOUND`, but then **discard all search results**. Instead of extracting criteria from discovered URLs, it falls back to hardcoded `REAL_OPPORTUNITIES_BASE`.
3. **Silent Fallback on Missing `GEMINI_API_KEY`**:
   - Line 326: `if gemini_service.is_available:` simply skips search discovery if the API key is missing and silently populates the state using `REAL_OPPORTUNITIES_BASE`. This violates requirement F5.

### 1.4 Test Suite Baseline
- `pytest` executes 21 tests successfully because `test_graph.py` passed via the silent fallback to `REAL_OPPORTUNITIES_BASE`.
- When `REAL_OPPORTUNITIES_BASE` is removed from `research_eligibility.py`, tests running without `GEMINI_API_KEY` will fail unless properly mocked using fixtures from `backend/tests/fixtures/opportunities.py`.

---

## 2. Logic Chain

1. **Enable URL Context Tool in `GenerateContentConfig` (F3)**:
   - Setting `tools=[types.Tool(url_context=types.UrlContext())]` instructs the Gemini model to fetch and read the external webpages referenced in the prompt.
   - For `analyze_url_and_extract_criteria`, `response_mime_type="application/json"` allows structured output of extracted criteria.
2. **Inspect and Verify `UrlRetrievalStatus` (F4)**:
   - The response candidate's `url_context_metadata` must be inspected.
   - For every entry in `candidate.url_context_metadata.url_metadata`, check:
     - `entry.url_retrieval_status == types.UrlRetrievalStatus.URL_RETRIEVAL_STATUS_SUCCESS`
   - If any URL returns `URL_RETRIEVAL_STATUS_ERROR`, `URL_RETRIEVAL_STATUS_PAYWALL`, or `URL_RETRIEVAL_STATUS_UNSAFE`:
     - Classify evidence as `"SECONDARY"` or `"UNVERIFIED"`.
     - Explicitly classify missing/unretrievable criteria as `"UNRESOLVED"` with a factual reason (e.g., `"Source page retrieval failed with status URL_RETRIEVAL_STATUS_PAYWALL"`).
     - NEVER synthesize, hallucinate, or fabricate quotes.
3. **Connect Search Grounding to URL Context Extraction (F2, F3)**:
   - `search_grounded_discovery` queries Google Search Grounding with profile parameters (target degree, field, country, requirements).
   - `search_grounded_discovery` extracts discovered candidate URLs, titles, and snippets from both `grounding_chunks` and structured model output.
   - `research_eligibility.py` validates URLs for safety (`is_safe_url`), normalizes them (`normalize_url`), deduplicates them (`seen_canonical_urls`), and passes each candidate URL batch to `gemini_service.analyze_url_and_extract_criteria`.
   - The resulting criteria, verbatim excerpts, and retrieval statuses are mapped directly to `Opportunity` and `EvidenceRecord` models.
4. **Enforce Honest Quotas & Eliminate Hardcoded Opportunities (F1, F5)**:
   - Move `REAL_OPPORTUNITIES_BASE` to `backend/tests/fixtures/opportunities.py`.
   - Remove `REAL_OPPORTUNITIES_BASE` completely from `backend/app/agents/research_eligibility.py`.
   - If `not gemini_service.is_available` in the live pipeline, raise an explicit `RuntimeError` (`"GEMINI_API_KEY is not configured. Live research pipeline requires a valid API key."`).
   - In unit/integration tests (`test_graph.py`), mock `gemini_service` to return fixture-backed responses to keep tests deterministic and offline.

---

## 3. Caveats

1. **Google Search Grounding & `response_mime_type` Interaction**:
   - Google Gemini API documentation notes that setting `response_mime_type="application/json"` together with `google_search` grounding can suppress or conflict with search metadata.
   - Therefore, in `search_grounded_discovery`, do NOT set `response_mime_type="application/json"` in `GenerateContentConfig`. Instead, request JSON in the prompt and parse `response.text` with a markdown code fence extractor, while extracting grounding URLs directly from `grounding_metadata.grounding_chunks`.
   - In `analyze_url_and_extract_criteria` (which uses `url_context`, not `google_search`), `response_mime_type="application/json"` is supported.
2. **URL Context Per-Request Limit**:
   - The URL Context tool accepts up to 20 URLs per request. ScholarSwarm's `settings.MAX_URLS_PER_REQUEST` is set to 10, which is well within the 20-URL threshold.
3. **Async Concurrency**:
   - Calls to `self._client.models.generate_content` are blocking I/O; they must remain wrapped in `asyncio.to_thread` to prevent stalling the FastAPI event loop.

---

## 4. Conclusion & Implementation Specifications for Worker

### 4.1 Implementation for `backend/app/services/gemini_service.py`

#### Updated `search_grounded_discovery`:
```python
    async def search_grounded_discovery(self, query: str, context_prompt: str) -> Dict[str, Any]:
        """
        Executes a Google Search grounded query using Gemini 2.5 Flash.
        Captures discovered URLs, grounding citations, and structured candidate opportunities.
        """
        if not self.is_available:
            return {
                "success": False,
                "error": "GEMINI_API_KEY is not configured.",
                "candidates": [],
                "sources": [],
                "search_queries": []
            }
        
        prompt = f"""You are an elite academic scholarship researcher.
Search query: {query}

Context:
{context_prompt}

TASK:
Search the live internet for official university degree programs and scholarships matching this query.
Return your response as structured information describing genuine opportunities found.

Format your response as a JSON array enclosed in ```json ... ``` code blocks:
```json
[
  {
    "program_name": "Exact Program Title",
    "university": "University or Institution Name",
    "country": "Country",
    "canonical_url": "https://official.university.edu/program-page",
    "degree_level": "Master's or PhD",
    "field": "Academic Field",
    "funding_snippet": "Summary of published funding or scholarship",
    "requirements_snippet": "Summary of published requirements",
    "deadline_snippet": "Published application deadline or Unknown"
  }
]
```
Ensure all URLs are real, unshortened links found in search results.
"""

        try:
            config = types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                temperature=0.2,
            )
            
            response = await asyncio.to_thread(
                self._client.models.generate_content,
                model=self.model,
                contents=prompt,
                config=config
            )
            
            citations = []
            search_queries = []
            sources = []
            
            if response.candidates and len(response.candidates) > 0:
                candidate = response.candidates[0]
                grounding_metadata = getattr(candidate, "grounding_metadata", None)
                if grounding_metadata:
                    chunks = getattr(grounding_metadata, "grounding_chunks", []) or []
                    for chunk in chunks:
                        web = getattr(chunk, "web", None)
                        if web:
                            sources.append({
                                "title": getattr(web, "title", "Official Source"),
                                "url": getattr(web, "uri", "")
                            })
                    web_queries = getattr(grounding_metadata, "web_search_queries", []) or []
                    search_queries = list(web_queries)

            # Parse structured candidates from response text
            candidates = []
            raw_text = response.text or ""
            import re
            json_match = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", raw_text, re.DOTALL)
            candidate_json = json_match.group(1) if json_match else None
            if not candidate_json:
                array_match = re.search(r"(\[\s*\{.*?\}\s*\])", raw_text, re.DOTALL)
                candidate_json = array_match.group(1) if array_match else None
            
            if candidate_json:
                try:
                    candidates = json.loads(candidate_json)
                except Exception:
                    candidates = []

            return {
                "success": True,
                "text": raw_text,
                "candidates": candidates,
                "sources": sources,
                "search_queries": search_queries,
                "model_used": self.model
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Gemini Search Grounding error: {str(e)}",
                "candidates": [],
                "sources": [],
                "search_queries": [],
                "model_used": self.model
            }
```

#### Updated `analyze_url_and_extract_criteria`:
```python
    async def analyze_url_and_extract_criteria(
        self,
        urls: List[str],
        program_name: str,
        university: str,
        student_profile_summary: str
    ) -> Dict[str, Any]:
        """
        Examines official webpage URLs using Gemini URL Context tool to extract
        requirements, funding, and verify eligibility against published evidence.
        """
        if not self.is_available:
            return {
                "success": False,
                "error": "GEMINI_API_KEY is not configured.",
                "data": None,
                "retrieval_metadata": [],
                "is_retrieval_successful": False
            }
            
        urls_formatted = "\n".join([f"- {u}" for u in urls[:settings.MAX_URLS_PER_REQUEST]])
        prompt = f"""You are the Research & Eligibility Auditor for university admissions and scholarships.
Analyze the following official webpage URLs using your URL Context retrieval tool:
Program: {program_name} at {university}

Official URLs to read:
{urls_formatted}

Student Profile:
{student_profile_summary}

TASK:
Read and examine the exact requirements published on these pages.
Extract:
1. Exact academic grade requirement (minimum CGPA, percentage, first-class honours).
2. Language proficiency requirements (IELTS/TOEFL minimum score).
3. Degree prerequisites and academic qualifications.
4. Specific scholarship & funding coverage (Tuition waiver, monthly stipend, research assistantship, or none).
5. Exact published application deadline for upcoming intakes.
6. Compare student profile against each requirement and determine criterion status:
   'MEETS', 'DOES_NOT_MEET', or 'UNRESOLVED' (if unstated or equivalency guidance is ambiguous).
7. Extract VERBATIM evidence excerpts directly from retrieved page content. Do NOT synthesize or fabricate quotes. If a requirement is not clearly stated on the retrieved page, mark status as 'UNRESOLVED'.

Return JSON in this format:
{{
  "admission_requirements": [
    {{
      "criterion_name": "Academic CGPA",
      "stated_requirement": "...",
      "student_value": "...",
      "status": "MEETS | DOES_NOT_MEET | UNRESOLVED",
      "evidence_excerpt": "verbatim quote from retrieved page",
      "source_url": "..."
    }}
  ],
  "scholarship_requirements": [
    {{
      "criterion_name": "Funding Eligibility",
      "stated_requirement": "...",
      "student_value": "...",
      "status": "MEETS | DOES_NOT_MEET | UNRESOLVED",
      "evidence_excerpt": "verbatim quote from retrieved page",
      "source_url": "..."
    }}
  ],
  "funding_details": {{
    "funding_type": "Fully Funded | Partial | Stipend | None",
    "coverage_description": "...",
    "amount": null,
    "currency": "CAD | EUR | SGD | USD",
    "tuition_covered": true,
    "stipend_amount": "..."
  }},
  "deadline": "YYYY-MM-DD or descriptive text",
  "deadline_type": "Fixed | Rolling | Priority | Unknown",
  "deadline_verified": true,
  "overall_eligibility_status": "MEETS_STATED_CRITERIA | POTENTIAL_MATCH | DOES_NOT_MEET | INSUFFICIENT_EVIDENCE",
  "eligibility_reasons": ["..."],
  "actionable_gaps": ["..."]
}}
"""
        try:
            # Explicitly enable types.Tool(url_context=types.UrlContext())
            config = types.GenerateContentConfig(
                tools=[types.Tool(url_context=types.UrlContext())],
                temperature=0.1,
                response_mime_type="application/json"
            )
            response = await asyncio.to_thread(
                self._client.models.generate_content,
                model=self.model,
                contents=prompt,
                config=config
            )
            
            # Inspect candidate.url_context_metadata and url_retrieval_status
            retrieval_metadata = []
            has_retrieval_success = False
            
            if response.candidates and len(response.candidates) > 0:
                candidate = response.candidates[0]
                url_context_meta = getattr(candidate, "url_context_metadata", None)
                if url_context_meta:
                    metadata_entries = getattr(url_context_meta, "url_metadata", []) or []
                    for entry in metadata_entries:
                        retrieved_url = getattr(entry, "retrieved_url", "")
                        status_enum = getattr(entry, "url_retrieval_status", None)
                        status_str = status_enum.value if hasattr(status_enum, "value") else str(status_enum or "URL_RETRIEVAL_STATUS_UNSPECIFIED")
                        is_success = (
                            status_str == "URL_RETRIEVAL_STATUS_SUCCESS"
                            or status_enum == types.UrlRetrievalStatus.URL_RETRIEVAL_STATUS_SUCCESS
                        )
                        if is_success:
                            has_retrieval_success = True
                            
                        retrieval_metadata.append({
                            "retrieved_url": retrieved_url,
                            "url_retrieval_status": status_str,
                            "is_success": is_success
                        })
            
            # Parse structured JSON safely
            raw_text = (response.text or "").strip()
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:]
            elif raw_text.startswith("```"):
                raw_text = raw_text[3:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]
            raw_text = raw_text.strip()
            
            data = json.loads(raw_text)
            
            return {
                "success": True,
                "data": data,
                "retrieval_metadata": retrieval_metadata,
                "is_retrieval_successful": has_retrieval_success,
                "model_used": self.model
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"URL analysis error: {str(e)}",
                "data": None,
                "retrieval_metadata": [],
                "is_retrieval_successful": False
            }
```

---

### 4.2 Implementation for `backend/tests/fixtures/opportunities.py`
Create new file `backend/tests/fixtures/opportunities.py` isolating the fixtures:
```python
"""
Isolated Opportunity Fixtures for Test Suites & Harness Evaluation.
These fixtures must NEVER be imported into live research pipeline code paths.
"""

REAL_OPPORTUNITIES_BASE = [
    {
        "title": "Vector Institute Scholarship in Artificial Intelligence (VSAI) & Master's",
        "program_name": "MSc Applied Computing / Computer Science with Vector Institute AI Concentration",
        "university": "University of Toronto",
        "country": "Canada",
        "degree_level": "Master's",
        "field": "Computer Science / Artificial Intelligence",
        "intake": "Fall 2026",
        "canonical_url": "https://web.cs.toronto.edu/graduate/mscac",
        "official_source_urls": [
            "https://web.cs.toronto.edu/graduate/mscac",
            "https://vectorinstitute.ai/scholarship/"
        ],
        "funding": {
            "funding_type": "Fully Funded",
            "coverage_description": "$17,500 CAD scholarship plus 8-month paid applied research internship ($35,000+ CAD)",
            "amount": 52500.0,
            "currency": "CAD",
            "tuition_covered": True
        },
        "deadline": "2025-12-01",
        "deadline_type": "Fixed",
        "deadline_verified": True,
        "admission_requirements": [
            {"criterion_type": "ACADEMIC_GRADE", "is_mandatory": True, "requirement_text": "B+ average in final 2 years of undergraduate study (equivalent to ~8.0/10.0 CGPA from recognized Indian institutions).", "official_equivalency_note": "PTU/NIT first class with distinction satisfied by 8.2 CGPA."},
            {"criterion_type": "LANGUAGE_TEST", "is_mandatory": True, "requirement_text": "IELTS 7.0 minimum with at least 6.5 in each band, or TOEFL iBT 93.", "official_equivalency_note": "Score required before unconditional offer."},
            {"criterion_type": "PREREQUISITE", "is_mandatory": True, "requirement_text": "Substantial background in Computer Science including data structures, algorithms, and linear algebra.", "official_equivalency_note": "Satisfied by B.Tech CS degree."}
        ]
    },
    {
        "title": "DAAD Helmut-Schmidt-Programme & Master of Science in Informatics",
        "program_name": "M.Sc. in Informatics (Artificial Intelligence & Software Engineering)",
        "university": "Technical University of Munich (TUM)",
        "country": "Germany",
        "degree_level": "Master's",
        "field": "Computer Science / Informatics",
        "intake": "Winter 2026 / Fall 2026",
        "canonical_url": "https://www.tum.de/en/studies/degree-programs/detail/informatics-master-of-science-msc",
        "official_source_urls": [
            "https://www.tum.de/en/studies/degree-programs/detail/informatics-master-of-science-msc",
            "https://www.daad.de/en/study-and-research-in-germany/scholarships/"
        ],
        "funding": {
            "funding_type": "Fully Funded",
            "coverage_description": "DAAD monthly stipend of €934, travel allowance, health insurance, zero tuition fee at TUM",
            "amount": 11200.0,
            "currency": "EUR",
            "tuition_covered": True
        },
        "deadline": "2026-05-31",
        "deadline_type": "Fixed",
        "deadline_verified": True,
        "admission_requirements": [
            {"criterion_type": "ACADEMIC_GRADE", "is_mandatory": True, "requirement_text": "Bachelor's degree in Computer Science with German grade equivalent 2.0 or better (approx. 7.5+ CGPA on 10-point scale).", "official_equivalency_note": "TUM Curricular Analysis required for Indian engineering degrees."},
            {"criterion_type": "LANGUAGE_TEST", "is_mandatory": True, "requirement_text": "English language proficiency certificate (IELTS min 6.5 or TOEFL min 88) for English-taught track.", "official_equivalency_note": "Planned IELTS meets criteria once completed."}
        ]
    },
    {
        "title": "NUS Research Scholarship & Master of Computing (AI Specialization)",
        "program_name": "Master of Computing (Artificial Intelligence Specialisation) / Research",
        "university": "National University of Singapore (NUS)",
        "country": "Singapore",
        "degree_level": "Master's",
        "field": "Computer Science / Artificial Intelligence",
        "intake": "August 2026",
        "canonical_url": "https://www.comp.nus.edu.sg/programmes/pg/mcomp-ai/",
        "official_source_urls": [
            "https://www.comp.nus.edu.sg/programmes/pg/mcomp-ai/",
            "https://nusgs.nus.edu.sg/scholarships-award/"
        ],
        "funding": {
            "funding_type": "Fully Funded",
            "coverage_description": "Full tuition fee subsidy plus monthly research stipend of S$2,200 - S$2,800",
            "amount": 33600.0,
            "currency": "SGD",
            "tuition_covered": True
        },
        "deadline": "2026-02-01",
        "deadline_type": "Fixed",
        "deadline_verified": True,
        "admission_requirements": [
            {"criterion_type": "ACADEMIC_GRADE", "is_mandatory": True, "requirement_text": "Good honours degree (or 4-year bachelor's degree with minimum 80% / 8.0 CGPA) in Computing or related field.", "official_equivalency_note": "8.2 CGPA satisfies NUS minimum threshold."},
            {"criterion_type": "LANGUAGE_TEST", "is_mandatory": True, "requirement_text": "IELTS 6.5 or TOEFL 90 minimum for applicants from non-English medium institutions.", "official_equivalency_note": "Medium of instruction certificate or IELTS score."}
        ]
    }
]
```

---

### 4.3 Integration in `backend/app/agents/research_eligibility.py`
In `execute_discovery_and_audit`:
1. Check `gemini_service.is_available`:
   ```python
   if not gemini_service.is_available:
       raise RuntimeError("GEMINI_API_KEY is not configured. Live research pipeline requires a valid API key.")
   ```
2. Loop over countries and execute discovery:
   ```python
   discovered_candidates: List[Dict[str, Any]] = []
   seen_canonical_urls = set()

   for country in profile.target_countries:
       query = f"official site:edu OR site:gov OR site:ac scholarship fully funded {profile.target_degree} in {profile.target_field} in {country} admission requirements CGPA deadline"
       
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
           context_prompt=f"Student has CGPA {profile.cgpa}/{profile.grading_scale} from {profile.institution}, degree {profile.current_degree}, seeking {profile.target_degree}."
       )
       
       if discovery_res.get("success"):
           for cand in discovery_res.get("candidates", []):
               raw_url = cand.get("canonical_url")
               if not raw_url or not is_safe_url(raw_url):
                   continue
               norm_url = normalize_url(raw_url)
               if norm_url in seen_canonical_urls:
                   continue
               seen_canonical_urls.add(norm_url)
               cand["canonical_url"] = norm_url
               cand["country"] = cand.get("country") or country
               discovered_candidates.append(cand)
   ```
3. For each discovered candidate, execute URL extraction:
   ```python
   opportunities: List[Opportunity] = []
   
   for cand in discovered_candidates:
       opp_id = str(uuid.uuid4())
       target_url = cand["canonical_url"]
       
       extract_res = await gemini_service.analyze_url_and_extract_criteria(
           urls=[target_url],
           program_name=cand.get("program_name", "Academic Program"),
           university=cand.get("university", "Target University"),
           student_profile_summary=f"CGPA {profile.cgpa}/{profile.grading_scale}, degree {profile.current_degree}, citizenship {profile.citizenship}"
       )
       
       now_iso = datetime.utcnow().isoformat()
       retrieval_timestamps = {target_url: now_iso}
       
       is_success = extract_res.get("is_retrieval_successful", False)
       retrieval_meta = extract_res.get("retrieval_metadata", [])
       primary_status = retrieval_meta[0]["url_retrieval_status"] if retrieval_meta else "URL_RETRIEVAL_STATUS_UNSPECIFIED"
       
       evidence_quality = "OFFICIAL" if is_success else "SECONDARY"
       
       extracted_data = extract_res.get("data") or {}
       # Process criteria and build EvidenceRecord instances:
       evidence_records: List[EvidenceRecord] = []
       
       # If retrieval failed (ERROR, PAYWALL, UNSAFE), criteria must be marked UNRESOLVED
       if not is_success:
           ev = EvidenceRecord(
               id=str(uuid.uuid4()),
               opportunity_id=opp_id,
               run_id=run_id,
               criterion_name="Official Webpage Verification",
               stated_requirement="Official published admission & scholarship criteria",
               student_value=f"Profile CGPA {profile.cgpa}",
               status="UNRESOLVED",
               evidence_excerpt=f"URL retrieval status: {primary_status}. Official page content could not be verified.",
               source_title=cand.get("university", "Official Source"),
               source_url=target_url,
               source_category="SECONDARY",
               uncertainty_or_conflict=f"Retrieval status: {primary_status}"
           )
           evidence_records.append(ev)
       else:
           # Build real evidence records from extracted_data["admission_requirements"]
           for req in extracted_data.get("admission_requirements", []):
               evidence_records.append(EvidenceRecord(
                   id=str(uuid.uuid4()),
                   opportunity_id=opp_id,
                   run_id=run_id,
                   criterion_name=req.get("criterion_name", "Admission Requirement"),
                   stated_requirement=req.get("stated_requirement", "Published requirement"),
                   student_value=req.get("student_value", f"Student CGPA {profile.cgpa}"),
                   status=req.get("status", "UNRESOLVED"),
                   evidence_excerpt=req.get("evidence_excerpt", "Verbatim excerpt"),
                   source_title=f"{cand.get('university')} Official Portal",
                   source_url=target_url,
                   source_category="OFFICIAL"
               ))
       
       # Build Opportunity
       opp = Opportunity(
           id=opp_id,
           run_id=run_id,
           canonical_url=target_url,
           title=f"{cand.get('program_name')} at {cand.get('university')}",
           program_name=cand.get("program_name", "Academic Program"),
           university=cand.get("university", "Target University"),
           country=cand.get("country", "Unknown"),
           degree_level=cand.get("degree_level", profile.target_degree),
           field=cand.get("field", profile.target_field),
           funding_details=FundingDetails(**(extracted_data.get("funding_details") or {"funding_type": "Unknown"})),
           deadline=extracted_data.get("deadline"),
           deadline_type=extracted_data.get("deadline_type", "Unknown"),
           deadline_verified=extracted_data.get("deadline_verified", False) and is_success,
           official_application_url=target_url,
           official_source_urls=[target_url],
           source_retrieval_timestamps=retrieval_timestamps,
           evidence_quality=evidence_quality,
           eligibility_status=extracted_data.get("overall_eligibility_status", "INSUFFICIENT_EVIDENCE") if is_success else "INSUFFICIENT_EVIDENCE",
           eligibility_reasons=extracted_data.get("eligibility_reasons", []),
           actionable_gaps=extracted_data.get("actionable_gaps", []),
           evidence_records=evidence_records
       )
       await repository.save_evidence_records(evidence_records)
       opportunities.append(opp)
       
   return opportunities
   ```

---

## 5. Verification Method

### 5.1 Verification Commands
The Worker can verify this implementation by running:
1. **Unit Verification of URL Context Tool Configuration & Metadata Parsing**:
   ```bash
   python -c "from app.services.gemini_service import GeminiService; from google.genai import types; s = GeminiService(); print('Model:', s.model)"
   ```
2. **Offline Mock Test with `pytest`**:
   Execute backend test suite ensuring clean execution:
   ```bash
   python -m pytest tests/test_graph.py -v
   ```
3. **No Hardcoded Data Check**:
   Grep `backend/app/agents/research_eligibility.py` to assert `REAL_OPPORTUNITIES_BASE` does NOT exist in live app code:
   ```bash
   python -c "with open('app/agents/research_eligibility.py') as f: content = f.read(); assert 'REAL_OPPORTUNITIES_BASE' not in content, 'Found hardcoded opportunities in live code!'"
   ```
4. **Mocked Integration Test for Retrieval Status Handling**:
   Test that simulating `URL_RETRIEVAL_STATUS_ERROR` or `URL_RETRIEVAL_STATUS_PAYWALL` marks criteria as `UNRESOLVED` and evidence as `SECONDARY`.

### 5.2 Invalidation Conditions
- If `types.Tool(url_context=types.UrlContext())` is omitted from `GenerateContentConfig`.
- If `candidate.url_context_metadata` is not inspected.
- If `REAL_OPPORTUNITIES_BASE` remains in `backend/app/agents/research_eligibility.py`.
- If missing `GEMINI_API_KEY` silently succeeds instead of raising an explicit error in the live pipeline.
