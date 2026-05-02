import { useQuery } from "@tanstack/react-query";
import {
  fetchScores,
  fetchTiers,
  fetchLiveEvents,
  fetchLiveBanner,
  fetchBlindSpots,
  fetchReportSummary,
  fetchPersonaDecision,
  fetchCompare,
  fetchInterventions,
  fetchAuditTrail,
  fetchAuditStats,
  fetchChallenges,
  fetchChallengeStats,
  fetchRiskPackage,
  fetchRegionTrend,
  fetchRegionBreakdown,
  fetchPricingQuote,
  fetchPlatformStatus,
  fetchGenieSuggestions,
  type PricingPersona,
} from "./api";
import { useAppStore } from "./store";

/**
 * Reads the current city out of the store. Subscribing here means every hook
 * automatically re-fetches when the user switches Chicago ↔ UK in the nav.
 */
function useCity(): string {
  return useAppStore((s) => s.city);
}

export function useScores() {
  const city = useCity();
  return useQuery({
    queryKey: ["scores", city],
    queryFn: () => fetchScores(city),
  });
}

export function useTiers() {
  const city = useCity();
  return useQuery({
    queryKey: ["tiers", city],
    queryFn: () => fetchTiers(city),
  });
}

export function useLiveEvents(regionId?: string) {
  const city = useCity();
  return useQuery({
    queryKey: ["liveEvents", city, regionId],
    queryFn: () => fetchLiveEvents(regionId, city),
  });
}

export function useLiveBanner() {
  const city = useCity();
  return useQuery({
    queryKey: ["liveBanner", city],
    queryFn: () => fetchLiveBanner(undefined, city),
    refetchInterval: 30_000,
  });
}

export function useBlindSpots() {
  const city = useCity();
  return useQuery({
    queryKey: ["blindSpots", city],
    queryFn: () => fetchBlindSpots(city),
  });
}

export function useReportSummary(regionId: string | null) {
  const city = useCity();
  return useQuery({
    queryKey: ["reportSummary", city, regionId],
    queryFn: () => fetchReportSummary(regionId!, city),
    enabled: !!regionId,
  });
}

export function usePersonaDecision(regionId: string | null) {
  const city = useCity();
  return useQuery({
    queryKey: ["personaDecision", city, regionId],
    queryFn: () => fetchPersonaDecision(regionId!, city),
    enabled: !!regionId,
  });
}

export function useCompare(leftId: string, rightId: string) {
  const city = useCity();
  return useQuery({
    queryKey: ["compare", city, leftId, rightId],
    queryFn: () => fetchCompare(leftId, rightId, city),
    enabled: !!leftId && !!rightId,
  });
}

export function useInterventions() {
  return useQuery({
    queryKey: ["interventions"],
    queryFn: fetchInterventions,
  });
}

export function useAuditTrail(regionId?: string) {
  return useQuery({
    queryKey: ["audit", regionId],
    queryFn: () => fetchAuditTrail(regionId),
  });
}

export function useAuditStats() {
  return useQuery({
    queryKey: ["auditStats"],
    queryFn: fetchAuditStats,
  });
}

export function useChallenges(regionId?: string) {
  return useQuery({
    queryKey: ["challenges", regionId],
    queryFn: () => fetchChallenges(regionId),
  });
}

export function useChallengeStats() {
  return useQuery({
    queryKey: ["challengeStats"],
    queryFn: fetchChallengeStats,
  });
}

export function useRiskPackage(regionId: string | null) {
  const city = useCity();
  return useQuery({
    queryKey: ["riskPackage", city, regionId],
    queryFn: () => fetchRiskPackage(regionId!, city),
    enabled: !!regionId,
  });
}

export function useRegionTrend(
  regionId: string | null,
  options: { horizonDays?: number; metric?: "risk_score" | "incident_rate" } = {},
) {
  const city = useCity();
  const { horizonDays = 30, metric = "incident_rate" } = options;
  return useQuery({
    queryKey: ["regionTrend", city, regionId, horizonDays, metric],
    queryFn: () => fetchRegionTrend(regionId!, { horizonDays, metric, city }),
    enabled: !!regionId,
  });
}

export function useRegionBreakdown(regionId: string | null) {
  const city = useCity();
  return useQuery({
    queryKey: ["regionBreakdown", city, regionId],
    queryFn: () => fetchRegionBreakdown(regionId!, city),
    enabled: !!regionId,
  });
}

export function usePricingQuote(
  regionId: string | null,
  options: { persona?: PricingPersona; basePremium?: number } = {},
) {
  const city = useCity();
  const { persona = "insurer", basePremium } = options;
  return useQuery({
    queryKey: ["pricingQuote", city, regionId, persona, basePremium],
    queryFn: () => fetchPricingQuote(regionId!, { persona, basePremium, city }),
    enabled: !!regionId,
  });
}

export function usePlatformStatus() {
  return useQuery({
    queryKey: ["platformStatus"],
    queryFn: fetchPlatformStatus,
    staleTime: 60_000,
  });
}

export function useGenieSuggestions() {
  const city = useCity();
  return useQuery({
    queryKey: ["genieSuggestions", city],
    queryFn: () => fetchGenieSuggestions(city),
    staleTime: 5 * 60_000,
  });
}
