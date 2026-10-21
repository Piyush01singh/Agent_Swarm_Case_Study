import React, { useState, useEffect } from 'react';
import {
  Sparkles,
  Search,
  GraduationCap,
  Award,
  Globe2,
  User,
  Code2
} from 'lucide-react';
import type { StudentProfile, Opportunity, AgentEvent } from './types';
import { checkHealth, startResearch, getOpportunities, subscribeToEvents, resetDemoData, getOpportunityDetails } from './api/client';
import { Navbar } from './components/Navbar';
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

  // Filter states
  const [selectedCountry, setSelectedCountry] = useState<string>("ALL");
  const [selectedStatus, setSelectedStatus] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState<string>("");

  // Modals & Drawers
  const [selectedEvidenceOpp, setSelectedEvidenceOpp] = useState<Opportunity | null>(null);
  const [selectedSopOpp, setSelectedSopOpp] = useState<Opportunity | null>(null);

  // Initial Health Check
  useEffect(() => {
    checkHealth()
      .then((data) => {
        setIsHealthy(true);
        if (data.gemini_model) setModelName(data.gemini_model);
      })
      .catch(() => setIsHealthy(false));
  }, []);

  // Launch Multi-Agent Research
  const handleStartResearch = async (updatedProfile: StudentProfile) => {
    setProfile(updatedProfile);
    setIsProfileModalOpen(false);
    setEvents([]);
    setOpportunities([]);
    setIsCompleted(false);
    setCurrentPhase("STARTING");

    try {
      const run = await startResearch(updatedProfile);
      setCurrentRunId(run.id);
      setCurrentPhase("PROFILE_INTELLIGENCE");

      // Subscribe to real-time Server-Sent Events (SSE)
      subscribeToEvents(
        run.id,
        (event: AgentEvent) => {
          setEvents((prev) => [...prev, event]);
          if (event.event_type.includes("SEARCH")) setCurrentPhase("DISCOVERY");
          else if (event.event_type.includes("SCORE")) setCurrentPhase("RANKING");
          else if (event.event_type.includes("REVIEW")) setCurrentPhase("REVIEW");
        },
        async () => {
          setIsCompleted(true);
          setCurrentPhase("COMPLETED");
          const opps = await getOpportunities(run.id);
          setOpportunities(opps);
        },
        (err) => {
          console.error("SSE stream error", err);
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
      />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        
        {/* Hero Section */}
        <div className="relative rounded-3xl bg-gradient-to-r from-slate-900 via-slate-900 to-emerald-950/40 border border-slate-800 p-8 sm:p-10 shadow-2xl overflow-hidden">
          <div className="relative z-10 max-w-3xl">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-semibold mb-4">
              <Sparkles className="h-3.5 w-3.5" />
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
            <div className="p-12 text-center rounded-2xl bg-slate-900/40 border border-slate-800 space-y-4">
              <GraduationCap className="h-10 w-10 text-emerald-400 mx-auto" />
              <h3 className="text-base font-bold text-white">No research results in current session</h3>
              <p className="text-xs text-slate-400 max-w-md mx-auto">
                Launch the 5-agent research cycle to discover live scholarships across Canada, Germany, and Singapore tailored to your profile.
              </p>
              <button
                onClick={() => setIsProfileModalOpen(true)}
                className="px-5 py-2 rounded-xl text-xs font-bold text-white bg-emerald-600 hover:bg-emerald-500 shadow-lg shadow-emerald-700/20 transition inline-flex items-center gap-2"
              >
                <Sparkles className="h-4 w-4" /> Start Research Now
              </button>
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
