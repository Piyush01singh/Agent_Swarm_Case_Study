import React from 'react';
import { AlertCircle, CheckCircle2, ChevronRight, HelpCircle } from 'lucide-react';
import type { Opportunity } from '../types';

interface GapPlannerProps {
  opportunities: Opportunity[];
}

export const GapPlanner: React.FC<GapPlannerProps> = ({ opportunities }) => {
  const allGaps: { opp: string; gap: string }[] = [];
  opportunities.forEach((o) => {
    (o.actionable_gaps || []).forEach((g) => {
      allGaps.push({ opp: `${o.university} (${o.program_name})`, gap: g });
    });
  });

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl">
      <div className="flex items-center justify-between pb-4 border-b border-slate-800">
        <div>
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            <AlertCircle className="h-4 w-4 text-amber-400" />
            Eligibility Gap Planner & Roadmap
          </h2>
          <p className="text-xs text-slate-400">
            Actionable requirements and missing documents to resolve before formal application submission.
          </p>
        </div>
        <span className="text-[11px] font-mono px-2.5 py-1 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
          {allGaps.length} Actionable Items
        </span>
      </div>

      <div className="mt-4 space-y-3">
        {allGaps.length === 0 ? (
          <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 shrink-0" />
            <span>No unresolved eligibility gaps found. Profile fully satisfies mandatory stated criteria across opportunities!</span>
          </div>
        ) : (
          allGaps.map((item, idx) => (
            <div
              key={idx}
              className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 flex items-start gap-3 text-xs"
            >
              <div className="h-6 w-6 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400 shrink-0 mt-0.5">
                <HelpCircle className="h-3.5 w-3.5" />
              </div>
              <div className="flex-1">
                <div className="font-semibold text-white">{item.gap}</div>
                <div className="text-[11px] text-emerald-400 mt-0.5 flex items-center gap-1">
                  <ChevronRight className="h-3 w-3" />
                  Target: {item.opp}
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
