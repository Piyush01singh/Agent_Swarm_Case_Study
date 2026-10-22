import React, { useState, useRef, useEffect } from 'react';
import { RefreshCw, Activity, ShieldCheck, GraduationCap, ChevronDown, Check, AlertTriangle, Zap } from 'lucide-react';
import type { GeminiModelOption } from '../types';

export const DEFAULT_MODELS: GeminiModelOption[] = [
  {
    id: "gemini-2.5-flash",
    name: "Gemini 2.5 Flash",
    category: "Text-out models",
    rpm_limit: 5,
    rpm_used: 0,
    rpm_left: 5,
    status: "available",
    badge: "Recommended"
  },
  {
    id: "gemini-3.6-flash",
    name: "Gemini 3.6 Flash",
    category: "Text-out models",
    rpm_limit: 5,
    rpm_used: 2,
    rpm_left: 3,
    status: "available",
    badge: "Active"
  },
  {
    id: "gemini-2.0-flash",
    name: "Gemini 2 Flash",
    category: "Text-out models",
    rpm_limit: 15,
    rpm_used: 0,
    rpm_left: 15,
    status: "available",
    badge: "High Capacity"
  },
  {
    id: "gemini-2.0-flash-lite",
    name: "Gemini 2 Flash Lite",
    category: "Text-out models",
    rpm_limit: 15,
    rpm_used: 0,
    rpm_left: 15,
    status: "available",
    badge: "Fast"
  },
  {
    id: "gemini-1.5-flash",
    name: "Gemini 1.5 Flash",
    category: "Text-out models",
    rpm_limit: 15,
    rpm_used: 0,
    rpm_left: 15,
    status: "available",
    badge: "Stable"
  },
  {
    id: "gemini-1.5-pro",
    name: "Gemini 1.5 Pro",
    category: "Text-out models",
    rpm_limit: 2,
    rpm_used: 0,
    rpm_left: 2,
    status: "available",
    badge: "Deep Reasoning"
  },
  {
    id: "gemini-3.1-flash-lite",
    name: "Gemini 3.1 Flash Lite",
    category: "Text-out models",
    rpm_limit: 15,
    rpm_used: 15,
    rpm_left: 0,
    status: "exhausted",
    badge: "Quota Exhausted"
  },
  {
    id: "gemini-3.8-flash",
    name: "Gemini 3.8 Flash",
    category: "Text-out models",
    rpm_limit: 5,
    rpm_used: 5,
    rpm_left: 0,
    status: "exhausted",
    badge: "Quota Exhausted"
  }
];

interface NavbarProps {
  onReset: () => void;
  onOpenProfile: () => void;
  isHealthy: boolean | null;
  modelName: string;
  availableModels?: GeminiModelOption[];
  onSelectModel?: (modelId: string) => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  onReset,
  onOpenProfile,
  isHealthy,
  modelName,
  availableModels = DEFAULT_MODELS,
  onSelectModel,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const models = availableModels && availableModels.length > 0 ? availableModels : DEFAULT_MODELS;
  const currentModel = models.find((m) => m.id === modelName) || {
    id: modelName,
    name: modelName,
    category: "Text-out models",
    rpm_limit: 15,
    rpm_used: modelName.includes("3.1") || modelName.includes("3.8") ? 15 : 0,
    rpm_left: modelName.includes("3.1") || modelName.includes("3.8") ? 0 : 5,
    status: modelName.includes("3.1") || modelName.includes("3.8") ? "exhausted" : "available",
  };

  const isCurrentExhausted = currentModel.status === "exhausted" || currentModel.rpm_left === 0;

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSelect = (modelId: string) => {
    if (onSelectModel) {
      onSelectModel(modelId);
    }
    setIsOpen(false);
  };

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
              5 Collaborating Agents • Live Grounding • Evidence-First
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Dynamic Model Selector Badge */}
          <div className="relative" ref={dropdownRef}>
            <button
              onClick={() => setIsOpen(!isOpen)}
              className={`hidden md:flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs transition shadow-sm ${
                isCurrentExhausted
                  ? 'bg-rose-950/40 border-rose-700/60 hover:bg-rose-900/40 text-rose-200'
                  : 'bg-slate-800/80 border-slate-700/60 hover:bg-slate-700/80 text-slate-200'
              }`}
              title="Click to switch Gemini model and view remaining RPM capacity"
              aria-label="Select Gemini model"
            >
              {isCurrentExhausted ? (
                <AlertTriangle className="h-3.5 w-3.5 text-rose-400" />
              ) : (
                <Activity className={`h-3.5 w-3.5 ${isHealthy ? 'text-emerald-400 animate-pulse' : 'text-amber-400'}`} />
              )}
              
              <span className="font-mono text-[11px] font-medium text-slate-200">
                {modelName}
              </span>

              {/* RPM Left Pill */}
              <span
                className={`text-[10px] font-semibold px-1.5 py-0.2 rounded ${
                  isCurrentExhausted
                    ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                    : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                }`}
              >
                {isCurrentExhausted ? '0 RPM (Exhausted)' : `${currentModel.rpm_left} RPM left`}
              </span>

              <span className="text-slate-500">|</span>
              
              <span className="text-slate-400 flex items-center gap-1">
                <ShieldCheck className="h-3 w-3 text-cyan-400" /> Grounded
              </span>

              <ChevronDown className={`h-3.5 w-3.5 text-slate-400 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`} />
            </button>

            {/* Model Selection Dropdown Menu */}
            {isOpen && (
              <div className="absolute right-0 mt-2 w-84 sm:w-96 rounded-2xl bg-slate-900 border border-slate-700 shadow-2xl p-3 z-50 animate-in fade-in slide-in-from-top-2 duration-150">
                <div className="flex items-center justify-between pb-2 mb-2 border-b border-slate-800 px-1">
                  <div>
                    <div className="flex items-center gap-1.5 font-semibold text-xs text-white">
                      <Zap className="h-3.5 w-3.5 text-cyan-400" />
                      Select Gemini Model
                    </div>
                    <p className="text-[11px] text-slate-400">
                      Choose an active model with available RPM capacity
                    </p>
                  </div>
                  <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700">
                    {models.filter(m => m.rpm_left > 0).length} Available
                  </span>
                </div>

                {/* Model Items */}
                <div className="space-y-1.5 max-h-[360px] overflow-y-auto pr-1">
                  {models.map((model) => {
                    const isSelected = model.id === modelName;
                    const isExhausted = model.status === 'exhausted' || model.rpm_left === 0;

                    return (
                      <button
                        key={model.id}
                        onClick={() => handleSelect(model.id)}
                        className={`w-full text-left p-2.5 rounded-xl border transition flex items-center justify-between gap-3 ${
                          isSelected
                            ? 'bg-emerald-950/40 border-emerald-500/50 shadow-sm shadow-emerald-900/20'
                            : isExhausted
                            ? 'bg-slate-900/50 border-slate-800/80 hover:border-slate-700 hover:bg-slate-800/40 opacity-75'
                            : 'bg-slate-800/40 border-slate-800 hover:border-emerald-500/40 hover:bg-slate-800/80'
                        }`}
                      >
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-1.5">
                            <span className="font-semibold text-xs text-white truncate">
                              {model.name}
                            </span>
                            {model.badge && (
                              <span
                                className={`text-[9px] font-bold px-1.5 py-0.2 rounded ${
                                  model.badge === 'Recommended'
                                    ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                                    : model.badge === 'Quota Exhausted'
                                    ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                                    : 'bg-cyan-500/10 text-cyan-300 border border-cyan-500/20'
                                }`}
                              >
                                {model.badge}
                              </span>
                            )}
                          </div>
                          <div className="text-[11px] font-mono text-slate-400 truncate mt-0.5">
                            {model.id}
                          </div>
                        </div>

                        {/* RPM Capacity & Status Pill */}
                        <div className="flex items-center gap-2 shrink-0">
                          <span
                            className={`text-[11px] font-bold px-2 py-0.5 rounded-full ${
                              isExhausted
                                ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                                : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                            }`}
                          >
                            {isExhausted ? '0 RPM left' : `${model.rpm_left}/${model.rpm_limit} RPM left`}
                          </span>

                          <div className="w-5 flex justify-center">
                            {isSelected ? (
                              <Check className="h-4 w-4 text-emerald-400" />
                            ) : null}
                          </div>
                        </div>
                      </button>
                    );
                  })}
                </div>

                <div className="pt-2 mt-2 border-t border-slate-800/80 px-1 text-[11px] text-slate-400 flex items-center justify-between">
                  <span>Selected model applies to live search grounding</span>
                  {isCurrentExhausted && (
                    <span className="text-amber-400 font-medium">Switch to continue search</span>
                  )}
                </div>
              </div>
            )}
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
