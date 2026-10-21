import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from app.db.supabase_client import get_supabase_client
from app.models.events import ResearchRun, AgentEvent
from app.models.opportunity import Opportunity
from app.models.evidence import EvidenceRecord
from app.models.sop import ApplicationDraft

# In-memory storage for local dev / tests / offline fallback
_memory_runs: Dict[str, ResearchRun] = {}
_memory_opportunities: Dict[str, Opportunity] = {} # opp_id -> Opportunity
_memory_evidence: Dict[str, List[EvidenceRecord]] = {} # opp_id -> list
_memory_events: Dict[str, List[AgentEvent]] = {} # run_id -> list
_memory_drafts: Dict[str, ApplicationDraft] = {} # opp_id -> draft

class Repository:
    def __init__(self):
        self.supabase = get_supabase_client()

    async def create_research_run(self, run: ResearchRun) -> ResearchRun:
        _memory_runs[run.id] = run
        _memory_events[run.id] = []
        
        client = get_supabase_client()
        if client:
            try:
                data = {
                    "id": run.id,
                    "created_at": run.created_at.isoformat(),
                    "updated_at": run.updated_at.isoformat(),
                    "status": run.status,
                    "student_profile": run.student_profile.model_dump(),
                    "current_phase": run.current_phase,
                    "research_round": run.research_round,
                    "total_candidates_found": run.total_candidates_found,
                    "total_verified": run.total_verified,
                    "error_message": run.error_message,
                    "retry_count": run.retry_count
                }
                client.table("research_runs").insert(data).execute()
            except Exception as e:
                print(f"Supabase insert error (using memory fallback): {e}")
        return run

    async def update_research_run_status(
        self,
        run_id: str,
        status: str,
        current_phase: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> Optional[ResearchRun]:
        run = _memory_runs.get(run_id)
        if run:
            run.status = status
            run.updated_at = datetime.utcnow()
            if current_phase:
                run.current_phase = current_phase
            if error_message:
                run.error_message = error_message
                
        client = get_supabase_client()
        if client:
            try:
                payload = {
                    "status": status,
                    "updated_at": datetime.utcnow().isoformat()
                }
                if current_phase:
                    payload["current_phase"] = current_phase
                if error_message:
                    payload["error_message"] = error_message
                client.table("research_runs").update(payload).eq("id", run_id).execute()
            except Exception as e:
                print(f"Supabase update error: {e}")
        return run

    async def get_research_run(self, run_id: str) -> Optional[ResearchRun]:
        if run_id in _memory_runs:
            run = _memory_runs[run_id]
            # Attach current opportunities
            run.opportunities = await self.get_opportunities(run_id)
            return run
            
        client = get_supabase_client()
        if client:
            try:
                res = client.table("research_runs").select("*").eq("id", run_id).execute()
                if res.data and len(res.data) > 0:
                    data = res.data[0]
                    from app.models.profile import StudentProfile
                    profile = StudentProfile(**data["student_profile"])
                    run = ResearchRun(
                        id=data["id"],
                        status=data["status"],
                        student_profile=profile,
                        current_phase=data.get("current_phase"),
                        research_round=data.get("research_round", 1),
                        total_candidates_found=data.get("total_candidates_found", 0),
                        total_verified=data.get("total_verified", 0),
                        error_message=data.get("error_message"),
                        retry_count=data.get("retry_count", 0)
                    )
                    run.opportunities = await self.get_opportunities(run_id)
                    _memory_runs[run_id] = run
                    return run
            except Exception as e:
                print(f"Supabase get run error: {e}")
        return None

    async def save_opportunities(self, run_id: str, opportunities: List[Opportunity]):
        for opp in opportunities:
            _memory_opportunities[opp.id] = opp
            
        client = get_supabase_client()
        if client:
            try:
                rows = []
                for opp in opportunities:
                    rows.append({
                        "id": opp.id,
                        "run_id": run_id,
                        "canonical_url": opp.canonical_url,
                        "title": opp.title,
                        "program_name": opp.program_name,
                        "university": opp.university,
                        "country": opp.country,
                        "degree_level": opp.degree_level,
                        "field": opp.field,
                        "intake": opp.intake,
                        "funding_type": opp.funding_details.funding_type,
                        "funding_coverage": opp.funding_details.coverage_description,
                        "funding_amount": opp.funding_details.amount,
                        "funding_currency": opp.funding_details.currency,
                        "deadline": opp.deadline,
                        "deadline_type": opp.deadline_type,
                        "deadline_verified": opp.deadline_verified,
                        "official_application_url": opp.official_application_url,
                        "official_source_urls": opp.official_source_urls,
                        "evidence_quality": opp.evidence_quality,
                        "eligibility_status": opp.eligibility_status,
                        "eligibility_reasons": opp.eligibility_reasons,
                        "match_score": opp.match_score.total_score if opp.match_score else 0,
                        "match_breakdown": opp.match_score.model_dump() if opp.match_score else {},
                        "match_explanation": opp.match_score.explanation if opp.match_score else "",
                        "is_top_five": opp.is_top_five,
                        "reviewer_status": opp.reviewer_status,
                        "reviewer_notes": opp.reviewer_notes
                    })
                if rows:
                    client.table("opportunities").upsert(rows).execute()
            except Exception as e:
                print(f"Supabase opportunities upsert error: {e}")

    async def get_opportunities(self, run_id: str) -> List[Opportunity]:
        opps = [opp for opp in _memory_opportunities.values() if opp.run_id == run_id]
        if opps:
            return sorted(opps, key=lambda x: (x.match_score.total_score if x.match_score else 0), reverse=True)
            
        client = get_supabase_client()
        if client:
            try:
                res = client.table("opportunities").select("*").eq("run_id", run_id).execute()
                opp_list = []
                for row in res.data or []:
                    from app.models.opportunity import FundingDetails, MatchScore
                    funding = FundingDetails(
                        funding_type=row.get("funding_type", "Unknown"),
                        coverage_description=row.get("funding_coverage", "TBD"),
                        amount=row.get("funding_amount"),
                        currency=row.get("funding_currency")
                    )
                    score = MatchScore(**row.get("match_breakdown", {})) if row.get("match_breakdown") else None
                    opp = Opportunity(
                        id=row["id"],
                        run_id=row["run_id"],
                        canonical_url=row["canonical_url"],
                        title=row["title"],
                        program_name=row["program_name"],
                        university=row["university"],
                        country=row["country"],
                        degree_level=row["degree_level"],
                        field=row["field"],
                        intake=row.get("intake"),
                        funding_details=funding,
                        deadline=row.get("deadline"),
                        deadline_type=row.get("deadline_type", "Unknown"),
                        deadline_verified=row.get("deadline_verified", False),
                        official_application_url=row.get("official_application_url"),
                        official_source_urls=row.get("official_source_urls", []),
                        evidence_quality=row.get("evidence_quality", "UNVERIFIED"),
                        eligibility_status=row.get("eligibility_status", "INSUFFICIENT_EVIDENCE"),
                        eligibility_reasons=row.get("eligibility_reasons", []),
                        match_score=score,
                        is_top_five=row.get("is_top_five", False),
                        reviewer_status=row.get("reviewer_status", "PENDING"),
                        reviewer_notes=row.get("reviewer_notes")
                    )
                    _memory_opportunities[opp.id] = opp
                    opp_list.append(opp)
                return sorted(opp_list, key=lambda x: (x.match_score.total_score if x.match_score else 0), reverse=True)
            except Exception as e:
                print(f"Supabase get opportunities error: {e}")
        return []

    async def get_opportunity_by_id(self, opp_id: str) -> Optional[Opportunity]:
        if opp_id in _memory_opportunities:
            return _memory_opportunities[opp_id]
        client = get_supabase_client()
        if client:
            try:
                res = client.table("opportunities").select("*").eq("id", opp_id).execute()
                if res.data and len(res.data) > 0:
                    row = res.data[0]
                    run_id = row.get("run_id")
                    if run_id:
                        opps = await self.get_opportunities(run_id)
                        for opp in opps:
                            if opp.id == opp_id:
                                return opp
                    # Direct deserialization fallback
                    from app.models.opportunity import FundingDetails, MatchScore
                    funding = FundingDetails(
                        funding_type=row.get("funding_type", "Unknown"),
                        coverage_description=row.get("funding_coverage", "TBD"),
                        amount=row.get("funding_amount"),
                        currency=row.get("funding_currency")
                    )
                    score = MatchScore(**row.get("match_breakdown", {})) if row.get("match_breakdown") else None
                    opp = Opportunity(
                        id=row["id"],
                        run_id=row.get("run_id", ""),
                        canonical_url=row["canonical_url"],
                        title=row["title"],
                        program_name=row["program_name"],
                        university=row["university"],
                        country=row["country"],
                        degree_level=row["degree_level"],
                        field=row["field"],
                        intake=row.get("intake"),
                        funding_details=funding,
                        deadline=row.get("deadline"),
                        deadline_type=row.get("deadline_type", "Unknown"),
                        deadline_verified=row.get("deadline_verified", False),
                        official_application_url=row.get("official_application_url"),
                        official_source_urls=row.get("official_source_urls", []),
                        evidence_quality=row.get("evidence_quality", "UNVERIFIED"),
                        eligibility_status=row.get("eligibility_status", "INSUFFICIENT_EVIDENCE"),
                        eligibility_reasons=row.get("eligibility_reasons", []),
                        match_score=score,
                        is_top_five=row.get("is_top_five", False),
                        reviewer_status=row.get("reviewer_status", "PENDING"),
                        reviewer_notes=row.get("reviewer_notes")
                    )
                    _memory_opportunities[opp.id] = opp
                    return opp
            except Exception as e:
                print(f"Supabase get_opportunity_by_id error: {e}")
        return None

    async def save_evidence_records(self, records: List[EvidenceRecord]):
        for r in records:
            if not r.id:
                r.id = str(uuid.uuid4())
            if r.opportunity_id not in _memory_evidence:
                _memory_evidence[r.opportunity_id] = []
            existing_ids = {item.id for item in _memory_evidence[r.opportunity_id]}
            if r.id not in existing_ids:
                _memory_evidence[r.opportunity_id].append(r)

        client = get_supabase_client()
        if client:
            try:
                rows = []
                for r in records:
                    rows.append({
                        "id": r.id,
                        "opportunity_id": r.opportunity_id,
                        "run_id": r.run_id,
                        "criterion_name": r.criterion_name,
                        "stated_requirement": r.stated_requirement,
                        "student_value": r.student_value,
                        "status": r.status,
                        "evidence_excerpt": r.evidence_excerpt,
                        "source_title": r.source_title,
                        "source_url": r.source_url,
                        "source_category": r.source_category,
                        "checked_at": r.checked_at.isoformat() if hasattr(r.checked_at, "isoformat") else str(r.checked_at),
                        "uncertainty_or_conflict": r.uncertainty_or_conflict
                    })
                if rows:
                    client.table("evidence_records").upsert(rows).execute()
            except Exception as e:
                print(f"Supabase evidence_records upsert error: {e}")

    async def get_evidence_for_opportunity(self, opp_id: str) -> List[EvidenceRecord]:
        if opp_id in _memory_evidence and _memory_evidence[opp_id]:
            return _memory_evidence[opp_id]
        client = get_supabase_client()
        if client:
            try:
                res = client.table("evidence_records").select("*").eq("opportunity_id", opp_id).execute()
                if res.data:
                    records = []
                    for row in res.data:
                        checked_at_val = row.get("checked_at")
                        parsed_checked = datetime.fromisoformat(checked_at_val.replace("Z", "+00:00")) if checked_at_val else datetime.now(timezone.utc)
                        rec = EvidenceRecord(
                            id=row.get("id"),
                            opportunity_id=row.get("opportunity_id"),
                            run_id=row.get("run_id"),
                            criterion_name=row.get("criterion_name", ""),
                            stated_requirement=row.get("stated_requirement", ""),
                            student_value=row.get("student_value"),
                            status=row.get("status", "UNRESOLVED"),
                            evidence_excerpt=row.get("evidence_excerpt"),
                            source_title=row.get("source_title"),
                            source_url=row.get("source_url", ""),
                            source_category=row.get("source_category", "OFFICIAL"),
                            checked_at=parsed_checked,
                            uncertainty_or_conflict=row.get("uncertainty_or_conflict")
                        )
                        records.append(rec)
                    _memory_evidence[opp_id] = records
                    return records
            except Exception as e:
                print(f"Supabase get evidence error: {e}")
        return _memory_evidence.get(opp_id, [])

    async def get_evidence_records(
        self,
        run_id: Optional[str] = None,
        opportunity_id: Optional[str] = None
    ) -> List[EvidenceRecord]:
        """Loads evidence records filtered by opportunity_id or run_id."""
        if opportunity_id:
            return await self.get_evidence_for_opportunity(opportunity_id)
        
        if run_id:
            matched: List[EvidenceRecord] = []
            for records_list in _memory_evidence.values():
                for rec in records_list:
                    if rec.run_id == run_id and rec not in matched:
                        matched.append(rec)
            if matched:
                return matched

            client = get_supabase_client()
            if client:
                try:
                    res = client.table("evidence_records").select("*").eq("run_id", run_id).execute()
                    if res.data:
                        records = []
                        for row in res.data:
                            checked_at_val = row.get("checked_at")
                            parsed_checked = datetime.fromisoformat(checked_at_val.replace("Z", "+00:00")) if checked_at_val else datetime.now(timezone.utc)
                            rec = EvidenceRecord(
                                id=row.get("id"),
                                opportunity_id=row.get("opportunity_id"),
                                run_id=row.get("run_id"),
                                criterion_name=row.get("criterion_name", ""),
                                stated_requirement=row.get("stated_requirement", ""),
                                student_value=row.get("student_value"),
                                status=row.get("status", "UNRESOLVED"),
                                evidence_excerpt=row.get("evidence_excerpt"),
                                source_title=row.get("source_title"),
                                source_url=row.get("source_url", ""),
                                source_category=row.get("source_category", "OFFICIAL"),
                                checked_at=parsed_checked,
                                uncertainty_or_conflict=row.get("uncertainty_or_conflict")
                            )
                            records.append(rec)
                        return records
                except Exception as e:
                    print(f"Supabase get_evidence_records by run_id error: {e}")
        return []

    async def save_agent_event(self, event: AgentEvent):
        if not event.id:
            event.id = str(uuid.uuid4())
        if event.run_id not in _memory_events:
            _memory_events[event.run_id] = []
        event.sequence_number = len(_memory_events[event.run_id]) + 1
        _memory_events[event.run_id].append(event)
        
        client = get_supabase_client()
        if client:
            try:
                row = {
                    "id": event.id,
                    "run_id": event.run_id,
                    "sequence_number": event.sequence_number,
                    "agent_role": event.agent_role,
                    "event_type": event.event_type,
                    "title": event.title,
                    "description": event.description,
                    "metadata": event.metadata
                }
                client.table("agent_events").insert(row).execute()
            except Exception as e:
                print(f"Supabase event save error: {e}")

    async def get_agent_events(self, run_id: str, after_seq: Optional[int] = None) -> List[AgentEvent]:
        events = _memory_events.get(run_id, [])
        if after_seq is not None:
            return [e for e in events if (e.sequence_number or 0) > after_seq]
        return events

    async def save_application_draft(self, draft: ApplicationDraft):
        if not draft.id:
            draft.id = str(uuid.uuid4())
        _memory_drafts[draft.opportunity_id] = draft
        
        client = get_supabase_client()
        if client:
            try:
                row = {
                    "id": draft.id,
                    "opportunity_id": draft.opportunity_id,
                    "run_id": draft.run_id,
                    "title": draft.title,
                    "program_name": draft.program_name,
                    "university": draft.university,
                    "sop_content": draft.sop_content,
                    "unconfirmed_claims": draft.unconfirmed_claims,
                    "is_reviewed_by_agent": draft.is_reviewed_by_agent,
                    "reviewer_feedback": draft.reviewer_feedback,
                    "word_count": draft.word_count
                }
                client.table("application_drafts").upsert(row).execute()
            except Exception as e:
                print(f"Supabase SOP draft error: {e}")

    async def get_application_draft(self, opp_id: str) -> Optional[ApplicationDraft]:
        return _memory_drafts.get(opp_id)

    async def reset_all_data(self):
        """Reset data for clean test runs or user demo reset."""
        _memory_runs.clear()
        _memory_opportunities.clear()
        _memory_evidence.clear()
        _memory_events.clear()
        _memory_drafts.clear()

repository = Repository()
