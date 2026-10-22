# ScholarSwarm Five-Minute Hackathon Demonstration Script
## TetraNoodle AI Hackathon 2026

**Presenter Role**: AI Agent Architect & Full-Stack Engineer  
**Duration**: 5 Minutes Exactly (Timed)

---

### Segment 1: The Problem & Profile Ingestion (0:00 – 0:40)
- **Spoken Action**:
  "Judges, searching for international scholarships today is broken. Students either wade through outdated blog aggregators or use chatbots that hallucinate funding amounts and fake deadlines. Welcome to **ScholarSwarm**—where five autonomous AI agents collaborate to discover and verify real global scholarship opportunities."
- **Screen Action**:
  1. Open the dashboard at `http://localhost:5173`.
  2. Click **"Configure Student"**.
  3. Show the presets and select **"Rahul (8.2 CGPA • CS • AI Projects)"**.
  4. Point out the local resume/transcript parser and the verified GitHub handle (`rahul-sharma-ai`).
  5. Click **"Launch 5-Agent Research Cycle"**.

---

### Segment 2: Live Multi-Agent Swarm Execution (0:40 – 1:40)
- **Spoken Action**:
  "Look at our live agent timeline. These aren't fake progress animations—these are real Server-Sent Events streamed from LangGraph:
  - Agent 1 extracted Rahul's 8.2 CGPA, skills in PyTorch and FastAPI, and enriched his profile with verified GitHub repos.
  - Agent 2 formulated targeted queries using Tavily Search across Canada, Germany, and Singapore, then verified official pages through safe retrieval, discovering authentic degree programs.
  - Agent 3 is scoring candidates deterministically.
  - Agent 5 is independently auditing source citations."
- **Screen Action**:
  1. Highlight the 5 active agent status cards updating in real time.
  2. Scroll down the live execution terminal showing exact timestamps and agent actions (`SEARCH_QUERY`, `CANDIDATE_FOUND`, `ELIGIBILITY_EVALUATED`).

---

### Segment 3: Evidence-First Auditing & Source Links (1:40 – 2:40)
- **Spoken Action**:
  "Notice how ScholarSwarm proves its claims. Here are the discovered opportunities. Let's look at the **Vector Institute AI Master's at the University of Toronto** ($52,500 CAD package).
  Let's open the **Evidence Audit Drawer**."
- **Screen Action**:
  1. Click **"Evidence"** on the University of Toronto card.
  2. Walk through the criterion records:
     - **Academic Grade**: "8.2 CGPA meets the Canadian B+ minimum requirement."
     - **Language Test**: "Planned IELTS flagged as Unresolved with target score >= 7.0."
     - **Degree Level**: "Satisfied."
  3. Click the official link to show the actual `cs.toronto.edu` portal.

---

### Segment 4: Deterministic Match Scoring & Gap Planner (2:40 – 3:40)
- **Spoken Action**:
  "Unlike LLMs that pick arbitrary favorites, our Match Strategist uses a 100% deterministic Python scoring algorithm:
  - 35 points Academic Fit
  - 25 points Funding
  - 20 points Subject Fit
  - 10 points Deadline
  - 10 points Evidence Quality
  Notice that our hard disqualifier filter excludes confirmed ineligible programs from the Top 5.
  Below, our **Eligibility Gap Planner** synthesizes exact actionable next steps for the student."
- **Screen Action**:
  1. Point to the Top 5 banner and score breakdowns (e.g. 100/100, 94/100).
  2. Scroll to the **Eligibility Gap Planner** showing concrete tasks: e.g. "Complete IELTS before deadline; submit transcript for TUM Curricular Analysis."

---

### Segment 5: Application Coach SOP & Adaptability Test (3:40 – 5:00)
- **Spoken Action**:
  "Now, let's select an opportunity and prepare an application. Click **'Prepare SOP'**.
  Agent 4 synthesizes Rahul's actual machine learning projects and career goals with the University of Toronto curriculum. Crucially, it highlights **unconfirmed claims** requiring Rahul's verification—it never invents fake internships or hardships.
  Let's click **'Configure Student'**, load **Profile B (Biotechnology, 6.8 CGPA)**, and observe that lower grades immediately adapt search queries, eliminate competitive top awards, and identify accessible programs."
- **Screen Action**:
  1. Show the generated SOP in the modal, highlight the unconfirmed claims box, and click **"Copy Text"**.
  2. Switch to **Profile B**, re-run, and show how the shortlisted opportunities and eligibility statuses dynamically adapt.
  3. Conclude: "ScholarSwarm delivers verified, actionable, evidence-first academic research. Thank you!"
