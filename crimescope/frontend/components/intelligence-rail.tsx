"use client";

import type { TractRiskPackage } from "../lib/contracts";
import { useAppStore } from "../lib/store";
import { usePricingQuote } from "../lib/hooks";
import { getCity } from "../lib/cities";

import type { Persona } from "../lib/store";
import type { PricingPersona } from "../lib/api";

type Props = { riskPkg: TractRiskPackage; persona: Persona };

// What the rail HEADER calls the recommendation block.
const PERSONA_ACTIONS: Record<Persona, string> = {
  insurer: "UNDERWRITING GUIDANCE",
  resident: "HOUSEHOLD SAFETY GUIDANCE",
  buyer: "INVESTMENT GUIDANCE",
  business: "OPERATIONAL GUIDANCE",
  planner: "PLANNING / INTERVENTION GUIDANCE",
};

// One-line framing shown UNDER the action label so persona changes are
// immediately legible even before the data loads.
const PERSONA_FRAMING: Record<Persona, string> = {
  insurer: "Pricing-first view: premium multiplier + decline thresholds.",
  resident: "Household view: contents/home risk and safety actions.",
  buyer: "Buyer view: investment stability and 12-month trend.",
  business: "Operator view: commercial exposure and continuity loading.",
  planner: "Planner view: intervention priority and underreporting risk.",
};

// What the pricing card is labelled per persona — the *number* changes
// meaning between £ premium, contents loading, commercial baseline, or a
// 0–100 prioritisation index.
const PERSONA_PRICING_LABEL: Record<Persona, string> = {
  insurer: "PREMIUM MULTIPLIER",
  resident: "CONTENTS/HOME LOADING",
  buyer: "PROPERTY RISK LOADING",
  business: "COMMERCIAL LOADING",
  planner: "INTERVENTION PRIORITY",
};

// Map the 5 store personas → the 5 backend pricing personas (now 1:1).
// Kept as a separate map so future renames don't break the API call.
const PERSONA_TO_PRICING: Record<Persona, PricingPersona> = {
  insurer: "insurer",
  resident: "resident",
  buyer: "real_estate",
  business: "business",
  planner: "planner",
};

// Persona-specific base premium defaults so the displayed £ is sensible.
const PERSONA_BASE_PREMIUM_UK: Record<Persona, number> = {
  insurer: 1000,
  resident: 600,
  buyer: 100,
  business: 2400,
  planner: 100,
};
const PERSONA_BASE_PREMIUM_US: Record<Persona, number> = {
  insurer: 1200,
  resident: 700,
  buyer: 100,
  business: 2800,
  planner: 100,
};

const BAND_COLOR: Record<string, string> = {
  preferred: "var(--cs-green)",
  standard: "var(--cs-cyan)",
  surcharge: "var(--cs-amber)",
  high_risk: "var(--cs-orange)",
  decline_recommended: "var(--cs-red)",
};

export default function IntelligenceRail({ riskPkg, persona }: Props) {
  const setProvenanceOpen = useAppStore((s) => s.setProvenanceOpen);
  const city = useAppStore((s) => s.city);
  const cityCfg = getCity(city);
  const isUK = cityCfg.country === "UK";
  // Planner view is a 0–100 prioritisation index, not a currency.
  const currency = persona === "planner" ? "" : isUK ? "£" : "$";
  const basePremium = (isUK ? PERSONA_BASE_PREMIUM_UK : PERSONA_BASE_PREMIUM_US)[persona];

  const { data: pricing } = usePricingQuote(riskPkg.regionId, {
    persona: PERSONA_TO_PRICING[persona],
    basePremium,
  });

  const tierColor =
    riskPkg.scores.overall >= 75 ? "var(--cs-red)"
    : riskPkg.scores.overall >= 50 ? "var(--cs-orange)"
    : riskPkg.scores.overall >= 30 ? "var(--cs-yellow)"
    : "var(--cs-green)";

  return (
    <div
      className="flex flex-col overflow-y-auto cs-side-panel"
      style={{
        width: 280,
        background: "var(--cs-bg)",
        borderLeft: "1px solid var(--cs-border)",
        fontFamily: "var(--cs-mono)",
      }}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-2.5 shrink-0"
        style={{
          height: 26,
          background: "var(--cs-panel)",
          borderBottom: "1px solid var(--cs-border)",
        }}
      >
        <span className="text-[9px] font-bold tracking-[1px]" style={{ color: "var(--cs-accent)" }}>
          {riskPkg.regionName}
        </span>
        <span className="text-[8px]" style={{ color: "var(--cs-gray2)" }}>{riskPkg.regionId}</span>
      </div>

      {/* Scores */}
      <div className="flex gap-1.5 px-2.5 py-2" style={{ borderBottom: "1px solid var(--cs-border)" }}>
        <div className="flex-1 text-center py-1" style={{ border: "1px solid var(--cs-border)", background: "var(--cs-panel2)" }}>
          <div className="text-[7px] font-semibold tracking-[0.8px]" style={{ color: "var(--cs-gray2)" }}>OVERALL</div>
          <div className="text-lg font-bold" style={{ color: tierColor }}>{riskPkg.scores.overall}</div>
        </div>
        <div className="flex-1 text-center py-1" style={{ border: "1px solid var(--cs-border)", background: "var(--cs-panel2)" }}>
          <div className="text-[7px] font-semibold tracking-[0.8px]" style={{ color: "var(--cs-gray2)" }}>VIOLENT</div>
          <div className="text-lg font-bold" style={{ color: "var(--cs-red)" }}>{riskPkg.scores.violent}</div>
        </div>
        <div className="flex-1 text-center py-1" style={{ border: "1px solid var(--cs-border)", background: "var(--cs-panel2)" }}>
          <div className="text-[7px] font-semibold tracking-[0.8px]" style={{ color: "var(--cs-gray2)" }}>PROPERTY</div>
          <div className="text-lg font-bold" style={{ color: "var(--cs-orange)" }}>{riskPkg.scores.property}</div>
        </div>
      </div>

      {/* Baseline vs ML */}
      <div className="flex items-center gap-3 px-2.5 py-1.5" style={{ borderBottom: "1px solid var(--cs-border)" }}>
        <div>
          <span className="text-[7px] font-semibold tracking-[0.8px]" style={{ color: "var(--cs-gray2)" }}>BASELINE </span>
          <span className="text-[11px] font-bold" style={{ color: "var(--cs-cyan)" }}>{riskPkg.baselineScore}</span>
        </div>
        <div>
          <span className="text-[7px] font-semibold tracking-[0.8px]" style={{ color: "var(--cs-gray2)" }}>ML </span>
          <span className="text-[11px] font-bold" style={{ color: "var(--cs-green)" }}>{riskPkg.mlScore}</span>
        </div>
        <div>
          <span className="text-[7px] font-semibold tracking-[0.8px]" style={{ color: "var(--cs-gray2)" }}>DELTA </span>
          <span className="text-[11px] font-bold" style={{ color: riskPkg.mlScore > riskPkg.baselineScore ? "var(--cs-red)" : "var(--cs-green)" }}>
            {riskPkg.mlScore > riskPkg.baselineScore ? "+" : ""}{riskPkg.mlScore - riskPkg.baselineScore}
          </span>
        </div>
      </div>

      {/* Premium Multiplier — the underwriter's number */}
      {pricing && (
        <div
          className="px-2.5 py-2"
          style={{
            borderBottom: "1px solid var(--cs-border)",
            background: "var(--cs-panel2)",
          }}
        >
          <div className="flex items-center justify-between mb-1">
            <span className="text-[8px] font-bold tracking-[1px]" style={{ color: "var(--cs-gray2)" }}>
              {PERSONA_PRICING_LABEL[persona]}
            </span>
            <span
              className="text-[8px] font-bold px-1.5 py-0.5 uppercase tracking-wide"
              style={{
                background: BAND_COLOR[pricing.band] || "var(--cs-gray3)",
                color: "#000",
              }}
            >
              {pricing.band.replace(/_/g, " ")}
            </span>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-[10px]" style={{ color: "var(--cs-gray2)" }}>
              {currency}{pricing.basePremium.toLocaleString()}
            </span>
            <span className="text-[10px]" style={{ color: "var(--cs-gray3)" }}>→</span>
            <span
              className="text-base font-bold tabular-nums"
              style={{ color: pricing.riskMultiplier >= 1 ? "var(--cs-amber)" : "var(--cs-green)" }}
            >
              {currency}{pricing.suggestedPremium.toLocaleString(undefined, { maximumFractionDigits: 0 })}
            </span>
            <span className="text-[10px] font-bold" style={{ color: "var(--cs-cyan)" }}>
              ×{pricing.riskMultiplier.toFixed(3)}
            </span>
          </div>
          <div className="mt-1 text-[8px]" style={{ color: "var(--cs-gray2)" }}>
            confidence {Math.round(pricing.confidence * 100)}% · α={pricing.alpha} · β={pricing.beta}
          </div>
          {pricing.drivers.length > 0 && (
            <div
              className="text-[8px] mt-1 truncate"
              title={pricing.drivers[0].evidence}
              style={{ color: "var(--cs-gray1)" }}
            >
              ▸ {pricing.drivers[0].name}
              {pricing.drivers[0].contributionPct !== 0 && (
                <span style={{ color: pricing.drivers[0].contributionPct > 0 ? "var(--cs-red)" : "var(--cs-green)" }}>
                  {` ${pricing.drivers[0].contributionPct > 0 ? "+" : ""}${pricing.drivers[0].contributionPct}%`}
                </span>
              )}
            </div>
          )}
        </div>
      )}

      {/* Persona Action — heading + framing line + recommended action chip */}
      <div className="px-2.5 py-2" style={{ borderBottom: "1px solid var(--cs-border)" }}>
        <div className="text-[8px] font-bold tracking-[1px] mb-0.5" style={{ color: "var(--cs-accent)" }}>
          {PERSONA_ACTIONS[persona]}
        </div>
        <div className="text-[9px] mb-1.5 leading-snug" style={{ color: "var(--cs-gray1)" }}>
          {PERSONA_FRAMING[persona]}
        </div>
        <span
          className="inline-block text-[9px] font-bold px-2 py-0.5 uppercase tracking-wide"
          style={{ background: "var(--cs-amber)", color: "#000" }}
        >
          {riskPkg.trustPassport.action}
        </span>
      </div>

      {/* Top Drivers */}
      <div
        className="px-2.5 shrink-0"
        style={{
          height: 22,
          display: "flex",
          alignItems: "center",
          background: "var(--cs-panel)",
          borderBottom: "1px solid var(--cs-border)",
        }}
      >
        <span className="text-[9px] font-bold tracking-[1px]" style={{ color: "var(--cs-accent)" }}>
          TOP DRIVERS
        </span>
      </div>
      <div style={{ borderBottom: "1px solid var(--cs-border)" }}>
        {riskPkg.drivers.slice(0, 4).map((d, i) => (
          <div
            key={i}
            className="flex items-center gap-1.5 px-2.5 py-1"
            style={{ borderBottom: i < Math.min(riskPkg.drivers.length, 4) - 1 ? "1px solid rgba(30,30,30,0.5)" : "none" }}
          >
            <span
              className="text-[9px]"
              style={{
                color: d.direction === "up" ? "var(--cs-red)" : d.direction === "down" ? "var(--cs-green)" : "var(--cs-gray2)",
              }}
            >
              {d.direction === "up" ? "▲" : d.direction === "down" ? "▼" : "→"}
            </span>
            <span className="text-[9px] flex-1 truncate" style={{ color: "var(--cs-text)" }}>{d.name}</span>
            <span
              className="text-[7px] font-bold px-1 uppercase shrink-0"
              style={{
                color: d.impact === "high" ? "var(--cs-red)" : d.impact === "medium" ? "var(--cs-amber)" : "var(--cs-green)",
              }}
            >
              {d.impact}
            </span>
          </div>
        ))}
      </div>

      {/* Provenance link */}
      <div className="px-2.5 py-2">
        <button
          onClick={() => setProvenanceOpen(true)}
          className="w-full text-[8px] font-bold py-1 uppercase tracking-wide text-center"
          style={{
            background: "var(--cs-panel2)",
            color: "var(--cs-gray1)",
            border: "1px solid var(--cs-border)",
          }}
        >
          VIEW EVIDENCE
        </button>
      </div>
    </div>
  );
}
