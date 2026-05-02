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

function withCity(path: string, city?: string | null): string {
  if (!city) return path;
  const sep = path.includes("?") ? "&" : "?";
  return `${path}${sep}city=${encodeURIComponent(city)}`;
}

export async function fetchScores(city?: string | null): Promise<TractScore[]> {
  const data = await get<{ tracts: TractScore[] }>(withCity("/api/regions/scores", city));
  return data.tracts;
}

export async function fetchTiers(city?: string | null): Promise<TierSummary[]> {
  return get<TierSummary[]>(withCity("/api/regions/tiers", city));
}

export async function fetchGeoJSON(city?: string | null): Promise<GeoJSON.FeatureCollection> {
  return get<GeoJSON.FeatureCollection>(withCity("/api/map/geojson", city));
}

export async function fetchLiveEvents(
  regionId?: string,
  city?: string | null,
): Promise<LiveEvent[]> {
  let path = `/api/live/feed`;
  if (regionId) path += `?region_id=${regionId}`;
  return get<LiveEvent[]>(withCity(path, city));
}

export async function fetchLiveBanner(regionId?: string, city?: string | null): Promise<LiveBanner> {
  let path = `/api/live/banner`;
  if (regionId) path += `?region_id=${regionId}`;
  return get<LiveBanner>(withCity(path, city));
}

// Re-export contract types for risk package
export type { TractRiskPackage, TrustPassport, Driver } from "./contracts";

export async function fetchRiskPackage(
  regionId: string,
  city?: string | null,
): Promise<import("./contracts").TractRiskPackage> {
  return get<import("./contracts").TractRiskPackage>(
    withCity(`/api/regions/risk-package?region_id=${regionId}`, city),
  );
}

export async function fetchBlindSpots(city?: string | null): Promise<TractScore[]> {
  const data = await get<{ blind_spots: TractScore[] }>(withCity("/api/regions/blind-spots", city));
  return data.blind_spots;
}

export async function fetchReportSummary(
  regionId: string,
  city?: string | null,
): Promise<ReportSummary> {
  return get<ReportSummary>(withCity(`/api/reports/summary?region_id=${regionId}`, city));
}

export async function fetchPersonaDecision(
  regionId: string,
  city?: string | null,
): Promise<PersonaDecision> {
  return get<PersonaDecision>(withCity(`/api/reports/persona-decision?region_id=${regionId}`, city));
}

export async function fetchCompare(
  leftId: string,
  rightId: string,
  city?: string | null,
): Promise<CompareResponse> {
  return get<CompareResponse>(
    withCity(`/api/compare?left_region_id=${leftId}&right_region_id=${rightId}`, city),
  );
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
  city?: string | null,
): Promise<SimulationResult> {
  const res = await fetch(`${API}${withCity("/api/simulator/run", city)}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ region_id: regionId, interventions, city: city ?? undefined }),
  });
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.json();
}

// --- Trend / forecast (real near-term risk projection) ---
export type TrendPoint = { date: string; value: number };
export type TrendForecastPoint = { date: string; value: number; lo: number; hi: number };
export type RegionTrend = {
  regionId: string;
  regionName: string;
  metric: "risk_score" | "incident_rate";
  horizonDays: number;
  history: TrendPoint[];
  forecast: TrendForecastPoint[];
  method: string;
  calibrationNote: string;
  trendDirection: "rising" | "falling" | "stable";
  next30dExpected: number;
  next30dLo: number;
  next30dHi: number;
};

export async function fetchRegionTrend(
  regionId: string,
  options: {
    horizonDays?: number;
    metric?: "risk_score" | "incident_rate";
    city?: string | null;
  } = {},
): Promise<RegionTrend> {
  const { horizonDays = 30, metric = "incident_rate", city } = options;
  const path = `/api/regions/trend?region_id=${encodeURIComponent(
    regionId,
  )}&horizon_days=${horizonDays}&metric=${metric}`;
  return get<RegionTrend>(withCity(path, city));
}

// --- Crime pattern breakdown ---
export type BreakdownCategory = {
  category: string;
  label: string;
  count30d: number;
  share: number;
  trendDirection: "rising" | "falling" | "stable";
  trendPct: number;
};

export type RegionBreakdown = {
  regionId: string;
  regionName: string;
  windowDays: number;
  total30d: number;
  categories: BreakdownCategory[];
  note: string;
};

export async function fetchRegionBreakdown(
  regionId: string,
  city?: string | null,
): Promise<RegionBreakdown> {
  return get<RegionBreakdown>(
    withCity(`/api/regions/breakdown?region_id=${encodeURIComponent(regionId)}`, city),
  );
}

// --- Pricing guidance ---
export type PricingPersona = "insurer" | "real_estate";
export type PricingBand =
  | "preferred"
  | "standard"
  | "surcharge"
  | "high_risk"
  | "decline_recommended";
export type PricingDriver = { name: string; contributionPct: number; evidence: string };

export type PricingQuote = {
  regionId: string;
  regionName: string;
  persona: PricingPersona;
  basePremium: number;
  suggestedPremium: number;
  riskMultiplier: number;
  band: PricingBand;
  drivers: PricingDriver[];
  confidence: number;
  methodology: string;
  alpha: number;
  beta: number;
  riskFactor: number;
  tierLoading: number;
  caveats: string[];
};

export async function fetchPricingQuote(
  regionId: string,
  options: {
    persona?: PricingPersona;
    basePremium?: number;
    city?: string | null;
  } = {},
): Promise<PricingQuote> {
  const { persona = "insurer", basePremium, city } = options;
  let path = `/api/pricing/quote?region_id=${encodeURIComponent(regionId)}&persona=${persona}`;
  if (basePremium !== undefined) path += `&base_premium=${basePremium}`;
  return get<PricingQuote>(withCity(path, city));
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

// --- Platform status (which Databricks features are wired) ---
export type PlatformStatus = {
  status: string;
  data_store_pref: string;
  backends_by_city: Record<string, "lakebase" | "postgres" | "json">;
  lakebase_configured: boolean;
  genie_configured: boolean;
  model_serving_configured: boolean;
  openai_configured: boolean;
};

export async function fetchPlatformStatus(): Promise<PlatformStatus> {
  return get<PlatformStatus>("/api/health/platform");
}

// --- Genie (Databricks natural-language Q&A) ---
export type GenieSuggestion = { label: string; prompt: string };

export type GenieSuggestionResponse = {
  city: string;
  label: string;
  geography: string;
  suggestions: GenieSuggestion[];
  configured: boolean;
};

export type GenieQueryResponse = {
  enabled: boolean;
  answer?: string | null;
  sql?: string | null;
  rows?: Record<string, unknown>[] | null;
  columns?: string[] | null;
  conversation_id?: string | null;
  message_id?: string | null;
  error?: string | null;
};

export async function fetchGenieSuggestions(
  city?: string | null,
): Promise<GenieSuggestionResponse> {
  return get<GenieSuggestionResponse>(withCity("/api/genie/suggestions", city));
}

export async function genieQuery(
  message: string,
  options: { city?: string | null; conversationId?: string | null } = {},
): Promise<GenieQueryResponse> {
  const res = await fetch(`${API}/api/genie/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message,
      city: options.city ?? undefined,
      conversation_id: options.conversationId ?? undefined,
    }),
  });
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.json();
}
