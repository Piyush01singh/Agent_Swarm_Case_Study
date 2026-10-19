import io
import re
from typing import Dict, Any, List, Optional
import pymupdf # PyMuPDF
import docx

def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extracts text layer from PDF using PyMuPDF."""
    text_content = []
    try:
        doc = pymupdf.open(stream=file_bytes, filetype="pdf")
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            if text:
                text_content.append(text)
        doc.close()
    except Exception as e:
        raise ValueError(f"Failed to parse PDF document: {str(e)}")
    
    extracted = "\n".join(text_content).strip()
    if not extracted:
        raise ValueError("PDF has no extractable text layer (may be scanned or image-only).")
    return extracted

def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extracts text from DOCX file using python-docx."""
    try:
        doc_stream = io.BytesIO(file_bytes)
        doc = docx.Document(doc_stream)
        paragraphs = [p.text for p in doc.paragraphs if p.text]
        # Also extract table text
        for table in doc.tables:
            for row in table.rows:
                row_text = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if row_text:
                    paragraphs.append(" | ".join(row_text))
    except Exception as e:
        raise ValueError(f"Failed to parse DOCX document: {str(e)}")
        
    extracted = "\n".join(paragraphs).strip()
    if not extracted:
        raise ValueError("DOCX document contains no text.")
    return extracted

def parse_profile_facts_from_text(text: str) -> Dict[str, Any]:
    """
    Deterministically extracts key profile signals like CGPA, degree, institutions, skills, and projects
    from resume/marksheet text to prefill or assist the Profile Intelligence Agent.
    """
    facts: Dict[str, Any] = {
        "cgpa": None,
        "degree": None,
        "institution": None,
        "skills": [],
        "projects": []
    }
    
    # 1. CGPA Extraction (e.g., "CGPA: 8.2", "8.2 / 10", "GPA: 3.8", "8.20 CGPA")
    cgpa_match = re.search(r'(?:CGPA|GPA|Grade|Score)[\s:=]+([0-9]+(?:\.[0-9]+)?)(?:\s*/\s*([0-9]+(?:\.[0-9]+)?))?', text, re.IGNORECASE)
    if cgpa_match:
        try:
            score = float(cgpa_match.group(1))
            facts["cgpa"] = score
        except ValueError:
            pass

    # 2. Degree Extraction
    degrees = [
        "B.Tech", "Bachelor of Technology", "B.E.", "Bachelor of Engineering",
        "B.S.", "Bachelor of Science", "BCA", "M.Tech", "M.S.", "Master of Science"
    ]
    for d in degrees:
        if re.search(rf'\b{re.escape(d)}\b', text, re.IGNORECASE):
            facts["degree"] = d
            break
            
    # 3. Known Skills extraction
    known_skills = [
        "Python", "PyTorch", "TensorFlow", "FastAPI", "React", "TypeScript",
        "Machine Learning", "Deep Learning", "NLP", "Natural Language Processing",
        "Computer Vision", "Docker", "SQL", "PostgreSQL", "Git", "Scikit-learn"
    ]
    extracted_skills = []
    for skill in known_skills:
        if re.search(rf'\b{re.escape(skill)}\b', text, re.IGNORECASE):
            extracted_skills.append(skill)
    facts["skills"] = extracted_skills
    
    return facts
