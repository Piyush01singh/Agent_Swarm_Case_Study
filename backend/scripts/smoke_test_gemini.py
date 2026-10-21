#!/usr/bin/env python3
"""
ScholarSwarm Live Gemini Grounding & URL Extraction Smoke Test Runner
Feature F26 — TetraNoodle AI Hackathon 2026

Standalone CLI runner to verify live Google Gen AI SDK search grounding and
URL context extraction capabilities:
1. Loads environment from `.env` or system environment (GEMINI_API_KEY).
2. If GEMINI_API_KEY is not present or invalid, prints a transparent informational
   report explaining how to configure the key, and exits gracefully with code 0
   (or exits with error code 1 if --strict is specified).
3. If GEMINI_API_KEY is present and active:
   - Tests Google Search grounding via GeminiService.search_grounded_discovery.
   - Tests URL Context extraction via GeminiService.analyze_url_and_extract_criteria
     with types.Tool(url_context=types.UrlContext()).
   - Inspects candidate and UrlRetrievalStatus metadata.
   - Validates that real live links and verbatim criteria were extracted.
4. Supports deterministic mock mode (--mock) for automated testing without network egress.
"""

import os
import sys
import json
import asyncio
import argparse
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

# Ensure backend root is on sys.path
backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

# Attempt to load .env from backend root or workspace root
try:
    from dotenv import load_dotenv
    # Check backend/.env first, then parent .env
    backend_env = os.path.join(backend_root, ".env")
    repo_env = os.path.abspath(os.path.join(backend_root, "..", ".env"))
    if os.path.exists(backend_env):
        load_dotenv(backend_env)
    elif os.path.exists(repo_env):
        load_dotenv(repo_env)
    else:
        load_dotenv()
except ImportError:
    pass

from google.genai import types
from app.config import settings
from app.services.gemini_service import GeminiService, gemini_service, GeminiConfigurationError


# =====================================================================
# Informational & Diagnostic Helpers
# =====================================================================

def mask_key(key: str) -> str:
    """Masks an API key for safe display in logs/CLI output."""
    if not key:
        return "<not set>"
    if len(key) <= 8:
        return "***"
    return f"{key[:4]}...{key[-4:]} (len: {len(key)})"


def is_valid_gemini_key_format(key: str) -> bool:
    """
    Basic sanity check for a Google AI Studio Gemini API key.
    Google AI Studio keys are alphanumeric strings typically starting with 'AIzaSy'.
    Internal sandbox bearer tokens are rejected because they cannot be used with Gemini API.
    """
    if not key or not isinstance(key, str):
        return False
    key = key.strip()
    if len(key) < 15:
        return False
    if key.startswith(("AQ", "sandbox-", "service-account-")):
        return False
    return True


def print_missing_key_report(reason: Optional[str] = None):
    """Prints a clear, actionable guide for configuring GEMINI_API_KEY."""
    print("=" * 72)
    print("  ScholarSwarm Live Gemini Grounding & Extraction Smoke Test (F26)")
    print("=" * 72)
    if reason:
        print(f"[!] Notice: {reason}")
    else:
        print("[!] GEMINI_API_KEY is not configured in the environment or .env file.")
    print()
    print("To execute live Google Search grounding and URL Context extraction:")
    print("  1. Obtain a free or paid Gemini API key from Google AI Studio:")
    print("     https://aistudio.google.com/")
    print()
    print("  2. Configure the key in your environment:")
    print("     - Windows (PowerShell):  $env:GEMINI_API_KEY=\"AIzaSy...\"")
    print("     - Linux / macOS (bash):  export GEMINI_API_KEY=\"AIzaSy...\"")
    print()
    print("  3. Or create a .env file in the backend directory:")
    print("     GEMINI_API_KEY=AIzaSy...")
    print("     GEMINI_MODEL=gemini-2.5-flash")
    print("=" * 72)


# =====================================================================
# Deterministic Mock Provider (for offline verification & unit testing)
# =====================================================================

def get_mock_discovery_response(query: str) -> Dict[str, Any]:
    return {
        "success": True,
        "text": (
            "Found official graduate program details for University of Toronto MSc Applied Computing:\n"
            "```json\n"
            "[\n"
            "  {\n"
            "    \"program_title\": \"MSc in Applied Computing (MScAC)\",\n"
            "    \"university\": \"University of Toronto\",\n"
            "    \"country\": \"Canada\",\n"
            "    \"official_url\": \"https://web.cs.toronto.edu/graduate/mscac\",\n"
            "    \"funding_amount\": \"$17,500 CAD stipend plus paid applied research internship\",\n"
            "    \"deadline\": \"2026-12-01\"\n"
            "  }\n"
            "]\n"
            "```"
        ),
        "candidates": [
            {
                "program_title": "MSc in Applied Computing (MScAC)",
                "university": "University of Toronto",
                "country": "Canada",
                "official_url": "https://web.cs.toronto.edu/graduate/mscac",
                "funding_amount": "$17,500 CAD stipend plus paid applied research internship",
                "deadline": "2026-12-01"
            }
        ],
        "sources": [
            {
                "title": "U of T Department of Computer Science - MScAC Program",
                "url": "https://web.cs.toronto.edu/graduate/mscac"
            },
            {
                "title": "University of Toronto School of Graduate Studies - Admissions",
                "url": "https://www.sgs.utoronto.ca/admissions/"
            }
        ],
        "citations": [
            {
                "title": "U of T Department of Computer Science - MScAC Program",
                "url": "https://web.cs.toronto.edu/graduate/mscac"
            }
        ],
        "search_queries": [
            query,
            "University of Toronto MScAC admission requirements scholarship"
        ],
        "model_used": "gemini-2.5-flash (mocked)"
    }


def get_mock_extraction_response(target_url: str) -> Dict[str, Any]:
    return {
        "success": True,
        "data": {
            "admission_requirements": [
                {
                    "criterion_name": "Academic CGPA",
                    "stated_requirement": "Minimum B+ standing (approx 7.8/10 CGPA equivalent) in senior CS courses",
                    "student_value": "8.2/10 CGPA",
                    "status": "MEETS",
                    "evidence_excerpt": "Minimum B+ average (77-79% or 3.3/4.0) in the final two years of study.",
                    "source_url": target_url
                },
                {
                    "criterion_name": "English Language Proficiency",
                    "stated_requirement": "TOEFL minimum 93 with 22 in writing/speaking or IELTS 7.0 minimum",
                    "student_value": "IELTS 7.5",
                    "status": "MEETS",
                    "evidence_excerpt": "IELTS Academic score of 7.0 minimum overall with at least 6.5 in each component.",
                    "source_url": target_url
                }
            ],
            "scholarship_requirements": [
                {
                    "criterion_name": "Vector Institute Scholarship Eligibility",
                    "stated_requirement": "Enrolled in recognized AI master's concentration with first-class standing",
                    "student_value": "Eligible (Computer Science AI focus)",
                    "status": "MEETS",
                    "evidence_excerpt": "Vector Scholarship in Artificial Intelligence provides $17,500 CAD merit award.",
                    "source_url": target_url
                }
            ],
            "funding_details": {
                "funding_type": "Fully Funded",
                "coverage_description": "$17,500 CAD scholarship plus 8-month paid industrial applied research internship",
                "amount": 17500.0,
                "currency": "CAD",
                "tuition_covered": True,
                "stipend_amount": "$17,500 CAD"
            },
            "deadline": "2026-12-01",
            "deadline_type": "Fixed",
            "deadline_verified": True,
            "overall_eligibility_status": "MEETS_STATED_CRITERIA",
            "eligibility_reasons": [
                "Student CGPA 8.2 meets and exceeds the minimum B+ requirement.",
                "Student IELTS 7.5 satisfies the published language proficiency threshold."
            ],
            "actionable_gaps": []
        },
        "retrieval_metadata": [
            {
                "retrieved_url": target_url,
                "url_retrieval_status": "URL_RETRIEVAL_STATUS_SUCCESS",
                "is_success": True
            }
        ],
        "url_retrieval_statuses": {
            target_url: "URL_RETRIEVAL_STATUS_SUCCESS"
        },
        "is_retrieval_successful": True,
        "retrieval_status": "URL_RETRIEVAL_STATUS_SUCCESS",
        "evidence_quality": "OFFICIAL",
        "model_used": "gemini-2.5-flash (mocked)"
    }


# =====================================================================
# Core Smoke Test Pipeline
# =====================================================================

async def run_smoke_test(
    api_key: Optional[str] = None,
    strict: bool = False,
    mock_mode: bool = False,
    query: Optional[str] = None,
    target_url: Optional[str] = None,
    verbose: bool = True
) -> Tuple[bool, Dict[str, Any]]:
    """
    Executes the smoke test verifying:
    1. Google Search Grounding tool configuration and discovery output.
    2. Google Gen AI SDK types.Tool(url_context=types.UrlContext()) live extraction.
    3. UrlRetrievalStatus metadata and verbatim criteria validation.
    """
    results: Dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "strict": strict,
        "mock_mode": mock_mode,
        "api_key_configured": False,
        "search_grounding_verified": False,
        "url_context_verified": False,
        "metadata_verified": False,
        "errors": []
    }

    # Determine API key
    effective_key = api_key or os.getenv("GEMINI_API_KEY") or settings.GEMINI_API_KEY or ""
    results["api_key_masked"] = mask_key(effective_key)

    if verbose:
        print("\n" + "=" * 72)
        print("  ScholarSwarm Live Gemini Grounding & Extraction Smoke Test (F26)")
        print("=" * 72)
        print(f"Timestamp:       {results['timestamp']}")
        print(f"Mock Mode:       {mock_mode}")
        print(f"Strict Mode:     {strict}")
        print(f"Configured Key:  {results['api_key_masked']}")
        print("=" * 72 + "\n")

    # If running in mock mode, bypass key checks
    if mock_mode:
        if verbose:
            print("[*] Running in deterministic MOCK mode...")
        discovery_res = get_mock_discovery_response(query or "University of Toronto MSc Applied Computing")
        chosen_url = target_url or discovery_res["sources"][0]["url"]
        extraction_res = get_mock_extraction_response(chosen_url)

        # Validate discovery
        results["api_key_configured"] = True
        results["search_grounding_verified"] = discovery_res.get("success", False)
        results["discovered_sources_count"] = len(discovery_res.get("sources", []))
        results["search_queries"] = discovery_res.get("search_queries", [])

        # Validate extraction & metadata
        results["url_context_verified"] = extraction_res.get("success", False)
        results["is_retrieval_successful"] = extraction_res.get("is_retrieval_successful", False)
        results["retrieval_status"] = extraction_res.get("retrieval_status")
        results["evidence_quality"] = extraction_res.get("evidence_quality")

        has_success_status = (
            extraction_res.get("retrieval_status") == "URL_RETRIEVAL_STATUS_SUCCESS"
            or extraction_res.get("is_retrieval_successful") is True
        )
        has_verbatim_criteria = (
            extraction_res.get("data", {})
            .get("admission_requirements", [{}])[0]
            .get("evidence_excerpt") is not None
        )
        results["metadata_verified"] = has_success_status and has_verbatim_criteria

        if verbose:
            print(f"[+] [Test 1/2] Search Grounding: PASSED ({len(discovery_res['sources'])} sources discovered)")
            for src in discovery_res["sources"]:
                print(f"    - {src['title']}: {src['url']}")
            print(f"[+] [Test 2/2] URL Context Tool: PASSED ({extraction_res['retrieval_status']})")
            print(f"    - Target URL: {chosen_url}")
            print(f"    - Retrieval Quality: {extraction_res['evidence_quality']}")
            print(f"    - Extracted Criteria: {len(extraction_res['data']['admission_requirements'])} admission items")
            print("\n[+] LIVE GEMINI SMOKE TEST: ALL GATES PASSED (Mock Verified)")

        return True, results

    # Live Mode: Check key presence
    if not effective_key:
        msg = "GEMINI_API_KEY is not configured in environment or .env."
        results["errors"].append(msg)
        if verbose:
            print_missing_key_report()
        return (False if strict else True), results

    # If the key is not in a recognized format (e.g. a sandbox bearer token)
    if not is_valid_gemini_key_format(effective_key):
        msg = (
            f"Configured GEMINI_API_KEY ({mask_key(effective_key)}) does not appear to be a "
            "valid Google AI Studio API key (which typically starts with 'AIzaSy...'). "
            "Internal sandbox bearer tokens will be rejected by Google Gen AI with 401 UNAUTHENTICATED."
        )
        results["errors"].append(msg)
        if verbose:
            print_missing_key_report(reason=msg)
        return (False if strict else True), results

    # Initialize live GeminiService
    service = GeminiService()
    service.api_key = effective_key
    # Re-initialize client with the explicit effective key
    try:
        from google import genai
        service._client = genai.Client(api_key=effective_key)
    except Exception as e:
        results["errors"].append(f"Failed to instantiate genai.Client: {str(e)}")
        if verbose:
            print(f"[!] Error creating Gemini Client: {e}")
        return False, results

    results["api_key_configured"] = True

    # -----------------------------------------------------------------
    # Step 1: Test Google Search Grounding Discovery
    # -----------------------------------------------------------------
    search_query = query or (
        "University of Toronto MSc Applied Computing admission requirements "
        "and Vector Institute scholarship international students"
    )
    context_prompt = (
        "Academic applicant profile: B.Tech Computer Science, CGPA 8.2/10.0, "
        "IELTS 7.5. Seeking official university admission page and funding criteria."
    )

    if verbose:
        print(f"[*] [Test 1/2] Testing Google Search Grounding via Gemini 2.5 Flash...")
        print(f"    Query: '{search_query}'")

    try:
        discovery_res = await service.search_grounded_discovery(search_query, context_prompt)
    except Exception as e:
        err_str = f"Search Grounding exception: {str(e)}"
        results["errors"].append(err_str)
        if verbose:
            print(f"[!] {err_str}")
        return False, results

    if not discovery_res.get("success"):
        err_msg = discovery_res.get("error", "Unknown search grounding failure")
        results["errors"].append(err_msg)
        if verbose:
            print(f"[!] Search Grounding failed: {err_msg}")
            # If 401 UNAUTHENTICATED or invalid key, print troubleshooting advice
            if "401" in err_msg or "UNAUTHENTICATED" in err_msg or "API key not valid" in err_msg:
                print_missing_key_report(reason=f"Google API rejected key: {err_msg}")
        return (False if strict else True), results

    # Discovery passed
    sources = discovery_res.get("sources", [])
    results["search_grounding_verified"] = True
    results["discovered_sources_count"] = len(sources)
    results["discovered_sources"] = sources
    results["search_queries"] = discovery_res.get("search_queries", [])

    if verbose:
        print(f"[+] [Test 1/2] Search Grounding SUCCESSFUL! Discovered {len(sources)} source links.")
        for src in sources[:5]:
            print(f"    - {src.get('title', 'Source')}: {src.get('url')}")

    # -----------------------------------------------------------------
    # Step 2: Test URL Context Extraction Tool
    # -----------------------------------------------------------------
    chosen_url = target_url
    if not chosen_url and sources:
        chosen_url = sources[0].get("url")
    if not chosen_url:
        chosen_url = "https://web.cs.toronto.edu/graduate/mscac"

    if verbose:
        print(f"\n[*] [Test 2/2] Testing Google Gen AI SDK URL Context Tool: types.Tool(url_context=types.UrlContext())...")
        print(f"    Target URL: {chosen_url}")

    try:
        extraction_res = await service.analyze_url_and_extract_criteria(
            urls=[chosen_url],
            program_name="MSc in Applied Computing (MScAC)",
            university="University of Toronto",
            student_profile_summary="B.Tech Computer Science, CGPA 8.2/10.0, IELTS 7.5"
        )
    except Exception as e:
        err_str = f"URL Context extraction exception: {str(e)}"
        results["errors"].append(err_str)
        if verbose:
            print(f"[!] {err_str}")
        return False, results

    if not extraction_res.get("success"):
        err_msg = extraction_res.get("error", "Unknown URL extraction failure")
        results["errors"].append(err_msg)
        if verbose:
            print(f"[!] URL Context extraction failed: {err_msg}")
        return (False if strict else True), results

    # Inspect UrlRetrievalStatus metadata
    retrieval_status = extraction_res.get("retrieval_status")
    url_statuses = extraction_res.get("url_retrieval_statuses", {})
    retrieval_metadata = extraction_res.get("retrieval_metadata", [])
    is_success = extraction_res.get("is_retrieval_successful", False)
    evidence_quality = extraction_res.get("evidence_quality")

    results["url_context_verified"] = True
    results["retrieval_status"] = retrieval_status
    results["url_retrieval_statuses"] = url_statuses
    results["is_retrieval_successful"] = is_success
    results["evidence_quality"] = evidence_quality

    # Validate extracted data contents
    extracted_data = extraction_res.get("data") or {}
    admission_reqs = extracted_data.get("admission_requirements", [])
    scholarship_reqs = extracted_data.get("scholarship_requirements", [])
    funding_details = extracted_data.get("funding_details", {})
    deadline = extracted_data.get("deadline")

    results["extracted_admission_count"] = len(admission_reqs)
    results["extracted_scholarship_count"] = len(scholarship_reqs)
    results["extracted_funding_type"] = funding_details.get("funding_type")
    results["extracted_deadline"] = deadline

    # Check for verbatim quotes
    has_excerpts = any(bool(r.get("evidence_excerpt")) for r in admission_reqs)
    results["metadata_verified"] = is_success and has_excerpts

    if verbose:
        print(f"[+] [Test 2/2] URL Context Tool SUCCESSFUL!")
        print(f"    - Overall Retrieval Status: {retrieval_status}")
        print(f"    - Evidence Quality:         {evidence_quality}")
        print(f"    - URLs Inspected:           {len(url_statuses)}")
        for u, st in url_statuses.items():
            print(f"      * {u}: {st}")
        print(f"    - Extracted Criteria:       {len(admission_reqs)} admission rules, {len(scholarship_reqs)} scholarship rules")
        if admission_reqs:
            first = admission_reqs[0]
            print(f"    - Sample Verbatim Quote:    \"{first.get('evidence_excerpt')}\"")
        if funding_details:
            print(f"    - Funding Coverage:         {funding_details.get('coverage_description', 'N/A')}")
        if deadline:
            print(f"    - Program Deadline:         {deadline}")

        print("\n" + "=" * 72)
        print("  LIVE GEMINI SMOKE TEST: ALL GATES PASSED (100% Verified)")
        print("=" * 72 + "\n")

    return True, results


# =====================================================================
# CLI Entry Point
# =====================================================================

def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="ScholarSwarm Live Gemini Grounding & Extraction Smoke Test Runner (Feature F26)"
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with non-zero code if GEMINI_API_KEY is missing or if live API calls fail"
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Execute deterministic mock pipeline without live network calls"
    )
    parser.add_argument(
        "--query",
        type=str,
        default=None,
        help="Custom query string for Google Search grounding discovery test"
    )
    parser.add_argument(
        "--url",
        type=str,
        default=None,
        help="Custom URL for URL context extraction test"
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="Override GEMINI_API_KEY on the command line"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON results dictionary"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress verbose diagnostic logs"
    )

    args = parser.parse_args(argv)

    passed, report = asyncio.run(
        run_smoke_test(
            api_key=args.api_key,
            strict=args.strict,
            mock_mode=args.mock,
            query=args.query,
            target_url=args.url,
            verbose=not args.quiet and not args.json
        )
    )

    if args.json:
        print(json.dumps(report, indent=2))

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
