import React from 'react';
import {
  UserCheck,
  Search,
  Award,
  FileEdit,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  RotateCcw,
  Clock,
  Terminal,
} from 'lucide-react';
import type { AgentEvent } from '../types';

interface AgentWorkspaceProps {
  events: AgentEvent[];
  currentPhase: string;
  isCompleted: boolean;
}

const AGENTS = [
  {
    role: "Profile Intelligence Agent",
    label: "Agent 1: Profile Intelligence",
    icon: UserCheck,
    color: "from-blue-600 to-indigo-600",
    badgeColor: "bg-blue-500/10 text-blue-400 border-blue-500/20",
    description: "Extracts verified metrics, transcripts, and GitHub repositories."
  },
  {
    role: "Research & Eligibility Agent",
    label: "Agent 2: Research & Eligibility",
    icon: Search,
    color: "from-emerald-600 to-teal-600",
    badgeColor: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    description: "Gemini Google Search Grounding & Official URL auditing."
  },
  {
    role: "Match Strategist Agent",
    label: "Agent 3: Match Strategist",
    icon: Award,
    color: "from-amber-600 to-orange-600",
    badgeColor: "bg-amber-500/10 text-amber-400 border-amber-500/20",
    description: "Deterministic 0-100 scoring & hard disqualifier filters."
  },
  {
    role: "Application Coach Agent",
    label: "Agent 4: Application Coach",
    icon: FileEdit,
    color: "from-purple-600 to-violet-600",
    badgeColor: "bg-purple-500/10 text-purple-400 border-purple-500/20",
    description: "SOP generation grounded in facts without hallucination."
  },
  {
    role: "Quality Reviewer Agent",
    label: "Agent 5: Quality Reviewer",
    icon: ShieldCheck,
    color: "from-rose-600 to-pink-600",
    badgeColor: "bg-rose-500/10 text-rose-400 border-rose-500/20",
    description: "Independent audit of claims, citations & re-research loops."
  }
];

export const AgentWorkspace: React.FC<AgentWorkspaceProps> = ({
  events,
  currentPhase,
  isCompleted,
}) => {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-800 gap-2">
        <div>
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            <Terminal className="h-4 w-4 text-emerald-400" />
            Active Agent Swarm Timeline
          </h2>
          <p className="text-xs text-slate-400">
            Real-time event stream from the 5 collaborating agents coordinated via LangGraph.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[11px] font-mono px-2.5 py-1 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
            Phase: <span className="text-emerald-400 font-bold">{currentPhase}</span>
          </span>
          {isCompleted && (
            <span className="text-[11px] font-semibold px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1">
              <CheckCircle2 className="h-3 w-3" /> Completed
            </span>
          )}
        </div>
      </div>

      {/* Five Agent Status Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 my-5">
        {AGENTS.map((agent) => {
          const Icon = agent.icon;
          const agentEvents = events.filter(e => e.agent_role === agent.role);
          const hasActivity = agentEvents.length > 0;
          const lastEvent = agentEvents[agentEvents.length - 1];

          return (
            <div
              key={agent.role}
              className={`p-3.5 rounded-xl border transition-all ${
                hasActivity
                  ? 'bg-slate-800/60 border-slate-700/80'
                  : 'bg-slate-900/40 border-slate-800/60 opacity-60'
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <div className={`h-7 w-7 rounded-lg bg-gradient-to-tr ${agent.color} flex items-center justify-center text-white`}>
                  <Icon className="h-4 w-4" />
                </div>
                <span className={`text-[10px] font-semibold px-2 py-0.5 rounded border ${agent.badgeColor}`}>
                  {hasActivity ? `${agentEvents.length} events` : 'Standby'}
                </span>
              </div>
              <h3 className="text-xs font-bold text-white tracking-tight">{agent.label}</h3>
              <p className="text-[11px] text-slate-400 mt-1 line-clamp-2">{agent.description}</p>
              {lastEvent && (
                <div className="mt-2 pt-2 border-t border-slate-800/80 text-[10px] text-emerald-400 truncate font-mono">
                  &gt; {lastEvent.title}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Live Activity Terminal Stream */}
      <div className="mt-4">
        <div className="flex items-center justify-between text-xs text-slate-400 mb-2 font-mono">
          <span>Live Execution Stream ({events.length} events)</span>
          <span className="flex items-center gap-1 text-[11px]">
            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-ping inline-block" /> Live SSE
          </span>
        </div>

        <div className="h-64 overflow-y-auto rounded-xl bg-slate-950 p-3 font-mono text-xs border border-slate-800/80 space-y-2 select-text">
          {events.length === 0 ? (
            <div className="h-full flex items-center justify-center text-slate-500 italic text-[11px]">
              Awaiting research task execution. Click "Configure Student" to begin.
            </div>
          ) : (
            events.map((ev, index) => {
              const isFlag = ev.event_type.includes("FLAG") || ev.event_type.includes("ERROR") || ev.event_type.includes("EXHAUSTED");
              const isRetry = ev.event_type.includes("RETRY") || ev.event_type.includes("WARNING") || ev.event_type.includes("EMPTY");
              const isMatch = ev.event_type.includes("RANKED") || ev.event_type.includes("COMPLETED");

              return (
                <div
                  key={ev.id || index}
                  className={`p-2 rounded-lg border text-[11px] leading-relaxed transition ${
                    isFlag
                      ? 'bg-rose-950/20 border-rose-900/40 text-rose-300'
                      : isRetry
                      ? 'bg-amber-950/20 border-amber-900/40 text-amber-300'
                      : isMatch
                      ? 'bg-emerald-950/20 border-emerald-900/40 text-emerald-300'
                      : 'bg-slate-900/50 border-slate-800/60 text-slate-300'
                  }`}
                >
                  <div className="flex items-center justify-between text-[10px] text-slate-400 mb-1">
                    <span className="font-bold uppercase tracking-wider text-slate-300 flex items-center gap-1">
                      {isFlag && <AlertTriangle className="h-3 w-3 text-rose-400" />}
                      {isRetry && <RotateCcw className="h-3 w-3 text-amber-400" />}
                      [{ev.agent_role}]
                    </span>
                    <span className="flex items-center gap-1 text-slate-500">
                      <Clock className="h-2.5 w-2.5" />
                      {new Date(ev.timestamp).toLocaleTimeString()}
                    </span>
                  </div>
                  <div className="font-semibold text-white">{ev.title}</div>
                  <div className="text-slate-400 mt-0.5 break-words">{ev.description}</div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
};
