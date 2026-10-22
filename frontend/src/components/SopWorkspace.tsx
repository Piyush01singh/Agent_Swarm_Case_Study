import React, { useState, useEffect } from 'react';
import { X, Copy, Check, Download, AlertTriangle, FileEdit, RefreshCw } from 'lucide-react';
import type { Opportunity, ApplicationDraft } from '../types';
import { generateSopDraft } from '../api/client';

interface SopWorkspaceProps {
  opportunity: Opportunity | null;
  runId: string;
  onClose: () => void;
}

export const SopWorkspace: React.FC<SopWorkspaceProps> = ({
  opportunity,
  runId,
  onClose,
}) => {
  const [draft, setDraft] = useState<ApplicationDraft | null>(null);
  const [content, setContent] = useState<string>("");
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isCopied, setIsCopied] = useState<boolean>(false);
  const userNotes = "";

  useEffect(() => {
    if (!opportunity) return;
    let cancelled = false;

    generateSopDraft(opportunity.id, runId, userNotes)
      .then((generated) => {
        if (!cancelled) {
          setDraft(generated);
          setContent(generated.sop_content);
        }
      })
      .catch((err) => {
        console.error("Failed to generate SOP draft:", err);
      })
      .finally(() => {
        if (!cancelled) {
          setIsLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [opportunity, runId]);

  if (!opportunity) return null;

  const handleCopy = () => {
    navigator.clipboard.writeText(content);
    setIsCopied(true);
    setTimeout(() => setIsCopied(false), 2000);
  };

  const handleDownload = () => {
    const element = document.createElement("a");
    const file = new Blob([content], { type: 'text/plain' });
    element.href = URL.createObjectURL(file);
    element.download = `SOP_${opportunity.university.replace(/\s+/g, '_')}.txt`;
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="relative bg-slate-900 border border-slate-800 rounded-2xl max-w-4xl w-full p-6 sm:p-8 shadow-2xl flex flex-col max-h-[90vh]">
        
        {/* Header */}
        <div className="flex items-start justify-between pb-4 border-b border-slate-800">
          <div>
            <span className="text-[10px] font-bold uppercase tracking-widest text-emerald-400 flex items-center gap-1">
              <FileEdit className="h-3 w-3" /> Agent 4: Application Coach
            </span>
            <h2 className="text-xl font-bold text-white tracking-tight mt-1">
              Statement of Purpose (SOP) Generator
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Personalized draft for <span className="text-emerald-300 font-semibold">{opportunity.program_name}</span> at {opportunity.university}.
            </p>
          </div>
          <button onClick={onClose} className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800">
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Workspace Body */}
        <div className="flex-1 overflow-y-auto py-4 space-y-4">
          
          {/* Unconfirmed Claims Banner */}
          {draft && draft.unconfirmed_claims.length > 0 && (
            <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 text-xs">
              <h4 className="font-bold text-amber-300 flex items-center gap-1.5 mb-2">
                <AlertTriangle className="h-4 w-4" /> Student Verification Required
              </h4>
              <p className="text-slate-300 text-[11px] mb-2">
                The Application Coach does not invent accomplishments or motivations. Please review and confirm these specific points before submitting:
              </p>
              <ul className="list-disc list-inside space-y-1 text-slate-300 text-[11px]">
                {draft.unconfirmed_claims.map((claim, idx) => (
                  <li key={idx}><span className="text-amber-200 font-medium">{claim}</span></li>
                ))}
              </ul>
            </div>
          )}

          {/* Editable SOP Textarea */}
          <div>
            <div className="flex items-center justify-between text-xs text-slate-400 mb-2">
              <span className="font-semibold text-slate-300">Editable Application Statement</span>
              <span>Word Count: {content.trim().split(/\s+/).filter(Boolean).length} words</span>
            </div>
            
            {isLoading ? (
              <div className="h-80 rounded-xl bg-slate-950 border border-slate-800 flex flex-col items-center justify-center gap-3 text-slate-400 text-xs">
                <RefreshCw className="h-6 w-6 text-emerald-400 animate-spin" />
                <span>Synthesizing student profile with program objectives...</span>
              </div>
            ) : (
              <textarea
                value={content}
                onChange={(e) => setContent(e.target.value)}
                rows={14}
                className="w-full rounded-xl bg-slate-950 border border-slate-800 p-4 font-serif text-sm text-slate-200 leading-relaxed focus:outline-none focus:border-emerald-500/80 shadow-inner"
              />
            )}
          </div>

          <div className="text-[11px] text-slate-500 italic">
            * ScholarSwarm is a research assistance product. It does not automatically submit applications to universities.
          </div>
        </div>

        {/* Footer Actions */}
        <div className="pt-4 border-t border-slate-800 flex items-center justify-between">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg text-xs font-semibold text-slate-400 hover:text-white"
          >
            Close
          </button>

          <div className="flex items-center gap-2">
            <button
              onClick={handleCopy}
              className="px-4 py-2 rounded-lg text-xs font-semibold text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 border border-slate-700 flex items-center gap-1.5 transition"
            >
              {isCopied ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
              {isCopied ? 'Copied' : 'Copy Text'}
            </button>

            <button
              onClick={handleDownload}
              className="px-4 py-2 rounded-lg text-xs font-bold text-white bg-emerald-600 hover:bg-emerald-500 shadow-md shadow-emerald-700/20 flex items-center gap-1.5 transition"
            >
              <Download className="h-3.5 w-3.5" />
              Export .TXT
            </button>
          </div>
        </div>

      </div>
    </div>
  );
};
