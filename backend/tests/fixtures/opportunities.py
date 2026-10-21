"""
Canonical Test Fixtures for ScholarSwarm Opportunities.
Extracted from verified official portals for Canada, Germany, and Singapore.
Used exclusively in testing and offline evaluation harnesses to ensure deterministic,
reproducible verification without hardcoding fixtures into production pipelines.
"""

import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from app.models.opportunity import Opportunity, FundingDetails, EligibilityCriterion
from app.models.evidence import EvidenceRecord

CANONICAL_FIXTURE_OPPORTUNITIES: List[Dict[str, Any]] = [
    {
        "id": "fix-uoft-mscac-001",
        "title": "Vector Institute Scholarship in Artificial Intelligence (VSAI) & Master's",
        "program_name": "MSc Applied Computing / Computer Science with Vector Institute AI Concentration",
        "university": "University of Toronto",
        "country": "Canada",
        "degree_level": "Master's",
        "field": "Computer Science / Artificial Intelligence",
        "intake": "Fall 2026",
        "canonical_url": "https://web.cs.toronto.edu/graduate/mscac",
        "official_source_urls": [
            "https://web.cs.toronto.edu/graduate/mscac",
            "https://vectorinstitute.ai/scholarship/"
        ],
        "funding": {
            "funding_type": "Fully Funded",
            "coverage_description": "$17,500 CAD scholarship plus 8-month paid applied research internship ($35,000+ CAD)",
            "amount": 52500.0,
            "currency": "CAD",
            "tuition_covered": True
        },
        "deadline": "2026-12-01",
        "deadline_type": "Fixed",
        "deadline_verified": True,
        "admission_requirements": [
            {
                "criterion_type": "ACADEMIC_GRADE",
                "is_mandatory": True,
                "requirement_text": "B+ average in final 2 years of undergraduate study (equivalent to ~8.0/10.0 CGPA from recognized Indian institutions).",
                "official_equivalency_note": "PTU/NIT first class with distinction satisfied by 8.2 CGPA."
            },
            {
                "criterion_type": "LANGUAGE_TEST",
                "is_mandatory": True,
                "requirement_text": "IELTS 7.0 minimum with at least 6.5 in each band, or TOEFL iBT 93.",
                "official_equivalency_note": "Score required before unconditional offer."
            },
            {
                "criterion_type": "PREREQUISITE",
                "is_mandatory": True,
                "requirement_text": "Substantial background in Computer Science including data structures, algorithms, and linear algebra.",
                "official_equivalency_note": "Satisfied by B.Tech CS degree."
            }
        ],
        "scholarship_requirements": [
            {
                "criterion_type": "ACADEMIC_GRADE",
                "is_mandatory": True,
                "requirement_text": "First class standing and strong nomination from recognized AI faculty.",
                "official_equivalency_note": "Top tier applicant preference."
            }
        ]
    },
    {
        "id": "fix-tum-informatics-002",
        "title": "DAAD Helmut-Schmidt-Programme & Master of Science in Informatics",
        "program_name": "M.Sc. in Informatics (Artificial Intelligence & Software Engineering)",
        "university": "Technical University of Munich (TUM)",
        "country": "Germany",
        "degree_level": "Master's",
        "field": "Computer Science / Informatics",
        "intake": "Winter 2026 / Fall 2026",
        "canonical_url": "https://www.tum.de/en/studies/degree-programs/detail/informatics-master-of-science-msc",
        "official_source_urls": [
            "https://www.tum.de/en/studies/degree-programs/detail/informatics-master-of-science-msc",
            "https://www.daad.de/en/study-and-research-in-germany/scholarships/"
        ],
        "funding": {
            "funding_type": "Fully Funded",
            "coverage_description": "DAAD monthly stipend of €934, travel allowance, health insurance, zero tuition fee at TUM",
            "amount": 11200.0,
            "currency": "EUR",
            "tuition_covered": True
        },
        "deadline": "2026-05-31",
        "deadline_type": "Fixed",
        "deadline_verified": True,
        "admission_requirements": [
            {
                "criterion_type": "ACADEMIC_GRADE",
                "is_mandatory": True,
                "requirement_text": "Bachelor's degree in Computer Science with German grade equivalent 2.0 or better (approx. 7.5+ CGPA on 10-point scale).",
                "official_equivalency_note": "TUM Curricular Analysis required for Indian engineering degrees."
            },
            {
                "criterion_type": "LANGUAGE_TEST",
                "is_mandatory": True,
                "requirement_text": "English language proficiency certificate (IELTS min 6.5 or TOEFL min 88) for English-taught track.",
                "official_equivalency_note": "Planned IELTS meets criteria once completed."
            }
        ],
        "scholarship_requirements": [
            {
                "criterion_type": "CITIZENSHIP",
                "is_mandatory": True,
                "requirement_text": "Applicants must be from developing countries eligible for DAAD Helmut-Schmidt funding.",
                "official_equivalency_note": "DAC list eligibility."
            }
        ]
    },
    {
        "id": "fix-nus-mcomp-003",
        "title": "NUS Research Scholarship & Master of Computing (AI Specialization)",
        "program_name": "Master of Computing (Artificial Intelligence Specialisation) / Research",
        "university": "National University of Singapore (NUS)",
        "country": "Singapore",
        "degree_level": "Master's",
        "field": "Computer Science / Artificial Intelligence",
        "intake": "August 2026",
        "canonical_url": "https://www.comp.nus.edu.sg/programmes/pg/mcomp-ai/",
        "official_source_urls": [
            "https://www.comp.nus.edu.sg/programmes/pg/mcomp-ai/",
            "https://nusgs.nus.edu.sg/scholarships-award/"
        ],
        "funding": {
            "funding_type": "Fully Funded",
            "coverage_description": "Full tuition fee subsidy plus monthly research stipend of S$2,200 - S$2,800",
            "amount": 33600.0,
            "currency": "SGD",
            "tuition_covered": True
        },
        "deadline": "2026-02-01",
        "deadline_type": "Fixed",
        "deadline_verified": True,
        "admission_requirements": [
            {
                "criterion_type": "ACADEMIC_GRADE",
                "is_mandatory": True,
                "requirement_text": "Good honours degree (or 4-year bachelor's degree with minimum 80% / 8.0 CGPA) in Computing or related field.",
                "official_equivalency_note": "8.2 CGPA satisfies NUS minimum threshold."
            },
            {
                "criterion_type": "LANGUAGE_TEST",
                "is_mandatory": True,
                "requirement_text": "IELTS 6.5 or TOEFL 90 minimum for applicants from non-English medium institutions.",
                "official_equivalency_note": "Medium of instruction certificate or IELTS score."
            }
        ],
        "scholarship_requirements": [
            {
                "criterion_type": "ACADEMIC_GRADE",
                "is_mandatory": True,
                "requirement_text": "At least Second Class Upper Honours or CGPA 4.0/5.0 equivalent for research stipend eligibility.",
                "official_equivalency_note": "High academic distinction."
            }
        ]
    },
    {
        "id": "fix-singa-phd-004",
        "title": "Singapore International Graduate Award (A*STAR SINGA)",
        "program_name": "PhD in Computing and Information Sciences / AI Research",
        "university": "Agency for Science, Technology and Research (A*STAR) & NUS/NTU",
        "country": "Singapore",
        "degree_level": "PhD",
        "field": "Computer Science / AI",
        "intake": "August 2026",
        "canonical_url": "https://www.a-star.edu.sg/scholarships/for-graduate-studies/singapore-international-graduate-award-singa",
        "official_source_urls": [
            "https://www.a-star.edu.sg/scholarships/for-graduate-studies/singapore-international-graduate-award-singa"
        ],
        "funding": {
            "funding_type": "Fully Funded",
            "coverage_description": "Full tuition fees + monthly stipend of S$2,700 (increased to S$3,200 after qualifying exam) + airfare grant & settling-in allowance",
            "amount": 42000.0,
            "currency": "SGD",
            "tuition_covered": True
        },
        "deadline": "2026-06-01",
        "deadline_type": "Fixed",
        "deadline_verified": True,
        "admission_requirements": [
            {
                "criterion_type": "DEGREE_LEVEL",
                "is_mandatory": True,
                "requirement_text": "Open for graduates with a passion for research and excellent academic results. Seeking PhD degree directly.",
                "official_equivalency_note": "Student must intend PhD track."
            },
            {
                "criterion_type": "ACADEMIC_GRADE",
                "is_mandatory": True,
                "requirement_text": "Excellent academic results (First Class Honours or 8.0+ CGPA).",
                "official_equivalency_note": "8.2 CGPA satisfies condition."
            }
        ],
        "scholarship_requirements": [
            {
                "criterion_type": "PREREQUISITE",
                "is_mandatory": True,
                "requirement_text": "Strong reports from two academic referees detailing research aptitude.",
                "official_equivalency_note": "Two academic recommendations required."
            }
        ]
    },
    {
        "id": "fix-ubc-msc-005",
        "title": "University of British Columbia International Graduate Tuition Award & MSc CS",
        "program_name": "Master of Science in Computer Science",
        "university": "University of British Columbia (UBC)",
        "country": "Canada",
        "degree_level": "Master's",
        "field": "Computer Science",
        "intake": "September 2026",
        "canonical_url": "https://www.cs.ubc.ca/students/grad/prospective/degree-programs/msc-program",
        "official_source_urls": [
            "https://www.cs.ubc.ca/students/grad/prospective/degree-programs/msc-program",
            "https://www.grad.ubc.ca/awards/international-tuition-award"
        ],
        "funding": {
            "funding_type": "Fully Funded",
            "coverage_description": "Guaranteed minimum funding package of $28,000 CAD/year (Teaching/Research Assistantship + International Tuition Award)",
            "amount": 28000.0,
            "currency": "CAD",
            "tuition_covered": True
        },
        "deadline": "2026-12-15",
        "deadline_type": "Fixed",
        "deadline_verified": True,
        "admission_requirements": [
            {
                "criterion_type": "ACADEMIC_GRADE",
                "is_mandatory": True,
                "requirement_text": "Minimum overall B+ average (76% at UBC) or 8.0/10 CGPA for Tier-1 Indian engineering institutions.",
                "official_equivalency_note": "8.2 CGPA fulfills published tier requirements."
            },
            {
                "criterion_type": "LANGUAGE_TEST",
                "is_mandatory": True,
                "requirement_text": "TOEFL iBT 100 or IELTS 7.0 overall with no component under 6.5.",
                "official_equivalency_note": "Planned IELTS."
            }
        ],
        "scholarship_requirements": []
    },
    {
        "id": "fix-ntu-msai-006",
        "title": "NTU Research Scholarship & Master of Science in Artificial Intelligence",
        "program_name": "Master of Science in Artificial Intelligence (MSAI)",
        "university": "Nanyang Technological University (NTU)",
        "country": "Singapore",
        "degree_level": "Master's",
        "field": "Artificial Intelligence",
        "intake": "August 2026",
        "canonical_url": "https://www.ntu.edu.sg/scse/admissions/programmes/detail/master-of-science-in-artificial-intelligence",
        "official_source_urls": [
            "https://www.ntu.edu.sg/scse/admissions/programmes/detail/master-of-science-in-artificial-intelligence",
            "https://www.ntu.edu.sg/admissions/graduate/financialmatters/scholarships"
        ],
        "funding": {
            "funding_type": "Tuition Waiver & Stipend",
            "coverage_description": "Ministry of Education (MOE) Service Obligation tuition subsidy + S$2,000/month research stipend",
            "amount": 28000.0,
            "currency": "SGD",
            "tuition_covered": True
        },
        "deadline": "2026-01-31",
        "deadline_type": "Fixed",
        "deadline_verified": True,
        "admission_requirements": [
            {"criterion_type": "ACADEMIC_GRADE", "is_mandatory": True, "requirement_text": "Good bachelor's degree in Computer Science, Data Science, or related STEM discipline.", "official_equivalency_note": "8.2 CGPA satisfies entry requirement."},
            {"criterion_type": "LANGUAGE_TEST", "is_mandatory": True, "requirement_text": "IELTS 6.5 or TOEFL 100 for graduates of non-English universities.", "official_equivalency_note": "Required."}
        ],
        "scholarship_requirements": []
    },
    {
        "id": "fix-mcgill-msc-007",
        "title": "McGill University Graduate Excellence Award & MSc Computer Science",
        "program_name": "M.Sc. in Computer Science (Thesis track / Machine Learning)",
        "university": "McGill University",
        "country": "Canada",
        "degree_level": "Master's",
        "field": "Computer Science",
        "intake": "Fall 2026",
        "canonical_url": "https://www.cs.mcgill.ca/academic/graduate/program/msc/",
        "official_source_urls": [
            "https://www.cs.mcgill.ca/academic/graduate/program/msc/",
            "https://www.mcgill.ca/gps/funding/opportunities"
        ],
        "funding": {
            "funding_type": "Fully Funded",
            "coverage_description": "Minimum guaranteed departmental stipend of $23,000 CAD/year plus international fee supplements",
            "amount": 25000.0,
            "currency": "CAD",
            "tuition_covered": True
        },
        "deadline": "2026-01-01",
        "deadline_type": "Fixed",
        "deadline_verified": True,
        "admission_requirements": [
            {"criterion_type": "ACADEMIC_GRADE", "is_mandatory": True, "requirement_text": "Minimum CGPA of 3.2/4.0 in undergraduate degree (approx. 7.8/10.0 in Indian grading system).", "official_equivalency_note": "8.2 CGPA exceeds threshold."},
            {"criterion_type": "LANGUAGE_TEST", "is_mandatory": True, "requirement_text": "TOEFL 86 (minimum 20 in each section) or IELTS 6.5 overall.", "official_equivalency_note": "Required."}
        ],
        "scholarship_requirements": []
    },
    {
        "id": "fix-kit-informatics-008",
        "title": "Karlsruhe Institute of Technology (KIT) Master in Informatics & DAAD Study Scholarship",
        "program_name": "Master of Science in Informatics",
        "university": "Karlsruhe Institute of Technology (KIT)",
        "country": "Germany",
        "degree_level": "Master's",
        "field": "Informatics / Computer Science",
        "intake": "Winter 2026",
        "canonical_url": "https://www.informatik.kit.edu/english/master.php",
        "official_source_urls": [
            "https://www.informatik.kit.edu/english/master.php",
            "https://www.daad.de"
        ],
        "funding": {
            "funding_type": "Stipend & Fee Relief",
            "coverage_description": "DAAD Graduate Grant (€934/month) + State waiver for academic excellence",
            "amount": 11200.0,
            "currency": "EUR",
            "tuition_covered": True
        },
        "deadline": "2026-07-15",
        "deadline_type": "Fixed",
        "deadline_verified": True,
        "admission_requirements": [
            {"criterion_type": "ACADEMIC_GRADE", "is_mandatory": True, "requirement_text": "Bachelor in Computer Science with strong theoretical computer science foundation (30+ ECTS in math/algorithms).", "official_equivalency_note": "B.Tech Computer Science curriculum meets ECTS mapping."},
            {"criterion_type": "LANGUAGE_TEST", "is_mandatory": True, "requirement_text": "English CEFR level B2/C1 (IELTS 6.5 or TOEFL 90).", "official_equivalency_note": "Standard test requirement."}
        ],
        "scholarship_requirements": []
    },
    {
        "id": "fix-sfu-bigdata-009",
        "title": "Simon Fraser University (SFU) Graduate Fellowship & Professional Master of Science in Big Data & AI",
        "program_name": "Professional Master of Science in Computer Science (Big Data & AI Concentration)",
        "university": "Simon Fraser University",
        "country": "Canada",
        "degree_level": "Master's",
        "field": "Artificial Intelligence / Big Data",
        "intake": "Fall 2026",
        "canonical_url": "https://www.sfu.ca/computing/prospective-students/graduate-students/programs/professional-masters-programs.html",
        "official_source_urls": [
            "https://www.sfu.ca/computing/prospective-students/graduate-students/programs/professional-masters-programs.html"
        ],
        "funding": {
            "funding_type": "Partial Tuition & Co-op",
            "coverage_description": "$7,000 CAD entrance scholarship + 4-month mandatory paid co-op placement ($18,000+ CAD)",
            "amount": 25000.0,
            "currency": "CAD",
            "tuition_covered": False
        },
        "deadline": "2026-02-15",
        "deadline_type": "Fixed",
        "deadline_verified": True,
        "admission_requirements": [
            {"criterion_type": "ACADEMIC_GRADE", "is_mandatory": True, "requirement_text": "Cumulative GPA of at least 3.0/4.33 (approx 7.2/10.0) in computing science or related field.", "official_equivalency_note": "8.2 CGPA strongly satisfies requirement."},
            {"criterion_type": "LANGUAGE_TEST", "is_mandatory": True, "requirement_text": "IELTS 7.0 overall with min 6.5 in all bands.", "official_equivalency_note": "Planned."}
        ],
        "scholarship_requirements": []
    },
    {
        "id": "fix-waterloo-mmath-010",
        "title": "University of Waterloo Master of Mathematics in Computer Science & Research Assistantship",
        "program_name": "MMath in Computer Science",
        "university": "University of Waterloo",
        "country": "Canada",
        "degree_level": "Master's",
        "field": "Computer Science",
        "intake": "Fall 2026",
        "canonical_url": "https://cs.uwaterloo.ca/current-graduate-students/degree-programs/master-mathematics-computer-science",
        "official_source_urls": [
            "https://cs.uwaterloo.ca/current-graduate-students/degree-programs/master-mathematics-computer-science",
            "https://uwaterloo.ca/graduate-studies-postdoctoral-affairs/awards"
        ],
        "funding": {
            "funding_type": "Fully Funded",
            "coverage_description": "Minimum guaranteed financial support of $27,000 CAD/year (Graduate Research Studentship + Teaching Assistantship)",
            "amount": 27000.0,
            "currency": "CAD",
            "tuition_covered": True
        },
        "deadline": "2026-12-15",
        "deadline_type": "Fixed",
        "deadline_verified": True,
        "admission_requirements": [
            {"criterion_type": "ACADEMIC_GRADE", "is_mandatory": True, "requirement_text": "78% overall standing in 4-year honours bachelor's degree in Computer Science (equivalent to ~8.0 CGPA).", "official_equivalency_note": "8.2 CGPA meets standing requirement."},
            {"criterion_type": "LANGUAGE_TEST", "is_mandatory": True, "requirement_text": "IELTS 7.5 or TOEFL 100 with 26 writing/speaking.", "official_equivalency_note": "Requires high language test band."}
        ],
        "scholarship_requirements": []
    }
]

# Backwards-compatible alias for existing tests and evaluation harnesses
REAL_OPPORTUNITIES_BASE = CANONICAL_FIXTURE_OPPORTUNITIES


def get_fixture_raw_opportunities(countries: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Returns a copy of canonical fixture dictionaries, optionally filtered by country."""
    if not countries:
        return [dict(item) for item in CANONICAL_FIXTURE_OPPORTUNITIES]
    return [dict(item) for item in CANONICAL_FIXTURE_OPPORTUNITIES if item.get("country") in countries]


def get_fixture_opportunity_models(
    run_id: str = "fixture-run",
    countries: Optional[List[str]] = None
) -> List[Opportunity]:
    """Builds and returns genuine Opportunity pydantic model instances from test fixtures."""
    raw_list = get_fixture_raw_opportunities(countries)
    models: List[Opportunity] = []
    now_dt = datetime.now(timezone.utc)
    now_iso = now_dt.isoformat()

    for raw in raw_list:
        opp_id = raw.get("id") or str(uuid.uuid4())
        funding_data = raw.get("funding", {})
        funding = FundingDetails(
            funding_type=funding_data.get("funding_type", "Unknown"),
            coverage_description=funding_data.get("coverage_description", "Unspecified"),
            amount=funding_data.get("amount"),
            currency=funding_data.get("currency"),
            tuition_covered=funding_data.get("tuition_covered", False)
        )

        adm_reqs = [
            EligibilityCriterion(
                criterion_type=req.get("criterion_type", "PREREQUISITE"),
                is_mandatory=req.get("is_mandatory", True),
                requirement_text=req.get("requirement_text", ""),
                official_equivalency_note=req.get("official_equivalency_note")
            )
            for req in raw.get("admission_requirements", [])
        ]

        sch_reqs = [
            EligibilityCriterion(
                criterion_type=req.get("criterion_type", "PREREQUISITE"),
                is_mandatory=req.get("is_mandatory", False),
                requirement_text=req.get("requirement_text", ""),
                official_equivalency_note=req.get("official_equivalency_note")
            )
            for req in raw.get("scholarship_requirements", [])
        ]

        evidence_records = [
            EvidenceRecord(
                id=str(uuid.uuid4()),
                opportunity_id=opp_id,
                run_id=run_id,
                criterion_name=req.criterion_type,
                stated_requirement=req.requirement_text,
                student_value="Satisfies published requirements",
                status="MEETS",
                evidence_excerpt=f"Requirement verified: {req.requirement_text}",
                source_title=f"{raw.get('university')} Official Admissions",
                source_url=raw.get("canonical_url", ""),
                source_category="OFFICIAL",
                checked_at=now_dt
            )
            for req in adm_reqs + sch_reqs
        ]

        opp = Opportunity(
            id=opp_id,
            run_id=run_id,
            canonical_url=raw.get("canonical_url", ""),
            title=raw.get("title", ""),
            program_name=raw.get("program_name", ""),
            university=raw.get("university", ""),
            country=raw.get("country", ""),
            degree_level=raw.get("degree_level", "Master's"),
            field=raw.get("field", "Computer Science"),
            intake=raw.get("intake"),
            admission_requirements=adm_reqs,
            scholarship_requirements=sch_reqs,
            funding_details=funding,
            deadline=raw.get("deadline"),
            deadline_type=raw.get("deadline_type", "Fixed"),
            deadline_verified=raw.get("deadline_verified", True),
            official_application_url=raw.get("canonical_url"),
            official_source_urls=raw.get("official_source_urls", [raw.get("canonical_url")]),
            source_retrieval_timestamps={u: now_iso for u in raw.get("official_source_urls", [raw.get("canonical_url")])},
            evidence_quality="OFFICIAL",
            eligibility_status="MEETS_STATED_CRITERIA",
            eligibility_reasons=["Meets academic requirements based on official fixture."],
            actionable_gaps=[],
            evidence_records=evidence_records,
            created_at=now_dt
        )
        models.append(opp)

    return models


def get_mock_discovery_response(countries: Optional[List[str]] = None) -> Dict[str, Any]:
    """Mock Gemini Search Grounding discovery response backed by canonical fixtures."""
    fixtures = get_fixture_raw_opportunities(countries)
    sources = [{"title": f["title"], "url": f["canonical_url"]} for f in fixtures]
    candidates = [
        {
            "program_name": f["program_name"],
            "university": f["university"],
            "country": f["country"],
            "canonical_url": f["canonical_url"],
            "degree_level": f["degree_level"],
            "field": f["field"],
            "funding_snippet": f["funding"].get("coverage_description", ""),
            "requirements_snippet": f["admission_requirements"][0]["requirement_text"] if f["admission_requirements"] else "",
            "deadline_snippet": f.get("deadline", "Unknown")
        }
        for f in fixtures
    ]
    return {
        "success": True,
        "text": "Discovered accredited university programs matching query.",
        "candidates": candidates,
        "sources": sources,
        "citations": sources,
        "search_queries": [f"official graduate scholarships {c}" for c in (countries or ["Canada"])],
        "model_used": "gemini-2.5-flash"
    }


def get_mock_url_analysis_response(url: str) -> Dict[str, Any]:
    """Mock Gemini URL Context extraction response backed by canonical fixtures."""
    matched = None
    for f in CANONICAL_FIXTURE_OPPORTUNITIES:
        if f["canonical_url"] == url or url in f.get("official_source_urls", []):
            matched = f
            break
    if not matched and CANONICAL_FIXTURE_OPPORTUNITIES:
        matched = CANONICAL_FIXTURE_OPPORTUNITIES[0]

    return {
        "success": True,
        "data": {
            "program_name": matched["program_name"],
            "university": matched["university"],
            "country": matched["country"],
            "degree_level": matched["degree_level"],
            "field": matched["field"],
            "funding_details": matched["funding"],
            "deadline": matched["deadline"],
            "deadline_type": matched["deadline_type"],
            "deadline_verified": matched["deadline_verified"],
            "overall_eligibility_status": "MEETS_STATED_CRITERIA",
            "eligibility_reasons": ["Verified criteria from official portal."],
            "actionable_gaps": [],
            "admission_requirements": [
                {
                    "criterion_name": req.get("criterion_type", "PREREQUISITE"),
                    "stated_requirement": req.get("requirement_text", ""),
                    "student_value": "Meets criteria",
                    "status": "MEETS",
                    "evidence_excerpt": req.get("requirement_text", ""),
                    "source_url": matched["canonical_url"]
                }
                for req in matched.get("admission_requirements", [])
            ],
            "scholarship_requirements": [
                {
                    "criterion_name": req.get("criterion_type", "PREREQUISITE"),
                    "stated_requirement": req.get("requirement_text", ""),
                    "student_value": "Meets scholarship criteria",
                    "status": "MEETS",
                    "evidence_excerpt": req.get("requirement_text", ""),
                    "source_url": matched["canonical_url"]
                }
                for req in matched.get("scholarship_requirements", [])
            ]
        },
        "retrieval_metadata": [
            {
                "retrieved_url": url,
                "url_retrieval_status": "URL_RETRIEVAL_STATUS_SUCCESS",
                "is_success": True
            }
        ],
        "url_retrieval_statuses": {url: "URL_RETRIEVAL_STATUS_SUCCESS"},
        "is_retrieval_successful": True,
        "retrieval_status": "URL_RETRIEVAL_STATUS_SUCCESS",
        "evidence_quality": "OFFICIAL",
        "model_used": "gemini-2.5-flash"
    }
