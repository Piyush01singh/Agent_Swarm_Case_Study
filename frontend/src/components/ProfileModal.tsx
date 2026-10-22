import React, { useState } from 'react';
import { X, Upload, Code2, AlertCircle, CheckCircle2, FileText } from 'lucide-react';
import type { StudentProfile } from '../types';
import { extractProfile } from '../api/client';

interface ProfileModalProps {
  isOpen: boolean;
  onClose: () => void;
  onStartResearch: (profile: StudentProfile) => void;
  currentProfile: StudentProfile;
}

export const ProfileModal: React.FC<ProfileModalProps> = ({
  isOpen,
  onClose,
  onStartResearch,
  currentProfile,
}) => {
  const [profile, setProfile] = useState<StudentProfile>(currentProfile);
  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const [transcriptFile, setTranscriptFile] = useState<File | null>(null);
  const [isExtracting, setIsExtracting] = useState(false);
  const [extractSuccess, setExtractSuccess] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleDocumentExtraction = async () => {
    if (!resumeFile && !transcriptFile && !profile.github_username) {
      setError("Please select a resume/transcript or enter a GitHub handle first.");
      return;
    }

    setIsExtracting(true);
    setError(null);
    setExtractSuccess(null);

    try {
      const formData = new FormData();
      if (resumeFile) formData.append('resume', resumeFile);
      if (transcriptFile) formData.append('transcript', transcriptFile);
      if (profile.github_username) formData.append('github_handle', profile.github_username);
      formData.append('profile_json', JSON.stringify(profile));

      const result = await extractProfile(formData);
      if (result.success && result.profile) {
        setProfile(result.profile);
        setExtractSuccess("Document text parsed and profile facts prefilled successfully!");
      }
    } catch (err: any) {
      setError(err.message || "Failed to parse documents.");
    } finally {
      setIsExtracting(false);
    }
  };

  const loadPreset = (presetKey: 'rahul' | 'profileB' | 'profileC') => {
    if (presetKey === 'rahul') {
      setProfile({
        full_name: "Rahul Sharma",
        email: "rahul.sharma@example.edu",
        current_degree: "B.Tech Computer Science",
        institution: "Punjab Technical University / NIT Jalandhar",
        cgpa: 8.2,
        grading_scale: "10.0",
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
        consent_given: true
      });
    } else if (presetKey === 'profileB') {
      setProfile({
        full_name: "Ananya Patel",
        email: "ananya.patel@example.edu",
        current_degree: "B.Sc Biotechnology",
        institution: "Delhi University",
        cgpa: 6.8,
        grading_scale: "10.0",
        target_degree: "Master's",
        target_field: "Bioinformatics / Computational Biology",
        target_countries: ["Germany"],
        intended_intake: "Winter 2026",
        citizenship: "India",
        funding_preference: "Partial / DAAD Scholarship",
        skills: ["R", "Python", "Genomics", "Biostatistics"],
        projects: [],
        github_username: "ananya-bio",
        career_goals: "Bridge computational pipelines with biological data analysis.",
        consent_given: true
      });
    } else if (presetKey === 'profileC') {
      setProfile({
        full_name: "Vikram Sengupta",
        email: "vikram.s@example.edu",
        current_degree: "M.Sc Mathematics & Computing",
        institution: "IIT Kharagpur",
        cgpa: 8.6,
        grading_scale: "10.0",
        target_degree: "PhD",
        target_field: "Data Science & Applied Optimization",
        target_countries: ["Singapore", "Canada"],
        intended_intake: "Fall 2026",
        citizenship: "India",
        funding_preference: "Full Research Scholarship (SINGA / RA)",
        language_tests: { test: "IELTS", score: null, status: "planned" },
        skills: ["Optimization", "Stochastic Analysis", "C++", "Python"],
        projects: [],
        github_username: "vikram-math",
        career_goals: "Publish core mathematical optimization theorems in deep learning architectures.",
        consent_given: true
      });
    }
  };

  const handleCountryToggle = (country: string) => {
    const current = profile.target_countries || [];
    if (current.includes(country)) {
      if (current.length > 1) {
        setProfile({ ...profile, target_countries: current.filter(c => c !== country) });
      }
    } else {
      setProfile({ ...profile, target_countries: [...current, country] });
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="relative bg-slate-900 border border-slate-800 rounded-2xl max-w-3xl w-full p-6 sm:p-8 shadow-2xl overflow-hidden">
        
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-slate-800">
          <div>
            <h2 className="text-xl font-bold text-white flex items-center gap-2">
              Configure Student Profile & Documents
            </h2>
            <p className="text-xs text-slate-400 mt-1">
              Supports real document extraction (PDF/DOCX), GitHub enrichment, and synthetic profiles.
            </p>
          </div>
          <button onClick={onClose} className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800">
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Presets */}
        <div className="mt-4 flex flex-wrap items-center gap-2 text-xs">
          <span className="text-slate-400 font-semibold">Load Preset:</span>
          <button
            onClick={() => loadPreset('rahul')}
            className="px-2.5 py-1 rounded-md bg-emerald-950/60 text-emerald-300 border border-emerald-800/60 hover:bg-emerald-900 transition"
          >
            Rahul (8.2 CGPA • CS • AI Projects)
          </button>
          <button
            onClick={() => loadPreset('profileB')}
            className="px-2.5 py-1 rounded-md bg-slate-800 text-slate-300 border border-slate-700 hover:bg-slate-700 transition"
          >
            Profile B (6.8 CGPA • Biotech)
          </button>
          <button
            onClick={() => loadPreset('profileC')}
            className="px-2.5 py-1 rounded-md bg-slate-800 text-slate-300 border border-slate-700 hover:bg-slate-700 transition"
          >
            Profile C (PhD • Missing IELTS)
          </button>
        </div>

        {error && (
          <div className="mt-4 p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-center gap-2">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {extractSuccess && (
          <div className="mt-4 p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 shrink-0" />
            <span>{extractSuccess}</span>
          </div>
        )}

        {/* Form Body */}
        <div className="mt-6 space-y-4 max-h-[60vh] overflow-y-auto pr-1">
          
          {/* Document Uploads */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 p-4 rounded-xl bg-slate-800/40 border border-slate-700/60">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1 flex items-center gap-1.5">
                <FileText className="h-3.5 w-3.5 text-cyan-400" /> Upload Resume (PDF / DOCX)
              </label>
              <input
                type="file"
                accept=".pdf,.docx"
                onChange={(e) => setResumeFile(e.target.files?.[0] || null)}
                className="block w-full text-xs text-slate-400 file:mr-2 file:py-1 file:px-2.5 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-slate-700 file:text-slate-200 hover:file:bg-slate-600 cursor-pointer"
              />
              {resumeFile && <span className="text-[11px] text-cyan-400 mt-1 block truncate">Selected: {resumeFile.name}</span>}
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1 flex items-center gap-1.5">
                <FileText className="h-3.5 w-3.5 text-cyan-400" /> Upload Marksheet/Transcript
              </label>
              <input
                type="file"
                accept=".pdf,.docx"
                onChange={(e) => setTranscriptFile(e.target.files?.[0] || null)}
                className="block w-full text-xs text-slate-400 file:mr-2 file:py-1 file:px-2.5 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-slate-700 file:text-slate-200 hover:file:bg-slate-600 cursor-pointer"
              />
              {transcriptFile && <span className="text-[11px] text-cyan-400 mt-1 block truncate">Selected: {transcriptFile.name}</span>}
            </div>

            <div className="sm:col-span-2 flex items-center justify-between pt-1">
              <span className="text-[11px] text-slate-400">
                Documents are parsed locally in memory; no sensitive files are permanently stored.
              </span>
              <button
                type="button"
                onClick={handleDocumentExtraction}
                disabled={isExtracting}
                className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-700 hover:bg-slate-600 text-white flex items-center gap-1.5 transition disabled:opacity-50"
              >
                <Upload className="h-3.5 w-3.5" />
                {isExtracting ? 'Extracting Text...' : 'Parse & Prefill'}
              </button>
            </div>
          </div>

          {/* Student Fields */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">Student Full Name</label>
              <input
                type="text"
                value={profile.full_name}
                onChange={(e) => setProfile({ ...profile, full_name: e.target.value })}
                className="w-full px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 text-xs text-white focus:outline-none focus:border-emerald-500"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">Public GitHub Username or URL</label>
              <div className="relative">
                <Code2 className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-slate-400" />
                <input
                  type="text"
                  placeholder="e.g. rahul-sharma-ai"
                  value={profile.github_username || ''}
                  onChange={(e) => setProfile({ ...profile, github_username: e.target.value })}
                  className="w-full pl-8 pr-3 py-2 rounded-lg bg-slate-800 border border-slate-700 text-xs text-white focus:outline-none focus:border-emerald-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">Current Degree</label>
              <input
                type="text"
                value={profile.current_degree}
                onChange={(e) => setProfile({ ...profile, current_degree: e.target.value })}
                className="w-full px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 text-xs text-white focus:outline-none focus:border-emerald-500"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">Undergraduate Institution</label>
              <input
                type="text"
                value={profile.institution}
                onChange={(e) => setProfile({ ...profile, institution: e.target.value })}
                className="w-full px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 text-xs text-white focus:outline-none focus:border-emerald-500"
              />
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">CGPA / Grade</label>
                <input
                  type="number"
                  step="0.1"
                  value={profile.cgpa}
                  onChange={(e) => setProfile({ ...profile, cgpa: parseFloat(e.target.value) || 0 })}
                  className="w-full px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 text-xs text-white focus:outline-none focus:border-emerald-500"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">Grading Scale</label>
                <input
                  type="text"
                  value={profile.grading_scale}
                  onChange={(e) => setProfile({ ...profile, grading_scale: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 text-xs text-white focus:outline-none focus:border-emerald-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">Target Degree Level</label>
              <select
                value={profile.target_degree}
                onChange={(e) => setProfile({ ...profile, target_degree: e.target.value })}
                className="w-full px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 text-xs text-white focus:outline-none focus:border-emerald-500"
              >
                <option value="Master's">Master's</option>
                <option value="PhD">PhD</option>
                <option value="Either">Either</option>
              </select>
            </div>
          </div>

          {/* Target Countries */}
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1.5">Target Study Destinations</label>
            <div className="flex flex-wrap gap-2">
              {['Canada', 'Germany', 'Singapore', 'United States', 'United Kingdom'].map((country) => {
                const isSelected = profile.target_countries?.includes(country);
                return (
                  <button
                    key={country}
                    type="button"
                    onClick={() => handleCountryToggle(country)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                      isSelected
                        ? 'bg-emerald-600 text-white'
                        : 'bg-slate-800 text-slate-400 hover:text-white border border-slate-700'
                    }`}
                  >
                    {country}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Specialization & Goals */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">Target Specialization</label>
              <input
                type="text"
                value={profile.target_field}
                onChange={(e) => setProfile({ ...profile, target_field: e.target.value })}
                className="w-full px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 text-xs text-white focus:outline-none focus:border-emerald-500"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">Intended Intake</label>
              <input
                type="text"
                value={profile.intended_intake || 'Fall 2026'}
                onChange={(e) => setProfile({ ...profile, intended_intake: e.target.value })}
                className="w-full px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 text-xs text-white focus:outline-none focus:border-emerald-500"
              />
            </div>
          </div>

          {/* Consent Checkbox */}
          <div className="pt-2">
            <label className="flex items-start gap-2.5 cursor-pointer">
              <input
                type="checkbox"
                checked={profile.consent_given}
                onChange={(e) => setProfile({ ...profile, consent_given: e.target.checked })}
                className="mt-0.5 rounded border-slate-700 bg-slate-800 text-emerald-500 focus:ring-0"
              />
              <span className="text-xs text-slate-400">
                I understand that profile facts will be processed by ScholarSwarm's 5 AI agents using Gemini Google Search grounding to discover live scholarships. No personal contact details will be submitted to third parties.
              </span>
            </label>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="mt-6 pt-4 border-t border-slate-800 flex items-center justify-between">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-lg text-xs font-medium text-slate-400 hover:text-white"
          >
            Cancel
          </button>

          <button
            type="button"
            onClick={() => onStartResearch(profile)}
            className="px-6 py-2.5 rounded-lg text-xs font-bold text-white bg-emerald-600 hover:bg-emerald-500 shadow-lg shadow-emerald-700/20 flex items-center gap-2 transition"
          >
            Launch 5-Agent Research Cycle
          </button>
        </div>

      </div>
    </div>
  );
};
