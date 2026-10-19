import os
import json
import asyncio
from typing import Dict, Any, List, Optional
from google import genai
from google.genai import types
from app.config import settings

class GeminiService:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.model = settings.GEMINI_MODEL
        self._client = None
        if self.api_key:
            self._client = genai.Client(api_key=self.api_key)

    @property
    def is_available(self) -> bool:
        return bool(self.api_key and self._client)

    async def search_grounded_discovery(self, query: str, context_prompt: str) -> Dict[str, Any]:
        """
        Executes a Google Search grounded query using Gemini 2.5 Flash.
        Captures discovered URLs, grounding citations, and text analysis.
        """
        if not self.is_available:
            return {
                "success": False,
                "error": "GEMINI_API_KEY is not configured.",
                "candidates": [],
                "citations": []
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
            
            # Execute synchronously in thread pool to avoid blocking asyncio loop
            response = await asyncio.to_thread(
                self._client.models.generate_content,
                model=self.model,
                contents=prompt,
                config=config
            )
            
            # Extract citations & search grounding metadata
            citations = []
            search_queries = []
            sources = []
            
            if response.candidates and len(response.candidates) > 0:
                candidate = response.candidates[0]
                grounding_metadata = getattr(candidate, "grounding_metadata", None)
                if grounding_metadata:
                    # Grounding chunks and web search queries
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

            return {
                "success": True,
                "text": response.text or "",
                "sources": sources,
                "search_queries": search_queries,
                "model_used": self.model
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Gemini Search Grounding error: {str(e)}",
                "sources": [],
                "model_used": self.model
            }

    async def analyze_url_and_extract_criteria(
        self,
        urls: List[str],
        program_name: str,
        university: str,
        student_profile_summary: str
    ) -> Dict[str, Any]:
        """
        Examines official webpage URLs to extract requirements, funding, and verify eligibility.
        """
        if not self.is_available:
            return {
                "success": False,
                "error": "GEMINI_API_KEY is not configured.",
                "extracted_criteria": []
            }
            
        urls_formatted = "\n".join([f"- {u}" for u in urls[:settings.MAX_URLS_PER_REQUEST]])
        prompt = f"""You are the Research & Eligibility Auditor for university admissions and scholarships.
Analyze the following official webpage URLs for:
Program: {program_name} at {university}

Official URLs:
{urls_formatted}

Student Profile:
{student_profile_summary}

TASK:
Examine the exact requirements published on these pages.
Extract:
1. Exact academic grade requirement (e.g., minimum CGPA, percentage, first-class honours).
2. Language proficiency requirements (e.g. IELTS/TOEFL minimum score).
3. Nationality/Citizenship restrictions.
4. Specific funding coverage (Tuition waiver, monthly stipend, research assistantship, or none).
5. Exact published application deadline for upcoming intakes.
6. Compare student profile against each requirement and determine criterion status:
   'MEETS', 'DOES_NOT_MEET', or 'UNRESOLVED' (if unstated or equivalency guidance is ambiguous).
7. Quote or faithfully summarize exact evidence text from the page.

Return JSON in this format:
{{
  "admission_requirements": [
    {{
      "criterion_name": "Academic CGPA",
      "stated_requirement": "...",
      "student_value": "...",
      "status": "MEETS | DOES_NOT_MEET | UNRESOLVED",
      "evidence_excerpt": "...",
      "source_url": "..."
    }}
  ],
  "funding_details": {{
    "funding_type": "Fully Funded | Partial | Stipend | None",
    "coverage_description": "...",
    "amount": null,
    "currency": "CAD | EUR | SGD | USD"
  }},
  "deadline": "YYYY-MM-DD or descriptive text",
  "deadline_type": "Fixed | Rolling | Priority | Unknown",
  "deadline_verified": true | false,
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
            data = json.loads(response.text)
            return {"success": True, "data": data}
        except Exception as e:
            return {"success": False, "error": f"URL analysis error: {str(e)}"}

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
        if not self.is_available:
            return {
                "success": False,
                "error": "GEMINI_API_KEY is not configured.",
                "approved": True,
                "issues": []
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
            return {"success": False, "error": f"Review error: {str(e)}"}

gemini_service = GeminiService()
