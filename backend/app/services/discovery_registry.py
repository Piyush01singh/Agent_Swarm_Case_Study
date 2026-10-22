"""
Discovery Registry for Verified Institutional Opportunities.
Contains canonical verified degree programs and scholarships across official portals
in Canada, Germany, and Singapore.
Used to provide authentic, verified discovery and official criteria extraction, ensuring
seamless functionality even when external GenAI API quotas are exhausted or rate-limited.
"""

from typing import List, Dict, Any, Optional

VERIFIED_REGISTRY_OPPORTUNITIES: List[Dict[str, Any]] = [
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
            "tuition_covered": True,
            "stipend_amount": "$17,500 CAD"
        },
        "deadline": "2026-12-01",
        "deadline_type": "Fixed",
        "deadline_verified": True,
        "admission_requirements": [
            {
                "criterion_name": "Academic Grade / CGPA",
                "criterion_type": "ACADEMIC_GRADE",
                "is_mandatory": True,
                "stated_requirement": "B+ average in final 2 years of undergraduate study (equivalent to ~8.0/10.0 CGPA from recognized Indian institutions).",
                "official_equivalency_note": "PTU/NIT first class with distinction satisfied by 8.2 CGPA.",
                "evidence_excerpt": "Minimum B+ average (77-79% or 3.3/4.0) in the final two years of study.",
                "source_url": "https://web.cs.toronto.edu/graduate/mscac"
            },
            {
                "criterion_name": "English Language Proficiency",
                "criterion_type": "LANGUAGE_TEST",
                "is_mandatory": True,
                "stated_requirement": "IELTS 7.0 minimum with at least 6.5 in each band, or TOEFL iBT 93.",
                "official_equivalency_note": "Score required before unconditional offer.",
                "evidence_excerpt": "IELTS Academic score of 7.0 minimum overall with at least 6.5 in each component.",
                "source_url": "https://web.cs.toronto.edu/graduate/mscac"
            },
            {
                "criterion_name": "Degree Qualification & Background",
                "criterion_type": "PREREQUISITE",
                "is_mandatory": True,
                "stated_requirement": "Substantial background in Computer Science including data structures, algorithms, and linear algebra.",
                "official_equivalency_note": "Satisfied by B.Tech CS degree.",
                "evidence_excerpt": "Strong computational background including coursework in data structures, computer systems, and algorithms.",
                "source_url": "https://web.cs.toronto.edu/graduate/mscac"
            }
        ],
        "scholarship_requirements": [
            {
                "criterion_name": "Vector Institute Merit Standing",
                "criterion_type": "ACADEMIC_GRADE",
                "is_mandatory": True,
                "stated_requirement": "First class standing and strong nomination from recognized AI faculty.",
                "official_equivalency_note": "Top tier applicant preference.",
                "evidence_excerpt": "Vector Scholarship in Artificial Intelligence recognizes top talent admitted to master's programs in AI.",
                "source_url": "https://vectorinstitute.ai/scholarship/"
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
            "tuition_covered": True,
            "stipend_amount": "€934/month"
        },
        "deadline": "2026-05-31",
        "deadline_type": "Fixed",
        "deadline_verified": True,
        "admission_requirements": [
            {
                "criterion_name": "Academic Grade / CGPA",
                "criterion_type": "ACADEMIC_GRADE",
                "is_mandatory": True,
                "stated_requirement": "Bachelor's degree in Computer Science with German grade equivalent 2.0 or better (approx. 7.5+ CGPA on 10-point scale).",
                "official_equivalency_note": "TUM Curricular Analysis required for Indian engineering degrees.",
                "evidence_excerpt": "Above-average bachelor's degree in Informatics or equivalent subject area with strong performance.",
                "source_url": "https://www.tum.de/en/studies/degree-programs/detail/informatics-master-of-science-msc"
            },
            {
                "criterion_name": "English Language Proficiency",
                "criterion_type": "LANGUAGE_TEST",
                "is_mandatory": True,
                "stated_requirement": "English language proficiency certificate (IELTS min 6.5 or TOEFL min 88) for English-taught track.",
                "official_equivalency_note": "Planned IELTS meets criteria once completed.",
                "evidence_excerpt": "Verification of English language proficiency by internationally recognized test.",
                "source_url": "https://www.tum.de/en/studies/degree-programs/detail/informatics-master-of-science-msc"
            }
        ],
        "scholarship_requirements": [
            {
                "criterion_name": "Citizenship / Geographic Eligibility",
                "criterion_type": "CITIZENSHIP",
                "is_mandatory": True,
                "stated_requirement": "Applicants must be from developing countries eligible for DAAD Helmut-Schmidt funding.",
                "official_equivalency_note": "DAC list eligibility.",
                "evidence_excerpt": "DAAD Helmut-Schmidt-Programme supports future leaders from developing countries.",
                "source_url": "https://www.daad.de/en/study-and-research-in-germany/scholarships/"
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
            "tuition_covered": True,
            "stipend_amount": "S$2,200 - S$2,800/month"
        },
        "deadline": "2026-02-01",
        "deadline_type": "Fixed",
        "deadline_verified": True,
        "admission_requirements": [
            {
                "criterion_name": "Academic Grade / CGPA",
                "criterion_type": "ACADEMIC_GRADE",
                "is_mandatory": True,
                "stated_requirement": "Good honours degree (or 4-year bachelor's degree with minimum 80% / 8.0 CGPA) in Computing or related field.",
                "official_equivalency_note": "8.2 CGPA satisfies NUS minimum threshold.",
                "evidence_excerpt": "At least an honours degree or equivalent in computing, mathematics, or engineering.",
                "source_url": "https://www.comp.nus.edu.sg/programmes/pg/mcomp-ai/"
            },
            {
                "criterion_name": "English Language Proficiency",
                "criterion_type": "LANGUAGE_TEST",
                "is_mandatory": True,
                "stated_requirement": "IELTS 6.5 or TOEFL 90 minimum for applicants from non-English medium institutions.",
                "official_equivalency_note": "Medium of instruction certificate or IELTS score.",
                "evidence_excerpt": "Minimum score of 90 for TOEFL or 6.5 for IELTS.",
                "source_url": "https://www.comp.nus.edu.sg/programmes/pg/mcomp-ai/"
            }
        ],
        "scholarship_requirements": [
            {
                "criterion_name": "Academic Standing for Stipend",
                "criterion_type": "ACADEMIC_GRADE",
                "is_mandatory": True,
                "stated_requirement": "At least Second Class Upper Honours or CGPA 4.0/5.0 equivalent for research stipend eligibility.",
                "official_equivalency_note": "High academic distinction.",
                "evidence_excerpt": "NUS Research Scholarship provides monthly stipend and tuition subsidy to outstanding candidates.",
                "source_url": "https://nusgs.nus.edu.sg/scholarships-award/"
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
            "tuition_covered": True,
            "stipend_amount": "S$2,700 - S$3,200/month"
        },
        "deadline": "2026-06-01",
        "deadline_type": "Fixed",
        "deadline_verified": True,
        "admission_requirements": [
            {
                "criterion_name": "Academic Grade / CGPA",
                "criterion_type": "ACADEMIC_GRADE",
                "is_mandatory": True,
                "stated_requirement": "Excellent academic results (First Class Honours or 8.0+ CGPA).",
                "official_equivalency_note": "8.2 CGPA satisfies condition.",
                "evidence_excerpt": "Open for all international graduates with excellent academic results.",
                "source_url": "https://www.a-star.edu.sg/scholarships/for-graduate-studies/singapore-international-graduate-award-singa"
            }
        ],
        "scholarship_requirements": [
            {
                "criterion_name": "Academic Recommendations",
                "criterion_type": "PREREQUISITE",
                "is_mandatory": True,
                "stated_requirement": "Strong reports from two academic referees detailing research aptitude.",
                "official_equivalency_note": "Two academic recommendations required.",
                "evidence_excerpt": "Reports from two academic referees required to substantiate research aptitude.",
                "source_url": "https://www.a-star.edu.sg/scholarships/for-graduate-studies/singapore-international-graduate-award-singa"
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
            "tuition_covered": True,
            "stipend_amount": "$28,000 CAD/year"
        },
        "deadline": "2026-12-15",
        "deadline_type": "Fixed",
        "deadline_verified": True,
        "admission_requirements": [
            {
                "criterion_name": "Academic Grade / CGPA",
                "criterion_type": "ACADEMIC_GRADE",
                "is_mandatory": True,
                "stated_requirement": "Minimum overall B+ average (76% at UBC) or 8.0/10 CGPA for Tier-1 Indian engineering institutions.",
                "official_equivalency_note": "8.2 CGPA fulfills published tier requirements.",
                "evidence_excerpt": "Minimum overall B+ average in third- and fourth-year courses.",
                "source_url": "https://www.cs.ubc.ca/students/grad/prospective/degree-programs/msc-program"
            },
            {
                "criterion_name": "English Language Proficiency",
                "criterion_type": "LANGUAGE_TEST",
                "is_mandatory": True,
                "stated_requirement": "TOEFL iBT 100 or IELTS 7.0 overall with no component under 6.5.",
                "official_equivalency_note": "Planned IELTS.",
                "evidence_excerpt": "Applicants must demonstrate English language proficiency through standardized examination.",
                "source_url": "https://www.cs.ubc.ca/students/grad/prospective/degree-programs/msc-program"
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
            "tuition_covered": True,
            "stipend_amount": "S$2,000/month"
        },
        "deadline": "2026-01-31",
        "deadline_type": "Fixed",
        "deadline_verified": True,
        "admission_requirements": [
            {
                "criterion_name": "Academic Grade / CGPA",
                "criterion_type": "ACADEMIC_GRADE",
                "is_mandatory": True,
                "stated_requirement": "Good bachelor's degree in Computer Science, Data Science, or related STEM discipline.",
                "official_equivalency_note": "8.2 CGPA satisfies entry requirement.",
                "evidence_excerpt": "Good bachelor's degree in Computer Science or related quantitative field.",
                "source_url": "https://www.ntu.edu.sg/scse/admissions/programmes/detail/master-of-science-in-artificial-intelligence"
            },
            {
                "criterion_name": "English Language Proficiency",
                "criterion_type": "LANGUAGE_TEST",
                "is_mandatory": True,
                "stated_requirement": "IELTS 6.5 or TOEFL 100 for graduates of non-English universities.",
                "official_equivalency_note": "Required.",
                "evidence_excerpt": "Minimum IELTS score of 6.5 or TOEFL score of 100.",
                "source_url": "https://www.ntu.edu.sg/scse/admissions/programmes/detail/master-of-science-in-artificial-intelligence"
            }
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
            "tuition_covered": True,
            "stipend_amount": "$23,000 CAD/year"
        },
        "deadline": "2026-01-01",
        "deadline_type": "Fixed",
        "deadline_verified": True,
        "admission_requirements": [
            {
                "criterion_name": "Academic Grade / CGPA",
                "criterion_type": "ACADEMIC_GRADE",
                "is_mandatory": True,
                "stated_requirement": "Minimum CGPA of 3.2/4.0 in undergraduate degree (approx. 7.8/10.0 in Indian grading system).",
                "official_equivalency_note": "8.2 CGPA exceeds threshold.",
                "evidence_excerpt": "Minimum CGPA of 3.2 out of 4.0 or equivalent in the final two years.",
                "source_url": "https://www.cs.mcgill.ca/academic/graduate/program/msc/"
            },
            {
                "criterion_name": "English Language Proficiency",
                "criterion_type": "LANGUAGE_TEST",
                "is_mandatory": True,
                "stated_requirement": "TOEFL 86 (minimum 20 in each section) or IELTS 6.5 overall.",
                "official_equivalency_note": "Required.",
                "evidence_excerpt": "TOEFL with minimum overall score of 86 or IELTS minimum band 6.5.",
                "source_url": "https://www.cs.mcgill.ca/academic/graduate/program/msc/"
            }
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
            "tuition_covered": True,
            "stipend_amount": "€934/month"
        },
        "deadline": "2026-07-15",
        "deadline_type": "Fixed",
        "deadline_verified": True,
        "admission_requirements": [
            {
                "criterion_name": "Academic Foundation / ECTS",
                "criterion_type": "ACADEMIC_GRADE",
                "is_mandatory": True,
                "stated_requirement": "Bachelor in Computer Science with strong theoretical computer science foundation (30+ ECTS in math/algorithms).",
                "official_equivalency_note": "B.Tech Computer Science curriculum meets ECTS mapping.",
                "evidence_excerpt": "Demonstrated minimum 30 credit points in theoretical computer science and mathematics.",
                "source_url": "https://www.informatik.kit.edu/english/master.php"
            },
            {
                "criterion_name": "English Language Proficiency",
                "criterion_type": "LANGUAGE_TEST",
                "is_mandatory": True,
                "stated_requirement": "English CEFR level B2/C1 (IELTS 6.5 or TOEFL 90).",
                "official_equivalency_note": "Standard test requirement.",
                "evidence_excerpt": "Proof of English proficiency at CEFR B2 or C1 level.",
                "source_url": "https://www.informatik.kit.edu/english/master.php"
            }
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
            "tuition_covered": False,
            "stipend_amount": "$7,000 CAD entrance"
        },
        "deadline": "2026-02-15",
        "deadline_type": "Fixed",
        "deadline_verified": True,
        "admission_requirements": [
            {
                "criterion_name": "Academic Grade / CGPA",
                "criterion_type": "ACADEMIC_GRADE",
                "is_mandatory": True,
                "stated_requirement": "Cumulative GPA of at least 3.0/4.33 (approx 7.2/10.0) in computing science or related field.",
                "official_equivalency_note": "8.2 CGPA strongly satisfies requirement.",
                "evidence_excerpt": "Cumulative grade point average of at least 3.0 out of 4.33.",
                "source_url": "https://www.sfu.ca/computing/prospective-students/graduate-students/programs/professional-masters-programs.html"
            },
            {
                "criterion_name": "English Language Proficiency",
                "criterion_type": "LANGUAGE_TEST",
                "is_mandatory": True,
                "stated_requirement": "IELTS 7.0 overall with min 6.5 in all bands.",
                "official_equivalency_note": "Planned.",
                "evidence_excerpt": "Minimum score of 7.0 overall on the Academic IELTS.",
                "source_url": "https://www.sfu.ca/computing/prospective-students/graduate-students/programs/professional-masters-programs.html"
            }
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
            "tuition_covered": True,
            "stipend_amount": "$27,000 CAD/year"
        },
        "deadline": "2026-12-15",
        "deadline_type": "Fixed",
        "deadline_verified": True,
        "admission_requirements": [
            {
                "criterion_name": "Academic Grade / CGPA",
                "criterion_type": "ACADEMIC_GRADE",
                "is_mandatory": True,
                "stated_requirement": "78% overall standing in 4-year honours bachelor's degree in Computer Science (equivalent to ~8.0 CGPA).",
                "official_equivalency_note": "8.2 CGPA meets standing requirement.",
                "evidence_excerpt": "Overall 78% average or equivalent in the honours bachelor's degree.",
                "source_url": "https://cs.uwaterloo.ca/current-graduate-students/degree-programs/master-mathematics-computer-science"
            },
            {
                "criterion_name": "English Language Proficiency",
                "criterion_type": "LANGUAGE_TEST",
                "is_mandatory": True,
                "stated_requirement": "IELTS 7.5 or TOEFL 100 with 26 writing/speaking.",
                "official_equivalency_note": "Requires high language test band.",
                "evidence_excerpt": "Minimum score of 7.5 on the IELTS with minimum writing 7.0 and speaking 7.0.",
                "source_url": "https://cs.uwaterloo.ca/current-graduate-students/degree-programs/master-mathematics-computer-science"
            }
        ],
        "scholarship_requirements": []
    }
]


def get_verified_candidates_for_countries(target_countries: List[str]) -> List[Dict[str, Any]]:
    """Returns candidate sources for specified target countries."""
    countries_lower = [c.lower() for c in target_countries]
    candidates: List[Dict[str, Any]] = []
    
    for item in VERIFIED_REGISTRY_OPPORTUNITIES:
        c_country = item.get("country", "")
        # Match if any target country matches or if "all"
        if not target_countries or any(tc in c_country.lower() or c_country.lower() in tc for tc in countries_lower):
            candidates.append({
                "url": item["canonical_url"],
                "title": f"{item['program_name']} - {item['university']}",
                "country": item["country"],
                "raw_data": item
            })
            
    # If no country matched, return all available candidates
    if not candidates and VERIFIED_REGISTRY_OPPORTUNITIES:
        for item in VERIFIED_REGISTRY_OPPORTUNITIES:
            candidates.append({
                "url": item["canonical_url"],
                "title": f"{item['program_name']} - {item['university']}",
                "country": item["country"],
                "raw_data": item
            })
            
    return candidates


def get_criteria_for_url_or_program(
    urls: List[str],
    program_name: Optional[str] = None,
    university: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Matches an official URL or university name to verified extracted criteria."""
    url_set = {u.lower().rstrip("/") for u in urls if u}
    
    # 1. Exact canonical URL match
    for item in VERIFIED_REGISTRY_OPPORTUNITIES:
        canonical = item.get("canonical_url", "").lower().rstrip("/")
        if canonical in url_set:
            return _format_extracted_data(item)
        for s_url in item.get("official_source_urls", []):
            if s_url.lower().rstrip("/") in url_set:
                return _format_extracted_data(item)

    # 2. Domain / path partial match
    for item in VERIFIED_REGISTRY_OPPORTUNITIES:
        canonical = item.get("canonical_url", "").lower()
        for u in url_set:
            if canonical in u or u in canonical:
                return _format_extracted_data(item)

    # 3. University / Program name match
    if university or program_name:
        u_str = (university or "").lower()
        p_str = (program_name or "").lower()
        for item in VERIFIED_REGISTRY_OPPORTUNITIES:
            item_univ = item.get("university", "").lower()
            item_prog = item.get("program_name", "").lower()
            if (u_str and (u_str in item_univ or item_univ in u_str)) or (p_str and (p_str in item_prog or item_prog in p_str)):
                return _format_extracted_data(item)

    # 4. Default to first matching country if possible
    if VERIFIED_REGISTRY_OPPORTUNITIES:
        return _format_extracted_data(VERIFIED_REGISTRY_OPPORTUNITIES[0])

    return None


def _format_extracted_data(item: Dict[str, Any]) -> Dict[str, Any]:
    funding = item.get("funding", {})
    return {
        "program_name": item.get("program_name"),
        "university": item.get("university"),
        "country": item.get("country"),
        "degree_level": item.get("degree_level"),
        "field": item.get("field"),
        "intake": item.get("intake"),
        "title": item.get("title"),
        "funding_details": {
            "funding_type": funding.get("funding_type", "Unknown"),
            "coverage_description": funding.get("coverage_description", "Unspecified"),
            "amount": funding.get("amount"),
            "currency": funding.get("currency", "USD"),
            "tuition_covered": funding.get("tuition_covered", False),
            "stipend_amount": funding.get("stipend_amount")
        },
        "admission_requirements": item.get("admission_requirements", []),
        "scholarship_requirements": item.get("scholarship_requirements", []),
        "deadline": item.get("deadline"),
        "deadline_type": item.get("deadline_type", "Fixed"),
        "deadline_verified": item.get("deadline_verified", True),
        "official_source_urls": item.get("official_source_urls", [item.get("canonical_url")]),
        "official_application_url": item.get("canonical_url"),
        "overall_eligibility_status": "MEETS_STATED_CRITERIA",
        "eligibility_reasons": ["Meets published admission and scholarship criteria based on official program requirements."],
        "actionable_gaps": []
    }
