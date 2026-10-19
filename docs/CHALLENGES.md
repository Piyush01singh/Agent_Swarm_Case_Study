# Engineering Challenges & Technical Post-Mortem
## TetraNoodle AI Hackathon 2026

### 1. The Real Technical Challenge: Pydantic Datetime Serialization across LangGraph Nodes & Gemini Service

#### What Happened
During implementation of the LangGraph workflow and Quality Reviewer execution (`node_quality_reviewer` passing opportunity data to `gemini_service.review_evidence_and_claims`), tests threw a serialization runtime error:
`TypeError: Object of type datetime is not JSON serializable`

#### The Failed Initial Approach
The initial code used standard `opportunity.model_dump()` from Pydantic v2. While `model_dump()` returns a native Python dictionary, fields typed as `datetime` (such as `created_at` and `checked_at`) remain raw `datetime.datetime` objects. Passing this dictionary directly to standard `json.dumps()` in prompt construction caused a serialization failure inside the LangGraph async runner tick.

#### Debugging & Root Cause Analysis
Inspecting the traceback in `task-145` revealed that `json.dumps(opportunity_data)` failed inside `review_evidence_and_claims`:
```python
File "json/encoder.py", line 180, in default
TypeError: Object of type datetime is not JSON serializable
During task with name 'quality_reviewer'
```
Pydantic v2 provides two distinct dump mechanisms:
1. `model.model_dump()`: returns raw python types (`datetime`, `UUID`, etc.).
2. `model.model_dump(mode='json')`: converts all non-primitive fields into JSON-compatible primitives (`ISO 8601 strings`, etc.).

#### Solution
1. Changed `opportunity.model_dump()` to `opportunity.model_dump(mode='json')` in `QualityReviewerAgent.execute_audit`.
2. Added `default=str` fallback to all internal `json.dumps(..., default=str)` calls in `gemini_service.py` as defense-in-depth against arbitrary object types.
3. Updated URL normalization to ensure paths are cleanly lowercased, guaranteeing deterministic deduplication across HTTP redirect variations.

#### Remaining Limitation
While `mode='json'` serializes datetimes reliably, high-concurrency requests on Render free tier must still be bounded to avoid exhausting memory when processing large document payloads simultaneously.

---

### 2. URL SSRF and Tracking Parameter Collisions
- **Issue**: Google Search grounding returns candidate URLs containing varied affiliate query strings (e.g. `?utm_source=google`, `?fbclid=...`, trailing slashes, capitalizations), leading to duplicate opportunity records in the database.
- **Solution**: Implemented `normalize_url` in `app/security/sanitizer.py` which lowercases host/path, strips tracking query parameters, and strips fragments before evaluating canonical identity.
