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
} from "./api";

export function useScores() {
  return useQuery({
    queryKey: ["scores"],
    queryFn: fetchScores,
  });
}

export function useTiers() {
  return useQuery({
    queryKey: ["tiers"],
    queryFn: fetchTiers,
  });
}

export function useLiveEvents(regionId?: string) {
  return useQuery({
    queryKey: ["liveEvents", regionId],
    queryFn: () => fetchLiveEvents(regionId),
  });
}

export function useLiveBanner() {
  return useQuery({
    queryKey: ["liveBanner"],
    queryFn: () => fetchLiveBanner(),
    refetchInterval: 30_000,
  });
}

export function useBlindSpots() {
  return useQuery({
    queryKey: ["blindSpots"],
    queryFn: fetchBlindSpots,
  });
}

export function useReportSummary(regionId: string | null) {
  return useQuery({
    queryKey: ["reportSummary", regionId],
    queryFn: () => fetchReportSummary(regionId!),
    enabled: !!regionId,
  });
}

export function usePersonaDecision(regionId: string | null) {
  return useQuery({
    queryKey: ["personaDecision", regionId],
    queryFn: () => fetchPersonaDecision(regionId!),
    enabled: !!regionId,
  });
}

export function useCompare(leftId: string, rightId: string) {
  return useQuery({
    queryKey: ["compare", leftId, rightId],
    queryFn: () => fetchCompare(leftId, rightId),
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
