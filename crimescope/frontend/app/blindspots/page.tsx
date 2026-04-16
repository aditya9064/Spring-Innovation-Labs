"use client";

import NavHeader from "../../components/nav-header";
import { useBlindSpots, useScores } from "../../lib/hooks";
import type { TractScore } from "../../lib/api";

const TIER_COLOR: Record<string, string> = {
  Critical: "var(--cs-red)",
  High: "var(--cs-orange)",
  Elevated: "var(--cs-yellow)",
  Moderate: "var(--cs-accent)",
  Low: "var(--cs-green)",
};

function PanelHeader({ title, meta }: { title: string; meta?: string }) {
  return (
    <div
      className="flex items-center justify-between px-3 shrink-0"
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
        {title}
      </span>
      {meta && (
        <span className="text-[9px] tracking-wide" style={{ color: "var(--cs-gray2)" }}>
          {meta}
        </span>
      )}
    </div>
  );
}

function BlindSpotRow({ tract }: { tract: TractScore }) {
  const delta = tract.model_vs_baseline ?? 0;
  const absDelta = Math.abs(delta);
  const direction = delta > 0 ? "OVER" : "UNDER";
  const dirColor = delta > 0 ? "var(--cs-red)" : "var(--cs-amber)";

  return (
    <div
      className="flex items-center gap-3 px-3 py-2"
      style={{
        borderBottom: "1px solid rgba(30,30,30,0.5)",
        fontFamily: "var(--cs-mono)",
      }}
    >
      <div
        className="w-9 h-9 flex items-center justify-center text-[11px] font-bold tabular-nums shrink-0"
        style={{
          border: `1px solid ${TIER_COLOR[tract.risk_tier] || "var(--cs-gray3)"}33`,
          background: `${TIER_COLOR[tract.risk_tier] || "var(--cs-gray3)"}0d`,
          color: TIER_COLOR[tract.risk_tier] || "var(--cs-gray2)",
        }}
      >
        {Math.round(tract.risk_score)}
      </div>
      <div className="flex-1 min-w-0">
        <div
          className="text-[11px] font-medium truncate"
          style={{ color: "var(--cs-text)" }}
        >
          {tract.name || tract.NAMELSAD || `Tract ${tract.tract_geoid.slice(-6)}`}
        </div>
        <div className="text-[9px] mt-0.5" style={{ color: "var(--cs-gray2)" }}>
          {tract.tract_geoid} · {tract.risk_tier}
        </div>
      </div>
      <div className="flex flex-col items-end gap-0.5 shrink-0">
        <span
          className="text-[10px] font-bold tabular-nums"
          style={{ color: dirColor }}
        >
          {direction} {(absDelta * 100).toFixed(0)}%
        </span>
        <span className="text-[8px] uppercase tracking-wide" style={{ color: "var(--cs-gray2)" }}>
          MODEL VS BASE
        </span>
      </div>
    </div>
  );
}

export default function BlindSpotsPage() {
  const { data: blindSpots = [], isLoading } = useBlindSpots();
  const { data: allScores = [] } = useScores();

  const overPredicted = blindSpots.filter(
    (s) => (s.model_vs_baseline ?? 0) > 0,
  );
  const underPredicted = blindSpots.filter(
    (s) => (s.model_vs_baseline ?? 0) < 0,
  );

  const totalTracts = allScores.length;
  const blindSpotPct =
    totalTracts > 0
      ? ((blindSpots.length / totalTracts) * 100).toFixed(1)
      : "—";

  const kpis = [
    {
      label: "BLIND SPOTS",
      value: String(blindSpots.length),
      sub: `${blindSpotPct}% OF ALL TRACTS`,
      color: "var(--cs-amber)",
    },
    {
      label: "OVER-PREDICTED",
      value: String(overPredicted.length),
      sub: "MODEL > BASELINE",
      color: "var(--cs-red)",
    },
    {
      label: "UNDER-PREDICTED",
      value: String(underPredicted.length),
      sub: "MODEL < BASELINE",
      color: "var(--cs-orange)",
    },
    {
      label: "THRESHOLD",
      value: ">30%",
      sub: "DIVERGENCE CUTOFF",
      color: "var(--cs-cyan)",
    },
  ];

  return (
    <div
      className="flex flex-col h-screen overflow-hidden"
      style={{ background: "var(--cs-bg)" }}
    >
      <NavHeader />

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
            <div className="text-[9px] tracking-wide" style={{ color: "var(--cs-gray2)" }}>
              {k.sub}
            </div>
          </div>
        ))}
      </div>

      {/* Explainer */}
      <PanelHeader title="ABOUT BLIND SPOTS" meta="UNDERREPORTING & DIVERGENCE" />
      <div
        className="px-3 py-2.5"
        style={{
          background: "var(--cs-bg)",
          borderBottom: "1px solid var(--cs-border)",
          fontFamily: "var(--cs-mono)",
        }}
      >
        <p className="text-[11px]" style={{ color: "var(--cs-gray1)" }}>
          Blind spots are tracts where the ML model and historical baseline diverge
          by more than 30%. This may indicate underreporting, emerging patterns not
          yet captured in historical data, or model calibration issues. These tracts
          require manual review before underwriting decisions.
        </p>
      </div>

      {/* Main Content */}
      <div className="flex flex-1 min-h-0 overflow-hidden">
        {/* Over-predicted */}
        <div
          className="flex-1 flex flex-col"
          style={{ borderRight: "1px solid var(--cs-border)" }}
        >
          <PanelHeader
            title="OVER-PREDICTED"
            meta={`${overPredicted.length} TRACTS`}
          />
          <div
            className="px-3 py-1.5 shrink-0"
            style={{
              background: "var(--cs-panel)",
              borderBottom: "1px solid var(--cs-border)",
              fontFamily: "var(--cs-mono)",
            }}
          >
            <span className="text-[9px]" style={{ color: "var(--cs-gray2)" }}>
              Model assigns higher risk than baseline — possible false alarm or
              emerging threat not yet reflected in baseline data.
            </span>
          </div>
          <div className="flex-1 overflow-y-auto">
            {isLoading ? (
              <div className="flex items-center justify-center py-12">
                <span
                  className="text-[10px] uppercase tracking-[1px]"
                  style={{ color: "var(--cs-gray2)", fontFamily: "var(--cs-mono)" }}
                >
                  LOADING...
                </span>
              </div>
            ) : overPredicted.length === 0 ? (
              <div className="text-center py-8 text-[11px]" style={{ color: "var(--cs-gray3)", fontFamily: "var(--cs-mono)" }}>
                NO OVER-PREDICTED TRACTS
              </div>
            ) : (
              overPredicted.map((t) => (
                <BlindSpotRow key={t.tract_geoid} tract={t} />
              ))
            )}
          </div>
        </div>

        {/* Under-predicted */}
        <div className="flex-1 flex flex-col">
          <PanelHeader
            title="UNDER-PREDICTED"
            meta={`${underPredicted.length} TRACTS`}
          />
          <div
            className="px-3 py-1.5 shrink-0"
            style={{
              background: "var(--cs-panel)",
              borderBottom: "1px solid var(--cs-border)",
              fontFamily: "var(--cs-mono)",
            }}
          >
            <span className="text-[9px]" style={{ color: "var(--cs-gray2)" }}>
              Model assigns lower risk than baseline — possible underreporting or
              data gaps masking actual crime levels.
            </span>
          </div>
          <div className="flex-1 overflow-y-auto">
            {isLoading ? (
              <div className="flex items-center justify-center py-12">
                <span
                  className="text-[10px] uppercase tracking-[1px]"
                  style={{ color: "var(--cs-gray2)", fontFamily: "var(--cs-mono)" }}
                >
                  LOADING...
                </span>
              </div>
            ) : underPredicted.length === 0 ? (
              <div className="text-center py-8 text-[11px]" style={{ color: "var(--cs-gray3)", fontFamily: "var(--cs-mono)" }}>
                NO UNDER-PREDICTED TRACTS
              </div>
            ) : (
              underPredicted.map((t) => (
                <BlindSpotRow key={t.tract_geoid} tract={t} />
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
