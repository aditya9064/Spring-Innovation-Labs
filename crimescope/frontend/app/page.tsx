"use client";

import dynamic from "next/dynamic";
import NavHeader from "../components/nav-header";
import { TractPanel } from "../components/tract-panel";
import LocationSearch from "../components/location-search";
import MapControls from "../components/map-controls";
import LiveFeed from "../components/live-feed";
import AIChatPanel from "../components/ai-chat";
import { useScores } from "../lib/hooks";
import { useAppStore } from "../lib/store";

const MapView = dynamic(() => import("../components/map-view"), { ssr: false });

const TIER_COLOR: Record<string, string> = {
  Critical: "var(--cs-red)",
  High: "var(--cs-orange)",
  Elevated: "var(--cs-yellow)",
  Moderate: "var(--cs-accent)",
  Low: "var(--cs-green)",
};

export default function DashboardPage() {
  const { data: scores = [], isLoading } = useScores();
  const tierFilter = useAppStore((s) => s.tierFilter);
  const chatOpen = useAppStore((s) => s.chatOpen);

  const filteredScores = scores.filter((s) => tierFilter.has(s.risk_tier));

  const tiers = scores.reduce<Record<string, number>>((acc, s) => {
    acc[s.risk_tier] = (acc[s.risk_tier] || 0) + 1;
    return acc;
  }, {});

  const avgScore =
    scores.length > 0
      ? (scores.reduce((s, t) => s + t.risk_score, 0) / scores.length).toFixed(
          1,
        )
      : "—";

  const kpis = [
    { label: "TRACTS ANALYZED", value: String(scores.length), sub: "CHICAGO METRO", color: "var(--cs-text)" },
    { label: "CRITICAL", value: String(tiers["Critical"] || 0), sub: "IMMEDIATE CONCERN", color: "var(--cs-red)" },
    { label: "HIGH RISK", value: String(tiers["High"] || 0), sub: "ELEVATED CONCERN", color: "var(--cs-orange)" },
    { label: "ELEVATED", value: String(tiers["Elevated"] || 0), sub: "WATCH LIST", color: "var(--cs-yellow)" },
    { label: "AVG SCORE", value: avgScore, sub: "ACROSS ALL TRACTS", color: "var(--cs-cyan)" },
  ];

  return (
    <div
      className="flex flex-col h-screen overflow-hidden"
      style={{ background: "var(--cs-bg)" }}
    >
      <NavHeader>
        <span
          className="text-[11px] font-semibold text-black/80 tracking-wide hidden lg:flex items-center gap-1.5"
        >
          <span
            className="inline-block w-1.5 h-1.5 rounded-full bg-black/60"
            style={{ animation: "cs-pulse 2s ease-in-out infinite" }}
          />
          {scores.length > 0
            ? `${scores.length} TRACTS LOADED`
            : "LOADING..."}
        </span>
      </NavHeader>

      {/* KPI Row */}
      <div
        className="flex shrink-0"
        style={{
          borderBottom: "1px solid var(--cs-border)",
          fontFamily: "var(--cs-mono)",
        }}
      >
        {kpis.map((k) => (
          <div
            key={k.label}
            className="flex-1 px-3.5 py-2.5"
            style={{ borderRight: "1px solid var(--cs-border)" }}
          >
            <div
              className="text-[9px] font-semibold uppercase tracking-[1.2px] mb-1"
              style={{ color: "var(--cs-gray2)" }}
            >
              {k.label}
            </div>
            <div
              className="text-xl font-bold tracking-tight leading-none mb-0.5"
              style={{ color: k.color }}
            >
              {k.value}
            </div>
            <div
              className="text-[9px] tracking-wide"
              style={{ color: "var(--cs-gray2)" }}
            >
              {k.sub}
            </div>
          </div>
        ))}
      </div>

      {/* Main Content: Map + Panels */}
      <div className="flex flex-1 min-h-0 overflow-hidden">
        {/* Map */}
        <div
          className="flex-1 relative"
          style={{ borderRight: "1px solid var(--cs-border)" }}
        >
          {/* Legend overlay */}
          <div
            className="absolute bottom-3 left-3 z-10 flex flex-col gap-1 px-2.5 py-2"
            style={{
              background: "rgba(0,0,0,0.85)",
              border: "1px solid var(--cs-border)",
              fontFamily: "var(--cs-mono)",
            }}
          >
            <span
              className="text-[8px] font-bold uppercase tracking-[1px] mb-0.5"
              style={{ color: "var(--cs-accent)" }}
            >
              RISK TIER
            </span>
            {["Critical", "High", "Elevated", "Moderate", "Low"].map(
              (tier) => (
                <div key={tier} className="flex items-center gap-1.5">
                  <span
                    className="w-2.5 h-2.5 shrink-0"
                    style={{
                      background: TIER_COLOR[tier],
                      opacity: tierFilter.has(tier) ? 1 : 0.2,
                    }}
                  />
                  <span
                    className="text-[9px] tracking-wide"
                    style={{
                      color: tierFilter.has(tier)
                        ? "var(--cs-gray1)"
                        : "var(--cs-gray3)",
                    }}
                  >
                    {tier.toUpperCase()}
                  </span>
                </div>
              ),
            )}
          </div>
          <LocationSearch />
          <MapControls />
          <MapView />
        </div>

        {/* Tract List Panel */}
        <div
          className="flex flex-col"
          style={{
            width: 340,
            background: "var(--cs-bg)",
          }}
        >
          {/* Panel Header */}
          <div
            className="flex items-center justify-between px-2.5 shrink-0"
            style={{
              height: 28,
              background: "var(--cs-panel)",
              borderBottom: "1px solid var(--cs-border)",
              fontFamily: "var(--cs-mono)",
            }}
          >
            <span
              className="text-[10px] font-bold tracking-[1.5px] uppercase"
              style={{ color: "var(--cs-accent)" }}
            >
              TRACT RANKING
            </span>
            <span
              className="text-[9px] tracking-wide"
              style={{ color: "var(--cs-gray2)" }}
            >
              {filteredScores.length}/{scores.length} TRACTS
            </span>
          </div>
          <TractPanel scores={filteredScores} loading={isLoading} />
        </div>

        {/* Live Feed Panel */}
        <LiveFeed />

        {/* AI Chat Panel */}
        {chatOpen && <AIChatPanel />}
      </div>
    </div>
  );
}
