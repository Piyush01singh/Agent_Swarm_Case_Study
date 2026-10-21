import React from 'react';
import { X, ExternalLink, CheckCircle2, AlertCircle, HelpCircle, ShieldCheck, Clock } from 'lucide-react';
import type { Opportunity } from '../types';

interface EvidenceDrawerProps {
  opportunity: Opportunity | null;
  onClose: () => void;
}

export const EvidenceDrawer: React.FC<EvidenceDrawerProps> = ({
  opportunity,
  onClose,
}) => {
  if (!opportunity) return null;

  const records = opportunity.evidence_records || [];

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-black/70 backdrop-blur-sm flex justify-end">
      <div className="relative w-full max-w-xl bg-slate-900 border-l border-slate-800 h-full p-6 sm:p-8 flex flex-col shadow-2xl overflow-y-auto">
        
        {/* Drawer Header */}
        <div className="flex items-start justify-between pb-4 border-b border-slate-800">
          <div>
            <span className="text-[10px] font-bold uppercase tracking-widest text-emerald-400">
              Audit Evidence Details
            </span>
            <h2 className="text-lg font-bold text-white tracking-tight mt-1">
              {opportunity.program_name}
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              {opportunity.university} • {opportunity.country}
            </p>
          </div>
          <button onClick={onClose} className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800">
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Evidence Status Summary */}
        <div className="my-5 p-4 rounded-xl bg-slate-800/40 border border-slate-800">
          <div className="flex items-center justify-between text-xs mb-2">
            <span className="text-slate-400 font-semibold">Evidence Quality Tier:</span>
            <span className="font-bold text-emerald-400 flex items-center gap-1">
              <ShieldCheck className="h-3.5 w-3.5" />
              {opportunity.evidence_quality || 'UNVERIFIED'}
            </span>
          </div>
          <div className="flex items-center justify-between text-xs">
            <span className="text-slate-400 font-semibold">Verified Official Source:</span>
            <a
              href={opportunity.canonical_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-cyan-400 hover:underline flex items-center gap-1 font-mono text-[11px] truncate max-w-[220px]"
            >
              {opportunity.canonical_url}
              <ExternalLink className="h-3 w-3 shrink-0" />
            </a>
          </div>
        </div>

        {/* Evidence Criteria Records List */}
        <div className="space-y-4 flex-1">
          <h3 className="text-xs font-bold text-white uppercase tracking-wider">
            Criterion-Level Grounding ({records.length} Checked)
          </h3>

          {records.length === 0 ? (
            <p className="text-xs text-slate-500 italic">No criterion records generated.</p>
          ) : (
            records.map((rec, index) => {
              const isMeets = rec.status === 'MEETS';
              const isUnresolved = rec.status === 'UNRESOLVED';
              const isFails = rec.status === 'DOES_NOT_MEET';

              return (
                <div
                  key={rec.id || index}
                  className="p-4 rounded-xl bg-slate-950 border border-slate-800/80 space-y-2.5"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs font-bold text-white tracking-tight">
                      {rec.criterion_name}
                    </span>
                    {isMeets && (
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1">
                        <CheckCircle2 className="h-3 w-3" /> Satisfied
                      </span>
                    )}
                    {isUnresolved && (
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20 flex items-center gap-1">
                        <HelpCircle className="h-3 w-3" /> Unresolved
                      </span>
                    )}
                    {isFails && (
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/20 flex items-center gap-1">
                        <AlertCircle className="h-3 w-3" /> Disqualified
                      </span>
                    )}
                  </div>

                  <div className="text-xs space-y-1 bg-slate-900/60 p-2.5 rounded-lg border border-slate-800/60">
                    <div className="text-slate-400">
                      <span className="font-semibold text-slate-300">Stated Policy: </span>
                      {rec.stated_requirement}
                    </div>
                    {rec.student_value && (
                      <div className="text-slate-400">
                        <span className="font-semibold text-slate-300">Student Profile: </span>
                        <span className="text-emerald-300">{rec.student_value}</span>
                      </div>
                    )}
                  </div>

                  {rec.evidence_excerpt && (
                    <div className="text-[11px] text-slate-400 italic bg-slate-900/40 p-2 rounded border border-slate-800/40">
                      <span className="font-semibold not-italic text-slate-300 block mb-0.5">Audit Excerpt:</span>
                      "{rec.evidence_excerpt}"
                    </div>
                  )}

                  <div className="flex items-center justify-between text-[10px] text-slate-500 pt-1">
                    <span className="flex items-center gap-1">
                      <Clock className="h-2.5 w-2.5" />
                      Checked: {new Date(rec.checked_at).toLocaleDateString()}
                    </span>
                    <a
                      href={rec.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-cyan-400 hover:underline flex items-center gap-1"
                    >
                      Source Link <ExternalLink className="h-2.5 w-2.5" />
                    </a>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Actionable Gaps */}
        {opportunity.actionable_gaps && opportunity.actionable_gaps.length > 0 && (
          <div className="mt-6 pt-4 border-t border-slate-800">
            <h4 className="text-xs font-bold text-amber-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
              <AlertCircle className="h-3.5 w-3.5" /> Actionable Next Steps
            </h4>
            <ul className="space-y-1.5 text-xs text-slate-300 list-disc list-inside">
              {opportunity.actionable_gaps.map((gap, i) => (
                <li key={i}>{gap}</li>
              ))}
            </ul>
          </div>
        )}

      </div>
    </div>
  );
};
