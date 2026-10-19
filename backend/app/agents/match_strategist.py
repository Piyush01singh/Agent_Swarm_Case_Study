from typing import List
from app.models.profile import StudentProfile
from app.models.opportunity import Opportunity
from app.models.events import AgentEvent
from app.services.scoring_service import calculate_match_score
from app.db.repository import repository

class MatchStrategistAgent:
    """
    Agent 3: Match Strategist Agent
    Ranks opportunities transparently using deterministic scoring functions,
    enforces hard eligibility filters, and isolates the top 5 recommendations.
    """
    def __init__(self):
        self.role_name = "Match Strategist Agent"

    async def execute_ranking(
        self,
        run_id: str,
        profile: StudentProfile,
        opportunities: List[Opportunity]
    ) -> List[Opportunity]:
        await repository.save_agent_event(AgentEvent(
            run_id=run_id,
            agent_role=self.role_name,
            event_type="SCORE_CALCULATED",
            title="Evaluating Deterministic Fit Scores",
            description="Calculating multidimensional match scores (0-100) across Academic (35), Funding (25), Subject (20), Deadline (10), and Evidence (10)."
        ))

        scored_opportunities: List[Opportunity] = []
        for opp in opportunities:
            score = calculate_match_score(profile, opp)
            opp.match_score = score
            scored_opportunities.append(opp)

        # Sort: eligible opportunities with highest scores first, followed by ineligible
        eligible_opps = [o for o in scored_opportunities if o.match_score and o.match_score.is_eligible_for_shortlist]
        ineligible_opps = [o for o in scored_opportunities if not (o.match_score and o.match_score.is_eligible_for_shortlist)]

        eligible_opps.sort(key=lambda x: (x.match_score.total_score if x.match_score else 0), reverse=True)
        ineligible_opps.sort(key=lambda x: (x.match_score.total_score if x.match_score else 0), reverse=True)

        # Mark top 5 in eligible list
        for i, opp in enumerate(eligible_opps):
            opp.is_top_five = (i < 5)

        ranked_list = eligible_opps + ineligible_opps

        top_five_names = [f"{o.university} ({o.match_score.total_score} pts)" for o in eligible_opps[:5]]
        await repository.save_agent_event(AgentEvent(
            run_id=run_id,
            agent_role=self.role_name,
            event_type="SHORTLIST_RANKED",
            title=f"Ranked Top 5 Opportunities (Total Candidates: {len(ranked_list)})",
            description=f"Identified top 5 recommendations: {', '.join(top_five_names)}.",
            metadata={"top_five_count": min(5, len(eligible_opps)), "eligible_count": len(eligible_opps), "disqualified_count": len(ineligible_opps)}
        ))

        # Save to database
        await repository.save_opportunities(run_id, ranked_list)
        return ranked_list
