# TEST_INFRA — Dual-Track E2E Testing Infrastructure

## 1. Test Philosophy

The ScholarSwarm End-to-End (E2E) Testing Track adheres to strict opaque-box verification standards, treating the backend API and agent workflow as an integrated, multi-tier system. The core tenets are:

1. **Opaque-Box Boundary Integrity**:
   - Tests execute against public REST endpoints (`/api/research/*`, `/api/opportunities/*`, `/api/profile/*`) and LangGraph state graph boundaries (`swarm_app.ainvoke`).
   - Tests inspect observable outputs, HTTP status codes, structured JSON responses, Pydantic data models, and event streams rather than asserting private internal helper states.

2. **Authoritative Expected Output Derivation**:
   - Every test case derives its assertions from documented requirements (`ORIGINAL_REQUEST.md`, `PROJECT.md`) and verified educational portal criteria.
   - Zero tolerance for synthetic placeholders or fabricated quotes. All official excerpts, eligibility rules, and funding amounts mirror genuine published standards.

3. **Deterministic & Reproducible Dual-Mode Operation**:
   - **Offline / Mock Mode**: Standard CI and local developer test runs execute deterministically without live credential dependencies. Fixtures (`backend/tests/fixtures/opportunities.py`) and simulated GenAI client calls ensure 100% repeatable assertions.
   - **Live Smoke Test Mode**: When `GEMINI_API_KEY` is present in the environment, live search grounding and official URL context calls execute directly against the Gemini API without mocking.

4. **Adversarial & Fault Resilience (Tiers 1–4)**:
   - Boundary stress, security injections (SSRF host forgery, loopbacks, AWS metadata, control characters), paywalled URLs, and malformed inputs are comprehensively verified before production readiness.

---

## 2. Feature Inventory Coverage Goals

Every feature in the ScholarSwarm Feature Inventory (F1 through F10) is verified in isolation (Tier 1) and evaluated across multi-feature integration workflows (Tiers 2–4).

### Feature Traceability Matrix

| Feature ID | Feature Name | Milestone | Test Tier | Test Module | Test Function(s) |
|---|---|---|---|---|---|
| **F1** | Eliminate `REAL_OPPORTUNITIES_BASE` | M1 | Tier 1 | `test_tier1_feature_coverage.py` | `test_f1_fixtures_are_isolated_and_conform_to_schema` |
| **F2** | Gemini Search Grounding Discovery | M1 | Tier 1, Tier 3 | `test_tier1_feature_coverage.py`, `test_tier3_cross_feature.py` | `test_f2_search_grounding_discovery_contract`, `test_xf1_search_discovery_to_url_extraction_pipeline` |
| **F3** | Google Gen AI SDK URL Context Tool | M1 | Tier 1 | `test_tier1_feature_coverage.py` | `test_f3_google_genai_sdk_url_context_tool_contract` |
| **F4** | Retrieval Metadata Handling | M1 | Tier 1, Tier 2 | `test_tier1_feature_coverage.py`, `test_tier2_boundary_corner.py` | `test_f4_retrieval_metadata_handling_distinguishes_status`, `test_b4_malformed_url_schemes_rejected` |
| **F5** | Explicit API Configuration Errors | M1 | Tier 1, Tier 2 | `test_tier1_feature_coverage.py`, `test_tier2_boundary_corner.py` | `test_f5_missing_api_key_returns_explicit_error_without_fallback`, `test_b6_service_resilience_when_gemini_raises_exception` |
| **F6** | Program-Specific Criteria Matching | M2 | Tier 1, Tier 2 | `test_tier1_feature_coverage.py`, `test_tier2_boundary_corner.py` | `test_f6_program_specific_criteria_matching`, `test_b2_cgpa_boundary_transitions` |
| **F7** | Verbatim Quotes & `UNRESOLVED` | M2 | Tier 1, Tier 4 | `test_tier1_feature_coverage.py`, `test_tier4_real_world.py` | `test_f7_verbatim_quotes_and_unresolved_classification`, `test_scenario_1_rahul_sharma_end_to_end_journey` |
| **F8** | Admission vs Scholarship Distinction | M2 | Tier 1, Tier 3 | `test_tier1_feature_coverage.py`, `test_tier3_cross_feature.py` | `test_f8_admission_vs_scholarship_distinction`, `test_xf2_eligibility_and_degree_prerequisite_disqualification` |
| **F9** | Runtime Deadline Verification | M2 | Tier 1, Tier 2 | `test_tier1_feature_coverage.py`, `test_tier2_boundary_corner.py` | `test_f9_runtime_deadline_verification_against_utc_date`, `test_b3_deadline_temporal_boundaries` |
| **F10** | Robust Official Domain Verification | M2 | Tier 1, Tier 3 | `test_tier1_feature_coverage.py`, `test_tier3_cross_feature.py` | `test_f10_robust_official_domain_verification`, `test_xf3_funding_claim_audit_and_bounded_re_research_loop` |
| **F11–F14**| 5-Agent Bounded Loop & Reviewer Audit | M3 | Tier 3 | `test_tier3_cross_feature.py` | `test_xf3_funding_claim_audit_and_bounded_re_research_loop`, `test_xf5_full_langgraph_workflow_execution` |
| **F15** | On-Demand Application Coach SOP | M3 | Tier 4 | `test_tier4_real_world.py` | `test_scenario_1_rahul_sharma_end_to_end_journey` |
| **F16** | Repository State Consistency & Reset | M3 | Tier 4 | `test_tier4_real_world.py` | `test_scenario_5_data_isolation_and_reset_endpoint` |

---

## 3. Test Architecture

The E2E test framework is organized under `backend/tests/e2e/`, complemented by canonical fixtures in `backend/tests/fixtures/`.

```
backend/
├── pytest.ini                            # Configures pythonpath = . and testpaths = tests
└── tests/
    ├── fixtures/
    │   ├── __init__.py
    │   └── opportunities.py              # Canonical fixture opportunities isolated from production
    └── e2e/
        ├── __init__.py
        ├── conftest.py                   # Async clients, student personas, and test factories
        ├── test_tier1_feature_coverage.py   # 10 tests: isolated F1-F10 verification
        ├── test_tier2_boundary_corner.py    # 35 tests: boundary, SSRF, edge inputs, error handling
        ├── test_tier3_cross_feature.py      # 5 tests: multi-feature state graph integration
        └── test_tier4_real_world.py         # 5 tests: 4 multi-country personas + reset isolation
```

### Tier Breakdown

1. **Tier 1 — Feature Coverage (`test_tier1_feature_coverage.py`)**:
   - Tests each feature from F1 to F10 in strict isolation.
   - Asserts contracts, SDK type compatibility, domain verification regexes, UTC deadline evaluations, and explicit configuration errors.

2. **Tier 2 — Boundary, Corner & Error Cases (`test_tier2_boundary_corner.py`)**:
   - Parameterized boundary testing:
     - CGPA thresholds: 0.0, 6.99 (DOES_NOT_MEET), 7.0, 7.99 (POTENTIAL_MATCH), 8.0, 9.99, 10.0 (MEETS).
     - Temporal edge cases: yesterday (EXPIRED), today (ACTIVE), tomorrow (ACTIVE), non-ISO dates, rolling deadlines.
     - SSRF Injection: localhost, 127.0.0.1, [::1], 0.0.0.0, 169.254.169.254 (AWS IMDS), RFC 1918 private IPs (10.0.0.1, 172.16.0.1, 192.168.1.1), `file://` protocol.
     - Malformed URLs: `javascript:`, `data:`, `ftp:`, empty strings, control characters.
     - Resilience against runtime LLM exceptions (timeouts, 503 errors).

3. **Tier 3 — Cross-Feature Integration (`test_tier3_cross_feature.py`)**:
   - State graph workflows and inter-agent handoffs:
     - Search Grounding Discovery -> URL Normalization -> Sanitization -> Extraction.
     - Eligibility Assessment -> Mandatory Disqualification -> Top-5 Shortlist Exclusion.
     - Ambiguous Funding Claim -> Quality Reviewer Flag -> Bounded Re-Research Loop.
     - Deadline Verification -> Multi-Factor Match Scoring.
     - End-to-end LangGraph 5-node workflow execution.

4. **Tier 4 — Realistic Real-World Scenarios (`test_tier4_real_world.py`)**:
   - Complete lifecycle validation across diverse international student personas:
     - End-to-end API invocations (`/api/research/start`, `/api/research/{id}/opportunities`, `/api/opportunities/{id}/sop`).
     - Actionable gap generation for missing prerequisites.
     - Multi-tenant data isolation and clean database state reset (`/api/opportunities/reset`).

---

## 4. Real-World Application Scenarios

The test framework evaluates four diverse student personas across multiple origin countries, target fields, and degree levels:

### Persona 1: Rahul Sharma (India -> Canada, Germany, Singapore)
- **Profile**: B.Tech CS, CGPA 8.2/10.0, First Class with Distinction.
- **Goals**: Master's in Computer Science / Artificial Intelligence, full funding required.
- **Language Status**: IELTS planned (score pending).
- **Projects**: Distributed Semantic Search Engine (FastAPI, FAISS, Docker), Medical Image Segmentation (PyTorch).
- **Expected Outcome**:
  - Discovers high-fit programs (UofT MScAC, TUM Informatics, NUS MComp).
  - Academic Grade evaluates to `MEETS` (exceeds 8.0 threshold).
  - English Language evaluates to `UNRESOLVED` with actionable gap: *"Complete IELTS (target >= 7.0) or TOEFL (target >= 95)"*.
  - Ranked in Top 5 shortlist based on high academic fit and full funding match.
  - On-demand SOP generated via Application Coach accurately integrates his vector search engine without hallucinated internships.

### Persona 2: Maria Santos (Brazil -> Germany, Canada)
- **Profile**: B.Sc Biotechnology, CGPA 6.8/10.0.
- **Goals**: Master's in Bioinformatics, partial funding accepted.
- **Language Status**: TOEFL iBT 102 (Completed, high band).
- **Projects**: CRISPR Off-Target Predictive Pipeline.
- **Expected Outcome**:
  - Evaluates against German and Canadian bioinformatics requirements.
  - Strict 8.0 threshold programs flag her CGPA as `DOES_NOT_MEET` or `POTENTIAL_MATCH` with formal transcript review requirement.
  - Language test is verified as `MEETS`.
  - Gap Planner presents clear admission guidance for prerequisite equivalency.

### Persona 3: Wei Chen (China -> Singapore)
- **Profile**: M.Sc Mathematics, CGPA 8.5/10.0 (85%).
- **Goals**: PhD in Data Science / Theoretical AI, full research scholarship.
- **Language Status**: Pending.
- **Projects**: Non-Convex Optimization for Deep Networks.
- **Expected Outcome**:
  - Filters for Singapore doctoral programs (A*STAR SINGA, NUS Research Scholarship).
  - Verifies PhD degree prerequisite compatibility.
  - Missing language score flagged as mandatory gap before final award offer.

### Persona 4: Fatima Al-Hassan (Nigeria -> Canada)
- **Profile**: B.Eng Electrical & Electronics Engineering, CGPA 9.1/10.0 (Top 1% distinction).
- **Goals**: PhD in Robotics & Autonomous Systems.
- **Language Status**: IELTS 8.0 (Completed).
- **Projects**: Autonomous Agricultural Quadrotor (ROS2, SLAM).
- **Expected Outcome**:
  - Academic grade strongly meets top competitive threshold (9.1/10.0).
  - Language requirement fully satisfied (`MEETS`).
  - Achieves top academic and evidence fit scores (total score >= 85/100).

---

## 5. Coverage Thresholds and Quality Gates

All builds and pull requests must satisfy the following automated quality gates:

| Quality Gate | Threshold | Verification Command | Current Status |
|---|---|---|---|
| **E2E Test Pass Rate** | **100% (55/55 tests)** | `pytest tests/e2e/ -v` | **PASSED (55/55)** |
| **Full Repo Test Pass Rate** | **100% (76/76 tests)** | `pytest tests/ -v` | **PASSED (76/76)** |
| **SSRF Injection Rejection** | **100% (13/13 blocked)** | `pytest tests/e2e/test_tier2_boundary_corner.py -k ssrf` | **PASSED (13/13)** |
| **Schema Strictness** | **Zero Validation Errors** | Pydantic v2 model validation | **PASSED** |
| **No Silent Fallbacks** | **Explicit API Config Errors** | `pytest tests/e2e/test_tier1_feature_coverage.py -k f5` | **PASSED** |

### Execution Commands

To execute the complete E2E test suite:
```bash
cd backend
pytest tests/e2e/ -v
```

To execute a specific tier:
```bash
cd backend
pytest tests/e2e/test_tier1_feature_coverage.py -v   # Tier 1: Feature Coverage (10 tests)
pytest tests/e2e/test_tier2_boundary_corner.py -v    # Tier 2: Boundary & Corner Cases (35 tests)
pytest tests/e2e/test_tier3_cross_feature.py -v      # Tier 3: Cross-Feature Integration (5 tests)
pytest tests/e2e/test_tier4_real_world.py -v         # Tier 4: Real-World Scenarios (5 tests)
```
