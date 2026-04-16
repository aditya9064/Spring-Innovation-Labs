const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type TractScore = {
  tract_geoid: string;
  name: string;
  risk_score: number;
  risk_tier: "Critical" | "High" | "Elevated" | "Moderate" | "Low";
  predicted_next_30d: number;
  violent_score?: number;
  property_score?: number;
  incident_count: number;
  trend_direction?: "rising" | "falling" | "stable";
  model_vs_baseline?: number;
  NAMELSAD?: string;
  top_drivers_json?: string;
};

export type TierSummary = {
  tier: string;
  count: number;
  pct: number;
};

export type LiveBanner = {
  status: string;
  headline: string;
  summary: string;
  updatedAt: string;
};

export type LiveEvent = {
  id: string;
  title: string;
  status: string;
  confidence: string;
  sourceType: string;
  occurredAt: string;
  summary: string;
  resolvedRegionId?: string;
  lat?: number;
  lng?: number;
};

export type CompareSnapshot = {
  regionId: string;
  regionName: string;
  city: string;
  geographyType: string;
  score: number;
  baselineScore: number;
  mlScore: number;
  confidence: number;
  completeness: number;
  freshnessHours: number;
  trustStatus: string;
  underreportingRisk: string;
  topDrivers: { name: string; direction: string; impact: number; summary: string }[];
  recommendation: {
    persona: string;
    label: string;
    nextStep: string;
    caveat: string;
    reviewRequired: boolean;
  };
  liveDisagreement: { status: string; summary: string; delta: number };
};

export type CompareResponse = {
  left: CompareSnapshot;
  right: CompareSnapshot;
  summary: string;
};

export type ReportSummary = {
  regionId: string;
  title: string;
  executiveSummary: string;
  riskDrivers: string[];
  trustNotes: string[];
  compareSummary: string;
  challengeState: string;
};

export type PersonaDecision = {
  persona: string;
  regionId: string;
  decision: string;
  headline: string;
  nextStep: string;
  caveat: string;
  abstain: boolean;
};

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API}${path}`);
  if (!res.ok) throw new Error(`API ${res.status}: ${path}`);
  return res.json();
}

export async function fetchScores(): Promise<TractScore[]> {
  const data = await get<{ tracts: TractScore[] }>("/api/regions/scores");
  return data.tracts;
}

export async function fetchTiers(): Promise<TierSummary[]> {
  return get<TierSummary[]>("/api/regions/tiers");
}

export async function fetchGeoJSON(): Promise<GeoJSON.FeatureCollection> {
  return get<GeoJSON.FeatureCollection>("/api/map/geojson");
}

export async function fetchLiveEvents(
  regionId?: string,
): Promise<LiveEvent[]> {
  const q = regionId ? `?region_id=${regionId}` : "";
  return get<LiveEvent[]>(`/api/live/feed${q}`);
}

export async function fetchLiveBanner(regionId?: string): Promise<LiveBanner> {
  const q = regionId ? `?region_id=${regionId}` : "";
  return get<LiveBanner>(`/api/live/banner${q}`);
}

export async function fetchBlindSpots(): Promise<TractScore[]> {
  const data = await get<{ blind_spots: TractScore[] }>("/api/regions/blind-spots");
  return data.blind_spots;
}

export async function fetchReportSummary(regionId: string): Promise<ReportSummary> {
  return get<ReportSummary>(`/api/reports/summary?region_id=${regionId}`);
}

export async function fetchPersonaDecision(regionId: string): Promise<PersonaDecision> {
  return get<PersonaDecision>(`/api/reports/persona-decision?region_id=${regionId}`);
}

export async function fetchCompare(leftId: string, rightId: string): Promise<CompareResponse> {
  return get<CompareResponse>(`/api/compare?left_region_id=${leftId}&right_region_id=${rightId}`);
}

// --- Simulator ---
export type Intervention = {
  id: string;
  label: string;
  direction: "increase" | "decrease";
  typical_impact_pct: number;
};

export type SimulationResult = {
  region_id: string;
  region_name: string;
  original_score: number;
  simulated_score: number;
  delta: number;
  original_tier: string;
  simulated_tier: string;
  breakdown: { intervention: string; intensity: number; score_impact: number }[];
  narrative: string;
};

export async function fetchInterventions(): Promise<Intervention[]> {
  return get<Intervention[]>("/api/simulator/interventions");
}

export async function runSimulation(
  regionId: string,
  interventions: { id: string; intensity: number }[],
): Promise<SimulationResult> {
  const res = await fetch(`${API}/api/simulator/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ region_id: regionId, interventions }),
  });
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.json();
}

// --- Audit Trail ---
export type AuditRecord = {
  id: string;
  timestamp: string;
  region_id: string;
  persona: string;
  decision: string;
  rationale: string;
  risk_score: number;
  risk_tier: string;
  overridden: boolean;
  override_reason: string | null;
};

export type AuditStats = {
  total_decisions: number;
  decision_breakdown: Record<string, number>;
  total_overrides: number;
  override_rate: number;
};

export async function fetchAuditTrail(regionId?: string): Promise<AuditRecord[]> {
  const q = regionId ? `?region_id=${regionId}` : "";
  return get<AuditRecord[]>(`/api/audit${q}`);
}

export async function createAuditEntry(entry: {
  region_id: string;
  persona: string;
  decision: string;
  rationale: string;
  risk_score: number;
  risk_tier: string;
  overridden?: boolean;
  override_reason?: string;
}): Promise<AuditRecord> {
  const res = await fetch(`${API}/api/audit`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(entry),
  });
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.json();
}

export async function fetchAuditStats(): Promise<AuditStats> {
  return get<AuditStats>("/api/audit/stats");
}

// --- Challenge Mode ---
export type ChallengeRecord = {
  id: string;
  timestamp: string;
  region_id: string;
  challenger_name: string;
  challenge_type: string;
  evidence: string;
  proposed_adjustment: number | null;
  status: string;
  reviewer_notes: string | null;
};

export type ChallengeStats = {
  total_challenges: number;
  by_status: Record<string, number>;
  by_type: Record<string, number>;
};

export async function fetchChallenges(regionId?: string): Promise<ChallengeRecord[]> {
  const q = regionId ? `?region_id=${regionId}` : "";
  return get<ChallengeRecord[]>(`/api/challenge${q}`);
}

export async function createChallenge(entry: {
  region_id: string;
  challenger_name: string;
  challenge_type: string;
  evidence: string;
  proposed_adjustment?: number;
}): Promise<ChallengeRecord> {
  const res = await fetch(`${API}/api/challenge`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(entry),
  });
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.json();
}

export async function fetchChallengeStats(): Promise<ChallengeStats> {
  return get<ChallengeStats>("/api/challenge/stats");
}

// --- WebSocket ---
export const WS_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000")
  .replace("http://", "ws://")
  .replace("https://", "wss://");
