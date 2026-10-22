import React, { useState, useEffect } from 'react';
import {
  Search,
  GraduationCap,
  Award,
  Globe2,
  User,
  Code2,
  RefreshCw,
  AlertTriangle,
  AlertCircle,
  Zap
} from 'lucide-react';
import type { StudentProfile, Opportunity, AgentEvent, GeminiModelOption } from './types';
import {
  checkHealth,
  startResearch,
  getOpportunities,
  subscribeToEvents,
  resetDemoData,
  getOpportunityDetails,
  getAvailableModels,
  selectModel
} from './api/client';
import { Navbar, DEFAULT_MODELS } from './components/Navbar';
import { ProfileModal } from './components/ProfileModal';
import { AgentWorkspace } from './components/AgentWorkspace';
import { OpportunityCard } from './components/OpportunityCard';
import { EvidenceDrawer } from './components/EvidenceDrawer';
import { SopWorkspace } from './components/SopWorkspace';
import { GapPlanner } from './components/GapPlanner';

const DEFAULT_PROFILE: StudentProfile = {
  full_name: "Rahul Sharma",
  email: "rahul.sharma@example.edu",
  current_degree: "B.Tech Computer Science",
  institution: "Punjab Technical University / NIT Jalandhar",
  cgpa: 8.2,
  grading_scale: "10.0",
  graduation_year: 2026,
  target_degree: "Master's",
  target_field: "Computer Science / Artificial Intelligence",
  target_countries: ["Canada", "Germany", "Singapore"],
  intended_intake: "Fall 2026",
  citizenship: "India",
  funding_preference: "Full Funding / Tuition Assistance",
  skills: ["Python", "PyTorch", "FastAPI", "Machine Learning", "NLP"],
  projects: [
    {
      title: "Autonomous Agent Evaluator",
      description: "Built scalable evaluation pipeline for LLM agents using PyTorch and FastAPI",
      technologies: ["Python", "PyTorch", "FastAPI"],
      is_ai_ml: true,
      evidence_source: "github"
    }
  ],
  github_username: "rahul-sharma-ai",
  career_goals: "Conduct research in resilient AI systems and build production-grade autonomous intelligence.",
  consent_given: true,
  missing_or_conflicting_facts: []
};

export const App: React.FC = () => {
  const [profile, setProfile] = useState<StudentProfile>(DEFAULT_PROFILE);
  const [isProfileModalOpen, setIsProfileModalOpen] = useState(false);
  const [currentRunId, setCurrentRunId] = useState<string | null>(null);
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [currentPhase, setCurrentPhase] = useState<string>("STANDBY");
  const [isCompleted, setIsCompleted] = useState<boolean>(false);
  const [isHealthy, setIsHealthy] = useState<boolean | null>(null);
  const [modelName, setModelName] = useState<string>("gemini-2.5-flash");
  const [availableModels, setAvailableModels] = useState<GeminiModelOption[]>(DEFAULT_MODELS);

  // Filter states
  const [selectedCountry, setSelectedCountry] = useState<string>("ALL");
  const [selectedStatus, setSelectedStatus] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState<string>("");

  // Modals & Drawers
  const [selectedEvidenceOpp, setSelectedEvidenceOpp] = useState<Opportunity | null>(null);
  const [selectedSopOpp, setSelectedSopOpp] = useState<Opportunity | null>(null);

  // Initial Health Check & Model Discovery
  useEffect(() => {
    checkHealth()
      .then((data) => {
        setIsHealthy(true);
        if (data.gemini_model) setModelName(data.gemini_model);
      })
      .catch(() => setIsHealthy(false));

    getAvailableModels()
      .then((data) => {
        if (data.models && data.models.length > 0) {
          setAvailableModels(data.models);
        }
        if (data.current_model) {
          setModelName(data.current_model);
        }
      })
      .catch((err) => {
        console.warn("Could not fetch models dynamically, using defaults:", err);
      });
  }, []);

  const handleModelChange = async (newModelId: string) => {
    setModelName(newModelId);
    try {
      await selectModel(newModelId);
    } catch (e) {
      console.warn("Failed to notify backend of model change:", e);
    }

    const chosen = availableModels.find((m) => m.id === newModelId);
    if (chosen && chosen.rpm_left > 0) {
      if (currentPhase === "QUOTA_EXHAUSTED") {
        setCurrentPhase("STANDBY");
        setEvents((prev) => prev.filter((ev) => ev.event_type !== "QUOTA_EXHAUSTED" && !ev.title.includes("Quota")));
      }
    }
  };

  // Launch Multi-Agent Research
  const handleStartResearch = async (updatedProfile: StudentProfile, overrideModel?: string) => {
    const activeModel = overrideModel || modelName;
    setProfile(updatedProfile);
    setIsProfileModalOpen(false);
    setEvents([]);
    setOpportunities([]);
    setIsCompleted(false);
    setCurrentPhase("STARTING");

    try {
      const run = await startResearch(updatedProfile, activeModel);
      setCurrentRunId(run.id);
      setCurrentPhase("PROFILE_INTELLIGENCE");

      // Subscribe to real-time Server-Sent Events (SSE)
      subscribeToEvents(
        run.id,
        (event: AgentEvent) => {
          setEvents((prev) => [...prev, event]);
          if (event.event_type === "QUOTA_EXHAUSTED") {
            setCurrentPhase("QUOTA_EXHAUSTED");
          } else if (event.event_type === "DISCOVERY_EMPTY") {
            setCurrentPhase("DISCOVERY_EMPTY");
          } else if (event.event_type === "ERROR") {
            setCurrentPhase("ERROR");
          } else if (event.event_type.includes("SEARCH") || event.event_type === "DISCOVERY_STARTED" || event.event_type.includes("CANDIDATE") || (event.event_type.includes("DISCOVERY") && event.event_type !== "DISCOVERY_EMPTY")) {
            setCurrentPhase("DISCOVERY");
          } else if (event.event_type.includes("SCORE") || event.event_type.includes("SHORTLIST")) {
            setCurrentPhase("RANKING");
            getOpportunities(run.id).then((opps) => {
              if (opps && opps.length > 0) setOpportunities(opps);
            });
          } else if (event.event_type.includes("REVIEW")) {
            setCurrentPhase("REVIEW");
          } else if (event.event_type.includes("COMPLETE")) {
            setIsCompleted(true);
            setCurrentPhase("COMPLETED");
            getOpportunities(run.id).then((opps) => {
              if (opps && opps.length > 0) setOpportunities(opps);
            });
          }
        },
        async () => {
          setIsCompleted(true);
          setCurrentPhase("COMPLETED");
          const opps = await getOpportunities(run.id);
          setOpportunities(opps);
        },
        async (err) => {
          console.error("SSE stream error or disconnect", err);
          try {
            const opps = await getOpportunities(run.id);
            if (opps && opps.length > 0) {
              setOpportunities(opps);
              setIsCompleted(true);
              setCurrentPhase("COMPLETED");
            }
          } catch (e) {
            console.error("Failed to fetch opportunities after SSE disconnect", e);
          }
        }
      );
    } catch (err: any) {
      alert(`Research cycle initiation failed: ${err.message}`);
      setCurrentPhase("ERROR");
    }
  };

  const handleViewEvidence = async (opportunity: Opportunity) => {
    setSelectedEvidenceOpp(opportunity);
    if (!opportunity.evidence_records || opportunity.evidence_records.length === 0) {
      try {
        const fullDetails = await getOpportunityDetails(opportunity.id);
        setSelectedEvidenceOpp(fullDetails);
      } catch (err) {
        console.error("Failed to fetch full opportunity evidence details:", err);
      }
    }
  };

  const handleReset = async () => {
    await resetDemoData();
    setEvents([]);
    setOpportunities([]);
    setCurrentRunId(null);
    setCurrentPhase("STANDBY");
    setIsCompleted(false);
  };

  // Filter opportunities
  const filteredOpportunities = opportunities.filter((o) => {
    if (selectedCountry !== "ALL" && o.country !== selectedCountry) return false;
    if (selectedStatus !== "ALL" && o.eligibility_status !== selectedStatus) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      const match =
        o.program_name.toLowerCase().includes(q) ||
        o.university.toLowerCase().includes(q) ||
        o.field.toLowerCase().includes(q);
      if (!match) return false;
    }
    return true;
  });

  const topFiveList = filteredOpportunities.filter((o) => o.is_top_five);
  const otherOpportunities = filteredOpportunities.filter((o) => !o.is_top_five);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-emerald-500 selection:text-white">
      {/* Navbar */}
      <Navbar
        onReset={handleReset}
        onOpenProfile={() => setIsProfileModalOpen(true)}
        isHealthy={isHealthy}
        modelName={modelName}
        availableModels={availableModels}
        onSelectModel={handleModelChange}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        
        {/* Hero Section */}
        <div className="relative rounded-3xl bg-gradient-to-r from-slate-900 via-slate-900 to-emerald-950/40 border border-slate-800 p-8 sm:p-10 shadow-2xl overflow-hidden">
          <div className="relative z-10 max-w-3xl">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-semibold mb-4">
              Autonomous Academic Research Engine
            </div>
            <h1 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight leading-tight">
              Evidence-First Global Scholarships Discovered by Five Collaborating AI Agents
            </h1>
            <p className="mt-3 text-sm text-slate-300 leading-relaxed">
              ScholarSwarm understands your student credentials, conducts grounded live web discovery using Gemini Search, verifies official admissions criteria, calculates deterministic fit scores, and assists your application.
            </p>

            {/* Quick Profile Summary Bar */}
            <div className="mt-6 flex flex-wrap items-center gap-3 text-xs">
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-800/80 border border-slate-700 text-slate-200">
                <User className="h-3.5 w-3.5 text-emerald-400" />
                <span className="font-semibold">{profile.full_name}</span> ({profile.current_degree}, CGPA {profile.cgpa})
              </div>
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-800/80 border border-slate-700 text-slate-200">
                <Globe2 className="h-3.5 w-3.5 text-cyan-400" />
                <span>Destinations: {profile.target_countries.join(', ')}</span>
              </div>
              {profile.github_username && (
                <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-800/80 border border-slate-700 text-slate-200">
                  <Code2 className="h-3.5 w-3.5 text-purple-400" />
                  <span>@{profile.github_username}</span>
                </div>
              )}
              <button
                onClick={() => setIsProfileModalOpen(true)}
                className="text-xs text-emerald-400 hover:text-emerald-300 font-semibold underline underline-offset-4 ml-1"
              >
                Change Profile
              </button>
            </div>
          </div>
        </div>

        {/* Five Agent Swarm Workspace */}
        <AgentWorkspace
          events={events}
          currentPhase={currentPhase}
          isCompleted={isCompleted}
        />

        {/* Opportunities Shortlist Section */}
        <section className="space-y-6">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800">
            <div>
              <h2 className="text-xl font-bold text-white flex items-center gap-2">
                <Award className="h-5 w-5 text-emerald-400" />
                Discovered Opportunities & Match Rankings
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Evaluated against official university admission policies and verified scholarship rules.
              </p>
            </div>

            {/* Filter & Search Controls */}
            <div className="flex flex-wrap items-center gap-2">
              <div className="relative">
                <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-slate-400" />
                <input
                  type="text"
                  placeholder="Search program or university..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-8 pr-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 w-48 sm:w-60"
                />
              </div>

              <select
                value={selectedCountry}
                onChange={(e) => setSelectedCountry(e.target.value)}
                className="px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs text-slate-300 focus:outline-none focus:border-emerald-500"
              >
                <option value="ALL">All Countries</option>
                <option value="Canada">Canada</option>
                <option value="Germany">Germany</option>
                <option value="Singapore">Singapore</option>
              </select>

              <select
                value={selectedStatus}
                onChange={(e) => setSelectedStatus(e.target.value)}
                className="px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs text-slate-300 focus:outline-none focus:border-emerald-500"
              >
                <option value="ALL">All Statuses</option>
                <option value="MEETS_STATED_CRITERIA">Meets Criteria</option>
                <option value="POTENTIAL_MATCH">Potential Match</option>
                <option value="DOES_NOT_MEET">Disqualified</option>
              </select>
            </div>
          </div>

          {/* Top 5 Recommended Section */}
          {topFiveList.length > 0 && (
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <span className="h-2 w-2 rounded-full bg-emerald-400" />
                <h3 className="text-sm font-bold uppercase tracking-wider text-emerald-400">
                  Top 5 Eligible Recommendations (Ranked by Match Score)
                </h3>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                {topFiveList.map((opp) => (
                  <OpportunityCard
                    key={opp.id}
                    opportunity={opp}
                    onViewEvidence={handleViewEvidence}
                    onGenerateSop={(o) => setSelectedSopOpp(o)}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Other Verified Opportunities */}
          {otherOpportunities.length > 0 && (
            <div className="space-y-4 pt-4">
              <h3 className="text-sm font-bold uppercase tracking-wider text-slate-400">
                Additional Verified Opportunities ({otherOpportunities.length})
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                {otherOpportunities.map((opp) => (
                  <OpportunityCard
                    key={opp.id}
                    opportunity={opp}
                    onViewEvidence={handleViewEvidence}
                    onGenerateSop={(o) => setSelectedSopOpp(o)}
                  />
                ))}
              </div>
            </div>
          )}

          {opportunities.length === 0 && (
            <div className="p-8 sm:p-12 text-center rounded-2xl bg-slate-900/60 border border-slate-800 space-y-4 shadow-xl">
              {/* 1. API Quota Exhausted State */}
              {currentPhase === "QUOTA_EXHAUSTED" || events.some(e => e.event_type === "QUOTA_EXHAUSTED" || e.title.includes("Quota")) ? (
                <>
                  <div className="h-12 w-12 rounded-2xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-center text-rose-400 mx-auto">
                    <AlertTriangle className="h-6 w-6" />
                  </div>
                  <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs font-semibold">
                    429 RESOURCE_EXHAUSTED
                  </div>
                  <h3 className="text-lg font-bold text-white">Gemini API Quota Exhausted</h3>
                  <p className="text-xs text-slate-300 max-w-lg mx-auto leading-relaxed">
                    Live Google Search grounding and official URL Context extraction could not proceed because the Google Gen AI API quota limit has been reached for <span className="font-mono text-rose-400 font-semibold">{modelName}</span>. ScholarSwarm enforces strict research integrity and will not fabricate synthetic opportunities.
                  </p>

                  {/* Switch Model to unexhausted model */}
                  <div className="p-4 rounded-2xl bg-slate-950/70 border border-slate-800 text-left max-w-lg mx-auto space-y-2.5">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-slate-200 flex items-center gap-1.5">
                        <Zap className="h-3.5 w-3.5 text-cyan-400" />
                        Available Models (Unexhausted RPM)
                      </span>
                      <span className="text-[10px] text-slate-400">Click to switch & start search</span>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      {availableModels.filter(m => m.rpm_left > 0).map((m) => (
                        <button
                          key={m.id}
                          onClick={() => {
                            handleModelChange(m.id);
                            handleStartResearch(profile, m.id);
                          }}
                          className={`p-2.5 rounded-xl border text-left transition flex items-center justify-between gap-2 ${
                            m.id === modelName
                              ? 'bg-emerald-950/50 border-emerald-500/50'
                              : 'bg-slate-900/60 border-slate-800 hover:border-emerald-500/50 hover:bg-slate-800/60'
                          }`}
                        >
                          <div className="min-w-0">
                            <div className="text-xs font-bold text-white truncate">{m.name}</div>
                            <div className="text-[10px] text-emerald-400 font-medium">
                              {m.rpm_left}/{m.rpm_limit} RPM left
                            </div>
                          </div>
                          <span className="text-[10px] text-emerald-400 font-bold bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20 shrink-0">
                            Start &rarr;
                          </span>
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="pt-2 flex items-center justify-center gap-3">
                    <button
                      onClick={() => setIsProfileModalOpen(true)}
                      className="px-5 py-2 rounded-xl text-xs font-bold text-white bg-slate-800 hover:bg-slate-700 border border-slate-700 transition"
                    >
                      Configure Profile
                    </button>
                    <button
                      onClick={() => handleStartResearch(profile, modelName)}
                      className="px-5 py-2 rounded-xl text-xs font-bold text-white bg-emerald-600 hover:bg-emerald-500 shadow-lg shadow-emerald-700/20 transition inline-flex items-center gap-1.5"
                    >
                      <RefreshCw className="h-3.5 w-3.5" /> Start Scholarship Search with {modelName}
                    </button>
                  </div>
                </>
              ) : currentPhase === "DISCOVERY_EMPTY" || events.some(e => e.event_type === "DISCOVERY_EMPTY") ? (
                /* 2. Honest Empty Discovery State */
                <>
                  <div className="h-12 w-12 rounded-2xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400 mx-auto">
                    <Search className="h-6 w-6" />
                  </div>
                  <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-400 text-xs font-semibold">
                    0 Programs Found
                  </div>
                  <h3 className="text-lg font-bold text-white">No Matching Programs Discovered</h3>
                  <p className="text-xs text-slate-300 max-w-lg mx-auto leading-relaxed">
                    Live Gemini Google Search grounding returned zero candidate degree programs matching your criteria across {profile.target_countries.join(', ')}. In accordance with our research integrity policy, no dummy or synthetic records were substituted.
                  </p>
                  <div className="pt-2 flex items-center justify-center gap-3">
                    <button
                      onClick={() => setIsProfileModalOpen(true)}
                      className="px-5 py-2 rounded-xl text-xs font-bold text-white bg-emerald-600 hover:bg-emerald-500 shadow-lg shadow-emerald-700/20 transition"
                    >
                      Adjust Target Countries / Field
                    </button>
                  </div>
                </>
              ) : currentPhase === "ERROR" || events.some(e => e.event_type === "ERROR") ? (
                /* 3. Explicit Workflow Error State (Fixes Infinite Spinner) */
                <>
                  <div className="h-12 w-12 rounded-2xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-center text-rose-400 mx-auto">
                    <AlertCircle className="h-6 w-6" />
                  </div>
                  <h3 className="text-lg font-bold text-white">Research Workflow Interrupted</h3>
                  <p className="text-xs text-slate-400 max-w-lg mx-auto leading-relaxed">
                    An error occurred while executing the multi-agent research swarm. Please review the system event log or retry.
                  </p>
                  <div className="pt-2">
                    <button
                      onClick={() => handleStartResearch(profile)}
                      className="px-5 py-2 rounded-xl text-xs font-bold text-white bg-emerald-600 hover:bg-emerald-500 shadow-lg shadow-emerald-700/20 transition inline-flex items-center gap-1.5"
                    >
                      <RefreshCw className="h-3.5 w-3.5" /> Restart Research
                    </button>
                  </div>
                </>
              ) : currentPhase !== "STANDBY" && !isCompleted ? (
                /* 4. Active In-Progress Execution */
                <>
                  <RefreshCw className="h-10 w-10 text-emerald-400 mx-auto animate-spin" />
                  <h3 className="text-base font-bold text-white">ScholarSwarm Research Cycle in Progress</h3>
                  <p className="text-xs text-slate-400 max-w-md mx-auto">
                    The 5-agent research swarm is currently discovering opportunities, verifying official admissions criteria, and calculating match rankings...
                  </p>
                </>
              ) : (
                /* 5. Initial Standby State */
                <>
                  <GraduationCap className="h-10 w-10 text-emerald-400 mx-auto" />
                  <h3 className="text-base font-bold text-white">Ready to Discover Scholarships</h3>
                  <p className="text-xs text-slate-400 max-w-md mx-auto">
                    Launch the 5-agent research cycle to discover live scholarships across Canada, Germany, and Singapore tailored to your profile.
                  </p>
                  <button
                    onClick={() => setIsProfileModalOpen(true)}
                    className="px-5 py-2 rounded-xl text-xs font-bold text-white bg-emerald-600 hover:bg-emerald-500 shadow-lg shadow-emerald-700/20 transition inline-flex items-center gap-2"
                  >
                    Start Research Now
                  </button>
                </>
              )}
            </div>
          )}
        </section>

        {/* Eligibility Gap Planner Section */}
        {opportunities.length > 0 && (
          <GapPlanner opportunities={opportunities} />
        )}

      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800 bg-slate-950/80 py-6 text-center text-xs text-slate-500">
        ScholarSwarm • TetraNoodle AI Hackathon 2026 • Evidence-First Scholarship Assistant • Built with React, Vite, FastAPI, LangGraph & Gemini
      </footer>

      {/* Modals & Drawers */}
      <ProfileModal
        isOpen={isProfileModalOpen}
        onClose={() => setIsProfileModalOpen(false)}
        onStartResearch={handleStartResearch}
        currentProfile={profile}
      />

      <EvidenceDrawer
        opportunity={selectedEvidenceOpp}
        onClose={() => setSelectedEvidenceOpp(null)}
      />

      <SopWorkspace
        opportunity={selectedSopOpp}
        runId={currentRunId || 'demo-run'}
        onClose={() => setSelectedSopOpp(null)}
      />
    </div>
  );
};

export default App;
