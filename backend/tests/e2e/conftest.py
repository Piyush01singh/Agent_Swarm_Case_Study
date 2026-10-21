"""
Pytest configuration and shared fixtures for ScholarSwarm E2E tests.
Provides asynchronous HTTP clients, mock Gemini service factories,
canonical student profiles, and database state management.
"""

import pytest
import pytest_asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.db.repository import repository
from app.models.profile import StudentProfile, ProjectOrAchievement
from app.models.opportunity import Opportunity, FundingDetails, EligibilityCriterion
from app.models.evidence import EvidenceRecord, MatchScore


@pytest_asyncio.fixture
async def clean_repo():
    """Resets all in-memory repository collections before and after each test."""
    await repository.reset_all_data()
    yield repository
    await repository.reset_all_data()


@pytest.fixture(autouse=True)
def mock_gemini_in_e2e_if_unavailable(monkeypatch):
    """
    Supplies deterministic responses from canonical test fixtures for discovery
    and URL extraction so full workflows and scenarios can be verified end-to-end
    deterministically without exhausting live quotas.
    """
    import app.agents.research_eligibility as re_agent_mod
    from tests.fixtures.opportunities import get_mock_discovery_response, get_mock_url_analysis_response

    async def _mock_discovery(query: str, context_prompt: str):
        countries = [c for c in ["Canada", "Germany", "Singapore"] if c.lower() in query.lower()]
        return get_mock_discovery_response(countries=countries or None)

    async def _mock_extract(urls, program_name="", university="", student_profile_summary=""):
        url = urls[0] if urls else ""
        return get_mock_url_analysis_response(url)

    monkeypatch.setattr(re_agent_mod.gemini_service, "search_grounded_discovery", _mock_discovery)
    monkeypatch.setattr(re_agent_mod.gemini_service, "analyze_url_and_extract_criteria", _mock_extract)


@pytest_asyncio.fixture
async def async_client(clean_repo):
    """Provides an httpx AsyncClient connected to the FastAPI ASGI application."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.fixture
def profile_rahul_sharma() -> StudentProfile:
    """
    Persona 1: Rahul Sharma
    - Indian undergraduate in Computer Science
    - CGPA 8.2/10.0 (Strong First Class)
    - Target: Master's in Computer Science / AI in Canada, Germany, Singapore
    - Language test: IELTS planned (no final score submitted)
    """
    return StudentProfile(
        full_name="Rahul Sharma",
        institution="Punjab Technical University",
        current_degree="B.Tech Computer Science and Engineering",
        cgpa=8.2,
        grading_scale="10.0",
        graduation_year=2025,
        target_degree="Master's",
        target_field="Computer Science / Artificial Intelligence",
        target_countries=["Canada", "Germany", "Singapore"],
        citizenship="India",
        funding_preference="Full Funding / Tuition Assistance",
        skills=["Python", "PyTorch", "Distributed Systems", "PostgreSQL", "FastAPI"],
        projects=[
            ProjectOrAchievement(
                title="Distributed Semantic Search Engine",
                description="Built high-throughput vector retrieval engine with HNSW indexing and FastAPI",
                technologies=["Python", "FastAPI", "FAISS", "Docker"],
                repo_url="https://github.com/rahulsharma/distributed-search"
            ),
            ProjectOrAchievement(
                title="Medical Imaging Segmentation",
                description="U-Net architecture for CT scan segmentation achieving 0.89 Dice score",
                technologies=["PyTorch", "OpenCV", "NumPy"]
            )
        ],
        language_tests={"test": "IELTS", "status": "planned", "score": None},
        career_goals="Conduct research in scalable AI systems and deploy foundation models for societal impact."
    )


@pytest.fixture
def profile_maria_santos() -> StudentProfile:
    """
    Persona 2: Maria Santos
    - Brazilian undergraduate in Biotechnology
    - CGPA 6.8/10.0 (Marginal academic standing)
    - Target: Master's in Bioinformatics in Germany or Canada
    - Language test: TOEFL iBT 102 (High language proficiency)
    """
    return StudentProfile(
        full_name="Maria Santos",
        institution="Federal University of Rio de Janeiro",
        current_degree="B.Sc Biotechnology",
        cgpa=6.8,
        grading_scale="10.0",
        graduation_year=2024,
        target_degree="Master's",
        target_field="Bioinformatics",
        target_countries=["Germany", "Canada"],
        citizenship="Brazil",
        funding_preference="Partial Tuition / Scholarship",
        skills=["R", "Python", "BioPython", "Genomics", "Statistical Genetics"],
        projects=[
            ProjectOrAchievement(
                title="CRISPR Off-Target Predictive Pipeline",
                description="Pipeline analyzing off-target mutations using ensemble classifiers",
                technologies=["Python", "BioPython", "scikit-learn"]
            )
        ],
        language_tests={"test": "TOEFL", "status": "completed", "score": "102"},
        career_goals="Specialize in computational biology and drug discovery."
    )


@pytest.fixture
def profile_wei_chen() -> StudentProfile:
    """
    Persona 3: Wei Chen
    - Chinese postgraduate in Mathematics
    - CGPA 8.5/10.0 equivalent (85%)
    - Target: PhD in Data Science / AI in Singapore
    - Language test: Not yet taken (pending)
    """
    return StudentProfile(
        full_name="Wei Chen",
        institution="Zhejiang University",
        current_degree="M.Sc Mathematics",
        cgpa=8.5,
        grading_scale="10.0",
        graduation_year=2024,
        target_degree="PhD",
        target_field="Data Science",
        target_countries=["Singapore"],
        citizenship="China",
        funding_preference="Full Funding / Research Stipend",
        skills=["Measure Theory", "Optimization", "Python", "C++", "Stochastic Modeling"],
        projects=[
            ProjectOrAchievement(
                title="Non-Convex Optimization for Deep Networks",
                description="Theoretical bounds for gradient descent on overparameterized landscapes",
                technologies=["Python", "Matplotlib", "LaTeX"]
            )
        ],
        language_tests={"test": "IELTS", "status": "planned", "score": None},
        career_goals="Pursue academic tenure track research in theoretical machine learning."
    )


@pytest.fixture
def profile_fatima_alhassan() -> StudentProfile:
    """
    Persona 4: Fatima Al-Hassan
    - Nigerian undergraduate in Electrical & Computer Engineering
    - CGPA 9.1/10.0 (Top 1% distinction)
    - Target: PhD in Robotics & Autonomous Systems in Canada
    - Language test: IELTS 8.0 (Completed)
    """
    return StudentProfile(
        full_name="Fatima Al-Hassan",
        institution="University of Lagos",
        current_degree="B.Eng Electrical and Electronics Engineering",
        cgpa=9.1,
        grading_scale="10.0",
        graduation_year=2025,
        target_degree="PhD",
        target_field="Robotics / Autonomous Systems",
        target_countries=["Canada"],
        citizenship="Nigeria",
        funding_preference="Full Funding / Fellowship",
        skills=["ROS2", "C++", "Control Theory", "SLAM", "Embedded Systems"],
        projects=[
            ProjectOrAchievement(
                title="Autonomous Agricultural Quadrotor",
                description="Visual-inertial SLAM on edge compute unit with custom PID controller",
                technologies=["C++", "ROS2", "Gazebo", "OpenCV"],
                repo_url="https://github.com/fatima-alhassan/agri-drone"
            )
        ],
        language_tests={"test": "IELTS", "status": "completed", "score": "8.0"},
        career_goals="Lead robotic perception research for environmental monitoring."
    )


@pytest.fixture
def create_mock_opportunity():
    """Helper factory to instantiate valid Opportunity objects with realistic defaults."""
    def _create(
        id: str = "test-opp-1",
        run_id: str = "test-run-1",
        title: str = "Test University AI Fellowship",
        university: str = "University of Test",
        country: str = "Canada",
        canonical_url: str = "https://www.test-uni.ca/scholarships/ai",
        funding_type: str = "Fully Funded",
        amount: float = 35000.0,
        deadline: Optional[str] = "2026-12-01",
        deadline_type: str = "Fixed",
        deadline_verified: bool = True,
        eligibility_status: str = "MEETS_STATED_CRITERIA",
        evidence_quality: str = "OFFICIAL"
    ) -> Opportunity:
        return Opportunity(
            id=id,
            run_id=run_id,
            canonical_url=canonical_url,
            title=title,
            program_name="M.Sc. in Computer Science",
            university=university,
            country=country,
            degree_level="Master's",
            field="Computer Science",
            intake="Fall 2026",
            funding_details=FundingDetails(
                funding_type=funding_type,
                coverage_description=f"${amount:,.0f} full tuition waiver and monthly research stipend",
                amount=amount,
                currency="CAD",
                tuition_covered=True
            ),
            deadline=deadline,
            deadline_type=deadline_type,
            deadline_verified=deadline_verified,
            official_application_url=canonical_url,
            official_source_urls=[canonical_url],
            source_retrieval_timestamps={canonical_url: datetime.now(timezone.utc).isoformat()},
            evidence_quality=evidence_quality,
            eligibility_status=eligibility_status,
            eligibility_reasons=["Meets academic requirements"],
            actionable_gaps=[],
            admission_requirements=[
                EligibilityCriterion(
                    criterion_type="ACADEMIC_GRADE",
                    is_mandatory=True,
                    requirement_text="Minimum 8.0/10.0 CGPA from recognized university",
                    official_equivalency_note="B+ average equivalent"
                )
            ],
            scholarship_requirements=[
                EligibilityCriterion(
                    criterion_type="ACADEMIC_GRADE",
                    is_mandatory=True,
                    requirement_text="Competitive selection based on academic excellence"
                )
            ]
        )
    return _create
