"use client";

import { useState, useEffect } from "react";
import { useCompare, useScores } from "../../lib/hooks";
import { useAppStore } from "../../lib/store";
import { getCity } from "../../lib/cities";
import type { CompareSnapshot } from "../../lib/api";

const PERSONA_CONFLICT_LABELS: Record<string, string> = {
  insurer: "Quote / reprice / review",
  resident: "Caution / monitor",
  buyer: "Invest / wait / avoid",
  business: "Site / relocate",
  planner: "Intervene / monitor",
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
      <span className="text-[10px] font-bold tracking-[1.5px] uppercase" style={{ color: "var(--cs-accent)" }}>
        {title}
      </span>
      {meta && (
        <span className="text-[9px] tracking-wide" style={{ color: "var(--cs-gray2)" }}>{meta}</span>
      )}
    </div>
  );
}

function SnapshotColumn({ snap, label }: { snap: CompareSnapshot; label: string }) {
  const riskColor =
    snap.score >= 75
      ? "var(--cs-red)"
      : snap.score >= 50
        ? "var(--cs-orange)"
        : snap.score >= 30
          ? "var(--cs-yellow)"
          : "var(--cs-green)";

  return (
    <div className="flex-1 flex flex-col" style={{ borderRight: "1px solid var(--cs-border)" }}>
      <PanelHeader title={label} meta={snap.regionId} />
      <div className="px-3 py-2" style={{ background: "var(--cs-bg)", borderBottom: "1px solid var(--cs-border)" }}>
        <div className="text-sm font-bold mb-1" style={{ color: "var(--cs-text)" }}>
          {snap.regionName}
        </div>
        <div className="flex items-center gap-2">
          <span
            className="text-[10px] font-bold px-2 py-0.5 uppercase tracking-wide"
            style={{ fontFamily: "var(--cs-mono)", background: "var(--cs-accent-lo)", color: "var(--cs-accent)", border: "1px solid var(--cs-accent-md)" }}
          >
            {snap.recommendation.label}
          </span>
          <span className="text-[9px]" style={{ color: "var(--cs-gray2)", fontFamily: "var(--cs-mono)" }}>
            {snap.trustStatus} · {snap.underreportingRisk} underreport risk
          </span>
        </div>
      </div>

      {/* Scores */}
      <PanelHeader title="SCORES" />
      <div className="px-3 py-2" style={{ background: "var(--cs-bg)", borderBottom: "1px solid var(--cs-border)" }}>
        <div className="flex gap-2" style={{ fontFamily: "var(--cs-mono)" }}>
          <div className="flex-1 text-center py-1.5" style={{ border: "1px solid var(--cs-border)", background: "var(--cs-panel2)" }}>
            <div className="text-[8px] font-semibold tracking-[0.8px] mb-1" style={{ color: "var(--cs-gray2)" }}>SCORE</div>
            <div className="text-lg font-bold" style={{ color: riskColor }}>{snap.score}</div>
          </div>
          <div className="flex-1 text-center py-1.5" style={{ border: "1px solid var(--cs-border)", background: "var(--cs-panel2)" }}>
            <div className="text-[8px] font-semibold tracking-[0.8px] mb-1" style={{ color: "var(--cs-gray2)" }}>ML</div>
            <div className="text-lg font-bold" style={{ color: "var(--cs-green)" }}>{snap.mlScore}</div>
          </div>
          <div className="flex-1 text-center py-1.5" style={{ border: "1px solid var(--cs-border)", background: "var(--cs-panel2)" }}>
            <div className="text-[8px] font-semibold tracking-[0.8px] mb-1" style={{ color: "var(--cs-gray2)" }}>BASE</div>
            <div className="text-lg font-bold" style={{ color: "var(--cs-cyan)" }}>{snap.baselineScore}</div>
          </div>
        </div>

        {/* Trust metrics */}
        <div className="flex gap-2 mt-2" style={{ fontFamily: "var(--cs-mono)" }}>
          <div className="flex-1 text-center py-1" style={{ border: "1px solid var(--cs-border)", background: "var(--cs-panel2)" }}>
            <div className="text-[8px] font-semibold tracking-[0.8px]" style={{ color: "var(--cs-gray2)" }}>CONF</div>
            <div className="text-sm font-bold" style={{ color: "var(--cs-amber)" }}>{(snap.confidence * 100).toFixed(0)}%</div>
          </div>
          <div className="flex-1 text-center py-1" style={{ border: "1px solid var(--cs-border)", background: "var(--cs-panel2)" }}>
            <div className="text-[8px] font-semibold tracking-[0.8px]" style={{ color: "var(--cs-gray2)" }}>COMPL</div>
            <div className="text-sm font-bold" style={{ color: "var(--cs-amber)" }}>{(snap.completeness * 100).toFixed(0)}%</div>
          </div>
          <div className="flex-1 text-center py-1" style={{ border: "1px solid var(--cs-border)", background: "var(--cs-panel2)" }}>
            <div className="text-[8px] font-semibold tracking-[0.8px]" style={{ color: "var(--cs-gray2)" }}>FRESH</div>
            <div className="text-sm font-bold" style={{ color: "var(--cs-amber)" }}>{snap.freshnessHours}h</div>
          </div>
        </div>
      </div>

      {/* Drivers */}
      <PanelHeader title="TOP DRIVERS" meta={`${snap.topDrivers.length} FACTORS`} />
      <div style={{ background: "var(--cs-bg)", borderBottom: "1px solid var(--cs-border)" }}>
        {snap.topDrivers.map((d, i) => (
          <div
            key={i}
            className="flex items-center gap-2 px-3 py-1.5 text-[11px]"
            style={{ fontFamily: "var(--cs-mono)", borderBottom: i < snap.topDrivers.length - 1 ? "1px solid rgba(30,30,30,0.5)" : "none" }}
          >
            <span style={{ color: d.direction === "up" ? "var(--cs-red)" : d.direction === "down" ? "var(--cs-green)" : "var(--cs-gray2)" }}>
              {d.direction === "up" ? "▲" : d.direction === "down" ? "▼" : "→"}
            </span>
            <span className="flex-1" style={{ color: "var(--cs-text)" }}>{d.name}</span>
            <span className="text-[9px] tabular-nums" style={{ color: "var(--cs-gray2)" }}>
              {d.impact.toFixed(3)}
            </span>
          </div>
        ))}
        {snap.topDrivers.length === 0 && (
          <div className="text-center py-4 text-[10px]" style={{ color: "var(--cs-gray3)", fontFamily: "var(--cs-mono)" }}>
            NO DRIVERS AVAILABLE
          </div>
        )}
      </div>

      {/* Disagreement */}
      <PanelHeader title="LIVE DISAGREEMENT" />
      <div className="px-3 py-2" style={{ background: "var(--cs-bg)", borderBottom: "1px solid var(--cs-border)", fontFamily: "var(--cs-mono)" }}>
        <div className="flex items-center gap-2 mb-1">
          <span
            className="text-[9px] font-bold px-1.5 py-0.5 uppercase tracking-wide"
            style={{
              background: snap.liveDisagreement.status === "aligned" ? "var(--cs-green-lo)" : "var(--cs-red-lo)",
              color: snap.liveDisagreement.status === "aligned" ? "var(--cs-green)" : "var(--cs-red)",
              border: `1px solid ${snap.liveDisagreement.status === "aligned" ? "var(--cs-green)" : "var(--cs-red)"}33`,
            }}
          >
            {snap.liveDisagreement.status}
          </span>
          <span className="text-[10px] font-bold" style={{ color: snap.liveDisagreement.delta > 0 ? "var(--cs-red)" : "var(--cs-green)" }}>
            {snap.liveDisagreement.delta > 0 ? "+" : ""}{snap.liveDisagreement.delta}
          </span>
        </div>
        <p className="text-[10px]" style={{ color: "var(--cs-gray2)" }}>
          {snap.liveDisagreement.summary}
        </p>
      </div>

      {/* Recommendation */}
      <PanelHeader title="RECOMMENDATION" />
      <div className="px-3 py-2" style={{ background: "var(--cs-bg)" }}>
        <span
          className="text-[10px] font-bold px-2 py-0.5 uppercase tracking-wide"
          style={{ fontFamily: "var(--cs-mono)", background: "var(--cs-amber)", color: "#000" }}
        >
          {snap.recommendation.label}
        </span>
        <p className="text-[10px] mt-1.5" style={{ color: "var(--cs-gray1)", fontFamily: "var(--cs-mono)" }}>
          {snap.recommendation.nextStep}
        </p>
        <p className="text-[10px] mt-0.5" style={{ color: "var(--cs-gray2)", fontFamily: "var(--cs-mono)" }}>
          {snap.recommendation.caveat}
        </p>
      </div>
    </div>
  );
}

export default function ComparePage() {
  const storeLeft = useAppStore((s) => s.compareLeft);
  const storeRight = useAppStore((s) => s.compareRight);
  const city = useAppStore((s) => s.city);
  const cityCfg = getCity(city);
  const { data: scores = [] } = useScores();

  const fallbackLeft = scores[0]?.tract_geoid || cityCfg.defaultRegionId;
  const fallbackRight = scores[1]?.tract_geoid || scores[0]?.tract_geoid || cityCfg.defaultRegionId;

  const [leftId, setLeftId] = useState(storeLeft || fallbackLeft);
  const [rightId, setRightId] = useState(storeRight || fallbackRight);

  useEffect(() => {
    if (storeLeft) setLeftId(storeLeft);
  }, [storeLeft]);
  useEffect(() => {
    if (storeRight) setRightId(storeRight);
  }, [storeRight]);
  // When the city changes, reset selectors to fresh fallbacks for that city.
  useEffect(() => {
    if (!storeLeft) setLeftId(fallbackLeft);
    if (!storeRight) setRightId(fallbackRight);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [city]);
  const { data: comparison, isLoading } = useCompare(leftId, rightId);

  const leftOptions = scores.filter((s) =>
    leftId
      ? s.tract_geoid.includes(leftId) || (s.name || "").toLowerCase().includes(leftId.toLowerCase())
      : true,
  );

  return (
    <div className="flex flex-col flex-1 overflow-hidden" style={{ background: "var(--cs-bg)" }}>

      {/* Tract Selectors */}
      <div
        className="flex shrink-0"
        style={{ borderBottom: "1px solid var(--cs-border)", fontFamily: "var(--cs-mono)" }}
      >
        <div className="flex-1 flex items-center gap-2 px-3" style={{ height: 36, background: "var(--cs-panel)", borderRight: "1px solid var(--cs-border)" }}>
          <span className="text-[9px] font-bold tracking-[1px] uppercase" style={{ color: "var(--cs-accent)" }}>A:</span>
          <input
            type="text"
            placeholder={`${cityCfg.geographyUnit.toUpperCase()} ID (e.g. ${fallbackLeft})...`}
            value={leftId}
            onChange={(e) => setLeftId(e.target.value)}
            className="flex-1 text-[11px] px-2 py-1 outline-none"
            style={{ background: "var(--cs-panel2)", border: "1px solid var(--cs-border)", color: "var(--cs-text)", fontFamily: "var(--cs-mono)" }}
          />
        </div>
        <div className="flex-1 flex items-center gap-2 px-3" style={{ height: 36, background: "var(--cs-panel)" }}>
          <span className="text-[9px] font-bold tracking-[1px] uppercase" style={{ color: "var(--cs-accent)" }}>B:</span>
          <input
            type="text"
            placeholder={`${cityCfg.geographyUnit.toUpperCase()} ID (e.g. ${fallbackRight})...`}
            value={rightId}
            onChange={(e) => setRightId(e.target.value)}
            className="flex-1 text-[11px] px-2 py-1 outline-none"
            style={{ background: "var(--cs-panel2)", border: "1px solid var(--cs-border)", color: "var(--cs-text)", fontFamily: "var(--cs-mono)" }}
          />
        </div>
      </div>

      {/* Comparison Summary KPI */}
      {comparison && (
        <div
          className="flex shrink-0"
          style={{ borderBottom: "1px solid var(--cs-border)", fontFamily: "var(--cs-mono)" }}
        >
          {[
            { label: "SCORE DELTA", value: `${Math.abs(comparison.left.score - comparison.right.score)}`, color: "var(--cs-red)" },
            { label: "TRACT A", value: String(comparison.left.score), color: "var(--cs-amber)" },
            { label: "TRACT B", value: String(comparison.right.score), color: "var(--cs-amber)" },
            { label: "ML DELTA", value: `${Math.abs(comparison.left.mlScore - comparison.right.mlScore)}`, color: "var(--cs-cyan)" },
            { label: "VERDICT", value: Math.abs(comparison.left.score - comparison.right.score) < 10 ? "SIMILAR" : "DIVERGENT", color: Math.abs(comparison.left.score - comparison.right.score) < 10 ? "var(--cs-green)" : "var(--cs-red)" },
          ].map((k) => (
            <div key={k.label} className="flex-1 px-3.5 py-2" style={{ borderRight: "1px solid var(--cs-border)" }}>
              <div className="text-[9px] font-semibold uppercase tracking-[1.2px] mb-1" style={{ color: "var(--cs-gray2)" }}>{k.label}</div>
              <div className="text-lg font-bold tracking-tight leading-none" style={{ color: k.color }}>{k.value}</div>
            </div>
          ))}
        </div>
      )}

      {/* Summary Text */}
      {comparison && (
        <div className="px-3.5 py-2 shrink-0" style={{ background: "var(--cs-panel)", borderBottom: "1px solid var(--cs-border)", fontFamily: "var(--cs-mono)" }}>
          <span className="text-[10px]" style={{ color: "var(--cs-gray1)" }}>
            {comparison.summary}
          </span>
        </div>
      )}

      {/* Persona Conflict Row */}
      {comparison && (
        <div className="flex shrink-0" style={{ borderBottom: "1px solid var(--cs-border)", fontFamily: "var(--cs-mono)" }}>
          <div className="flex-1 px-3.5 py-2" style={{ borderRight: "1px solid var(--cs-border)" }}>
            <div className="text-[8px] font-semibold uppercase tracking-[1.2px] mb-0.5" style={{ color: "var(--cs-gray2)" }}>PERSONA CONFLICT</div>
            <div className="text-[10px]" style={{ color: comparison.left.recommendation.label !== comparison.right.recommendation.label ? "var(--cs-red)" : "var(--cs-green)" }}>
              {comparison.left.recommendation.label !== comparison.right.recommendation.label
                ? `DIVERGENT — A: ${comparison.left.recommendation.label} vs B: ${comparison.right.recommendation.label}`
                : `ALIGNED — Both: ${comparison.left.recommendation.label}`}
            </div>
          </div>
          <div className="flex-1 px-3.5 py-2" style={{ borderRight: "1px solid var(--cs-border)" }}>
            <div className="text-[8px] font-semibold uppercase tracking-[1.2px] mb-0.5" style={{ color: "var(--cs-gray2)" }}>CONFIDENCE DIFF</div>
            <div className="text-[10px] font-bold" style={{ color: "var(--cs-amber)" }}>
              {Math.abs((comparison.left.confidence - comparison.right.confidence) * 100).toFixed(0)}% gap
            </div>
          </div>
          <div className="flex-1 px-3.5 py-2">
            <div className="text-[8px] font-semibold uppercase tracking-[1.2px] mb-0.5" style={{ color: "var(--cs-gray2)" }}>TREND DIFF</div>
            <div className="text-[10px] font-bold" style={{ color: "var(--cs-cyan)" }}>
              {Math.abs(comparison.left.freshnessHours - comparison.right.freshnessHours)}h freshness gap
            </div>
          </div>
        </div>
      )}

      {/* Side-by-Side */}
      {isLoading ? (
        <div className="flex-1 flex items-center justify-center">
          <span className="text-[10px] uppercase tracking-[1px]" style={{ color: "var(--cs-gray2)", fontFamily: "var(--cs-mono)" }}>
            LOADING COMPARISON...
          </span>
        </div>
      ) : comparison ? (
        <div className="flex flex-1 min-h-0 overflow-y-auto">
          <SnapshotColumn snap={comparison.left} label="TRACT A" />
          <SnapshotColumn snap={comparison.right} label="TRACT B" />
        </div>
      ) : (
        <div className="flex-1 flex items-center justify-center">
          <span className="text-[10px] uppercase tracking-[1px]" style={{ color: "var(--cs-gray3)", fontFamily: "var(--cs-mono)" }}>
            ENTER TRACT IDS TO COMPARE
          </span>
        </div>
      )}
    </div>
  );
}
