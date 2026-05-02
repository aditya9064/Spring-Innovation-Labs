"use client";

import { useState, useRef } from "react";
import { useAppStore } from "../../lib/store";
import { useReportSummary, usePersonaDecision, useLiveEvents, useScores, useChallenges } from "../../lib/hooks";
import { createChallenge, createAuditEntry } from "../../lib/api";
import { getCity } from "../../lib/cities";
import { useQueryClient } from "@tanstack/react-query";
import {
  tractRiskPackage as defaultPkg,
  liveEvents as fallbackLiveEvents,
  insurerDecision as fallbackDecision,
} from "../../lib/contracts";

const IMPACT_COLOR: Record<string, string> = {
  high: "var(--cs-red)",
  medium: "var(--cs-amber)",
  low: "var(--cs-gray2)",
};

const DIR_ICON: Record<string, string> = {
  up: "▲",
  down: "▼",
  flat: "→",
};

const STATUS_STYLE: Record<string, { bg: string; fg: string }> = {
  verified: { bg: "var(--cs-green-lo)", fg: "var(--cs-green)" },
  reported: { bg: "var(--cs-accent-lo)", fg: "var(--cs-accent)" },
  unverified: { bg: "var(--cs-red-lo)", fg: "var(--cs-red)" },
};

function PanelHeader({
  title,
  meta,
}: {
  title: string;
  meta?: string;
}) {
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

function PanelBody({
  children,
  pad = true,
}: {
  children: React.ReactNode;
  pad?: boolean;
}) {
  return (
    <div
      style={{ background: "var(--cs-bg)" }}
      className={pad ? "px-3 py-2.5" : ""}
    >
      {children}
    </div>
  );
}

export default function ReportsPage() {
  const [search, setSearch] = useState("");
  const reportTract = useAppStore((s) => s.reportTract);
  const searchResult = useAppStore((s) => s.searchResult);
  const city = useAppStore((s) => s.city);
  const cityCfg = getCity(city);
  const { data: allScores = [] } = useScores();

  const activeRegionId =
    reportTract || search.trim() || allScores[0]?.tract_geoid || cityCfg.defaultRegionId;

  const { data: apiSummary } = useReportSummary(activeRegionId);
  const { data: apiDecision } = usePersonaDecision(activeRegionId);
  const { data: apiLiveEvents = [] } = useLiveEvents(activeRegionId);

  const hasTractFromSearch = !!(reportTract && searchResult);

  const matchedScore = allScores.find((s) => s.tract_geoid === activeRegionId);

  const pkg = hasTractFromSearch
    ? {
        ...defaultPkg,
        regionId: searchResult.geoid,
        regionName: apiSummary?.title?.replace("Risk Report: ", "") || searchResult.name,
        riskLevel: searchResult.tier.toLowerCase(),
        mlScore: searchResult.score,
        baselineScore: matchedScore?.incident_count ?? defaultPkg.baselineScore,
        scores: {
          overall: searchResult.score,
          violent: Math.round(searchResult.score * 0.78),
          property: Math.min(100, Math.round(searchResult.score * 1.08)),
        },
      }
    : defaultPkg;

  const decision = apiDecision || fallbackDecision;
  const liveEvents = apiLiveEvents.length > 0 ? apiLiveEvents : fallbackLiveEvents;

  const scores = [
    { label: "OVERALL", value: pkg.scores.overall, color: "var(--cs-amber)" },
    { label: "VIOLENT", value: pkg.scores.violent, color: "var(--cs-red)" },
    { label: "PROPERTY", value: pkg.scores.property, color: "var(--cs-orange)" },
  ];

  const passportFields = [
    { label: "CONFIDENCE", value: pkg.trustPassport.confidence },
    { label: "COMPLETENESS", value: pkg.trustPassport.completeness },
    { label: "FRESHNESS", value: pkg.trustPassport.freshness },
    { label: "SRC AGREEMENT", value: pkg.trustPassport.sourceAgreement },
    { label: "UNDERREPORT RISK", value: pkg.trustPassport.underreportingRisk },
    { label: "ACTION", value: pkg.trustPassport.action },
  ];

  return (
    <div className="flex flex-col flex-1 overflow-hidden" style={{ background: "var(--cs-bg)" }}>

      {/* Search Bar */}
      <div
        className="flex items-center gap-2 px-3.5 shrink-0"
        style={{
          height: 36,
          background: "var(--cs-panel)",
          borderBottom: "1px solid var(--cs-border)",
          fontFamily: "var(--cs-mono)",
        }}
      >
        <span className="text-[9px] font-bold tracking-[1px] uppercase" style={{ color: "var(--cs-accent)" }}>
          {cityCfg.geographyUnit.toUpperCase()}:
        </span>
        <input
          type="text"
          placeholder={`ENTER ${cityCfg.geographyUnit.toUpperCase()} ID (e.g. ${cityCfg.defaultRegionId})...`}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="flex-1 text-[11px] px-2 py-1 outline-none"
          style={{
            background: "var(--cs-panel2)",
            border: "1px solid var(--cs-border)",
            color: "var(--cs-text)",
            fontFamily: "var(--cs-mono)",
          }}
        />
      </div>

      {/* Scrollable Report Content */}
      <div className="flex-1 overflow-y-auto">
        {/* Location Banner */}
        {hasTractFromSearch && (
          <div
            className="flex items-center gap-3 px-3.5 py-2"
            style={{
              background: "var(--cs-accent-lo)",
              borderBottom: "1px solid var(--cs-accent-md)",
              fontFamily: "var(--cs-mono)",
            }}
          >
            <span className="text-[9px] font-bold tracking-[1px] uppercase" style={{ color: "var(--cs-accent)" }}>
              REPORT FOR
            </span>
            <span className="text-[11px] font-semibold" style={{ color: "var(--cs-text)" }}>
              {searchResult.address}
            </span>
            <span className="text-[10px]" style={{ color: "var(--cs-gray2)" }}>
              · {cityCfg.geographyUnit.toUpperCase()} {searchResult.geoid}
            </span>
          </div>
        )}

        {/* API Summary Banner */}
        {apiSummary && (
          <>
            <PanelHeader title="EXECUTIVE SUMMARY" meta={cityCfg.shortLabel} />
            <PanelBody>
              <div className="flex items-baseline gap-3 mb-2">
                <span className="text-base font-bold" style={{ color: "var(--cs-text)" }}>
                  {apiSummary.title}
                </span>
              </div>
              <p className="text-[11px] mb-2" style={{ color: "var(--cs-gray1)", fontFamily: "var(--cs-mono)" }}>
                {apiSummary.executiveSummary}
              </p>
              {apiSummary.riskDrivers.length > 0 && (
                <div className="mt-2">
                  <span className="text-[9px] font-bold uppercase tracking-[1px]" style={{ color: "var(--cs-accent)", fontFamily: "var(--cs-mono)" }}>
                    TOP DRIVERS:
                  </span>
                  {apiSummary.riskDrivers.map((d, i) => (
                    <span key={i} className="text-[10px] ml-2" style={{ color: "var(--cs-gray1)", fontFamily: "var(--cs-mono)" }}>
                      {d}{i < apiSummary.riskDrivers.length - 1 ? " ·" : ""}
                    </span>
                  ))}
                </div>
              )}
            </PanelBody>
          </>
        )}

        {!apiSummary && (
          <>
            <PanelHeader title="EXECUTIVE SUMMARY" meta={pkg.city.toUpperCase()} />
            <PanelBody>
              <div className="flex items-baseline gap-3 mb-2">
                <span className="text-base font-bold" style={{ color: "var(--cs-text)" }}>
                  {pkg.regionName}
                </span>
                <span className="text-[10px] tracking-wide" style={{ color: "var(--cs-gray2)", fontFamily: "var(--cs-mono)" }}>
                  {pkg.regionId}
                </span>
              </div>
              <div className="flex items-center gap-3">
                <span
                  className="text-[10px] font-bold px-2 py-0.5 uppercase tracking-wide"
                  style={{
                    fontFamily: "var(--cs-mono)",
                    background: "var(--cs-accent-lo)",
                    color: "var(--cs-accent)",
                    border: "1px solid var(--cs-accent-md)",
                  }}
                >
                  {pkg.riskLevel}
                </span>
                <span className="text-[11px]" style={{ color: "var(--cs-gray1)", fontFamily: "var(--cs-mono)" }}>
                  ML Score: <span className="font-bold" style={{ color: "var(--cs-text)" }}>{pkg.mlScore}</span> / 100
                </span>
              </div>
            </PanelBody>
          </>
        )}

        {/* Scores + Drivers Row */}
        <div className="flex" style={{ borderBottom: "1px solid var(--cs-border)" }}>
          <div style={{ width: "40%", borderRight: "1px solid var(--cs-border)" }}>
            <PanelHeader title="RISK SCORES" />
            <PanelBody>
              <div className="flex gap-3">
                {scores.map((s) => (
                  <div key={s.label} className="flex-1 text-center py-1.5" style={{ border: "1px solid var(--cs-border)", background: "var(--cs-panel2)" }}>
                    <div className="text-[8px] font-semibold uppercase tracking-[0.8px] mb-1" style={{ color: "var(--cs-gray2)", fontFamily: "var(--cs-mono)" }}>
                      {s.label}
                    </div>
                    <div className="text-2xl font-bold tracking-tight" style={{ color: s.color, fontFamily: "var(--cs-mono)" }}>
                      {s.value}
                    </div>
                  </div>
                ))}
              </div>
            </PanelBody>
          </div>
          <div className="flex-1">
            <PanelHeader title="KEY RISK DRIVERS" meta={`${pkg.drivers.length} FACTORS`} />
            <PanelBody pad={false}>
              <table className="w-full" style={{ fontFamily: "var(--cs-mono)", borderCollapse: "collapse" }}>
                <thead>
                  <tr>
                    {["DRIVER", "DIR", "IMPACT"].map((h) => (
                      <th key={h} className="text-left text-[9px] font-bold uppercase tracking-[1.2px] px-3 py-1.5 whitespace-nowrap" style={{ color: "var(--cs-accent)", background: "var(--cs-panel)", borderBottom: "1px solid var(--cs-border)" }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {pkg.drivers.map((d, i) => (
                    <tr key={i}>
                      <td className="text-[11px] px-3 py-1.5" style={{ color: "var(--cs-text)", borderBottom: "1px solid rgba(30,30,30,0.5)" }}>{d.name}</td>
                      <td className="text-[11px] px-3 py-1.5" style={{ color: d.direction === "up" ? "var(--cs-red)" : d.direction === "down" ? "var(--cs-green)" : "var(--cs-gray2)", borderBottom: "1px solid rgba(30,30,30,0.5)" }}>{DIR_ICON[d.direction]}</td>
                      <td className="px-3 py-1.5" style={{ borderBottom: "1px solid rgba(30,30,30,0.5)" }}>
                        <span className="text-[9px] font-bold px-1.5 py-0.5 uppercase tracking-wide" style={{ color: IMPACT_COLOR[d.impact], background: d.impact === "high" ? "var(--cs-red-lo)" : d.impact === "medium" ? "rgba(245,158,11,0.08)" : "transparent", border: `1px solid ${d.impact === "high" ? "rgba(239,68,68,0.2)" : d.impact === "medium" ? "rgba(245,158,11,0.2)" : "var(--cs-border)"}` }}>{d.impact}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </PanelBody>
          </div>
        </div>

        {/* Trust Passport */}
        <PanelHeader title="DATA TRUST PASSPORT" meta="QUALITY METRICS" />
        <PanelBody>
          <div className="grid grid-cols-3 gap-2" style={{ fontFamily: "var(--cs-mono)" }}>
            {passportFields.map((f) => (
              <div key={f.label} className="px-2.5 py-2 text-center" style={{ background: "var(--cs-panel2)", border: "1px solid var(--cs-border)" }}>
                <div className="text-[8px] font-semibold uppercase tracking-[0.8px] mb-1.5" style={{ color: "var(--cs-gray2)" }}>{f.label}</div>
                <div className="text-[11px] font-bold uppercase" style={{ color: "var(--cs-amber)" }}>{f.value}</div>
              </div>
            ))}
          </div>
        </PanelBody>

        {/* Trust Notes from API */}
        {apiSummary?.trustNotes && apiSummary.trustNotes.length > 0 && (
          <>
            <PanelHeader title="DATA PROVENANCE" meta="TRUST NOTES" />
            <PanelBody>
              {apiSummary.trustNotes.map((note, i) => (
                <div key={i} className="text-[10px] py-0.5" style={{ color: "var(--cs-gray1)", fontFamily: "var(--cs-mono)" }}>
                  <span style={{ color: "var(--cs-gray3)" }}>{">"} </span>{note}
                </div>
              ))}
            </PanelBody>
          </>
        )}

        {/* What Changed */}
        <PanelHeader title="WHAT CHANGED" />
        <PanelBody>
          <p className="text-[11px] mb-2" style={{ color: "var(--cs-gray1)", fontFamily: "var(--cs-mono)" }}>
            {pkg.whatChanged.summary}
          </p>
          {pkg.whatChanged.topChanges.map((c, i) => (
            <div key={i} className="text-[10px] py-0.5" style={{ color: "var(--cs-gray1)", fontFamily: "var(--cs-mono)" }}>
              <span style={{ color: "var(--cs-gray3)" }}>{">"} </span>{c}
            </div>
          ))}
        </PanelBody>

        {/* Model vs Baseline + Live Intelligence */}
        <div className="flex" style={{ borderBottom: "1px solid var(--cs-border)" }}>
          <div style={{ width: "35%", borderRight: "1px solid var(--cs-border)" }}>
            <PanelHeader title="MODEL VS BASELINE" />
            <PanelBody>
              <div className="flex gap-3" style={{ fontFamily: "var(--cs-mono)" }}>
                <div className="flex-1 text-center py-2" style={{ border: "1px solid var(--cs-border)", background: "var(--cs-panel2)" }}>
                  <div className="text-[8px] font-semibold tracking-[0.8px] mb-1" style={{ color: "var(--cs-gray2)" }}>ML SCORE</div>
                  <div className="text-xl font-bold" style={{ color: "var(--cs-green)" }}>{pkg.mlScore}</div>
                </div>
                <div className="flex-1 text-center py-2" style={{ border: "1px solid var(--cs-border)", background: "var(--cs-panel2)" }}>
                  <div className="text-[8px] font-semibold tracking-[0.8px] mb-1" style={{ color: "var(--cs-gray2)" }}>BASELINE</div>
                  <div className="text-xl font-bold" style={{ color: "var(--cs-cyan)" }}>{pkg.baselineScore}</div>
                </div>
              </div>
              <div className="mt-2 text-center" style={{ fontFamily: "var(--cs-mono)" }}>
                <span className="text-[9px] tracking-wide" style={{ color: "var(--cs-gray2)" }}>DELTA </span>
                <span className="text-[12px] font-bold" style={{ color: pkg.liveDisagreement.delta > 0 ? "var(--cs-red)" : "var(--cs-green)" }}>
                  {pkg.liveDisagreement.delta > 0 ? "+" : ""}{pkg.liveDisagreement.delta}
                </span>
              </div>
            </PanelBody>
          </div>

          <div className="flex-1">
            <PanelHeader title="LIVE INTELLIGENCE" meta={`${liveEvents.length} EVENTS`} />
            <PanelBody pad={false}>
              <table className="w-full" style={{ fontFamily: "var(--cs-mono)", borderCollapse: "collapse" }}>
                <thead>
                  <tr>
                    {["EVENT", "STATUS", "CONF", "TIME"].map((h) => (
                      <th key={h} className="text-left text-[9px] font-bold uppercase tracking-[1.2px] px-3 py-1.5 whitespace-nowrap" style={{ color: "var(--cs-accent)", background: "var(--cs-panel)", borderBottom: "1px solid var(--cs-border)" }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {liveEvents.map((evt) => {
                    const st = STATUS_STYLE[evt.status] || STATUS_STYLE.unverified;
                    return (
                      <tr key={evt.id}>
                        <td className="text-[11px] px-3 py-1.5 max-w-[300px] truncate" style={{ color: "var(--cs-text)", borderBottom: "1px solid rgba(30,30,30,0.5)" }}>{evt.title}</td>
                        <td className="px-3 py-1.5" style={{ borderBottom: "1px solid rgba(30,30,30,0.5)" }}>
                          <span className="text-[9px] font-bold px-1.5 py-0.5 uppercase tracking-wide" style={{ background: st.bg, color: st.fg, border: `1px solid ${st.fg}33` }}>{evt.status}</span>
                        </td>
                        <td className="text-[10px] px-3 py-1.5 uppercase" style={{ color: "var(--cs-gray1)", borderBottom: "1px solid rgba(30,30,30,0.5)" }}>{evt.confidence}</td>
                        <td className="text-[10px] px-3 py-1.5 whitespace-nowrap" style={{ color: "var(--cs-gray2)", borderBottom: "1px solid rgba(30,30,30,0.5)" }}>
                          {new Date(evt.occurredAt).toLocaleString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </PanelBody>
          </div>
        </div>

        {/* Insurer Recommendation */}
        <PanelHeader title="INSURER RECOMMENDATION" meta={decision.persona.toUpperCase()} />
        <PanelBody>
          <div className="flex items-center gap-3 mb-2">
            <span
              className="text-[10px] font-bold px-2 py-0.5 uppercase tracking-wide"
              style={{ fontFamily: "var(--cs-mono)", background: "var(--cs-amber)", color: "#000" }}
            >
              {decision.decision}
            </span>
            <span className="text-[12px] font-semibold" style={{ color: "var(--cs-text)" }}>
              {decision.headline}
            </span>
          </div>
          <div className="space-y-1.5" style={{ fontFamily: "var(--cs-mono)" }}>
            <div className="text-[10px]" style={{ color: "var(--cs-gray1)" }}>
              <span style={{ color: "var(--cs-accent)" }}>NEXT STEP: </span>
              {decision.nextStep}
            </div>
            <div className="text-[10px]" style={{ color: "var(--cs-gray1)" }}>
              <span style={{ color: "var(--cs-amber)" }}>CAVEAT: </span>
              {decision.caveat}
            </div>
          </div>
        </PanelBody>

        {/* Human Challenge Mode */}
        <ChallengeSection regionId={activeRegionId} riskScore={pkg.mlScore} riskTier={pkg.riskLevel} />

        {/* Export Actions */}
        <PanelHeader title="EXPORT" meta="PERSONA-SPECIFIC REPORTS" />
        <PanelBody>
          <div className="text-[9px] mb-2" style={{ color: "var(--cs-gray2)", fontFamily: "var(--cs-mono)" }}>
            Generate a downloadable brief tailored to a specific persona.
          </div>
          <div className="grid grid-cols-2 gap-2 mb-3" style={{ fontFamily: "var(--cs-mono)" }}>
            {[
              { persona: "INSURER", desc: "Tract review, pricing guidance, underwriting notes" },
              { persona: "BUYER", desc: "Neighborhood summary, stability assessment" },
              { persona: "BUSINESS", desc: "Site risk summary, operating exposure" },
              { persona: "PLANNER", desc: "Hotspot movement brief, intervention priority" },
            ].map((p) => (
              <button
                key={p.persona}
                onClick={() => exportCSV(activeRegionId, pkg, decision)}
                className="text-left px-2.5 py-2 transition-colors"
                style={{ background: "var(--cs-panel2)", border: "1px solid var(--cs-border)" }}
              >
                <div className="text-[9px] font-bold tracking-wide mb-0.5" style={{ color: "var(--cs-accent)" }}>{p.persona} BRIEF</div>
                <div className="text-[8px]" style={{ color: "var(--cs-gray2)" }}>{p.desc}</div>
              </button>
            ))}
          </div>
          <div className="flex gap-2" style={{ fontFamily: "var(--cs-mono)" }}>
            <button
              onClick={() => exportCSV(activeRegionId, pkg, decision)}
              className="text-[10px] font-bold px-3 py-1.5 uppercase tracking-wide"
              style={{ background: "var(--cs-panel2)", color: "var(--cs-gray1)", border: "1px solid var(--cs-border)" }}
            >
              EXPORT CSV
            </button>
            <button
              onClick={() => window.print()}
              className="text-[10px] font-bold px-3 py-1.5 uppercase tracking-wide"
              style={{ background: "var(--cs-panel2)", color: "var(--cs-gray1)", border: "1px solid var(--cs-border)" }}
            >
              PRINT / PDF
            </button>
          </div>
        </PanelBody>

        <div style={{ height: 20 }} />
      </div>
    </div>
  );
}

function ChallengeSection({ regionId, riskScore, riskTier }: { regionId: string; riskScore: number; riskTier: string }) {
  const { data: challenges = [] } = useChallenges(regionId);
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    challenger_name: "",
    challenge_type: "score_too_high",
    evidence: "",
    proposed_adjustment: "",
  });

  const handleSubmit = async () => {
    if (!form.challenger_name || !form.evidence) return;
    await createChallenge({
      region_id: regionId,
      challenger_name: form.challenger_name,
      challenge_type: form.challenge_type,
      evidence: form.evidence,
      proposed_adjustment: form.proposed_adjustment ? parseFloat(form.proposed_adjustment) : undefined,
    });
    qc.invalidateQueries({ queryKey: ["challenges"] });
    setShowForm(false);
    setForm({ challenger_name: "", challenge_type: "score_too_high", evidence: "", proposed_adjustment: "" });
  };

  const STATUS_COLOR: Record<string, string> = {
    pending: "var(--cs-amber)",
    accepted: "var(--cs-green)",
    rejected: "var(--cs-red)",
    under_review: "var(--cs-cyan)",
  };

  return (
    <>
      <div className="flex items-center justify-between px-3 shrink-0" style={{ height: 28, background: "var(--cs-panel)", borderBottom: "1px solid var(--cs-border)", fontFamily: "var(--cs-mono)" }}>
        <span className="text-[10px] font-bold tracking-[1.5px] uppercase" style={{ color: "var(--cs-accent)" }}>HUMAN CHALLENGE MODE</span>
        <button onClick={() => setShowForm(!showForm)} className="text-[9px] font-bold px-2 py-0.5 uppercase tracking-wide" style={{ background: showForm ? "var(--cs-red)" : "var(--cs-amber)", color: "#000" }}>
          {showForm ? "CANCEL" : "CHALLENGE SCORE"}
        </button>
      </div>

      {showForm && (
        <div className="px-3 py-3" style={{ background: "var(--cs-panel2)", borderBottom: "1px solid var(--cs-border)", fontFamily: "var(--cs-mono)" }}>
          <div className="grid grid-cols-2 gap-2 mb-2">
            <div>
              <label className="text-[9px] font-bold uppercase tracking-[1px] block mb-1" style={{ color: "var(--cs-gray2)" }}>YOUR NAME</label>
              <input type="text" value={form.challenger_name} onChange={(e) => setForm({ ...form, challenger_name: e.target.value })} placeholder="Full name..." className="w-full text-[11px] px-2 py-1 outline-none" style={{ background: "var(--cs-bg)", border: "1px solid var(--cs-border)", color: "var(--cs-text)" }} />
            </div>
            <div>
              <label className="text-[9px] font-bold uppercase tracking-[1px] block mb-1" style={{ color: "var(--cs-gray2)" }}>CHALLENGE TYPE</label>
              <select value={form.challenge_type} onChange={(e) => setForm({ ...form, challenge_type: e.target.value })} className="w-full text-[11px] px-2 py-1 outline-none" style={{ background: "var(--cs-bg)", border: "1px solid var(--cs-border)", color: "var(--cs-text)" }}>
                <option value="score_too_high">Score Too High</option>
                <option value="score_too_low">Score Too Low</option>
                <option value="data_quality">Data Quality Issue</option>
                <option value="missing_context">Missing Context</option>
              </select>
            </div>
          </div>
          <div className="mb-2">
            <label className="text-[9px] font-bold uppercase tracking-[1px] block mb-1" style={{ color: "var(--cs-gray2)" }}>EVIDENCE</label>
            <textarea value={form.evidence} onChange={(e) => setForm({ ...form, evidence: e.target.value })} rows={2} placeholder="Describe your evidence for contesting this score..." className="w-full text-[11px] px-2 py-1 outline-none resize-none" style={{ background: "var(--cs-bg)", border: "1px solid var(--cs-border)", color: "var(--cs-text)" }} />
          </div>
          <div className="flex items-end gap-2">
            <div className="flex-1">
              <label className="text-[9px] font-bold uppercase tracking-[1px] block mb-1" style={{ color: "var(--cs-gray2)" }}>PROPOSED SCORE (OPTIONAL)</label>
              <input type="number" min="0" max="100" value={form.proposed_adjustment} onChange={(e) => setForm({ ...form, proposed_adjustment: e.target.value })} placeholder="0-100" className="w-full text-[11px] px-2 py-1 outline-none" style={{ background: "var(--cs-bg)", border: "1px solid var(--cs-border)", color: "var(--cs-text)" }} />
            </div>
            <button onClick={handleSubmit} disabled={!form.challenger_name || !form.evidence} className="text-[10px] font-bold px-4 py-1.5 uppercase tracking-wide" style={{ background: form.challenger_name && form.evidence ? "var(--cs-amber)" : "var(--cs-gray3)", color: "#000" }}>
              SUBMIT CHALLENGE
            </button>
          </div>
        </div>
      )}

      <div style={{ background: "var(--cs-bg)" }}>
        {challenges.length === 0 ? (
          <div className="px-3 py-4 text-center text-[10px]" style={{ color: "var(--cs-gray3)", fontFamily: "var(--cs-mono)" }}>
            NO CHALLENGES FILED FOR THIS TRACT
          </div>
        ) : (
          challenges.map((c) => (
            <div key={c.id} className="px-3 py-2" style={{ borderBottom: "1px solid rgba(30,30,30,0.5)", fontFamily: "var(--cs-mono)" }}>
              <div className="flex items-center gap-2 mb-1">
                <span className="text-[9px] font-bold px-1.5 py-0.5 uppercase tracking-wide" style={{ background: `${STATUS_COLOR[c.status] || "var(--cs-gray2)"}1a`, color: STATUS_COLOR[c.status] || "var(--cs-gray2)", border: `1px solid ${STATUS_COLOR[c.status] || "var(--cs-gray2)"}33` }}>
                  {c.status.replace(/_/g, " ")}
                </span>
                <span className="text-[10px]" style={{ color: "var(--cs-text)" }}>{c.challenge_type.replace(/_/g, " ")}</span>
                <span className="flex-1" />
                <span className="text-[9px]" style={{ color: "var(--cs-gray3)" }}>{c.challenger_name}</span>
              </div>
              <p className="text-[10px]" style={{ color: "var(--cs-gray1)" }}>{c.evidence}</p>
              {c.reviewer_notes && <p className="text-[9px] mt-1" style={{ color: "var(--cs-amber)" }}>Review: {c.reviewer_notes}</p>}
            </div>
          ))
        )}
      </div>
    </>
  );
}

function exportCSV(regionId: string, pkg: typeof defaultPkg, decision: typeof fallbackDecision) {
  const rows = [
    ["Field", "Value"],
    ["Region ID", regionId],
    ["Region Name", pkg.regionName],
    ["Risk Level", pkg.riskLevel],
    ["ML Score", String(pkg.mlScore)],
    ["Baseline Score", String(pkg.baselineScore)],
    ["Overall Score", String(pkg.scores.overall)],
    ["Violent Score", String(pkg.scores.violent)],
    ["Property Score", String(pkg.scores.property)],
    ["Decision", decision.decision],
    ["Headline", decision.headline],
    ["Next Step", decision.nextStep],
    ["Caveat", decision.caveat],
    ...pkg.drivers.map((d) => [`Driver: ${d.name}`, `${d.direction} (${d.impact})`]),
  ];
  const csv = rows.map((r) => r.map((c) => `"${c.replace(/"/g, '""')}"`).join(",")).join("\n");
  const blob = new Blob([csv], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `crimescope-report-${regionId}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}
