"use client";

import { useMemo, useState } from "react";
import { usePricingQuote } from "../lib/hooks";
import type { PricingBand, PricingPersona } from "../lib/api";

type Props = {
  regionId: string;
  /** Which persona to default to. Falls back to "insurer". */
  defaultPersona?: PricingPersona;
  /** Initial base premium (currency-agnostic). */
  defaultBasePremium?: number;
};

const BAND_META: Record<PricingBand, { label: string; bg: string; fg: string }> = {
  preferred: { label: "PREFERRED", bg: "var(--cs-green-lo)", fg: "var(--cs-green)" },
  standard: { label: "STANDARD", bg: "var(--cs-panel2)", fg: "var(--cs-text)" },
  surcharge: { label: "SURCHARGE", bg: "rgba(245,158,11,0.15)", fg: "var(--cs-amber)" },
  high_risk: { label: "HIGH RISK", bg: "var(--cs-red-lo)", fg: "var(--cs-red)" },
  decline_recommended: { label: "DECLINE / REVIEW", bg: "var(--cs-red-lo)", fg: "var(--cs-red)" },
};

const PERSONAS: { id: PricingPersona; label: string; defaultBase: number; baseLabel: string }[] = [
  { id: "insurer", label: "INSURER", defaultBase: 1200, baseLabel: "Base premium" },
  { id: "real_estate", label: "REAL ESTATE", defaultBase: 100, baseLabel: "Risk loading on $100" },
  { id: "resident", label: "RESIDENT", defaultBase: 600, baseLabel: "Contents/home baseline" },
  { id: "business", label: "BUSINESS", defaultBase: 2400, baseLabel: "Commercial baseline" },
  { id: "planner", label: "PLANNER", defaultBase: 100, baseLabel: "Prioritisation index (0–100)" },
];

/**
 * Pricing guidance card driven by `/api/pricing/quote`.
 *
 * Surfaces the suggested premium, the band, the multiplier, the top
 * contributing drivers, and the explicit methodology + α/β so the user
 * understands exactly how the suggestion is derived.
 */
export default function PricingCard({
  regionId,
  defaultPersona = "insurer",
  defaultBasePremium,
}: Props) {
  const [persona, setPersona] = useState<PricingPersona>(defaultPersona);
  const [basePremium, setBasePremium] = useState<number>(
    defaultBasePremium ?? PERSONAS.find((p) => p.id === defaultPersona)?.defaultBase ?? 1200,
  );
  const cfg = useMemo(() => PERSONAS.find((p) => p.id === persona) ?? PERSONAS[0], [persona]);

  const { data, isLoading, isError } = usePricingQuote(regionId, { persona, basePremium });

  const switchPersona = (id: PricingPersona) => {
    setPersona(id);
    const next = PERSONAS.find((p) => p.id === id);
    if (next) setBasePremium(next.defaultBase);
  };

  const band = data ? BAND_META[data.band] : BAND_META.standard;
  const deltaPct = data ? (data.riskMultiplier - 1) * 100 : 0;

  return (
    <div className="px-3 py-2" style={{ fontFamily: "var(--cs-mono)" }}>
      {/* Persona toggle */}
      <div className="flex items-center gap-1 mb-2">
        {PERSONAS.map((p) => (
          <button
            key={p.id}
            onClick={() => switchPersona(p.id)}
            className="text-[8px] font-bold px-1.5 py-0.5 tracking-[1px]"
            style={{
              background: persona === p.id ? "var(--cs-accent)" : "transparent",
              color: persona === p.id ? "#000" : "var(--cs-gray2)",
              border: `1px solid ${persona === p.id ? "var(--cs-accent)" : "var(--cs-border)"}`,
            }}
          >
            {p.label}
          </button>
        ))}
      </div>

      {/* Base premium input */}
      <label className="block text-[8px] font-bold tracking-[1px] uppercase mb-1" style={{ color: "var(--cs-gray2)" }}>
        {cfg.baseLabel}
      </label>
      <input
        type="number"
        value={basePremium}
        min={0}
        step={persona === "insurer" ? 50 : 5}
        onChange={(e) => {
          const v = parseFloat(e.target.value);
          if (!Number.isNaN(v)) setBasePremium(v);
        }}
        className="w-full text-[11px] px-2 py-1 outline-none mb-2"
        style={{
          background: "var(--cs-panel2)",
          border: "1px solid var(--cs-border)",
          color: "var(--cs-text)",
          fontFamily: "var(--cs-mono)",
        }}
      />

      {isLoading || !data ? (
        <div className="text-[9px] uppercase tracking-[1px] py-3 text-center" style={{ color: "var(--cs-gray3)" }}>
          {isError ? "PRICING UNAVAILABLE" : "CALCULATING…"}
        </div>
      ) : (
        <>
          {/* Suggested premium */}
          <div className="flex items-end gap-2 mb-1.5">
            <div className="flex-1">
              <div className="text-[8px] font-bold tracking-[1px] uppercase" style={{ color: "var(--cs-gray2)" }}>
                Suggested
              </div>
              <div className="text-2xl font-bold tabular-nums" style={{ color: band.fg }}>
                ${data.suggestedPremium.toFixed(2)}
              </div>
              <div className="text-[9px]" style={{ color: "var(--cs-gray2)" }}>
                {data.riskMultiplier.toFixed(2)}× base
                <span className="ml-1" style={{ color: deltaPct > 0 ? "var(--cs-red)" : deltaPct < 0 ? "var(--cs-green)" : "var(--cs-gray2)" }}>
                  ({deltaPct > 0 ? "+" : ""}{deltaPct.toFixed(1)}%)
                </span>
              </div>
            </div>
            <span
              className="text-[9px] font-bold px-2 py-0.5 tracking-[1px] uppercase"
              style={{ background: band.bg, color: band.fg, border: `1px solid ${band.fg}33` }}
            >
              {band.label}
            </span>
          </div>

          {/* Confidence + risk factor breakdown */}
          <div className="flex gap-2 mb-2 text-[9px]" style={{ color: "var(--cs-gray2)" }}>
            <span>
              CONF <span className="tabular-nums" style={{ color: "var(--cs-text)" }}>{Math.round(data.confidence * 100)}%</span>
            </span>
            <span>·</span>
            <span>
              α <span className="tabular-nums" style={{ color: "var(--cs-text)" }}>{data.alpha}</span> · β <span className="tabular-nums" style={{ color: "var(--cs-text)" }}>{data.beta}</span>
            </span>
            <span>·</span>
            <span>
              RISK FACTOR <span className="tabular-nums" style={{ color: "var(--cs-text)" }}>{(data.riskFactor * 100).toFixed(0)}%</span>
            </span>
          </div>

          {/* Drivers */}
          <div className="text-[8px] font-bold tracking-[1px] uppercase mb-1" style={{ color: "var(--cs-gray2)" }}>
            Why this price
          </div>
          <ul className="space-y-1 mb-2">
            {data.drivers.map((d, i) => (
              <li key={i} className="flex items-start justify-between gap-2 text-[10px]">
                <div className="flex-1">
                  <div style={{ color: "var(--cs-text)" }}>{d.name}</div>
                  <div className="text-[9px]" style={{ color: "var(--cs-gray2)" }}>{d.evidence}</div>
                </div>
                <span
                  className="text-[10px] font-bold tabular-nums shrink-0"
                  style={{ color: d.contributionPct > 0 ? "var(--cs-red)" : d.contributionPct < 0 ? "var(--cs-green)" : "var(--cs-gray2)" }}
                >
                  {d.contributionPct > 0 ? "+" : ""}{d.contributionPct.toFixed(1)}%
                </span>
              </li>
            ))}
          </ul>

          {/* Caveats */}
          {data.caveats.length > 0 && (
            <ul className="space-y-0.5 mb-2">
              {data.caveats.map((c, i) => (
                <li key={i} className="text-[9px] flex gap-1.5" style={{ color: "var(--cs-gray2)" }}>
                  <span style={{ color: "var(--cs-amber)" }}>•</span> {c}
                </li>
              ))}
            </ul>
          )}

          {/* Methodology — explicit so the suggestion is auditable */}
          <p className="text-[8px] leading-snug" style={{ color: "var(--cs-gray3)" }}>
            <span className="font-bold" style={{ color: "var(--cs-gray2)" }}>METHOD: </span>
            {data.methodology}
          </p>
        </>
      )}
    </div>
  );
}
