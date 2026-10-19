# Hackathon Technical Interview Preparation & Defense Guide
## ScholarSwarm | TetraNoodle AI Hackathon 2026

Concise, high-conviction answers explaining architecture decisions, trade-offs, and design rationale.

---

### 1. Explain ScholarSwarm in 30 seconds.
"ScholarSwarm is an autonomous, evidence-first scholarship intelligence platform. Instead of generic search engines or unreliable chatbots, five collaborating AI agents coordinated by LangGraph read a student's actual resume, transcripts, and GitHub repositories. They use live Gemini Google Search grounding to discover genuine university programs, verify criterion-level admissions policies against official university domains, calculate a transparent 0-100 deterministic match score, and draft a grounded Statement of Purpose without hallucinations."

---

### 2. What is an AI agent?
"An AI agent is an autonomous software component with a designated role, explicit boundary of responsibility, access to tools, and the capability to observe state, reason, make decisions, and interact with other agents or databases to accomplish a goal."

---

### 3. Why five agent roles?
"Five roles reflect the distinct domains of academic application research:
1. **Profile Intelligence**: Document understanding and credential extraction.
2. **Research & Eligibility**: Web discovery and official page extraction.
3. **Match Strategist**: Deterministic ranking and shortlisting.
4. **Application Coach**: Personalized document preparation.
5. **Quality Reviewer**: Independent adversarial auditing.
Combining them into one mega-prompt causes instruction drift and ungrounded claims; splitting them into dozens causes coordination overhead and latency."

---

### 4. Why combine discovery and eligibility into Agent 2?
"Discovery and eligibility verification operate on the exact same research context: the university program page and its admissions regulations. Having a separate scout find a URL and a separate auditor re-fetch the same page wastes token budgets, multiplies network latency, and risks context fragmentation."

---

### 5. How do agents communicate?
"Agents communicate strictly through a **typed shared state (`SwarmState`)** in LangGraph. Outputs from each agent are validated using strict Pydantic models (`StudentProfile`, `Opportunity`, `EvidenceRecord`, `MatchScore`), preventing unstructured text hallucination from contaminating downstream nodes."

---

### 6. Why LangGraph rather than CrewAI?
"CrewAI is primarily designed for autonomous role-play with loose coordination and opaque looping. LangGraph provides a **deterministic, cyclically bounded state machine** with explicit conditional edges, granular retry control, typed state transitions, and first-class async execution suited for production-grade APIs."

---

### 7. Why Gemini Search grounding + URL Context rather than Tavily, Firecrawl, or custom scrapers?
"Gemini Google Search grounding integrates directly with Google's search index natively within the model call, returning real grounding citations without requiring secondary paid subscription services like Tavily or Firecrawl. URL Context allows direct page analysis within the same tool ecosystem, minimizing infrastructure footprint."

---

### 8. Why `gemini-2.5-flash` and how were free-tier requirements checked?
"`gemini-2.5-flash` offers state-of-the-art token efficiency, low latency, native JSON schema support, and full compatibility with Google Search grounding within the standard API tier. Crucially, model name is made configurable via `GEMINI_MODEL` so teams can adapt without changing business logic."

---

### 9. Why React + Vite rather than Next.js?
"ScholarSwarm has a dedicated Python FastAPI backend that manages long-running LangGraph agent cycles, Server-Sent Events, and PDF extraction. A pure React + Vite SPA provides instant build speeds, zero server-side rendering complexity, and free global edge distribution on Cloudflare Pages without duplicate backend runtimes."

---

### 10. Why Python + FastAPI?
"Python is the standard language for LangGraph, Pydantic, PyMuPDF, and AI orchestration. FastAPI provides high-performance asynchronous event streaming (SSE), strict Pydantic request/response validation, automatic OpenAPI docs, and native compatibility with Render free web services."

---

### 11. Why Supabase rather than SQLite for deployment?
"Render's free web services run on ephemeral containers that sleep after inactivity and discard local disk modifications upon restarting. An external Supabase PostgreSQL database ensures research runs, opportunity evidence, and agent event histories persist across container sleeps and redeployments."

---

### 12. Why Pydantic?
"Pydantic provides runtime validation, schema enforcement, and type safety for every data boundary: API inputs, external LLM outputs, database records, and LangGraph state. In Pydantic v2, `model_dump(mode='json')` guarantees clean serialization of dates and complex structures."

---

### 13. Why Server-Sent Events (SSE)?
"Agent research is a long-running, multi-step asynchronous workflow. WebSockets require bidirectional protocol negotiation and stateful connection management, whereas SSE runs over standard HTTP, supports automatic client reconnection, traverses corporate firewalls effortlessly, and streams real-time agent execution events with sequence numbers."

---

### 14. How is the match score calculated?
"The match score is **100% deterministic code**:
- Academic & Eligibility Fit: 35 points
- Funding Coverage & Suitability: 25 points
- Subject & Program Fit: 20 points
- Deadline & Readiness: 10 points
- Evidence Quality & Freshness: 10 points
Total: 0 to 100 points. The LLM explains the fit; it is forbidden from altering the numerical score."

---

### 15. How are official sources verified?
"A source is classified as `OFFICIAL` only when its domain corresponds to a certified university (`.edu`, `.ac.*`), official government scholarship board (`.gov`, `.gc.ca`, `daad.de`), or recognized research institute (`vectorinstitute.ai`, `a-star.edu.sg`). Generic blog aggregators are flagged as `SECONDARY`."

---

### 16. How are hallucinations handled?
"1. Constrained JSON schemas on LLM outputs.
2. Criterion-level evidence records requiring stated requirement, student fact, status, and citation excerpt.
3. Quality Reviewer Agent (Agent 5) independently auditing claims.
4. Hard Python filters barring ungrounded claims from being marked satisfied."

---

### 17. How does retry and recovery work?
"If an opportunity lacks critical official evidence, Agent 5 flags it and routes execution back to Agent 2 via a LangGraph conditional edge. The loop is strictly bounded to a maximum of 2 rounds to prevent infinite cycles."

---

### 18. What happens if a whole research branch fails?
"LangGraph maintains partial state. If search discovery fails for one country (e.g. Germany network timeout), results already collected for Canada and Singapore are preserved, and the workflow completes with partial status rather than failing entirely."

---

### 19. What security and privacy risks exist?
"1. **SSRF**: Discovered URLs are validated against private, link-local, and loopback IP ranges before retrieval.
2. **Student Privacy**: Uploaded resumes and transcripts are parsed locally in memory; raw files are not persisted or sent to external search vendors.
3. **Prompt Injection**: Extracted resume and webpage text is treated strictly as untrusted data inside delimiters, preventing user text from overriding system instructions."

---

### 20. How do you know that a result is correct?
"Because every recommendation is anchored to an inspectable `EvidenceRecord` showing:
- Exact stated policy from the official university portal.
- Student's verified metric.
- Explicit comparison verdict (`MEETS`, `DOES_NOT_MEET`, or `UNRESOLVED`).
- Clickable official source link with timestamp."
