-- ScholarSwarm Supabase PostgreSQL Schema
-- TetraNoodle AI Hackathon 2026

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Research Runs Table
CREATE TABLE IF NOT EXISTS research_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status VARCHAR(32) NOT NULL DEFAULT 'QUEUED', -- QUEUED, RUNNING, COMPLETED, PARTIAL, FAILED, INTERRUPTED
    student_profile JSONB NOT NULL,
    current_phase VARCHAR(64),
    research_round INT NOT NULL DEFAULT 1,
    total_candidates_found INT NOT NULL DEFAULT 0,
    total_verified INT NOT NULL DEFAULT 0,
    error_message TEXT,
    retry_count INT NOT NULL DEFAULT 0
);

-- Index on research_runs status & created_at
CREATE INDEX IF NOT EXISTS idx_research_runs_status ON research_runs(status);
CREATE INDEX IF NOT EXISTS idx_research_runs_created_at ON research_runs(created_at DESC);

-- 2. Opportunities Table
CREATE TABLE IF NOT EXISTS opportunities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_id UUID NOT NULL REFERENCES research_runs(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    canonical_url TEXT NOT NULL,
    title TEXT NOT NULL,
    program_name TEXT NOT NULL,
    university TEXT NOT NULL,
    country VARCHAR(64) NOT NULL,
    degree_level VARCHAR(32) NOT NULL, -- Master's, PhD, Either
    field VARCHAR(128) NOT NULL,
    intake VARCHAR(64),
    
    admission_requirements JSONB NOT NULL DEFAULT '[]'::jsonb,
    scholarship_requirements JSONB NOT NULL DEFAULT '[]'::jsonb,
    
    funding_type VARCHAR(64), -- Fully Funded, Partial Tuition, Stipend, etc.
    funding_coverage VARCHAR(64),
    funding_amount NUMERIC,
    funding_currency VARCHAR(16),
    
    deadline TEXT,
    deadline_type VARCHAR(32), -- Fixed, Rolling, Priority, Unknown
    deadline_verified BOOLEAN NOT NULL DEFAULT FALSE,
    
    official_application_url TEXT,
    official_source_urls JSONB NOT NULL DEFAULT '[]'::jsonb,
    source_retrieval_timestamps JSONB NOT NULL DEFAULT '{}'::jsonb,
    evidence_quality VARCHAR(32) NOT NULL DEFAULT 'UNVERIFIED', -- OFFICIAL, SECONDARY, INSUFFICIENT, UNVERIFIED
    
    eligibility_status VARCHAR(32) NOT NULL DEFAULT 'INSUFFICIENT_EVIDENCE', -- MEETS_STATED_CRITERIA, POTENTIAL_MATCH, DOES_NOT_MEET, INSUFFICIENT_EVIDENCE
    eligibility_reasons JSONB NOT NULL DEFAULT '[]'::jsonb,
    
    match_score NUMERIC DEFAULT 0,
    match_breakdown JSONB NOT NULL DEFAULT '{}'::jsonb,
    match_explanation TEXT,
    
    is_top_five BOOLEAN NOT NULL DEFAULT FALSE,
    reviewer_status VARCHAR(32) NOT NULL DEFAULT 'PENDING', -- PENDING, APPROVED, REJECTED, FLAGGED
    reviewer_notes TEXT,
    
    CONSTRAINT uq_run_canonical_url UNIQUE (run_id, canonical_url)
);

CREATE INDEX IF NOT EXISTS idx_opportunities_run_id ON opportunities(run_id);
CREATE INDEX IF NOT EXISTS idx_opportunities_score ON opportunities(match_score DESC);
CREATE INDEX IF NOT EXISTS idx_opportunities_status ON opportunities(eligibility_status);

-- 3. Evidence Records Table
CREATE TABLE IF NOT EXISTS evidence_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    opportunity_id UUID NOT NULL REFERENCES opportunities(id) ON DELETE CASCADE,
    run_id UUID NOT NULL REFERENCES research_runs(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    criterion_name TEXT NOT NULL,
    stated_requirement TEXT NOT NULL,
    student_value TEXT,
    status VARCHAR(32) NOT NULL, -- MEETS, DOES_NOT_MEET, UNRESOLVED, NOT_APPLICABLE
    evidence_excerpt TEXT,
    source_title TEXT,
    source_url TEXT NOT NULL,
    source_category VARCHAR(32) NOT NULL DEFAULT 'OFFICIAL', -- OFFICIAL, SECONDARY, UNVERIFIED
    checked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    uncertainty_or_conflict TEXT
);

CREATE INDEX IF NOT EXISTS idx_evidence_opportunity_id ON evidence_records(opportunity_id);
CREATE INDEX IF NOT EXISTS idx_evidence_run_id ON evidence_records(run_id);

-- 4. Agent Events Table (for SSE and live replay)
CREATE TABLE IF NOT EXISTS agent_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_id UUID NOT NULL REFERENCES research_runs(id) ON DELETE CASCADE,
    sequence_number BIGSERIAL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    agent_role VARCHAR(64) NOT NULL, -- Profile Intelligence Agent, Research & Eligibility Agent, Match Strategist Agent, Application Coach Agent, Quality Reviewer Agent, System Supervisor
    event_type VARCHAR(64) NOT NULL, -- SEARCH_QUERY, CANDIDATE_FOUND, URL_RETRIEVED, REQUIREMENT_EXTRACTED, ELIGIBILITY_EVALUATED, DUPLICATE_REMOVED, RETRIEVAL_FAILED, RETRY_SCHEDULED, REVIEWER_FLAGGED, SCORE_CALCULATED, SOP_GENERATED, COMPLETED, ERROR
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_agent_events_run_id ON agent_events(run_id, sequence_number ASC);

-- 5. Application Drafts Table (SOP)
CREATE TABLE IF NOT EXISTS application_drafts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    opportunity_id UUID NOT NULL REFERENCES opportunities(id) ON DELETE CASCADE,
    run_id UUID NOT NULL REFERENCES research_runs(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    title TEXT NOT NULL,
    program_name TEXT NOT NULL,
    university TEXT NOT NULL,
    sop_content TEXT NOT NULL,
    unconfirmed_claims JSONB NOT NULL DEFAULT '[]'::jsonb,
    is_reviewed_by_agent BOOLEAN NOT NULL DEFAULT FALSE,
    reviewer_feedback TEXT,
    word_count INT NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_sop_opportunity_id ON application_drafts(opportunity_id);
