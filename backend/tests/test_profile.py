import pytest
from app.models.profile import StudentProfile, ProjectOrAchievement

def test_student_profile_defaults():
    profile = StudentProfile()
    assert profile.full_name == "Rahul Sharma"
    assert profile.cgpa == 8.2
    assert profile.current_degree == "B.Tech Computer Science"
    assert "Canada" in profile.target_countries
    assert "Germany" in profile.target_countries
    assert "Singapore" in profile.target_countries

def test_student_profile_custom_validation():
    profile = StudentProfile(
        full_name="Ananya Verma",
        current_degree="B.Sc Biotechnology",
        institution="Delhi University",
        cgpa=7.4,
        target_degree="Master's",
        target_field="Bioinformatics",
        target_countries=["Germany"]
    )
    assert profile.full_name == "Ananya Verma"
    assert profile.cgpa == 7.4
    assert profile.target_field == "Bioinformatics"
    assert len(profile.target_countries) == 1

def test_project_achievement_provenance():
    proj = ProjectOrAchievement(
        title="ScholarSwarm Multi-Agent Engine",
        description="Autonomous scholarship discovery agent",
        technologies=["Python", "FastAPI", "LangGraph"],
        is_ai_ml=True,
        evidence_source="github"
    )
    assert proj.is_ai_ml is True
    assert proj.evidence_source == "github"
