import os
import json
import asyncio
from typing import Dict, Any, List, Optional
from google import genai
from google.genai import types
from app.config import settings
from app.services.safe_retriever import safe_page_retriever


class GeminiConfigurationError(RuntimeError):
    """Raised when live Gemini discovery or URL extraction is requested without a valid API key."""
    def __init__(
        self,
        message: str = (
            "GEMINI_API_KEY is not configured. Live research discovery requires a valid Gemini API key. "
            "Please configure GEMINI_API_KEY in the environment or .env file."
        )
    ):
        super().__init__(message)
        self.message = message


class GeminiService:
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key if api_key is not None else settings.GEMINI_API_KEY
        self.model = model or settings.GEMINI_MODEL
        self._client = None
        self._is_quota_exhausted = False
        self._exhausted_models = set()
        self._init_client()

    def set_model(self, model_name: str) -> None:
        """Dynamically switch active Gemini model and update settings."""
        self.model = model_name
        settings.GEMINI_MODEL = model_name
        exhausted_set = getattr(self, "_exhausted_models", set())
        self._is_quota_exhausted = (model_name in exhausted_set)

    def reload_credentials(self, new_key: Optional[str] = None) -> None:
        """Reload GEMINI_API_KEY from environment/settings and re-initialize genai Client."""
        from app.config import reload_settings
        reload_settings()
        self.api_key = new_key if new_key is not None else settings.GEMINI_API_KEY
        self.model = settings.GEMINI_MODEL
        self._is_quota_exhausted = False
        self._exhausted_models.clear()
        self._init_client()

    def _init_client(self) -> None:
        if self.api_key:
            # HttpOptions timeout in google-genai expects milliseconds
            timeout_ms = int(getattr(settings, "GEMINI_TIMEOUT_SECONDS", 90) * 1000)
            http_opts = types.HttpOptions(timeout=timeout_ms)
            self._client = genai.Client(api_key=self.api_key, http_options=http_opts)
        else:
            self._client = None

    @property
    def is_available(self) -> bool:
        return bool(self.api_key and self._client)

    def ensure_available(self) -> None:
        """Validates that Gemini API key and client are configured; raises GeminiConfigurationError otherwise."""
        if not self.is_available:
            raise GeminiConfigurationError()

    async def validate_connection(self) -> Dict[str, Any]:
        """
        Validates live authentication against Google Gen AI API.
        Distinguishes authentication errors (401 UNAUTHENTICATED) from quota (429) or demand (503).
        """
        if not self.is_available:
            return {
                "authenticated": False,
                "status": "UNCONFIGURED",
                "message": "GEMINI_API_KEY is not configured.",
                "error": "KEY_MISSING"
            }
        
        try:
            response = await asyncio.to_thread(
                self._client.models.generate_content,
                model=self.model,
                contents="ping",
            )
            return {
                "authenticated": True,
                "status": "AUTHENTICATED",
                "message": "Successfully authenticated with Google Gen AI API.",
                "model": self.model,
                "response_sample": (response.text or "").strip()[:50]
            }
        except Exception as e:
            err_str = str(e)
            if "401" in err_str or "UNAUTHENTICATED" in err_str or "API key not valid" in err_str:
                return {
                    "authenticated": False,
                    "status": "UNAUTHENTICATED",
                    "message": "Google Gen AI rejected the key with 401 UNAUTHENTICATED.",
                    "error": err_str
                }
            elif "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                self._exhausted_models.add(self.model)
                self._is_quota_exhausted = True
                return {
                    "authenticated": True,
                    "status": "QUOTA_EXHAUSTED",
                    "message": "Key is authenticated, but requests exceeded current quota (429 RESOURCE_EXHAUSTED).",
                    "error": err_str
                }
            elif "503" in err_str or "UNAVAILABLE" in err_str:
                return {
                    "authenticated": True,
                    "status": "TEMPORARILY_UNAVAILABLE",
                    "message": f"Key is authenticated, but model '{self.model}' is experiencing high demand (503 UNAVAILABLE).",
                    "error": err_str
                }
            elif "404" in err_str or "not found" in err_str.lower() or "no longer available" in err_str.lower():
                return {
                    "authenticated": True,
                    "status": "MODEL_DEPRECATED_OR_NOT_FOUND",
                    "message": f"Key is authenticated, but model '{self.model}' was not found or is unavailable to this account.",
                    "error": err_str
                }
            else:
                return {
                    "authenticated": False,
                    "status": "ERROR",
                    "message": f"Unexpected error during Gemini connection check: {err_str}",
                    "error": err_str
                }

    check_connection = validate_connection

    async def search_grounded_discovery(self, query: str, context_prompt: str) -> Dict[str, Any]:
        """
        Executes search grounded query (legacy Gemini Google Search fallback).
        Captures discovered URLs, grounding citations, and text analysis.
        """
        if self._is_quota_exhausted or not self.is_available:
            return {
                "success": False,
                "error": "GEMINI_API_KEY is not configured or quota is exhausted.",
                "status": "QUOTA_EXHAUSTED" if self._is_quota_exhausted else "ERROR",
                "candidates": [],
                "sources": [],
                "citations": [],
                "search_queries": [query],
                "model_used": self.model
            }
        
        prompt = f"""You are an elite academic scholarship researcher.
Search query: {query}

Context:
{context_prompt}

TASK:
Search the live internet for official university degree programs and scholarships matching this query.
Return your response as structured information describing genuine opportunities found.
Provide:
1. Program Title
2. University / Provider Name
3. Country
4. Official URL (must be real, un-shortened link)
5. Degree level & academic field
6. Funding amount or scholarship description
7. Admission/Scholarship requirements
8. Application deadline if found
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
                "citations": sources,
                "search_queries": search_queries,
                "model_used": self.model
            }
        except Exception as e:
            err_str = str(e)
            is_quota = "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "quota" in err_str.lower()
            if is_quota:
                getattr(self, "_exhausted_models", set()).add(self.model)
                self._is_quota_exhausted = True
            return {
                "success": False,
                "error": f"Gemini Search Grounding error: {err_str}",
                "status": "QUOTA_EXHAUSTED" if is_quota else "ERROR",
                "candidates": [],
                "sources": [],
                "citations": [],
                "search_queries": [query],
                "model_used": self.model
            }

    async def analyze_url_and_extract_criteria(
        self,
        urls: List[str],
        program_name: str,
        university: str,
        student_profile_summary: str,
        page_text: Optional[str] = None,
        retrieval_status: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyzes official university webpage criteria.
        Uses safe_page_retriever to retrieve official page content with SSRF protections,
        and passes the extracted text to Gemini for criteria analysis instead of requiring Gemini URL Context.
        Also inspects candidate url_context_metadata if present (for mock/backward compatibility).
        """
        if self._is_quota_exhausted or not self.is_available:
            err_msg = "QUOTA_EXHAUSTED" if self._is_quota_exhausted else "GEMINI_API_KEY is not configured."
            return {
                "success": False,
                "error": err_msg,
                "status": "QUOTA_EXHAUSTED" if self._is_quota_exhausted else "NOT_CONFIGURED",
                "data": None,
                "retrieval_metadata": [],
                "url_retrieval_statuses": {u: "URL_RETRIEVAL_STATUS_ERROR" for u in urls},
                "is_retrieval_successful": False,
                "retrieval_status": "URL_RETRIEVAL_STATUS_ERROR",
                "evidence_quality": "UNVERIFIED"
            }

        # Safe page retrieval via SafePageRetriever (Requirement 3)
        retrieved_content = page_text or ""
        safe_primary_status = retrieval_status or "URL_RETRIEVAL_STATUS_SUCCESS"
        safe_is_success = True if page_text else (False if not urls else True)

        if page_text is None and urls:
            try:
                ret_result = await safe_page_retriever.retrieve_page(urls[0])
                safe_primary_status = ret_result.get("status", "URL_RETRIEVAL_STATUS_ERROR")
                safe_is_success = ret_result.get("success", False)
                retrieved_content = ret_result.get("text", "")
            except Exception:
                safe_primary_status = "URL_RETRIEVAL_STATUS_ERROR"
                safe_is_success = False

        # If URLs were provided and safe page retrieval failed, return unverified result immediately
        # without consuming Gemini API quota or making redundant model calls
        if urls and not safe_is_success and not retrieved_content.strip():
            return {
                "success": True,
                "data": None,
                "retrieval_metadata": [
                    {
                        "retrieved_url": u,
                        "url_retrieval_status": safe_primary_status,
                        "is_success": False
                    }
                    for u in urls
                ],
                "url_retrieval_statuses": {u: safe_primary_status for u in urls},
                "is_retrieval_successful": False,
                "retrieval_status": safe_primary_status,
                "evidence_quality": "UNVERIFIED",
                "model_used": self.model
            }

        urls_formatted = "\n".join([f"- {u}" for u in urls[:settings.MAX_URLS_PER_REQUEST]]) if urls else "None provided"
        content_section = f"\n\nAUTHENTIC OFFICIAL PAGE CONTENT:\n\"\"\"\n{retrieved_content}\n\"\"\"\n" if retrieved_content else ""

        prompt = f"""You are the Research & Eligibility Auditor for university admissions and scholarships.
Analyze the following official webpage text and details:
Program: {program_name} at {university}

Official URLs:
{urls_formatted}
{content_section}
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
            config = types.GenerateContentConfig(
                temperature=0.1,
                response_mime_type="application/json"
            )
            response = await asyncio.to_thread(
                self._client.models.generate_content,
                model=self.model,
                contents=prompt,
                config=config
            )

            # Inspect candidate.url_context_metadata if present (from mock or tool)
            retrieval_metadata = []
            retrieval_statuses: Dict[str, str] = {}
            has_retrieval_success = False
            primary_status = "URL_RETRIEVAL_STATUS_UNSPECIFIED"

            candidate = response.candidates[0] if (response.candidates and len(response.candidates) > 0) else None
            url_context_meta = getattr(candidate, "url_context_metadata", None) if candidate else None

            if url_context_meta:
                metadata_entries = getattr(url_context_meta, "url_metadata", []) or []
                for entry in metadata_entries:
                    retrieved_url = getattr(entry, "retrieved_url", "")
                    status_enum = getattr(entry, "url_retrieval_status", None)
                    status_str = status_enum.name if hasattr(status_enum, "name") else (
                        status_enum.value if hasattr(status_enum, "value") else str(status_enum or "URL_RETRIEVAL_STATUS_UNSPECIFIED")
                    )
                    is_success = (
                        status_str == "URL_RETRIEVAL_STATUS_SUCCESS"
                        or status_enum == types.UrlRetrievalStatus.URL_RETRIEVAL_STATUS_SUCCESS
                    )
                    if is_success:
                        has_retrieval_success = True
                    if primary_status == "URL_RETRIEVAL_STATUS_UNSPECIFIED":
                        primary_status = status_str

                    retrieval_metadata.append({
                        "retrieved_url": retrieved_url,
                        "url_retrieval_status": status_str,
                        "is_success": is_success
                    })
                    if retrieved_url:
                        retrieval_statuses[retrieved_url] = status_str
            else:
                # Use SafePageRetriever status when url_context_metadata is not populated
                if not urls:
                    primary_status = "URL_RETRIEVAL_STATUS_UNSPECIFIED"
                    has_retrieval_success = False
                else:
                    primary_status = safe_primary_status
                    has_retrieval_success = safe_is_success
                    for u in urls:
                        retrieval_statuses[u] = primary_status
                        retrieval_metadata.append({
                            "retrieved_url": u,
                            "url_retrieval_status": primary_status,
                            "is_success": has_retrieval_success
                        })

            evidence_quality = "OFFICIAL" if has_retrieval_success else "UNVERIFIED"

            data = None
            if has_retrieval_success:
                raw_text = (response.text or "").strip()
                if raw_text.startswith("```json"):
                    raw_text = raw_text[7:]
                elif raw_text.startswith("```"):
                    raw_text = raw_text[3:]
                if raw_text.endswith("```"):
                    raw_text = raw_text[:-3]
                raw_text = raw_text.strip()
                try:
                    data = json.loads(raw_text)
                except Exception as exc:
                    return {
                        "success": False,
                        "error": f"URL analysis error: Failed to parse model JSON: {str(exc)}",
                        "status": "ERROR",
                        "data": None,
                        "retrieval_metadata": retrieval_metadata,
                        "url_retrieval_statuses": {u: "URL_RETRIEVAL_STATUS_ERROR" for u in urls},
                        "is_retrieval_successful": False,
                        "retrieval_status": "URL_RETRIEVAL_STATUS_ERROR",
                        "evidence_quality": "UNVERIFIED",
                        "model_used": self.model
                    }

            return {
                "success": True,
                "data": data,
                "retrieval_metadata": retrieval_metadata,
                "url_retrieval_statuses": retrieval_statuses,
                "is_retrieval_successful": has_retrieval_success,
                "retrieval_status": primary_status,
                "evidence_quality": evidence_quality,
                "model_used": self.model
            }
        except Exception as e:
            err_str = str(e)
            is_quota = "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "quota" in err_str.lower()
            if is_quota:
                getattr(self, "_exhausted_models", set()).add(self.model)
                self._is_quota_exhausted = True
            return {
                "success": False,
                "error": f"URL analysis error: {err_str}",
                "status": "QUOTA_EXHAUSTED" if is_quota else "ERROR",
                "data": None,
                "retrieval_metadata": [],
                "url_retrieval_statuses": {u: "URL_RETRIEVAL_STATUS_ERROR" for u in urls},
                "is_retrieval_successful": False,
                "retrieval_status": "URL_RETRIEVAL_STATUS_ERROR",
                "evidence_quality": "UNVERIFIED"
            }

    async def generate_sop_draft(
        self,
        student_profile_dict: Dict[str, Any],
        opportunity_dict: Dict[str, Any],
        user_notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generates an editable Statement of Purpose (SOP) connecting verified student background
        to the specific program and scholarship focus without fabricating any claims.
        """
        if not self.is_available:
            return {
                "success": False,
                "error": "GEMINI_API_KEY is not configured.",
                "sop_content": "",
                "unconfirmed_claims": []
            }
            
        prompt = f"""You are the Application Coach Agent for ScholarSwarm.
Write a personalized, coherent Statement of Purpose (SOP) for the following student and target opportunity.

STUDENT PROFILE (ONLY use facts established here):
Name: {student_profile_dict.get('full_name')}
Undergraduate Degree: {student_profile_dict.get('current_degree')} from {student_profile_dict.get('institution')} (CGPA: {student_profile_dict.get('cgpa')}/10.0)
Skills: {', '.join(student_profile_dict.get('skills', []))}
Projects: {json.dumps(student_profile_dict.get('projects', []), default=str)}
Career Goals: {student_profile_dict.get('career_goals')}
Additional Student Notes: {user_notes or 'None'}

TARGET OPPORTUNITY:
Program: {opportunity_dict.get('program_name')}
University: {opportunity_dict.get('university')}
Country: {opportunity_dict.get('country')}
Funding: {json.dumps(opportunity_dict.get('funding_details', {}), default=str)}

RULES:
1. NEVER invent internships, publications, awards, or personal hardships not present in the profile.
2. Emphasize actual AI/ML software engineering and projects from the student's profile.
3. Explicitly list any statements or personal motivations that the student must verify/confirm before submission.

Return JSON in this format:
{{
  "title": "Statement of Purpose - [Program Name] - [Student Name]",
  "sop_content": "Full text of the SOP organized into clear paragraphs...",
  "unconfirmed_claims": ["List of claims or personal points student needs to confirm"],
  "word_count": 650
}}
"""
        try:
            config = types.GenerateContentConfig(
                temperature=0.3,
                response_mime_type="application/json"
            )
            response = await asyncio.to_thread(
                self._client.models.generate_content,
                model=self.model,
                contents=prompt,
                config=config
            )
            data = json.loads(response.text)
            return {"success": True, "data": data}
        except Exception as e:
            return {"success": False, "error": f"SOP Generation error: {str(e)}"}

    async def review_evidence_and_claims(
        self,
        opportunity_data: Dict[str, Any],
        student_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Quality Reviewer Agent evaluation: challenges claims, detects unsupported statements,
        and ensures evidence satisfies criteria.
        """
        if self._is_quota_exhausted or not self.is_available:
            err_code = "QUOTA_EXHAUSTED" if self._is_quota_exhausted else "GEMINI_NOT_AVAILABLE"
            return {
                "success": False,
                "error": err_code,
                "approved": False,
                "data": {
                    "approved": False,
                    "confidence_rating": "LOW",
                    "issues_detected": [
                        {
                            "criterion": "Quality Review Audit",
                            "issue": f"Quality review unresolved ({err_code}).",
                            "recommendation": "Review manually or retry when Gemini API quota is refreshed."
                        }
                    ],
                    "reviewer_notes": f"Quality review unreviewed / unresolved ({err_code})."
                }
            }
            
        prompt = f"""You are the Quality Reviewer Agent for ScholarSwarm.
Review the following research findings for accuracy and evidence grounding.

Target Opportunity:
{json.dumps(opportunity_data, default=str)}

Student Profile:
{json.dumps(student_data, default=str)}

TASK:
1. Check whether official sources support the claimed funding amount and eligibility status.
2. Identify ambiguous deadlines or unverified claims.
3. If any claim lacks evidence or contradicts official university policy, flag it with specific correction instructions.

Return JSON in this format:
{{
  "approved": true | false,
  "confidence_rating": "HIGH | MEDIUM | LOW",
  "issues_detected": [
    {{
      "criterion": "...",
      "issue": "...",
      "recommendation": "..."
    }}
  ],
  "reviewer_notes": "Summary of audit..."
}}
"""
        try:
            config = types.GenerateContentConfig(
                temperature=0.1,
                response_mime_type="application/json"
            )
            response = await asyncio.to_thread(
                self._client.models.generate_content,
                model=self.model,
                contents=prompt,
                config=config
            )
            data = json.loads(response.text)
            return {"success": True, "data": data}
        except Exception as e:
            err_str = str(e)
            is_quota = "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "quota" in err_str.lower()
            if is_quota:
                getattr(self, "_exhausted_models", set()).add(self.model)
                self._is_quota_exhausted = True
                return {
                    "success": False,
                    "error": "QUOTA_EXHAUSTED",
                    "approved": False,
                    "data": {
                        "approved": False,
                        "confidence_rating": "LOW",
                        "issues_detected": [
                            {
                                "criterion": "Quality Review Audit",
                                "issue": "Quality review unresolved (QUOTA_EXHAUSTED).",
                                "recommendation": "Review manually or retry when Gemini API quota is refreshed."
                            }
                        ],
                        "reviewer_notes": "Quality review unreviewed / unresolved (QUOTA_EXHAUSTED)."
                    }
                }
            return {
                "success": False,
                "error": f"Review error: {err_str}",
                "approved": False,
                "data": None
            }

    # API naming compatibility alias
    review_opportunity_claims = review_evidence_and_claims


gemini_service = GeminiService()
