import type { StudentProfile, ResearchRun, Opportunity, ApplicationDraft, GeminiModelOption } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export async function checkHealth() {
  const res = await fetch(`${API_BASE_URL}/api/health`);
  if (!res.ok) throw new Error(`Health check failed: ${res.statusText}`);
  return res.json();
}

export async function getAvailableModels(): Promise<{ current_model: string; models: GeminiModelOption[] }> {
  const res = await fetch(`${API_BASE_URL}/api/models`);
  if (!res.ok) throw new Error(`Failed to fetch models: ${res.statusText}`);
  return res.json();
}

export async function selectModel(modelId: string): Promise<{ success: boolean; current_model: string; message: string }> {
  const res = await fetch(`${API_BASE_URL}/api/models/select`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ model: modelId }),
  });
  if (!res.ok) throw new Error(`Failed to select model: ${res.statusText}`);
  return res.json();
}

export async function extractProfile(formData: FormData) {
  const res = await fetch(`${API_BASE_URL}/api/profile/extract`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errorData.detail || 'Profile extraction failed');
  }
  return res.json();
}

export async function startResearch(profile: StudentProfile, model?: string): Promise<ResearchRun> {
  const url = model 
    ? `${API_BASE_URL}/api/research/start?model=${encodeURIComponent(model)}`
    : `${API_BASE_URL}/api/research/start`;
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(profile),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errorData.detail || 'Failed to start research cycle');
  }
  return res.json();
}

export async function getResearchStatus(runId: string): Promise<ResearchRun> {
  const res = await fetch(`${API_BASE_URL}/api/research/${runId}`);
  if (!res.ok) throw new Error(`Failed to fetch research status`);
  return res.json();
}

export async function getOpportunities(runId: string): Promise<Opportunity[]> {
  const res = await fetch(`${API_BASE_URL}/api/research/${runId}/opportunities`);
  if (!res.ok) throw new Error(`Failed to fetch opportunities`);
  return res.json();
}

export async function getOpportunityDetails(opportunityId: string): Promise<Opportunity> {
  const res = await fetch(`${API_BASE_URL}/api/opportunities/${opportunityId}`);
  if (!res.ok) throw new Error(`Failed to fetch opportunity details`);
  return res.json();
}

export async function generateSopDraft(
  opportunityId: string,
  runId: string,
  specificInterests?: string
): Promise<ApplicationDraft> {
  const res = await fetch(`${API_BASE_URL}/api/opportunities/${opportunityId}/sop`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      opportunity_id: opportunityId,
      run_id: runId,
      specific_interests: specificInterests || null,
    }),
  });
  if (!res.ok) throw new Error(`Failed to generate SOP draft`);
  return res.json();
}

export async function resetDemoData() {
  const res = await fetch(`${API_BASE_URL}/api/opportunities/reset`, {
    method: 'POST',
  });
  return res.json();
}

export function subscribeToEvents(
  runId: string,
  onEvent: (event: any) => void,
  onDone: () => void,
  onError: (err: any) => void
) {
  const eventSource = new EventSource(`${API_BASE_URL}/api/research/${runId}/events`);

  eventSource.addEventListener('agent_event', (e) => {
    try {
      const data = JSON.parse(e.data);
      onEvent(data);
    } catch (err) {
      console.error('Error parsing SSE event data', err);
    }
  });

  eventSource.addEventListener('done', () => {
    eventSource.close();
    onDone();
  });

  eventSource.onerror = (err) => {
    onError(err);
  };

  return () => {
    eventSource.close();
  };
}
