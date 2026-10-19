export interface ProjectOrAchievement {
  title: string;
  description: string;
  technologies: string[];
  repo_url?: string;
  is_ai_ml: boolean;
  evidence_source: string;
}

export interface StudentProfile {
  full_name: string;
  email?: string;
  current_degree: string;
  institution: string;
  cgpa: number;
  grading_scale: string;
  graduation_year?: number;
  target_degree: string;
  target_field: string;
  target_countries: string[];
  intended_intake?: string;
  citizenship?: string;
  funding_preference?: string;
  language_tests?: {
    test?: string;
    score?: string | null;
    status?: string;
  };
  skills: string[];
  projects: ProjectOrAchievement[];
  github_username?: string;
  github_url?: string;
  career_goals?: string;
  consent_given: boolean;
  missing_or_conflicting_facts?: string[];
}

export interface FundingDetails {
  funding_type: string;
  coverage_description: string;
  amount?: number | null;
  currency?: string | null;
  stipend_amount?: string | null;
  tuition_covered: boolean;
}

export interface EvidenceRecord {
  id?: string;
  opportunity_id?: string;
  run_id?: string;
  criterion_name: string;
  stated_requirement: string;
  student_value?: string;
  status: 'MEETS' | 'DOES_NOT_MEET' | 'UNRESOLVED' | 'NOT_APPLICABLE';
  evidence_excerpt?: string;
  source_title?: string;
  source_url: string;
  source_category: string;
  checked_at: string;
  uncertainty_or_conflict?: string;
}

export interface MatchScore {
  total_score: number;
  academic_fit: number;
  funding_fit: number;
  subject_fit: number;
  deadline_fit: number;
  evidence_fit: number;
  explanation: string;
  is_eligible_for_shortlist: boolean;
}

export interface Opportunity {
  id: string;
  run_id: string;
  canonical_url: string;
  title: string;
  program_name: string;
  university: string;
  country: string;
  degree_level: string;
  field: string;
  intake?: string;
  funding_details: FundingDetails;
  deadline?: string;
  deadline_type: string;
  deadline_verified: boolean;
  official_application_url?: string;
  official_source_urls: string[];
  evidence_quality: string;
  eligibility_status: 'MEETS_STATED_CRITERIA' | 'POTENTIAL_MATCH' | 'DOES_NOT_MEET' | 'INSUFFICIENT_EVIDENCE';
  eligibility_reasons: string[];
  actionable_gaps: string[];
  evidence_records?: EvidenceRecord[];
  match_score?: MatchScore;
  is_top_five: boolean;
  reviewer_status: string;
  reviewer_notes?: string;
}

export interface AgentEvent {
  id: string;
  run_id?: string;
  sequence_number?: number;
  timestamp: string;
  agent_role: string;
  event_type: string;
  title: string;
  description: string;
  metadata?: Record<string, any>;
}

export interface ResearchRun {
  id: string;
  created_at: string;
  updated_at: string;
  status: 'QUEUED' | 'RUNNING' | 'COMPLETED' | 'PARTIAL' | 'FAILED' | 'INTERRUPTED';
  student_profile: StudentProfile;
  current_phase?: string;
  research_round: number;
  total_candidates_found: number;
  total_verified: number;
  error_message?: string;
  retry_count: number;
}

export interface ApplicationDraft {
  id: string;
  opportunity_id: string;
  run_id: string;
  title: string;
  program_name: string;
  university: string;
  sop_content: string;
  unconfirmed_claims: string[];
  is_reviewed_by_agent: boolean;
  reviewer_feedback?: string;
  word_count: number;
}
