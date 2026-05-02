"use client";

import { useParams } from "next/navigation";
import { useRiskPackage, useScores, useLiveEvents, usePersonaDecision, useReportSummary } from "../../../../lib/hooks";
import { useAppStore } from "../../../../lib/store";
import TrustPassportCard from "../../../../components/trust-passport";
import WhatChangedCard from "../../../../components/what-changed";
import DisagreementBanner from "../../../../components/disagreement-banner";
import RegionTrendChart from "../../../../components/region-trend-chart";
import BreakdownCard from "../../../../components/breakdown-card";
import PricingCard from "../../../../components/pricing-card";
import Link from "next/link";

function SectionHeader({ title, meta }: { title: string; meta?: string }) {
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
      {meta && <span className="text-[9px] tracking-wide" style={{ color: "var(--cs-gray2)" }}>{meta}</span>}
    </div>
  );
}

export default function RegionDetailPage() {
  const { regionId } = useParams<{ regionId: string }>();
  const { data: riskPkg, isLoading } = useRiskPackage(regionId);
  const { data: scores = [] } = useScores();
  const { data: liveEvents = [] } = useLiveEvents(regionId);
  const { data: personaDecision } = usePersonaDecision(regionId);
  const { data: reportSummary } = useReportSummary(regionId);
  const persona = useAppStore((s) => s.persona);
  const setCompareLeft = useAppStore((s) => s.setCompareLeft);

  if (isLoading || !riskPkg) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <span className="text-[10px] uppercase tracking-[1px]" style={{ color: "var(--cs-gray2)", fontFamily: "var(--cs-mono)" }}>
          LOADING REGION {regionId}...
        </span>
      </div>
    );
  }

  const tierColor =
    riskPkg.scores.overall >= 75 ? "var(--cs-red)"
    : riskPkg.scores.overall >= 50 ? "var(--cs-orange)"
    : riskPkg.scores.overall >= 30 ? "var(--cs-yellow)"
    : "var(--cs-green)";

  const neighbors = scores
    .filter((s) => s.tract_geoid !== regionId)
    .sort((a, b) => Math.abs(a.risk_score - riskPkg.scores.overall) - Math.abs(b.risk_score - riskPkg.scores.overall))
    .slice(0, 5);

  return (
    <div className="flex flex-col flex-1 overflow-y-auto" style={{ background: "var(--cs-bg)" }}>
      {/* Region Header */}
      <div className="flex items-center gap-3 px-4 py-3 shrink-0" style={{ borderBottom: "1px solid var(--cs-border)", fontFamily: "var(--cs-mono)" }}>
        <Link href="/" className="text-[10px] font-bold tracking-wide" style={{ color: "var(--cs-gray2)" }}>← DASHBOARD</Link>
        <div className="w-px h-4" style={{ background: "var(--cs-border)" }} />
        <div>
          <h1 className="text-sm font-bold" style={{ color: "var(--cs-text)" }}>{riskPkg.regionName}</h1>
          <div className="flex items-center gap-2 mt-0.5">
            <span className="text-[9px]" style={{ color: "var(--cs-gray2)" }}>{riskPkg.regionId}</span>
            <span className="text-[9px]" style={{ color: "var(--cs-gray2)" }}>·</span>
            <span className="text-[9px]" style={{ color: "var(--cs-gray2)" }}>{riskPkg.city}</span>
            <span className="text-[9px]" style={{ color: "var(--cs-gray2)" }}>·</span>
            <span className="text-[9px] font-bold uppercase" style={{ color: tierColor }}>{riskPkg.riskLevel}</span>
          </div>
        </div>
        <div className="flex-1" />
        <button
          onClick={() => { setCompareLeft(regionId); }}
          className="text-[9px] font-bold px-2 py-1 uppercase tracking-wide"
          style={{ background: "var(--cs-panel2)", color: "var(--cs-gray1)", border: "1px solid var(--cs-border)" }}
        >
          COMPARE
        </button>
        <Link
          href={`/reports?region=${regionId}`}
          className="text-[9px] font-bold px-2 py-1 uppercase tracking-wide"
          style={{ background: "var(--cs-panel2)", color: "var(--cs-gray1)", border: "1px solid var(--cs-border)" }}
        >
          EXPORT REPORT
        </Link>
      </div>

      <div className="flex flex-1 min-h-0">
        {/* Left: Scores + Drivers + Trend */}
        <div className="flex-1 flex flex-col" style={{ borderRight: "1px solid var(--cs-border)" }}>
          {/* Score cards */}
          <div className="flex px-4 py-3 gap-3" style={{ borderBottom: "1px solid var(--cs-border)", fontFamily: "var(--cs-mono)" }}>
            {[
              { label: "OVERALL", value: riskPkg.scores.overall, color: tierColor },
              { label: "VIOLENT", value: riskPkg.scores.violent, color: "var(--cs-red)" },
              { label: "PROPERTY", value: riskPkg.scores.property, color: "var(--cs-orange)" },
              { label: "BASELINE", value: riskPkg.baselineScore, color: "var(--cs-cyan)" },
              { label: "ML MODEL", value: riskPkg.mlScore, color: "var(--cs-green)" },
            ].map((s) => (
              <div key={s.label} className="flex-1 text-center py-2" style={{ border: "1px solid var(--cs-border)", background: "var(--cs-panel2)" }}>
                <div className="text-[8px] font-semibold tracking-[0.8px] mb-1" style={{ color: "var(--cs-gray2)" }}>{s.label}</div>
                <div className="text-2xl font-bold" style={{ color: s.color }}>{s.value}</div>
              </div>
            ))}
          </div>

          {/* Top Drivers */}
          <SectionHeader title="TOP DRIVERS" meta={`${riskPkg.drivers.length} FACTORS`} />
          <div style={{ borderBottom: "1px solid var(--cs-border)" }}>
            {riskPkg.drivers.map((d, i) => (
              <div
                key={i}
                className="flex items-start gap-3 px-4 py-2"
                style={{ fontFamily: "var(--cs-mono)", borderBottom: i < riskPkg.drivers.length - 1 ? "1px solid rgba(30,30,30,0.5)" : "none" }}
              >
                <span className="text-sm mt-0.5" style={{ color: d.direction === "up" ? "var(--cs-red)" : d.direction === "down" ? "var(--cs-green)" : "var(--cs-gray2)" }}>
                  {d.direction === "up" ? "▲" : d.direction === "down" ? "▼" : "→"}
                </span>
                <div className="flex-1">
                  <div className="text-[11px] font-medium" style={{ color: "var(--cs-text)" }}>{d.name}</div>
                  <div className="text-[10px] mt-0.5" style={{ color: "var(--cs-gray2)" }}>{d.evidence}</div>
                </div>
                <span
                  className="text-[8px] font-bold px-1.5 py-0.5 uppercase shrink-0"
                  style={{
                    background: d.impact === "high" ? "var(--cs-red-lo)" : d.impact === "medium" ? "rgba(245,158,11,0.1)" : "var(--cs-green-lo)",
                    color: d.impact === "high" ? "var(--cs-red)" : d.impact === "medium" ? "var(--cs-amber)" : "var(--cs-green)",
                  }}
                >
                  {d.impact} IMPACT
                </span>
              </div>
            ))}
          </div>

          {/* Trend + 30-day forecast */}
          <SectionHeader title="TREND · 12mo HISTORY → 30d FORECAST" />
          <div className="shrink-0" style={{ height: 220, borderBottom: "1px solid var(--cs-border)" }}>
            <RegionTrendChart regionId={regionId} horizonDays={30} metric="incident_rate" />
          </div>

          {/* Crime pattern breakdown */}
          <SectionHeader title="CRIME PATTERN BREAKDOWN" meta="NEXT 30D" />
          <div className="shrink-0" style={{ borderBottom: "1px solid var(--cs-border)" }}>
            <BreakdownCard regionId={regionId} />
          </div>

          {/* Live Events */}
          <SectionHeader title="LIVE EVENTS" meta={`${liveEvents.length} EVENTS`} />
          <div className="flex-1 overflow-y-auto" style={{ fontFamily: "var(--cs-mono)" }}>
            {liveEvents.length === 0 ? (
              <div className="text-center py-6 text-[10px]" style={{ color: "var(--cs-gray3)" }}>NO LIVE EVENTS FOR THIS REGION</div>
            ) : (
              liveEvents.map((ev) => (
                <div key={ev.id} className="px-4 py-2" style={{ borderBottom: "1px solid var(--cs-border)" }}>
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className="text-[9px] font-bold uppercase px-1 py-0.5" style={{
                      background: ev.status === "verified" ? "var(--cs-green-lo)" : "rgba(245,158,11,0.1)",
                      color: ev.status === "verified" ? "var(--cs-green)" : "var(--cs-amber)",
                    }}>
                      {ev.status}
                    </span>
                    <span className="text-[9px]" style={{ color: "var(--cs-gray2)" }}>
                      {new Date(ev.occurredAt).toLocaleString()}
                    </span>
                  </div>
                  <div className="text-[10px] font-medium" style={{ color: "var(--cs-text)" }}>{ev.title}</div>
                  <div className="text-[9px] mt-0.5" style={{ color: "var(--cs-gray2)" }}>{ev.summary}</div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Right: Trust + Disagreement + Recommendation + Neighbors */}
        <div className="flex flex-col overflow-y-auto" style={{ width: 340 }}>
          <SectionHeader title="TRUST PASSPORT" />
          <TrustPassportCard passport={riskPkg.trustPassport} />

          <SectionHeader title="VERIFIED vs LIVE" />
          <DisagreementBanner disagreement={riskPkg.liveDisagreement} />

          <SectionHeader title="WHAT CHANGED & WHY" />
          <WhatChangedCard whatChanged={riskPkg.whatChanged} />

          {/* Persona Decision */}
          {personaDecision && (
            <>
              <SectionHeader title={`${persona.toUpperCase()} RECOMMENDATION`} />
              <div className="px-3 py-2" style={{ borderBottom: "1px solid var(--cs-border)", fontFamily: "var(--cs-mono)" }}>
                <span className="inline-block text-[9px] font-bold px-2 py-0.5 uppercase tracking-wide mb-1.5" style={{ background: "var(--cs-amber)", color: "#000" }}>
                  {personaDecision.decision}
                </span>
                <p className="text-[10px] font-medium mb-1" style={{ color: "var(--cs-text)" }}>{personaDecision.headline}</p>
                <p className="text-[9px]" style={{ color: "var(--cs-gray1)" }}>{personaDecision.nextStep}</p>
                <p className="text-[9px] mt-1" style={{ color: "var(--cs-gray2)" }}>{personaDecision.caveat}</p>
              </div>
            </>
          )}

          {/* Pricing guidance — insurer + real-estate personas */}
          <SectionHeader title="PRICING GUIDANCE" meta="AUDITABLE" />
          <div style={{ borderBottom: "1px solid var(--cs-border)" }}>
            <PricingCard
              regionId={regionId}
              defaultPersona={persona === "insurer" ? "insurer" : persona === "buyer" ? "real_estate" : "insurer"}
            />
          </div>

          {/* Nearby Regions */}
          <SectionHeader title="NEARBY REGIONS" meta={`${neighbors.length} TRACTS`} />
          <div style={{ fontFamily: "var(--cs-mono)" }}>
            {neighbors.map((n) => (
              <Link
                key={n.tract_geoid}
                href={`/dashboard/region/${n.tract_geoid}`}
                className="flex items-center gap-2 px-3 py-1.5 transition-colors"
                style={{ borderBottom: "1px solid var(--cs-border)" }}
              >
                <span className="text-[10px] font-bold" style={{
                  color: n.risk_score >= 75 ? "var(--cs-red)" : n.risk_score >= 50 ? "var(--cs-orange)" : n.risk_score >= 30 ? "var(--cs-yellow)" : "var(--cs-green)",
                }}>
                  {n.risk_score.toFixed(0)}
                </span>
                <span className="text-[10px] flex-1 truncate" style={{ color: "var(--cs-text)" }}>{n.name || n.tract_geoid}</span>
                <span className="text-[8px] uppercase" style={{ color: "var(--cs-gray2)" }}>{n.risk_tier}</span>
              </Link>
            ))}
          </div>

          {/* Limitations */}
          <SectionHeader title="LIMITATIONS" />
          <div className="px-3 py-2" style={{ fontFamily: "var(--cs-mono)" }}>
            <ul className="space-y-1">
              {[
                "Scores are modeled estimates, not ground truth.",
                "Live signals may have unverified sources.",
                "Underreporting may affect completeness.",
                "Model accuracy varies by tract density.",
              ].map((l, i) => (
                <li key={i} className="text-[9px] flex gap-1.5" style={{ color: "var(--cs-gray2)" }}>
                  <span style={{ color: "var(--cs-amber)" }}>•</span> {l}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
