import pytest
from app.security.sanitizer import normalize_url, is_safe_url
from app.models.evidence import EvidenceRecord, EligibilityAssessment

def test_url_normalization():
    raw_1 = "https://web.cs.toronto.edu/graduate/mscac/?utm_source=google&utm_medium=cpc#apply"
    norm_1 = normalize_url(raw_1)
    assert norm_1 == "https://web.cs.toronto.edu/graduate/mscac"
    
    raw_2 = "HTTPS://TUM.DE/STUDIES/DEGREE/DETAIL///"
    norm_2 = normalize_url(raw_2)
    assert norm_2 == "https://tum.de/studies/degree/detail"

def test_safe_url_ssrf_protection():
    assert is_safe_url("https://web.cs.toronto.edu") is True
    assert is_safe_url("https://www.tum.de/en") is True
    
    # Unsafe URLs
    assert is_safe_url("http://localhost:8000/secret") is False
    assert is_safe_url("http://127.0.0.1/admin") is False
    assert is_safe_url("http://169.254.169.254/latest/meta-data") is False
    assert is_safe_url("file:///etc/passwd") is False
    assert is_safe_url("ftp://ftp.server.com") is False

def test_evidence_record_integrity():
    record = EvidenceRecord(
        criterion_name="Academic CGPA",
        stated_requirement="Minimum 8.0/10 CGPA required",
        student_value="8.2 / 10.0",
        status="MEETS",
        evidence_excerpt="Applicant achieves 8.2 CGPA from PTU/NIT, satisfying 8.0 requirement.",
        source_title="University Admission Regulations",
        source_url="https://cs.toronto.edu",
        source_category="OFFICIAL"
    )
    assert record.status == "MEETS"
    assert record.source_category == "OFFICIAL"
