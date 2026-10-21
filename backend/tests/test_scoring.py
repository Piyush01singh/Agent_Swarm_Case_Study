import pytest
from app.models.profile import StudentProfile
from app.models.opportunity import Opportunity, FundingDetails
from app.models.evidence import EvidenceRecord
from app.services.scoring_service import calculate_match_score

def test_scoring_weights_and_dimensions():
    profile = StudentProfile(cgpa=8.2, target_degree="Master's", target_field="Computer Science")
    opp = Opportunity(
        id="opp-1",
        run_id="run-1",
        canonical_url="https://cs.toronto.edu/mscac",
        title="Vector AI Scholarship",
        program_name="MSc Applied Computing",
        university="University of Toronto",
        country="Canada",
        degree_level="Master's",
        field="Computer Science / Artificial Intelligence",
        funding_details=FundingDetails(
            funding_type="Fully Funded",
            coverage_description="Full funding package",
            tuition_covered=True
        ),
        deadline="2026-12-01",
        deadline_type="Fixed",
        deadline_verified=True,
        evidence_quality="OFFICIAL",
        eligibility_status="MEETS_STATED_CRITERIA"
    )
    score = calculate_match_score(profile, opp)
    
    assert score.academic_fit == 35.0
    assert score.funding_fit == 25.0
    assert score.subject_fit == 20.0
    assert score.deadline_fit == 10.0
    assert score.evidence_fit == 10.0
    assert score.total_score == 100.0
    assert score.is_eligible_for_shortlist is True

def test_hard_disqualifier_excludes_from_shortlist():
    profile = StudentProfile(cgpa=6.5) # below cutoff
    opp = Opportunity(
        id="opp-2",
        run_id="run-1",
        canonical_url="https://tum.de/msc",
        title="TUM Informatics",
        program_name="MSc Informatics",
        university="TUM",
        country="Germany",
        degree_level="Master's",
        field="Informatics",
        funding_details=FundingDetails(funding_type="Fully Funded"),
        evidence_records=[
            EvidenceRecord(
                criterion_name="Minimum CGPA",
                stated_requirement="Minimum 7.5 CGPA required",
                student_value="6.5",
                status="DOES_NOT_MEET",
                source_url="https://tum.de"
            )
        ],
        eligibility_status="DOES_NOT_MEET"
    )
    score = calculate_match_score(profile, opp)
    assert score.is_eligible_for_shortlist is False
    assert score.academic_fit == 0.0

def test_potential_match_partial_score():
    profile = StudentProfile(cgpa=8.2)
    opp = Opportunity(
        id="opp-3",
        run_id="run-1",
        canonical_url="https://nus.edu.sg/mcomp",
        title="NUS MComp",
        program_name="MComp AI",
        university="NUS",
        country="Singapore",
        degree_level="Master's",
        field="Artificial Intelligence",
        funding_details=FundingDetails(funding_type="Stipend & Fee Relief"),
        evidence_quality="SECONDARY",
        eligibility_status="POTENTIAL_MATCH"
    )
    score = calculate_match_score(profile, opp)
    assert score.is_eligible_for_shortlist is True
    assert 25.0 <= score.academic_fit <= 30.0
    assert score.evidence_fit == 5.0 # secondary
