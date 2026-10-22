"""
Unit and Integration Tests for Tavily Search API, Safe Page Retriever,
and Gemini Criteria Analysis without URL Context tool.
Covers:
- TAVILY_API_KEY configuration and TavilyConfigurationError
- Query caching and retry backoff
- SSRF protections and HTTP status mapping (SUCCESS, PAYWALL, UNSAFE, ERROR)
- Safe page text injection into Gemini analysis prompt
- Strict zero-dummy fallback on 0 candidates or retrieval failure
"""

import pytest
import json
from unittest.mock import MagicMock, AsyncMock, patch
import httpx

from app.services.tavily_service import TavilyService, TavilyConfigurationError
from app.services.safe_retriever import SafePageRetriever
from app.services.gemini_service import GeminiService
from app.agents.research_eligibility import ResearchEligibilityAgent
from app.models.profile import StudentProfile
from app.db.repository import repository


@pytest.fixture
def mock_student_profile() -> StudentProfile:
    return StudentProfile(
        full_name="Priya Patel",
        current_degree="B.Tech Computer Science",
        institution="IIT Delhi",
        cgpa=8.9,
        grading_scale="10.0",
        target_degree="Master's",
        target_field="Artificial Intelligence",
        target_countries=["Canada", "Germany"],
        language_tests={"test": "IELTS", "score": "7.5", "status": "completed"}
    )


# ==============================================================================
# 1. Tavily Service Configuration & Search
# ==============================================================================

def test_tavily_missing_key_ensure_available_raises():
    """Verify TavilyService raises TavilyConfigurationError when API key is missing."""
    service = TavilyService(api_key="")
    assert service.is_available is False
    with pytest.raises(TavilyConfigurationError):
        service.ensure_available()


@pytest.mark.asyncio
async def test_tavily_search_missing_key_returns_not_configured():
    """Verify search returns unconfigured status when key is absent."""
    service = TavilyService(api_key="")
    res = await service.search("masters scholarship in canada")
    assert res["success"] is False
    assert res["status"] == "NOT_CONFIGURED"
    assert "TAVILY_API_KEY is not configured" in res["error"]


@pytest.mark.asyncio
async def test_tavily_search_caching_prevents_duplicate_api_calls():
    """Verify that identical queries are served from cache without duplicate network requests."""
    service = TavilyService(api_key="tvly-test-key")
    service.clear_cache()

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "results": [
            {
                "title": "UofT MScAC Scholarship",
                "url": "https://web.cs.toronto.edu/graduate/mscac",
                "content": "$17,500 CAD scholarship",
                "score": 0.98
            }
        ]
    }

    call_count = 0

    async def mock_post(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return mock_resp

    with patch("httpx.AsyncClient.post", side_effect=mock_post):
        # First call: hits API and caches
        res1 = await service.search("scholarship in canada")
        assert res1["success"] is True
        assert res1["cached"] is False
        assert len(res1["results"]) == 1
        assert call_count == 1

        # Second call: served from cache
        res2 = await service.search("scholarship in canada")
        assert res2["success"] is True
        assert res2["cached"] is True
        assert len(res2["results"]) == 1
        assert call_count == 1  # No secondary network call


@pytest.mark.asyncio
async def test_tavily_search_quota_exhausted_handling():
    """Verify HTTP 429/432 from Tavily flags quota exhausted."""
    service = TavilyService(api_key="tvly-test-key")
    service.clear_cache()

    mock_resp = MagicMock()
    mock_resp.status_code = 429
    mock_resp.text = "Rate limit exceeded"

    with patch("httpx.AsyncClient.post", AsyncMock(return_value=mock_resp)):
        res = await service.search("scholarship query")
        assert res["success"] is False
        assert res["status"] == "QUOTA_EXHAUSTED"
        assert service._is_quota_exhausted is True


# ==============================================================================
# 2. Safe Page Retriever & SSRF Protection
# ==============================================================================

@pytest.mark.asyncio
async def test_safe_retriever_blocks_ssrf_and_private_ips():
    """Verify SSRF protection blocks localhost, 127.0.0.1, private IPs, and non-http schemes."""
    retriever = SafePageRetriever()

    blocked_urls = [
        "http://localhost:8080/admin",
        "http://127.0.0.1:8000/internal",
        "http://192.168.1.1/router",
        "http://10.0.0.1/secret",
        "http://169.254.169.254/latest/meta-data",
        "ftp://university.edu/admissions.pdf",
        "file:///etc/passwd",
    ]

    for url in blocked_urls:
        res = await retriever.retrieve_page(url)
        assert res["success"] is False
        assert res["status"] == "URL_RETRIEVAL_STATUS_UNSAFE"
        assert "SSRF" in res["error"]


@pytest.mark.asyncio
async def test_safe_retriever_detects_paywall_and_access_denied():
    """Verify HTTP 401 and 403 responses are cleanly classified as URL_RETRIEVAL_STATUS_PAYWALL."""
    retriever = SafePageRetriever()
    retriever.clear_cache()

    mock_resp_403 = MagicMock()
    mock_resp_403.status_code = 403
    mock_resp_403.url = "https://oxford.ac.uk/restricted"

    with patch("httpx.AsyncClient.get", AsyncMock(return_value=mock_resp_403)):
        res = await retriever.retrieve_page("https://oxford.ac.uk/restricted")
        assert res["success"] is False
        assert res["status"] == "URL_RETRIEVAL_STATUS_PAYWALL"
        assert "Access Denied" in res["error"]


def test_safe_retriever_clean_html_strips_scripts_and_chrome():
    """Verify clean_html_to_text strips scripts, styles, nav, and comments."""
    raw_html = """
    <html>
        <head>
            <style>body { color: red; }</style>
            <script>alert('xss');</script>
        </head>
        <body>
            <nav><a href="/">Home</a></nav>
            <h1>Master of Science in Computer Science</h1>
            <p>Minimum CGPA: 8.0/10.0 required for admission.</p>
            <footer>Copyright 2026 University</footer>
        </body>
    </html>
    """
    clean = SafePageRetriever.clean_html_to_text(raw_html)
    assert "Master of Science in Computer Science" in clean
    assert "Minimum CGPA: 8.0/10.0" in clean
    assert "alert" not in clean
    assert "color: red" not in clean
    assert "Home" not in clean
    assert "Copyright" not in clean


# ==============================================================================
# 3. Gemini Criteria Analysis with Page Text
# ==============================================================================

@pytest.mark.asyncio
async def test_gemini_analysis_receives_page_text_without_url_context_tool():
    """Verify analyze_url_and_extract_criteria embeds page text into prompt and doesn't require url_context tool."""
    service = GeminiService(api_key="mock-key")
    mock_client = MagicMock()
    service._client = mock_client

    mock_response = MagicMock()
    mock_response.candidates = []
    mock_response.text = json.dumps({
        "admission_requirements": [
            {
                "criterion_name": "Academic CGPA",
                "stated_requirement": "Minimum 8.0/10.0",
                "student_value": "8.9",
                "status": "MEETS",
                "evidence_excerpt": "Minimum 8.0/10.0 CGPA required",
                "source_url": "https://tum.de/msc"
            }
        ],
        "scholarship_requirements": [],
        "funding_details": {"funding_type": "Fully Funded", "coverage_description": "DAAD stipend"},
        "deadline": "2026-05-31",
        "deadline_type": "Fixed",
        "deadline_verified": True,
        "overall_eligibility_status": "MEETS_STATED_CRITERIA"
    })
    mock_client.models.generate_content.return_value = mock_response

    res = await service.analyze_url_and_extract_criteria(
        urls=["https://tum.de/msc"],
        program_name="MSc Informatics",
        university="TUM",
        student_profile_summary="CGPA 8.9",
        page_text="Published requirements: Minimum 8.0/10.0 CGPA required. Application deadline: 2026-05-31."
    )

    assert res["success"] is True
    assert res["is_retrieval_successful"] is True
    assert res["retrieval_status"] == "URL_RETRIEVAL_STATUS_SUCCESS"
    assert res["evidence_quality"] == "OFFICIAL"
    assert res["data"]["deadline"] == "2026-05-31"

    # Verify generate_content received the content text
    call_args = mock_client.models.generate_content.call_args
    assert "Published requirements: Minimum 8.0/10.0" in call_args.kwargs.get("contents", "")


# ==============================================================================
# 4. Research Eligibility Agent Integration
# ==============================================================================

@pytest.mark.asyncio
async def test_research_agent_zero_candidates_returns_empty_without_dummy_fallback(mock_student_profile):
    """Verify ResearchEligibilityAgent strictly returns [] and emits DISCOVERY_EMPTY when no candidates are found."""
    agent = ResearchEligibilityAgent()
    run_id = "test-empty-tavily-run"

    empty_tavily = {
        "success": True,
        "status": "SUCCESS",
        "results": [],
        "query": "query",
        "cached": False
    }

    with patch("app.services.tavily_service.tavily_service.ensure_available", return_value=None), \
         patch("app.services.tavily_service.tavily_service.search", AsyncMock(return_value=empty_tavily)), \
         patch("app.services.gemini_service.gemini_service.ensure_available", return_value=None):

        opps = await agent.execute_discovery_and_audit(run_id, mock_student_profile)

    assert opps == []
    events = await repository.get_agent_events(run_id)
    empty_events = [e for e in events if e.event_type == "DISCOVERY_EMPTY"]
    assert len(empty_events) >= 1
    assert "No Candidates Found" in empty_events[0].title
