"""
Automated unit and CLI tests for ScholarSwarm Live Gemini Smoke Test Runner (Feature F26).
Verifies:
1. CLI execution with --help exits with 0 and prints usage.
2. Missing or unconfigured GEMINI_API_KEY exits gracefully with 0 (or exits with 1 if --strict).
3. CLI execution in mock mode (--mock) passes all gates.
4. CLI execution with mocked live Google Gen AI SDK search grounding and URL Context extraction.
5. JSON output formatting and metadata assertions.
"""

import os
import sys
import json
import pytest
import subprocess
from unittest.mock import patch, AsyncMock, MagicMock

backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

from scripts.smoke_test_gemini import (
    main,
    run_smoke_test,
    mask_key,
    is_valid_gemini_key_format,
    get_mock_discovery_response,
    get_mock_extraction_response,
)
from app.services.gemini_service import GeminiService


# =====================================================================
# 1. Helper Unit Tests
# =====================================================================

def test_mask_key_sanitization():
    """Verify that sensitive API keys are properly masked in logs."""
    assert mask_key("") == "<not set>"
    assert mask_key("short") == "***"
    key_str = "AIzaSyB1234567890abcdefGHIJKLMN"
    masked = mask_key(key_str)
    assert masked.startswith("AIza...")
    assert f"len: {len(key_str)}" in masked
    assert "1234567890" not in masked


def test_is_valid_gemini_key_format():
    """Verify key format classification distinguishing Google AI Studio keys from sandbox bearer tokens."""
    # Invalid keys
    assert is_valid_gemini_key_format("") is False
    assert is_valid_gemini_key_format(None) is False
    assert is_valid_gemini_key_format("too_short") is False
    assert is_valid_gemini_key_format("sandbox_bearer_token_redacted") is False

    # Valid key formats (both traditional AIza and modern AQ keys)
    assert is_valid_gemini_key_format("AIzaSyB1234567890abcdefGHIJKLMN") is True
    assert is_valid_gemini_key_format("AIzaDummyValidLengthApiKey1234567890") is True
    assert is_valid_gemini_key_format("AQ.Ab8DummyValidLengthApiKey1234567890") is True
    assert is_valid_gemini_key_format("AQDummyApiKeyFormatTesting1234567890") is True


# =====================================================================
# 2. CLI Execution Tests
# =====================================================================

def test_smoke_cli_help():
    """Verify CLI execution with --help flag exits cleanly and displays usage."""
    script_path = os.path.join(backend_root, "scripts", "smoke_test_gemini.py")
    res = subprocess.run(
        [sys.executable, script_path, "--help"],
        capture_output=True,
        text=True,
        cwd=backend_root
    )
    assert res.returncode == 0
    assert "ScholarSwarm Live Gemini Grounding & Extraction Smoke Test Runner" in res.stdout
    assert "--strict" in res.stdout
    assert "--mock" in res.stdout
    assert "--query" in res.stdout
    assert "--url" in res.stdout


def test_smoke_cli_missing_key_graceful_exit():
    """Verify CLI execution with empty/missing key exits with code 0 and transparent report."""
    with patch.dict(os.environ, {"GEMINI_API_KEY": ""}, clear=False):
        exit_code = main(["--api-key", "", "--quiet"])
        assert exit_code == 0


def test_smoke_cli_missing_key_strict_exit():
    """Verify CLI execution with empty/missing key and --strict exits with code 1."""
    with patch.dict(os.environ, {"GEMINI_API_KEY": ""}, clear=False):
        exit_code = main(["--api-key", "", "--strict", "--quiet"])
        assert exit_code == 1


def test_smoke_cli_mock_mode_success():
    """Verify CLI execution with --mock flag exits with code 0."""
    exit_code = main(["--mock", "--quiet"])
    assert exit_code == 0


def test_smoke_cli_json_output(capsys):
    """Verify CLI execution with --mock --json outputs well-formed JSON report."""
    exit_code = main(["--mock", "--json"])
    assert exit_code == 0
    captured = capsys.readouterr()
    report = json.loads(captured.out)

    assert report["mock_mode"] is True
    assert report["search_grounding_verified"] is True
    assert report["url_context_verified"] is True
    assert report["metadata_verified"] is True
    assert report["discovered_sources_count"] >= 1
    assert report["retrieval_status"] == "URL_RETRIEVAL_STATUS_SUCCESS"
    assert report["evidence_quality"] == "OFFICIAL"


# =====================================================================
# 3. Mocked Live Execution Tests
# =====================================================================

@pytest.mark.asyncio
async def test_smoke_test_with_mocked_gemini_service_success():
    """
    Verify full smoke test pipeline when GeminiService returns live-structured
    search grounding and URL context extraction responses.
    """
    mock_discovery = {
        "success": True,
        "text": "Live search discovered Toronto MScAC details.",
        "candidates": [
            {
                "program_title": "MSc Applied Computing",
                "university": "University of Toronto",
                "country": "Canada",
                "official_url": "https://web.cs.toronto.edu/graduate/mscac",
                "funding_amount": "$17,500 CAD stipend"
            }
        ],
        "sources": [
            {
                "title": "U of T Department of Computer Science",
                "url": "https://web.cs.toronto.edu/graduate/mscac"
            }
        ],
        "citations": [
            {
                "title": "U of T Department of Computer Science",
                "url": "https://web.cs.toronto.edu/graduate/mscac"
            }
        ],
        "search_queries": ["University of Toronto MSc Applied Computing"],
        "model_used": "gemini-2.5-flash"
    }

    mock_extraction = {
        "success": True,
        "data": {
            "admission_requirements": [
                {
                    "criterion_name": "Academic CGPA",
                    "stated_requirement": "Minimum B+ average in senior CS courses",
                    "student_value": "8.2/10",
                    "status": "MEETS",
                    "evidence_excerpt": "Minimum B+ average (77-79% or 3.3/4.0) in senior coursework.",
                    "source_url": "https://web.cs.toronto.edu/graduate/mscac"
                }
            ],
            "scholarship_requirements": [
                {
                    "criterion_name": "Funding Eligibility",
                    "stated_requirement": "Graduate stipend support",
                    "student_value": "Eligible",
                    "status": "MEETS",
                    "evidence_excerpt": "Students receive $17,500 CAD stipend during academic terms.",
                    "source_url": "https://web.cs.toronto.edu/graduate/mscac"
                }
            ],
            "funding_details": {
                "funding_type": "Fully Funded",
                "coverage_description": "$17,500 CAD stipend",
                "tuition_covered": True
            },
            "deadline": "2026-12-01",
            "deadline_type": "Fixed",
            "overall_eligibility_status": "MEETS_STATED_CRITERIA"
        },
        "retrieval_metadata": [
            {
                "retrieved_url": "https://web.cs.toronto.edu/graduate/mscac",
                "url_retrieval_status": "URL_RETRIEVAL_STATUS_SUCCESS",
                "is_success": True
            }
        ],
        "url_retrieval_statuses": {
            "https://web.cs.toronto.edu/graduate/mscac": "URL_RETRIEVAL_STATUS_SUCCESS"
        },
        "is_retrieval_successful": True,
        "retrieval_status": "URL_RETRIEVAL_STATUS_SUCCESS",
        "evidence_quality": "OFFICIAL",
        "model_used": "gemini-2.5-flash"
    }

    dummy_valid_key = "AIzaSyB1234567890abcdefGHIJKLMN"

    with patch.object(GeminiService, "validate_connection", new_callable=AsyncMock) as mock_auth, \
         patch.object(GeminiService, "search_grounded_discovery", new_callable=AsyncMock) as mock_search, \
         patch.object(GeminiService, "analyze_url_and_extract_criteria", new_callable=AsyncMock) as mock_extract, \
         patch("google.genai.Client") as mock_client:

        mock_auth.return_value = {"authenticated": True, "status": "AUTHENTICATED"}
        mock_search.return_value = mock_discovery
        mock_extract.return_value = mock_extraction

        passed, results = await run_smoke_test(
            api_key=dummy_valid_key,
            strict=True,
            mock_mode=False,
            verbose=False
        )

        assert passed is True
        assert results["api_key_configured"] is True
        assert results["live_authenticated"] is True
        assert results["search_grounding_verified"] is True
        assert results["discovered_sources_count"] == 1
        assert results["url_context_verified"] is True
        assert results["is_retrieval_successful"] is True
        assert results["retrieval_status"] == "URL_RETRIEVAL_STATUS_SUCCESS"
        assert results["evidence_quality"] == "OFFICIAL"
        assert results["extracted_admission_count"] == 1
        assert results["metadata_verified"] is True
        assert len(results["errors"]) == 0


@pytest.mark.asyncio
async def test_smoke_test_with_mocked_gemini_service_search_failure():
    """Verify that search grounding failure is captured and returned appropriately."""
    dummy_valid_key = "AIzaSyB1234567890abcdefGHIJKLMN"

    with patch.object(GeminiService, "validate_connection", new_callable=AsyncMock) as mock_auth, \
         patch.object(GeminiService, "search_grounded_discovery", new_callable=AsyncMock) as mock_search, \
         patch("google.genai.Client"):

        mock_auth.return_value = {"authenticated": True, "status": "AUTHENTICATED"}
        mock_search.return_value = {
            "success": False,
            "error": "Simulated Google Search grounding quota exceeded.",
            "sources": []
        }

        # Under strict mode, should fail
        passed_strict, results_strict = await run_smoke_test(
            api_key=dummy_valid_key,
            strict=True,
            mock_mode=False,
            verbose=False
        )
        assert passed_strict is False
        assert results_strict["search_grounding_verified"] is False
        assert len(results_strict["errors"]) > 0

        # Under non-strict mode
        passed_non_strict, results_non_strict = await run_smoke_test(
            api_key=dummy_valid_key,
            strict=False,
            mock_mode=False,
            verbose=False
        )
        assert passed_non_strict is True
        assert results_non_strict["search_grounding_verified"] is False


@pytest.mark.asyncio
async def test_smoke_test_with_mocked_gemini_service_url_extraction_failure():
    """Verify that URL context extraction failure is captured and reported."""
    dummy_valid_key = "AIzaSyB1234567890abcdefGHIJKLMN"

    mock_discovery = {
        "success": True,
        "sources": [{"title": "Test", "url": "https://example.edu/program"}],
        "search_queries": ["Test query"]
    }

    mock_extraction_fail = {
        "success": False,
        "error": "URL_RETRIEVAL_STATUS_ERROR: Connection refused",
        "is_retrieval_successful": False,
        "retrieval_status": "URL_RETRIEVAL_STATUS_ERROR",
        "evidence_quality": "UNVERIFIED"
    }

    with patch.object(GeminiService, "validate_connection", new_callable=AsyncMock) as mock_auth, \
         patch.object(GeminiService, "search_grounded_discovery", new_callable=AsyncMock) as mock_search, \
         patch.object(GeminiService, "analyze_url_and_extract_criteria", new_callable=AsyncMock) as mock_extract, \
         patch("google.genai.Client"):

        mock_auth.return_value = {"authenticated": True, "status": "AUTHENTICATED"}
        mock_search.return_value = mock_discovery
        mock_extract.return_value = mock_extraction_fail

        passed_strict, results = await run_smoke_test(
            api_key=dummy_valid_key,
            strict=True,
            mock_mode=False,
            verbose=False
        )
        assert passed_strict is False
        assert results["search_grounding_verified"] is True
        assert results["url_context_verified"] is False
        assert len(results["errors"]) > 0


@pytest.mark.asyncio
async def test_smoke_test_authentication_failure():
    """Verify that 401 UNAUTHENTICATED fails the smoke test and reports error."""
    dummy_key = "AQ.Ab8InvalidTestKey1234567890abcdef"

    with patch.object(GeminiService, "validate_connection", new_callable=AsyncMock) as mock_auth, \
         patch("google.genai.Client"):

        mock_auth.return_value = {
            "authenticated": False,
            "status": "UNAUTHENTICATED",
            "message": "Google Gen AI rejected the key with 401 UNAUTHENTICATED."
        }

        passed, results = await run_smoke_test(
            api_key=dummy_key,
            strict=False,
            mock_mode=False,
            verbose=False
        )
        assert passed is False
        assert results["live_authenticated"] is False
        assert results["authentication_status"] == "UNAUTHENTICATED"
        assert any("401 UNAUTHENTICATED" in err for err in results["errors"])
