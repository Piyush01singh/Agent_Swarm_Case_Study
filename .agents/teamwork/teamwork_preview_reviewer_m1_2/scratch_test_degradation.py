import sys, os
sys.path.insert(0, os.path.abspath("."))
import asyncio
from unittest.mock import patch, AsyncMock
from app.agents.research_eligibility import ResearchEligibilityAgent
from app.models.profile import StudentProfile

async def test_agent_degradation():
    agent = ResearchEligibilityAgent()
    profile = StudentProfile(
        full_name="Test Student",
        current_degree="B.Tech CS",
        cgpa=8.5,
        target_degree="Master's",
        target_field="Computer Science",
        target_countries=["Canada"]
    )
    
    mock_discovery = {
        "success": True,
        "candidates": [
            {"canonical_url": "https://paywalled.edu/opp1", "program_name": "MSc CS", "university": "Paywall Univ"},
            {"canonical_url": "https://unsafe.edu/opp2", "program_name": "MSc AI", "university": "Unsafe Univ"},
            {"canonical_url": "https://error.edu/opp3", "program_name": "MSc Data", "university": "Error Univ"},
            {"canonical_url": "https://crash.edu/opp4", "program_name": "MSc Crash", "university": "Crash Univ"}
        ],
        "sources": [],
        "citations": []
    }
    
    async def mock_extract(urls, **kwargs):
        u = urls[0]
        if "paywalled" in u:
            return {
                "success": True,
                "is_retrieval_successful": False,
                "retrieval_status": "URL_RETRIEVAL_STATUS_PAYWALL",
                "evidence_quality": "UNVERIFIED",
                "data": {"program_name": "MSc CS", "university": "Paywall Univ"}
            }
        elif "unsafe" in u:
            return {
                "success": True,
                "is_retrieval_successful": False,
                "retrieval_status": "URL_RETRIEVAL_STATUS_UNSAFE",
                "evidence_quality": "UNVERIFIED",
                "data": {"program_name": "MSc AI", "university": "Unsafe Univ"}
            }
        elif "error" in u:
            # Gemini URL Context returned status URL_RETRIEVAL_STATUS_ERROR
            return {
                "success": True,
                "is_retrieval_successful": False,
                "retrieval_status": "URL_RETRIEVAL_STATUS_ERROR",
                "evidence_quality": "UNVERIFIED",
                "data": {"program_name": "MSc Data", "university": "Error Univ"}
            }
        else:
            # Exception / network crash case
            return {
                "success": False,
                "is_retrieval_successful": False,
                "retrieval_status": "URL_RETRIEVAL_STATUS_ERROR",
                "evidence_quality": "UNVERIFIED",
                "error": "Network timeout",
                "data": None
            }

    with patch("app.agents.research_eligibility.gemini_service.ensure_available"), \
         patch("app.agents.research_eligibility.gemini_service.search_grounded_discovery", new=AsyncMock(return_value=mock_discovery)), \
         patch("app.agents.research_eligibility.gemini_service.analyze_url_and_extract_criteria", side_effect=mock_extract):
        opps = await agent.execute_discovery_and_audit("run-deg-1", profile)
        print(f"Discovered {len(opps)} opps")
        for opp in opps:
            print(f"Opp: {opp.title}, Quality: {opp.evidence_quality}, Status: {opp.eligibility_status}")
            assert opp.evidence_quality == "UNVERIFIED"
            assert opp.eligibility_status == "INSUFFICIENT_EVIDENCE"
            assert opp.deadline_verified is False
            assert len(opp.evidence_records) > 0
            for ev in opp.evidence_records:
                print(f"  Ev status: {ev.status}, category: {ev.source_category}, note: {ev.uncertainty_or_conflict}")
                assert ev.status == "UNRESOLVED"
                assert ev.source_category == "UNVERIFIED"
                assert ev.evidence_excerpt is None

if __name__ == "__main__":
    asyncio.run(test_agent_degradation())
