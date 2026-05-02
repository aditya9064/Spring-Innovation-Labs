"use client";

import { useEffect } from "react";
import dynamic from "next/dynamic";
import LocationSearch from "../components/location-search";
import MapControls from "../components/map-controls";
import AIChatPanel from "../components/ai-chat";
import IntelligenceRail from "../components/intelligence-rail";
import { useScores, useRiskPackage, usePlatformStatus } from "../lib/hooks";
import { useAppStore } from "../lib/store";
import { getCity } from "../lib/cities";

const MapView = dynamic(() => import("../components/map-view"), { ssr: false });

const TIER_COLOR: Record<string, string> = {
  Critical: "var(--cs-red)",
  High: "var(--cs-orange)",
  Elevated: "var(--cs-yellow)",
  Moderate: "var(--cs-accent)",
  Low: "var(--cs-green)",
};

export default function DashboardPage() {
  const { data: scores = [] } = useScores();
  const tierFilter = useAppStore((s) => s.tierFilter);
  const chatOpen = useAppStore((s) => s.chatOpen);
  const selectedTract = useAppStore((s) => s.selectedTract);
  const setSelectedTract = useAppStore((s) => s.setSelectedTract);
  const persona = useAppStore((s) => s.persona);
  const city = useAppStore((s) => s.city);
  const cityCfg = getCity(city);
  const { data: riskPkg } = useRiskPackage(selectedTract);
  const { data: platform } = usePlatformStatus();

  // Auto-select the city's default region whenever the city changes (or on
  // first paint with no selection). This guarantees the IntelligenceRail
  // is always visible — without it, the persona toggle in the topbar
  // produces no visible change on the dashboard until a region is clicked.
  useEffect(() => {
    if (!selectedTract) {
      setSelectedTract(cityCfg.defaultRegionId);
    }
  }, [selectedTract, cityCfg.defaultRegionId, setSelectedTract]);

  const tiers = scores.reduce<Record<string, number>>((acc, s) => {
    acc[s.risk_tier] = (acc[s.risk_tier] || 0) + 1;
    return acc;
  }, {});

  const avgScore =
    scores.length > 0
      ? (scores.reduce((s, t) => s + t.risk_score, 0) / scores.length).toFixed(1)
      : "—";

  const kpis = [
    {
      label: cityCfg.geographyUnitPlural.toUpperCase(),
      value: String(scores.length),
      color: "var(--cs-text)",
    },
    { label: "CRITICAL", value: String(tiers["Critical"] || 0), color: "var(--cs-red)" },
    { label: "HIGH", value: String(tiers["High"] || 0), color: "var(--cs-orange)" },
    { label: "AVG SCORE", value: avgScore, color: "var(--cs-cyan)" },
  ];

  const backendKind = platform?.backends_by_city?.[city] ?? "json";
  const platformPills: { label: string; on: boolean; tone: string }[] = [
    {
      label:
        backendKind === "lakebase"
          ? "LAKEBASE"
          : backendKind === "postgres"
            ? "POSTGRES"
            : "JSON",
      on: backendKind !== "json",
      tone: backendKind === "lakebase" ? "var(--cs-accent)" : "var(--cs-cyan)",
    },
    { label: "GENIE", on: !!platform?.genie_configured, tone: "var(--cs-amber)" },
    {
      label: "MODEL SERVING",
      on: !!platform?.model_serving_configured,
      tone: "var(--cs-green)",
    },
  ];

  return (
    <>
      {/* KPI Strip */}
      <div
        className="flex items-center shrink-0"
        style={{
          borderBottom: "1px solid var(--cs-border)",
          fontFamily: "var(--cs-mono)",
        }}
      >
        {kpis.map((k) => (
          <div
            key={k.label}
            className="flex items-center gap-2 px-4 py-1.5"
            style={{ borderRight: "1px solid var(--cs-border)" }}
          >
            <span className="text-[8px] font-semibold uppercase tracking-[1px]" style={{ color: "var(--cs-gray2)" }}>
              {k.label}
            </span>
            <span className="text-base font-bold leading-none" style={{ color: k.color }}>
              {k.value}
            </span>
          </div>
        ))}
        <div className="flex-1" />
        <div className="flex items-center gap-1 px-3" title="Active Databricks integrations">
          {platformPills.map((p) => (
            <span
              key={p.label}
              className="text-[8px] font-bold tracking-[0.8px] px-1.5 py-0.5"
              style={{
                background: p.on ? p.tone : "transparent",
                color: p.on ? "#000" : "var(--cs-gray3)",
                border: `1px solid ${p.on ? p.tone : "var(--cs-border)"}`,
              }}
            >
              {p.label}
            </span>
          ))}
        </div>
      </div>

      {/* Main Content */}
      <div className="flex flex-1 min-h-0 overflow-hidden">
        {/* Map */}
        <div className="flex-1 relative" style={{ borderRight: "1px solid var(--cs-border)" }}>
          {/* Legend */}
          <div
            className="absolute bottom-3 left-3 z-10 flex flex-col gap-1 px-2 py-1.5"
            style={{
              background: "rgba(0,0,0,0.85)",
              border: "1px solid var(--cs-border)",
              fontFamily: "var(--cs-mono)",
            }}
          >
            {["Critical", "High", "Elevated", "Moderate", "Low"].map((tier) => (
              <div key={tier} className="flex items-center gap-1.5">
                <span
                  className="w-2 h-2 shrink-0"
                  style={{
                    background: TIER_COLOR[tier],
                    opacity: tierFilter.has(tier) ? 1 : 0.2,
                  }}
                />
                <span
                  className="text-[8px] tracking-wide"
                  style={{
                    color: tierFilter.has(tier) ? "var(--cs-gray1)" : "var(--cs-gray3)",
                  }}
                >
                  {tier.toUpperCase()}
                </span>
              </div>
            ))}
          </div>
          <LocationSearch />
          <MapControls />
          <MapView />
        </div>

        {/* Detail rail — only shows when a region is selected */}
        {selectedTract && riskPkg && (
          <IntelligenceRail riskPkg={riskPkg} persona={persona} />
        )}

        {chatOpen && <AIChatPanel />}
      </div>
    </>
  );
}
