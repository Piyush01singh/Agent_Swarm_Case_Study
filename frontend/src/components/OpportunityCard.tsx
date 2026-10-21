import React from 'react';
import {
  ExternalLink,
  ShieldCheck,
  Calendar,
  DollarSign,
  Award,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  BookOpen,
} from 'lucide-react';
import type { Opportunity } from '../types';

interface OpportunityCardProps {
  opportunity: Opportunity;
  onViewEvidence: (opp: Opportunity) => void;
  onGenerateSop: (opp: Opportunity) => void;
}

export const OpportunityCard: React.FC<OpportunityCardProps> = ({
  opportunity,
  onViewEvidence,
  onGenerateSop,
}) => {
  const score = opportunity.match_score?.total_score || 0;
  const isTopFive = opportunity.is_top_five;
  const status = opportunity.eligibility_status;

  const getStatusBadge = () => {
    switch (status) {
      case 'MEETS_STATED_CRITERIA':
        return (
          <span className="flex items-center gap-1 text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <CheckCircle2 className="h-3 w-3" /> Meets Stated Criteria
          </span>
        );
      case 'POTENTIAL_MATCH':
        return (
          <span className="flex items-center gap-1 text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <HelpCircle className="h-3 w-3" /> Potential Match
          </span>
        );
      case 'DOES_NOT_MEET':
        return (
          <span className="flex items-center gap-1 text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/20">
            <AlertCircle className="h-3 w-3" /> Does Not Meet
          </span>
        );
      default:
        return (
          <span className="flex items-center gap-1 text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-slate-700 text-slate-300">
            Insufficient Evidence
          </span>
        );
    }
  };

  return (
    <div
      className={`relative rounded-2xl border transition-all p-5 shadow-lg flex flex-col justify-between ${
        isTopFive
          ? 'bg-gradient-to-b from-slate-900 via-slate-900 to-slate-950 border-emerald-500/40 ring-1 ring-emerald-500/20'
          : 'bg-slate-900/80 border-slate-800'
      }`}
    >
      {/* Top Banner for Top 5 */}
      {isTopFive && (
        <div className="absolute -top-3 left-4 px-3 py-0.5 rounded-full bg-emerald-600 text-white text-[10px] font-bold uppercase tracking-wider flex items-center gap-1 shadow-md">
          <Award className="h-3 w-3" /> Top 5 Recommended Match
        </div>
      )}

      <div>
        {/* Header: Status & Score */}
        <div className="flex items-start justify-between gap-2 mb-3">
          <div className="flex flex-wrap items-center gap-2">
            {getStatusBadge()}
            <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
              {opportunity.country}
            </span>
          </div>

          <div className="flex flex-col items-end">
            <div className="flex items-baseline gap-1">
              <span className="text-xl font-black text-white">{score}</span>
              <span className="text-xs text-slate-400">/100</span>
            </div>
            <span className="text-[9px] text-slate-500 uppercase tracking-widest font-semibold">Match Score</span>
          </div>
        </div>

        {/* Program Title & University */}
        <h3 className="text-base font-bold text-white tracking-tight leading-snug">
          {opportunity.program_name}
        </h3>
        <p className="text-xs font-semibold text-emerald-400 mt-0.5">
          {opportunity.university}
        </p>

        {/* Opportunity Metadata Tags */}
        <div className="grid grid-cols-2 gap-2 my-3 text-xs">
          <div className="flex items-center gap-1.5 text-slate-300 bg-slate-800/50 p-2 rounded-lg border border-slate-800">
            <DollarSign className="h-3.5 w-3.5 text-emerald-400 shrink-0" />
            <span className="truncate text-[11px]" title={opportunity.funding_details.coverage_description}>
              {opportunity.funding_details.funding_type || 'Funding Available'}
            </span>
          </div>

          <div className="flex items-center gap-1.5 text-slate-300 bg-slate-800/50 p-2 rounded-lg border border-slate-800">
            <Calendar className="h-3.5 w-3.5 text-cyan-400 shrink-0" />
            <span className="truncate text-[11px]" title={opportunity.deadline || 'Deadline TBD'}>
              {opportunity.deadline ? `Deadline: ${opportunity.deadline}` : 'Deadline: Rolling/TBD'}
            </span>
          </div>
        </div>

        {/* Match Explanation */}
        {opportunity.match_score?.explanation && (
          <p className="text-xs text-slate-400 italic bg-slate-950/40 p-2.5 rounded-lg border border-slate-800/60 leading-relaxed mb-4">
            "{opportunity.match_score.explanation}"
          </p>
        )}
      </div>

      {/* Footer Actions */}
      <div className="pt-3 border-t border-slate-800 flex items-center justify-between gap-2 mt-auto">
        <a
          href={opportunity.canonical_url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-xs text-slate-400 hover:text-white flex items-center gap-1 font-medium transition"
        >
          <ExternalLink className="h-3.5 w-3.5" />
          <span>Official Portal</span>
        </a>

        <div className="flex items-center gap-2">
          <button
            onClick={() => onViewEvidence(opportunity)}
            className="px-3 py-1.5 rounded-lg text-xs font-semibold text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 border border-slate-700 flex items-center gap-1 transition"
          >
            <ShieldCheck className="h-3.5 w-3.5 text-cyan-400" />
            Evidence ({opportunity.evidence_records?.length ?? 0})
          </button>

          <button
            onClick={() => onGenerateSop(opportunity)}
            className="px-3 py-1.5 rounded-lg text-xs font-bold text-white bg-emerald-600 hover:bg-emerald-500 shadow-md shadow-emerald-700/20 flex items-center gap-1 transition"
          >
            <BookOpen className="h-3.5 w-3.5" />
            Prepare SOP
          </button>
        </div>
      </div>
    </div>
  );
};
