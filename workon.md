# MASTER BUILD PROMPT — SCHOLARSWARM
## TetraNoodle AI Hackathon 2026 | AI Scholarship Finder

Act as a senior AI engineer, full-stack developer, AI-agent architect and deployment engineer. Your task is to implement a complete, working application named **ScholarSwarm** for the TetraNoodle AI Hackathon 2026.

Do not stop after proposing an architecture, creating a UI mockup or writing example code. Inspect the workspace, implement the application, run it, execute tests, fix errors, and prepare the project for straightforward free-tier deployment.

Make implementation decisions independently within the specifications below. Do not repeatedly ask for confirmation. If an external API key is unavailable, implement the integration, document the configuration required and test everything that can be tested without that key. Never claim an external integration or live research run succeeded unless it actually did.

---

# 1. PROJECT OBJECTIVE

Build an AI-powered scholarship research website that understands a student's academic profile, discovers real international study and funding opportunities, verifies requirements, ranks the best matches and helps prepare an application.

The fictional demonstration student is Rahul:
- Final-year B.Tech Computer Science student from Jalandhar, India.
- CGPA: 8.2.
- Has built AI projects and maintains a public GitHub profile.
- Wants to pursue postgraduate studies abroad, initially considering Canada, Germany and Singapore.
- Needs financial assistance to afford university education.

The application must support different students and must not be hardcoded specifically for Rahul.

## Required outcomes

1. Accept resume and marksheet/transcript uploads, profile information and an optional public GitHub URL or username.
2. Extract and normalize the student's academic details, skills, projects and achievements.
3. Enrich the profile using relevant public GitHub data.
4. Search the live internet for real university programs and scholarships.
5. Discover approximately 20–30 candidate opportunities when practical and verify at least 10 distinct opportunities when reliable source availability permits.
6. Compare admission requirements and scholarship eligibility with the student profile.
7. Provide criterion-level source evidence, explicit unknowns and actionable eligibility gaps.
8. Rank the top five suitable opportunities using a transparent scoring formula.
9. Show funding details, deadlines or their verification status, application instructions, reasons for matching and official links.
10. Generate an editable statement of purpose (SOP) for one selected opportunity.
11. Show the actual activities of five collaborating AI agent roles on the website.
12. Handle API failures, malformed outputs, unavailable websites, duplicate opportunities and incomplete research branches.
13. Demonstrate that a different student profile can use the same architecture without rewriting the agents.
14. Deploy the frontend, backend and persistent data storage using available free tiers where practical.
15. Include a GitHub-ready repository, automated tests, diagrams, experiment notes, interview preparation and a reproducible five-minute demo script.

The product is a research and application-assistance system. It must never automatically submit applications or fabricate scholarship information, deadlines, funding values, eligibility rules or student achievements.

# 2. LOCKED TECHNOLOGY AND DEPLOYMENT DECISIONS

Use this stack unless a genuine compatibility blocker requires an explicitly documented alternative.

| Layer | Selected technology |
|---|---|
| Frontend | React + Vite + TypeScript |
| Styling | Tailwind CSS + shadcn/ui where useful |
| Backend | Python + FastAPI |
| Agent orchestration | LangGraph |
| Primary LLM | Google Gemini API |
| Web discovery | Gemini Google Search grounding |
| Page research | Gemini URL Context |
| Profile enrichment | GitHub REST API |
| Structured validation | Pydantic |
| Persistent storage | Supabase PostgreSQL |
| Live progress | Server-Sent Events (SSE) |
| Frontend hosting | Cloudflare Pages |
| Backend hosting | Render free web service |
| Documents | PyMuPDF + python-docx; OCR only when necessary |

Use one primary Gemini model for all five agent roles. Different roles should have distinct instructions, responsibilities, inputs, outputs and tool permissions; they do not require five different LLM models.

Do not add Tavily, Firecrawl, CrewAI, n8n, a vector database, Redis, paid queues or additional hosting services to the initial implementation. Introduce an alternative only if testing demonstrates that a required capability cannot be implemented reliably with the selected stack.

## Verify the Gemini model before implementation

Use the official documentation:
- Google Search grounding: https://ai.google.dev/gemini-api/docs/google-search
- URL Context: https://ai.google.dev/gemini-api/docs/url-context
- Gemini pricing: https://ai.google.dev/gemini-api/docs/pricing
- Google Gen AI SDK: https://googleapis.github.io/python-genai/

Use `gemini-2.5-flash` as the initial candidate model, **but verify its current availability, compatibility with both required tools and free-tier search-grounding allowance before committing to it**. If it has been retired or those capabilities change, choose the least expensive currently supported model that meets the same requirements.

Do not blindly upgrade to a newer model if its Google Search grounding is unavailable on the standard free tier. Do not hardcode the model throughout the application. Make it configurable with `GEMINI_MODEL`.

Use the current, documented Google Gen AI SDK and supported API interface. Pin a dependency version that has actually been tested. Do not mix incompatible examples from old and new SDK versions.

If free-tier quotas or terms change, document the limitation honestly. Never describe the whole project as guaranteed to be free when actual API usage, limits or account requirements depend on the provider.

# 3. THE FIVE AI AGENT ROLES

Implement exactly these five named agent roles, with genuine information exchange through LangGraph.

These are five task-specific AI roles, not five separate AI models. They must not be five unrelated prompts that each execute once without sharing information.

## Agent 1 — Profile Intelligence Agent

**Goal:** Build a reliable, structured representation of the student.

Responsibilities:
- Parse supported resumes and academic transcripts/marksheets.
- Extract education, degree, institution, academic results, grading scale when known, graduation status, skills, projects, internships, publications, awards and certifications when documented.
- Use the GitHub REST API to retrieve relevant public repository metadata and README content.
- Identify evidence that a student has actually worked on AI, machine learning or software projects.
- Separate document-backed facts, user-entered facts and inferred information.
- Detect conflicts between the resume, transcript and user-entered fields.
- Identify missing or uncertain facts that may affect eligibility.
- Never invent achievements, grades, internships or technical skills.

**Input:** Student form, extracted document text and optional public GitHub information.

**Output:** A validated `StudentProfile`, supporting provenance where available, and a list of missing/conflicting facts.

Use PyMuPDF for PDFs and python-docx for Word files. Use OCR only when a scanned document lacks a usable text layer and OCR is available.

## Agent 2 — Research & Eligibility Agent

**Goal:** Find genuine opportunities and determine what their official requirements establish about the student.

This role combines the former Opportunity Scout and Eligibility Auditor because discovery and eligibility verification share the same research context. However, implement them as separate workflow phases.

### Phase A: Opportunity discovery
- Use Gemini Google Search grounding to discover candidate universities, postgraduate programs, scholarships and funding opportunities dynamically.
- Generate targeted queries from the student's degree level, specialization, academic background, citizenship where relevant, intake, target countries and funding needs.
- Research Canada, Germany and Singapore initially and expand to other relevant destinations when justified.
- Run independent search tasks concurrently where appropriate.
- Prefer official university, government and funding-provider websites.
- Preserve actual search queries, source citations and candidate URLs.
- Collect enough candidates to account for duplicates, unsuitable awards and retrieval failures.

### Phase B: Official-page retrieval
- Use Gemini URL Context to retrieve supplied official URLs and examine the actual webpage content.
- Discover the official program page and the scholarship/funding page separately when necessary.
- Batch URL Context requests within the currently supported limit of 20 URLs per request. Prefer smaller batches when needed for extraction quality.
- Capture citation annotations, source URLs and retrieval status.
- Do not assume URL Context automatically follows every link on a page.
- If a page cannot be retrieved, retry appropriately or perform a targeted Google Search query.

### Phase C: Requirement extraction and eligibility assessment
Extract and compare the requirements actually published by the provider, including:
- Program title, university and country.
- Degree level and relevant academic field.
- Intended intake, if published.
- Citizenship/nationality and residency restrictions.
- Academic grade requirements and official grading-equivalency guidance.
- Language tests and score requirements.
- Work experience, research experience or prerequisite subjects where applicable.
- Funding coverage, amount and currency where published.
- Deadline and deadline type.
- Application process, required documents and official application link.

Keep university admission eligibility separate from scholarship eligibility.

For every important requirement:
- Identify the requirement.
- Record the student's corresponding profile fact, if known.
- Record the result and a concise explanation.
- Preserve an evidence excerpt when it is genuinely available from retrieved content.
- Store the official source URL and source title.
- Record when the source was checked.
- Identify unresolved uncertainty.

Do not fabricate exact quotations. If retrieval does not expose a reliable verbatim passage, store a source-grounded summary and citation rather than presenting invented wording as a quote.

### Eligibility statuses

Use exactly these core statuses:

- `MEETS_STATED_CRITERIA`: The checked mandatory requirements are supported by evidence and satisfied.
- `POTENTIAL_MATCH`: No known mandatory disqualifier, but one or more relevant requirements remain unresolved.
- `DOES_NOT_MEET`: At least one verified mandatory requirement fails.
- `INSUFFICIENT_EVIDENCE`: Available evidence does not establish a reliable verdict.

These statuses describe only the requirements actually checked. They never guarantee admission or funding.

Never convert an 8.2 CGPA into a foreign grading system using an invented universal formula. Use the relevant institution's published equivalency guidance or mark it as unresolved.

**Output:** Candidate opportunity records, criterion-level eligibility assessments, official source evidence, unresolved questions and targeted re-research requests.

## Agent 3 — Match Strategist Agent

**Goal:** Rank opportunities transparently rather than asking the LLM to choose its favourites.

Responsibilities:
- Consume validated opportunity and eligibility records.
- Apply deterministic eligibility rules before ranking.
- Exclude verified mandatory failures from the eligible top-five shortlist; optionally show them in a separate section explaining why they failed.
- Calculate match scores using deterministic Python code.
- Ask the LLM to explain why an opportunity fits, not to invent or arbitrarily alter its score.
- Explain missing requirements, financial suitability and practical next steps.
- Keep match scores distinct from admission or scholarship-success probabilities.

Use this initial scoring formula:

| Dimension | Weight |
|---|---:|
| Academic and eligibility fit | 35 |
| Funding coverage and financial suitability | 25 |
| Subject and program fit | 20 |
| Deadline and application readiness | 10 |
| Evidence quality and freshness | 10 |
| **Total** | **100** |

Use scores from 0 to 100. Apply hard eligibility filters separately before the score is used.

Unknown mandatory criteria must remain visible and reduce confidence/readiness. A high score cannot compensate for a confirmed mandatory failure.

**Output:** Ranked opportunities, deterministic numeric scores, source-grounded explanations, eligibility status and suggested next actions.

## Agent 4 — Application Coach Agent

**Goal:** Prepare a personalized, editable application draft based on actual student information.

Responsibilities:
- Accept a selected, researched opportunity.
- Use verified student education, skills, projects and achievements.
- Use the program's official description, objectives and published application instructions.
- Connect the student's actual background to the opportunity's academic focus.
- Ask for missing motivations and personal goals when relevant.
- Produce an editable, coherent SOP with a download/export option.
- Mark statements that require student confirmation.
- Never invent personal hardships, awards, publications, internships, leadership, experience or motivations.
- Do not submit any application automatically.

**Output:** An editable SOP draft and a list of factual claims or personal details requiring confirmation.

## Agent 5 — Quality Reviewer Agent

**Goal:** Independently challenge results and prevent unsupported claims from being presented as verified.

Responsibilities:
- Review important opportunity facts, funding amounts, deadlines, eligibility decisions and citations.
- Confirm that the source actually supports the associated claim.
- Flag secondary sources when official evidence should be obtained.
- Detect inconsistent eligibility results, duplicate awards and outdated/ambiguous deadlines.
- Check SOP claims against the student's available evidence.
- Return precise issues to Agent 2 for targeted re-research or Agent 4 for draft corrections.
- Approve results only when critical claims meet the defined evidence policy.
- Preserve explicit unknowns when a reliable answer cannot be obtained.

**Output:** Approval/rejection status, specific correction requests and an uncertainty report when needed.

## Why five agents?

Five is a deliberate architecture decision, not a magical number. Discovery and eligibility are combined because they use the same research context. Profile understanding, ranking, application drafting and independent quality review remain separate because they have distinct responsibilities.

The LangGraph supervisor is ordinary workflow orchestration, not a sixth agent.

The website must show genuine role execution and information exchange. Do not simulate agent progress with timers or hardcoded log messages.

# 4. LANGGRAPH WORKFLOW AND RECOVERY

Implement a bounded, conditional LangGraph workflow.

Recommended workflow:

1. Validate and normalize the student profile.
2. Run targeted search queries in parallel where practical.
3. Collect, normalize and deduplicate candidate opportunity URLs.
4. Retrieve official pages through URL Context in supported-size batches.
5. Extract and normalize requirements into Pydantic models.
6. Evaluate eligibility criterion by criterion.
7. If critical evidence is missing, send a targeted re-research task back to Agent 2.
8. Rank valid opportunities using Agent 3 and deterministic scoring code.
9. Generate a draft using Agent 4 if the student selects an opportunity.
10. Have Agent 5 review evidence, recommendations and the draft.
11. If corrections are required, route the relevant issues back to the responsible role.
12. Return final results and unresolved uncertainties to the dashboard.

The reviewer must not simply approve its own previous output. It should have separate review instructions and inspect the evidence records.

Implement:
- Typed shared graph state.
- Clear node responsibilities.
- Conditional edges.
- Parallel research branches where appropriate.
- Bounded retries with backoff for transient failures.
- Per-node timeouts.
- Strict maximum re-research loops.
- Persistent run/job status and event records.
- Preservation of completed results when a different branch fails.
- An explicit terminal failure or interrupted state when a run cannot continue.

Use LangGraph checkpointing if it integrates cleanly with the selected persistent storage and can be tested within the project scope. Otherwise, persist node results and run status in Supabase, allow safe retries of failed phases, and do not claim full workflow resumption unless implemented and tested.

Do not introduce an additional background-worker service because of the free-tier deployment requirement. Run research as a bounded task in the FastAPI service, persist its progress, and clearly handle interrupted runs. Ensure repeated start requests do not accidentally launch duplicate jobs.

# 5. GEMINI GOOGLE SEARCH + URL CONTEXT INTEGRATION

This integration is central to the project. It must be implemented with real API calls, not mocked data.

## Google Search grounding

Use Gemini's Google Search tool for broad, profile-specific discovery.

Search query examples should be constructed from the current profile, such as:
- Fully funded master's opportunities in AI/Computer Science for the student's country and intended intake.
- Official international graduate scholarship programs at relevant universities.
- University-level funding pages for the target subject and degree level.
- Official government scholarship databases for the target destination.

These are examples of query patterns, not hardcoded research results. Generate queries from the profile and expand them when results are insufficient.

Preserve genuine source URLs and citation metadata returned by the API. Where possible, retain the search queries and retrieval status for the activity timeline.

## URL Context

Use URL Context for the candidate URLs discovered by research.

Extract published information from the supplied source URLs and retain URL citation annotations. Batch requests according to the current tool limit and keep batches small enough to maintain reliable extraction.

Use official sources for critical claims. If only secondary evidence is available, label it as secondary and trigger additional official-source research where reasonable.

Search citations are useful provenance, but they do not automatically prove that the eligibility interpretation is correct. The reviewer must compare important claims with evidence.

## Model and quota management

- Keep `GEMINI_MODEL` configurable.
- Use a separate service module to encapsulate Gemini calls.
- Apply API timeouts, limited retries and request budgets.
- Limit search rounds, URLs processed and concurrent calls.
- Avoid asking every agent to repeat the same research request.
- Cache normalized evidence where useful and when its freshness remains acceptable.
- Record quota, permission and API errors in an understandable form.
- Do not silently switch to paid functionality or a different search vendor when the configured free quota fails.
- If the quota is exhausted, retain valid partial results, explain the limitation and allow a later retry.
- Do not treat cached fixture data as real live search output.

If a fallback retrieval method becomes necessary, implement a minimal direct-page extraction fallback using a safe Python HTTP client and Trafilatura. This is optional and should only be added when a real retrieval limitation is observed; it must not replace the agreed Gemini discovery method.

# 6. OPPORTUNITY EVIDENCE MODEL

Use Pydantic models for at least the following entities:

- `StudentProfile`
- `AcademicRecord`
- `ProjectOrAchievement`
- `Opportunity`
- `FundingDetails`
- `EligibilityCriterion`
- `EvidenceRecord`
- `EligibilityAssessment`
- `MatchScore`
- `ResearchRun`
- `AgentEvent`
- `ApplicationDraft`

An opportunity record should support:
- Stable ID.
- Title and program name.
- University or provider.
- Country.
- Degree level and field.
- Intake.
- Admission requirements.
- Scholarship requirements.
- Funding type, coverage, amount and currency, where published.
- Deadline, type and verification status.
- Official application URL.
- Official source URLs.
- Source retrieval timestamps.
- Evidence quality and verification status.
- Eligibility results.
- Match score and explanation.

An evidence record should support:
- Claim/criterion.
- Requirement stated by the provider.
- Relevant student value, if known.
- Result status.
- Evidence excerpt or faithful summary.
- Source title and URL.
- Source category, such as official or secondary.
- Timestamp checked.
- Reason for uncertainty or conflict.

Use proper `null` or an explicit unknown state for unavailable amounts, deadlines, grades or other facts. Do not use plausible guesses to fill missing values.

Normalize URLs and use canonical URL/provider/program identity to deduplicate opportunities.

Keep admission requirements separate from funding eligibility. Keep university application deadlines separate from scholarship deadlines. Preserve the deadline and intake as actually published; do not infer the year, timezone or whether a cycle is current when it is unclear.

Classify a source as official only when there is reasonable evidence that the domain belongs to the university, government or funding provider. A familiar-looking domain or extension by itself is not enough.

# 7. STUDENT PROFILE INPUTS

The website should accept:
- Resume upload.
- Transcript/marksheet upload.
- Public GitHub profile URL or username.
- Degree and institution.
- CGPA/grades and grading scale, where known.
- Degree level sought: master's, PhD or either.
- Subject/specialization.
- Target countries.
- Intended intake.
- Citizenship/nationality when relevant.
- Language-test status and score when applicable.
- Work/research experience and achievements.
- Funding preferences, such as full funding or tuition assistance.
- Career goals and application motivation.

Prefill information from uploaded documents when possible and let the student review and correct it before starting research.

Continue useful research even when some profile fields are missing. Ask only for missing information that materially affects evaluation, and make uncertainty visible.

## Privacy and consent

The website must tell users that profile facts may be processed through external AI tools. The current free-tier terms may permit provider use of prompts and outputs to improve services, so do not quietly send private student data without consent.

For the public demo:
- Prefer Rahul's fictional profile and sample documents.
- Minimize personal data sent to the API.
- Extract supported file text locally, then send only relevant profile facts where possible.
- Add an explicit consent notice before external processing of a real student's information.
- Do not persist uploaded resume/marksheet files by default.
- Do not log full resumes, transcripts or API keys.
- Provide a clear demo reset or data deletion function.
- Never submit a real application.

# 8. MATCH SCORING

Implement the ranking formula in regular Python functions with unit tests.

| Dimension | Weight |
|---|---:|
| Academic and eligibility fit | 35 |
| Funding coverage and financial suitability | 25 |
| Subject/program fit | 20 |
| Deadline and application readiness | 10 |
| Evidence quality and freshness | 10 |
| **Total** | **100** |

Mandatory eligibility rules must be evaluated first. A verified failure is not eligible for the main top-five list, regardless of score.

An unknown mandatory criterion must remain explicit. Do not silently count it as passed.

A fit score is not an admission probability, probability of receiving funding or a guarantee of suitability.

Use the score to order eligible candidates. Use the LLM to explain the reasoning in straightforward language. Never let the LLM alter the numeric score without executing the validated scoring logic.

# 9. WEBSITE SCREENS AND USER EXPERIENCE

Build a polished, minimal, responsive dashboard. Avoid a generic chatbot-only interface. The product should look like a serious research assistant.

## A. Home/dashboard
- Clear explanation of ScholarSwarm.
- Start Research action.
- Profile summary and last research status.
- Link to recent results when persisted.

## B. Student profile
- Resume and transcript uploads.
- GitHub profile entry.
- Editable extracted facts.
- Degree, field, country, intake and funding preferences.
- Missing-field warnings.
- Consent notice for external AI processing.

## C. Live agent workspace
- Five real agent roles and their current status.
- Actual search tasks, source retrievals, evidence extraction and eligibility checks.
- Visible correction requests, retry attempts, branch failures and recovery.
- Event timestamps and useful status descriptions.
- No fake progress bars or invented agent events.

## D. Opportunity shortlist
- Top five recommendations where enough verified results exist.
- Broader list of unique verified opportunities.
- University/program name, country, degree, funding, deadline/status, eligibility result and match score.
- Explanation of why the opportunity matches.
- Official source and application links.
- Filters by country, degree, funding and eligibility.
- Clear labels for potential matches and unverified claims.

## E. Opportunity evidence details
Show each critical criterion, the student's corresponding data, result, source evidence, official link and check timestamp.

## F. Eligibility gap planner
Explain missing or uncertain requirements and suggest the next useful action. Distinguish a missing document from a confirmed mandatory disqualifier.

## G. Application workspace
- Select an opportunity.
- Generate an SOP using verified profile facts and the official program description.
- Edit the output.
- Highlight facts requiring confirmation.
- Review the draft.
- Download/export the draft.
- Never submit the application.

## H. UI states and accessibility
- Responsive desktop and mobile layouts.
- Clear loading, success, empty and error states.
- Accessible labels and keyboard navigation.
- Safe rendering of source excerpts.
- Visible distinction between live research and demo fixtures.
- Useful messages when Render is waking up or a data/API provider is unavailable.

The frontend must be functional. All controls should perform their advertised actions.

# 10. BACKEND, EVENTS AND DATABASE

Keep the backend modular and deployable.

Recommended directories:

```text
scholarswarm/
  frontend/
    src/
      components/
      pages/
      api/
      hooks/
      types/
      styles/
    public/
    package.json
    vite.config.ts
    tsconfig.json
  backend/
    app/
      main.py
      config.py
      api/
      agents/
        profile_intelligence.py
        research_eligibility.py
        match_strategist.py
        application_coach.py
        quality_reviewer.py
      graph/
        workflow.py
        state.py
        nodes.py
      services/
        gemini_service.py
        github_service.py
        document_service.py
        research_service.py
        scoring_service.py
      models/
      db/
      security/
    tests/
    requirements.txt
    Dockerfile
  supabase/
    schema.sql
  docs/
    ARCHITECTURE.md
    EXPERIMENT.md
    CHALLENGES.md
    INTERVIEW_PREP.md
    DEMO_SCRIPT.md
  .env.example
  .gitignore
  README.md
```

Adapt the structure as needed, but keep model calls, agent responsibilities, graph orchestration, scoring, storage and API routes testable separately. Avoid a single monolithic Python file.

## Required API routes

Implement suitable equivalents of:
- `GET /api/health`
- `POST /api/profile/extract`
- `POST /api/research/start`
- `GET /api/research/{run_id}`
- `GET /api/research/{run_id}/events` (SSE)
- `GET /api/research/{run_id}/opportunities`
- `GET /api/opportunities/{opportunity_id}`
- `POST /api/opportunities/{opportunity_id}/verify`
- `POST /api/opportunities/{opportunity_id}/sop`
- A controlled demo reset or data deletion endpoint.

Validate requests and responses with Pydantic. Use consistent HTTP status codes and error responses.

## Supabase PostgreSQL

Use Supabase for persistent research runs, opportunities, evidence records, status information and agent-event summaries.

Provide `supabase/schema.sql` or equivalent reproducible migrations. The backend owns database access. Never expose the Supabase service-role key to the browser.

Persist events with a research-run ID so SSE clients can reconnect and retrieve missed events. Support event IDs or an equivalent replay mechanism.

Use proper status transitions: `QUEUED`, `RUNNING`, `COMPLETED`, `PARTIAL`, `FAILED` and `INTERRUPTED` as appropriate.

On server startup or status lookup, do not leave an abandoned run indefinitely labelled `RUNNING`. Detect interrupted runs and offer a safe retry or resume route. Do not claim that a graph automatically resumes from checkpoints unless that behaviour is implemented and tested.

## SSE progress

Use real `AgentEvent` records such as:
- Profile extraction started/completed.
- Search query issued.
- Candidate URL discovered.
- Official URL retrieved.
- Requirement extracted.
- Eligibility status evaluated.
- Duplicate candidate removed.
- Source could not be retrieved.
- Retry scheduled/executed.
- Reviewer correction requested.
- Match score calculated.
- SOP draft generated/reviewed.
- Final results completed.

Progress must come from actual code execution, not hardcoded event sequences.

# 11. DEPLOYMENT-FIRST IMPLEMENTATION

Write the code from the beginning so a fresh clone can be deployed without major restructuring.

## Cloudflare Pages: frontend

- Root directory: `frontend`
- Build command: `npm ci && npm run build`
- Build output directory: `dist`
- Frontend API base URL: `VITE_API_BASE_URL`

Use environment variables for the backend URL; do not hardcode localhost or the deployed hostname.

Build and test the frontend in production mode locally before deploying it.

## Render: backend

- Root directory: `backend`
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

Bind to the platform-provided port. Provide `/api/health`. Ensure all critical imports, static configuration and database connection failures have useful startup errors.

Render's free web services can sleep when idle, take time to wake, restart and lose local filesystem changes. The design must not rely on local files or a local SQLite database for durable deployed records. Explain cold starts in the README and demo script.

Because free Render does not provide the same capabilities as a paid persistent background worker, keep execution and queue management simple. Use bounded in-process execution, Supabase-persisted progress and graceful interrupted-run handling; do not require a separate paid worker.

## Supabase: persistent storage

Configure database access with backend-only environment variables:
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`

Use secure backend access and an appropriate database schema. Do not put service credentials in Vite variables or commit them. Ensure run data cannot be accessed merely by guessing a short or sequential ID.

Supabase free projects have storage/usage limits and can pause after inactivity. The UI should handle database unavailability gracefully, and the README should explain reactivation.

## CORS and configuration

Configure CORS to allow only:
- Local frontend development origin.
- The deployed Cloudflare Pages origin.
- Any explicitly configured trusted custom origin, if needed.

Do not enable unrestricted CORS for production.

Create a complete `.env.example` containing only placeholders:

```dotenv
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.5-flash
GITHUB_TOKEN=
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
FRONTEND_ORIGIN=http://localhost:5173

VITE_API_BASE_URL=http://localhost:8000

MAX_UPLOAD_MB=10
MAX_RESEARCH_CANDIDATES=30
TARGET_VERIFIED_OPPORTUNITIES=10
MAX_RESEARCH_ROUNDS=3
MAX_URLS_PER_REQUEST=10
MAX_CONCURRENT_RESEARCH_REQUESTS=2
GEMINI_TIMEOUT_SECONDS=90
```

Treat `gemini-2.5-flash` as a configurable initial candidate, not an immutable assumption. Update the default only if current official documentation and a real integration test justify it. Ensure the frontend and backend environment variables are separated in documentation and hosting configuration.

The exact research limits should be adjustable and enforced in code. Default URL batches below the maximum supported by URL Context to improve extraction reliability.

Provide detailed setup commands for Windows PowerShell as well as general cross-platform instructions.

# 12. FREE-TIER COST AND DATA CONTROLS

The goal is a practical zero-budget or near-zero-budget hackathon deployment. Do not guarantee all usage remains free.

- Use free static hosting, a free backend service and a free persistent database where available.
- Verify current platform/API quotas before deployment.
- Use a model/tool combination whose Google Search grounding and URL Context access fits the actual available quota.
- Cache reusable evidence when its freshness permits.
- Do not repeat identical search queries and extraction calls unnecessarily.
- Bound the number of candidates, retries, model calls and concurrent tasks.
- Expose a clear quota/limit error in the UI.
- Never silently switch to paid services.
- Provide a live mode that uses actual API calls and a separate optional demo/test mode using clearly labelled fixtures.
- Never display fixtures as real current scholarship findings.
- Do not require a credit card or paid platform feature unless absolutely unavoidable; if the selected model/API account requires paid access, explain that limitation and offer an honest alternative.

Do not upload real student documents to external AI services without proper consent. Keep only the necessary extracted profile facts and research records. Do not log personally sensitive document contents.

# 13. SECURITY REQUIREMENTS

- Keep API credentials on the backend.
- Validate file extension, MIME type and size.
- Use safe temporary filenames and delete temporary uploads after processing by default.
- Never execute uploaded files or downloaded repository content.
- Validate GitHub usernames and URLs.
- Treat all webpage content, README text and extracted documents as untrusted data, not instructions that can override the agent's task.
- Validate output before using it as a tool argument.
- Escape user-provided and source-extracted content before displaying it.
- Use random opaque IDs for research runs.
- Apply basic request/rate limits to expensive research operations.
- Set external request timeouts and handle redirects safely.
- If a direct-fetch fallback is implemented, reject localhost, private-network, link-local and otherwise unsafe destinations, including after redirects, to reduce SSRF risk.
- Follow applicable website terms and rate limits. Do not bypass paywalls, authentication or access controls.
- Never expose internal API keys, private prompts containing user data or full uploaded documents in browser responses/logs.
- Do not submit scholarship or university applications automatically.

# 14. FAILURE HANDLING

Implement recovery as real software behaviour.

| Failure | Required behaviour |
|---|---|
| Gemini request times out | Retry a bounded number of times with backoff, then report failure |
| Search grounding unavailable or quota exhausted | Preserve prior valid results and show a clear error |
| URL Context cannot retrieve a source | Record failure, retry if appropriate, then mark the relevant evidence unverified |
| Model output is malformed | Validate, retry within a limit or route for review |
| One country research branch fails | Retain results from successful branches |
| Duplicate opportunity discovered | Merge or suppress duplicates using canonical URL/provider identity |
| Deadline not published or ambiguous | Preserve unknown status and explain the limitation |
| Eligibility evidence conflicts | Trigger review/targeted research and keep the conflict visible |
| Quality Reviewer rejects a claim | Return the specific claim for correction or further research |
| Research task is interrupted | Persist partial results and allow a safe retry/resume path |
| Supabase unavailable | Show a clear service error without fabricating saved results |
| Render wakes from idle | Show a clear loading/connecting state rather than a false failure |
| Upload parsing fails | Identify the file and offer correction; do not invent extracted facts |

Use maximum loop counts and idempotent node outputs where practical. A failure must not cause unlimited retries or silently overwrite stronger evidence.

# 15. TESTING AND QUALITY ASSURANCE

Use pytest for backend tests and a suitable frontend test framework such as Vitest.

Write tests for:
1. Student-profile validation.
2. PDF/DOCX extraction and failed extraction.
3. GitHub API error and rate-limit handling.
4. Opportunity/evidence schema validation.
5. URL/source citation parsing.
6. Duplicate detection.
7. Eligibility statuses and mandatory failures.
8. Unknown grade equivalencies and missing requirements.
9. Score calculation and hard eligibility filters.
10. Missing, stale or ambiguous deadlines.
11. Malformed Gemini outputs.
12. Bounded retries and graph-loop termination.
13. Partial results after a branch failure.
14. Reviewer-triggered correction routing.
15. SOP unsupported-claim detection.
16. Upload validation and unsafe-URL handling.
17. SSE event creation and replay.
18. Frontend loading, error, empty and populated states.
19. API contract integration.
20. Interrupted-run recovery or safe restart.

Use mocked services for unit tests but label them as mocked. Create a separate live integration smoke test that verifies Gemini Google Search grounding and URL Context access when valid credentials are supplied.

Do not claim live tests passed when only mocks were used.

## Three synthetic test profiles

Use:
- Rahul: B.Tech Computer Science, 8.2 CGPA, AI projects.
- Profile B: a student with a different specialization and lower academic results.
- Profile C: a student seeking a different degree level with missing language-test information.

Demonstrate that profile data changes queries, eligibility decisions and rankings where it should. Do not hardcode identical results for all students.

# 16. MOST INTERESTING EXPERIMENT

Implement a reproducible experiment named **Self-Correcting Scholarship Research**.

Procedure:
1. Run the research and eligibility workflow on a test profile.
2. Let the Quality Reviewer identify unsupported claims, missing evidence or ambiguous requirements.
3. Route specific issues back to Agent 2.
4. Run targeted research and produce corrected or explicitly uncertain results.
5. Compare the first and second passes.

Measure:
- Percentage of critical claims with adequate official-source evidence.
- Eligibility classification accuracy on manually labelled criteria.
- Unsupported claims detected and corrected.
- Recovery rate under deliberately injected retrieval failures.
- Additional Gemini calls and latency due to correction.

Document the method, sample size, results and limitations in `docs/EXPERIMENT.md`.

Do not claim improved accuracy before measuring it. If the experiment remains incomplete, label it as planned and include instructions to run it.

# 17. DOCUMENTATION AND HACKATHON SUBMISSION

Create a polished, GitHub-ready repository.

## README.md
Include:
- Problem statement and goals.
- Core features.
- Screenshot placeholders that can be replaced with actual screenshots.
- Architecture diagram in Mermaid.
- Five agent roles and their responsibilities.
- Explanation of how structured data is exchanged.
- Technology choices and alternatives.
- Why Gemini Search + URL Context were selected.
- Why five agent roles were chosen instead of six.
- Evidence, eligibility and scoring design.
- Failure handling and security.
- Live API configuration.
- Frontend/backend deployment setup.
- Supabase schema setup.
- Local development commands for Windows and cross-platform users.
- Testing instructions.
- Known limitations, free-tier constraints and privacy considerations.

## docs/ARCHITECTURE.md
Include workflow and deployment Mermaid diagrams, the five agent roles, graph state, source evidence model, and explanation of which components use AI versus deterministic code.

## docs/EXPERIMENT.md
Document the self-correction experiment and actual measurements only.

## docs/CHALLENGES.md
After implementation, describe the biggest real engineering challenge, the failed approach, debugging process, solution and remaining limitation. Do not invent a challenge that never occurred.

## docs/INTERVIEW_PREP.md
Prepare concise, easy-to-remember answers to:
- Explain ScholarSwarm in 30 seconds.
- What is an AI agent?
- Why five agent roles?
- Why combine discovery and eligibility?
- How do agents communicate?
- Why LangGraph rather than CrewAI?
- Why Gemini Search grounding + URL Context rather than Tavily, Firecrawl or custom scraping?
- Why this specific Gemini model and how were free-tier requirements checked?
- Why React + Vite rather than Next.js?
- Why Python + FastAPI?
- Why Supabase rather than SQLite for deployment?
- Why Pydantic?
- Why SSE?
- How is the match score calculated?
- How are official sources verified?
- How are hallucinations handled?
- How does retry/recovery work?
- What happens if a whole research branch fails?
- What security and privacy risks exist?
- What is the self-correction experiment?
- What is the biggest real technical challenge?
- How do you know that a result is correct?

Explain trade-offs rather than claiming one technology is universally superior. Do not claim benchmarking, experimental improvements or feature performance unless measured.

## docs/DEMO_SCRIPT.md
Prepare an actual five-minute demonstration:
- 0:00–0:40 — Enter Rahul's fictional profile and upload sample documents.
- 0:40–1:40 — Show actual agent activity and live candidate discovery.
- 1:40–2:40 — Open official sources and inspect eligibility evidence.
- 2:40–3:40 — Show the ranked shortlist and eligibility gap planner.
- 3:40–4:20 — Generate/review an SOP draft.
- 4:20–5:00 — Demonstrate recovery from a real tested failure or show a tested second-profile run.

The script must reflect the actual implemented features and must not depend on fabricated results.

## Other repository files
- `.env.example` with placeholders, never secrets.
- Dependency lock/manifest files appropriate for Python and Node.
- `.gitignore`.
- Supabase schema/migration files.
- Automated tests and fixtures.
- Deployment instructions.
- Optional Docker configuration only if it genuinely simplifies local setup.
- Architecture diagram assets if they already exist in the workspace. If not, use Mermaid diagrams; do not block implementation waiting for image assets.

# 18. FIVE-DAY BUILD PRIORITIES

Day 1 — Foundation:
- Inspect workspace and establish the deployable repository structure.
- Create validated data/evidence models.
- Implement profile form, document extraction and GitHub enrichment.
- Configure Supabase schema and FastAPI skeleton.

Day 2 — Research:
- Confirm model/tool access using current Gemini documentation and an actual smoke test.
- Implement Google Search discovery, URL Context retrieval, evidence extraction and deduplication.
- Obtain genuine candidate opportunities and verify official pages.

Day 3 — Agents:
- Implement five agent roles and LangGraph workflow.
- Add deterministic eligibility/scoring logic, bounded correction loops and failure recovery.
- Persist research runs/events and stream them through SSE.

Day 4 — Product:
- Build profile, live workspace, shortlist, evidence details, gap planner and SOP workspace.
- Connect the complete user journey.
- Handle service cold starts, timeouts, data availability and error states.

Day 5 — Validation and submission:
- Run automated tests and a live integration smoke test.
- Test a second student and an injected retrieval failure.
- Audit the final results for real sources and supported eligibility claims.
- Finish documentation, environment setup and demo script.
- Verify clean-clone build and deployment configuration.

Prioritize the working end-to-end research pipeline over decorative UI features. Reduce polish or optional capabilities before compromising live research or evidence correctness.

# 19. DEFINITION OF DONE

The project is ready when:

1. The frontend builds and runs.
2. The FastAPI backend starts using documented commands.
3. A user can upload supported documents and enter a profile.
4. The Profile Intelligence Agent creates a validated student profile and uses GitHub data when supplied.
5. The Research & Eligibility Agent actually calls Gemini Google Search and URL Context.
6. The system discovers genuine candidates and verifies at least 10 distinct opportunities when reliable sources and quotas permit.
7. Important eligibility decisions have criterion-level evidence and explicit unknown states.
8. The Match Strategist generates the top five recommendations using the tested deterministic score.
9. The Application Coach generates an editable SOP.
10. The Quality Reviewer can flag findings and trigger correction/research.
11. The dashboard displays actual workflow events.
12. A deliberately failed retrieval can recover within configured limits while preserving valid results.
13. A different student profile changes relevant search/evaluation outputs.
14. Database records persist across backend sleeps/redeployments.
15. The repository has all required documentation and tests.
16. Cloudflare Pages, Render and Supabase setup is documented with the required environment variables.
17. The fresh-clone/local setup has been tested.
18. No fixtures are presented as live results, no secrets are committed, and no test/experiment result is falsely claimed.

# 20. HOW TO WORK

Begin by inspecting the current workspace.

Then:
1. Create a concise implementation checklist and file structure.
2. Implement the smallest working end-to-end workflow first.
3. Verify Gemini Search and URL Context access before building dependent features.
4. Create the database schema and API contracts early.
5. Build and test each module as it is added.
6. Run the full frontend and backend locally and fix errors.
7. Verify the production build and hosting configuration.
8. Finish documentation that reflects the actual implementation.

Do not just return the plan or dump a large amount of untested code. Implement the real files, run the code, execute the tests, inspect failures and correct them.

If you encounter a blocked API, missing credential or unavailable free-tier feature, document the exact blocker and implement the remaining functionality without pretending that the integration worked.

At completion, report:
- What was implemented.
- The exact run commands.
- The tests actually executed and their results.
- Which Gemini integrations were verified live.
- Which deployment settings remain.
- Any known limitation or unfinished requirement.
- How to reproduce the five-minute demo.

**Build ScholarSwarm as a reliable, evidence-first scholarship research product, not merely a chatbot or a polished frontend.**