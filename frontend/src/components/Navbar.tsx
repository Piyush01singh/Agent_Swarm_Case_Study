import React from 'react';
import { RefreshCw, Activity, GraduationCap } from 'lucide-react';
import type { GeminiModelOption } from '../types';

export const DEFAULT_MODELS: GeminiModelOption[] = [
  {
    id: "gemini-3.1-flash-lite",
    name: "Gemini 3.1 Flash Lite",
    category: "Text-out models",
    rpm_limit: 15,
    rpm_used: 0,
    rpm_left: 15,
    status: "available",
    badge: "Active Model"
  }
];

interface NavbarProps {
  onReset: () => void;
  onOpenProfile: () => void;
  isHealthy: boolean | null;
  modelName: string;
  apiKeySuffix?: string;
  availableModels?: GeminiModelOption[];
  onSelectModel?: (modelId: string) => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  onReset,
  onOpenProfile,
  isHealthy,
  modelName = "gemini-3.1-flash-lite",
}) => {
  return (
    <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-emerald-600 to-cyan-500 flex items-center justify-center text-white shadow-lg shadow-emerald-900/30">
            <GraduationCap className="h-6 w-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-lg tracking-tight text-white">ScholarSwarm</span>
              <span className="text-[10px] uppercase font-semibold tracking-wider px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                AI Hackathon 2026
              </span>
            </div>
            <p className="text-xs text-slate-400 hidden sm:block">
              5 Collaborating Agents • Tavily Live Search • Gemini 3.1 Flash Lite
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Active Gemini Model Badge */}
          <div
            className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs bg-slate-800/80 border-slate-700/60 text-slate-200 shadow-sm"
            title="Single active evaluation model: gemini-3.1-flash-lite"
          >
            <Activity className={`h-3.5 w-3.5 ${isHealthy ? 'text-emerald-400 animate-pulse' : 'text-amber-400'}`} />
            
            <span className="font-mono text-[11px] font-medium text-slate-200">
              {modelName || "gemini-3.1-flash-lite"}
            </span>
          </div>

          <button
            onClick={onReset}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 border border-slate-700 transition"
            title="Reset system state for clean demo run"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Reset</span>
          </button>

          <button
            onClick={onOpenProfile}
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold text-white bg-emerald-600 hover:bg-emerald-500 shadow-md shadow-emerald-700/20 transition"
          >
            <span>Configure Student</span>
          </button>
        </div>
      </div>
    </header>
  );
};
