"use client";

import { useState } from "react";
import { useAuditTrail, useAuditStats, useScores } from "../../lib/hooks";
import { createAuditEntry } from "../../lib/api";
import { useAppStore } from "../../lib/store";
import { useQueryClient } from "@tanstack/react-query";

function PanelHeader({ title, meta }: { title: string; meta?: string }) {
  return (
    <div className="flex items-center justify-between px-3 shrink-0" style={{ height: 28, background: "var(--cs-panel)", borderBottom: "1px solid var(--cs-border)", fontFamily: "var(--cs-mono)" }}>
      <span className="text-[10px] font-bold tracking-[1.5px] uppercase" style={{ color: "var(--cs-accent)" }}>{title}</span>
      {meta && <span className="text-[9px] tracking-wide" style={{ color: "var(--cs-gray2)" }}>{meta}</span>}
    </div>
  );
}

const DECISION_COLOR: Record<string, string> = {
  accept: "var(--cs-green)",
  "conditional accept": "var(--cs-amber)",
  "manual review": "var(--cs-orange)",
  decline: "var(--cs-red)",
};

export default function AuditPage() {
  const { data: trail = [] } = useAuditTrail();
  const { data: stats } = useAuditStats();
  const { data: scores = [] } = useScores();
  const persona = useAppStore((s) => s.persona);
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ region_id: "", decision: "accept", rationale: "", overridden: false, override_reason: "" });

  const handleSubmit = async () => {
    const tract = scores.find((s) => s.tract_geoid === form.region_id);
    await createAuditEntry({
      region_id: form.region_id,
      persona,
      decision: form.decision,
      rationale: form.rationale,
      risk_score: tract?.risk_score ?? 0,
      risk_tier: tract?.risk_tier ?? "Unknown",
      overridden: form.overridden,
      override_reason: form.overridden ? form.override_reason : undefined,
    });
    qc.invalidateQueries({ queryKey: ["audit"] });
    qc.invalidateQueries({ queryKey: ["auditStats"] });
    setShowForm(false);
    setForm({ region_id: "", decision: "accept", rationale: "", overridden: false, override_reason: "" });
  };

  const kpis = [
    { label: "TOTAL DECISIONS", value: String(stats?.total_decisions ?? 0), color: "var(--cs-text)" },
    { label: "OVERRIDES", value: String(stats?.total_overrides ?? 0), color: "var(--cs-amber)" },
    { label: "OVERRIDE RATE", value: `${stats?.override_rate ?? 0}%`, color: "var(--cs-orange)" },
    { label: "MOST COMMON", value: stats?.decision_breakdown ? Object.entries(stats.decision_breakdown).sort((a, b) => b[1] - a[1])[0]?.[0]?.toUpperCase() || "—" : "—", color: "var(--cs-cyan)" },
  ];

  return (
    <div className="flex flex-col flex-1 overflow-hidden" style={{ background: "var(--cs-bg)" }}>

      {/* KPI Row */}
      <div className="flex shrink-0" style={{ borderBottom: "1px solid var(--cs-border)", fontFamily: "var(--cs-mono)" }}>
        {kpis.map((k) => (
          <div key={k.label} className="flex-1 px-3.5 py-2.5" style={{ borderRight: "1px solid var(--cs-border)" }}>
            <div className="text-[9px] font-semibold uppercase tracking-[1.2px] mb-1" style={{ color: "var(--cs-gray2)" }}>{k.label}</div>
            <div className="text-xl font-bold tracking-tight leading-none" style={{ color: k.color }}>{k.value}</div>
          </div>
        ))}
      </div>

      {/* Actions Bar */}
      <div className="flex items-center justify-between px-3.5 shrink-0" style={{ height: 36, background: "var(--cs-panel)", borderBottom: "1px solid var(--cs-border)", fontFamily: "var(--cs-mono)" }}>
        <span className="text-[10px] font-bold tracking-[1.5px] uppercase" style={{ color: "var(--cs-accent)" }}>DECISION AUDIT TRAIL</span>
        <button onClick={() => setShowForm(!showForm)} className="text-[10px] font-bold px-2.5 py-1 uppercase tracking-wide" style={{ background: showForm ? "var(--cs-red)" : "var(--cs-accent)", color: "#000" }}>
          {showForm ? "CANCEL" : "+ LOG DECISION"}
        </button>
      </div>

      {/* New Decision Form */}
      {showForm && (
        <div className="px-3.5 py-3 shrink-0" style={{ background: "var(--cs-panel2)", borderBottom: "1px solid var(--cs-border)", fontFamily: "var(--cs-mono)" }}>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-[9px] font-bold uppercase tracking-[1px] block mb-1" style={{ color: "var(--cs-gray2)" }}>TRACT ID</label>
              <select value={form.region_id} onChange={(e) => setForm({ ...form, region_id: e.target.value })} className="w-full text-[11px] px-2 py-1.5 outline-none" style={{ background: "var(--cs-bg)", border: "1px solid var(--cs-border)", color: "var(--cs-text)" }}>
                <option value="">Select tract...</option>
                {scores.slice(0, 50).map((s) => <option key={s.tract_geoid} value={s.tract_geoid}>{s.name || s.tract_geoid} ({Math.round(s.risk_score)})</option>)}
              </select>
            </div>
            <div>
              <label className="text-[9px] font-bold uppercase tracking-[1px] block mb-1" style={{ color: "var(--cs-gray2)" }}>DECISION</label>
              <select value={form.decision} onChange={(e) => setForm({ ...form, decision: e.target.value })} className="w-full text-[11px] px-2 py-1.5 outline-none" style={{ background: "var(--cs-bg)", border: "1px solid var(--cs-border)", color: "var(--cs-text)" }}>
                <option value="accept">Accept</option>
                <option value="conditional accept">Conditional Accept</option>
                <option value="manual review">Manual Review</option>
                <option value="decline">Decline</option>
              </select>
            </div>
          </div>
          <div className="mt-2">
            <label className="text-[9px] font-bold uppercase tracking-[1px] block mb-1" style={{ color: "var(--cs-gray2)" }}>RATIONALE</label>
            <textarea value={form.rationale} onChange={(e) => setForm({ ...form, rationale: e.target.value })} rows={2} className="w-full text-[11px] px-2 py-1.5 outline-none resize-none" style={{ background: "var(--cs-bg)", border: "1px solid var(--cs-border)", color: "var(--cs-text)" }} placeholder="Explain the decision reasoning..." />
          </div>
          <div className="mt-2 flex items-center gap-3">
            <label className="flex items-center gap-1.5 text-[10px]" style={{ color: "var(--cs-gray1)" }}>
              <input type="checkbox" checked={form.overridden} onChange={(e) => setForm({ ...form, overridden: e.target.checked })} style={{ accentColor: "var(--cs-amber)" }} />
              OVERRIDE MODEL RECOMMENDATION
            </label>
            {form.overridden && (
              <input type="text" placeholder="Override reason..." value={form.override_reason} onChange={(e) => setForm({ ...form, override_reason: e.target.value })} className="flex-1 text-[11px] px-2 py-1 outline-none" style={{ background: "var(--cs-bg)", border: "1px solid var(--cs-border)", color: "var(--cs-text)" }} />
            )}
          </div>
          <button onClick={handleSubmit} disabled={!form.region_id || !form.rationale} className="mt-2 text-[10px] font-bold px-4 py-1.5 uppercase tracking-wide" style={{ background: form.region_id && form.rationale ? "var(--cs-accent)" : "var(--cs-gray3)", color: "#000" }}>
            SUBMIT
          </button>
        </div>
      )}

      {/* Audit Log */}
      <div className="flex-1 overflow-y-auto">
        {trail.length === 0 ? (
          <div className="flex items-center justify-center py-16" style={{ fontFamily: "var(--cs-mono)" }}>
            <div className="text-center">
              <div className="text-[11px] mb-1" style={{ color: "var(--cs-gray2)" }}>NO DECISIONS LOGGED YET</div>
              <div className="text-[9px]" style={{ color: "var(--cs-gray3)" }}>USE &ldquo;LOG DECISION&rdquo; TO RECORD AN UNDERWRITING DECISION</div>
            </div>
          </div>
        ) : (
          trail.slice().reverse().map((r) => (
            <div key={r.id} className="px-3.5 py-2.5" style={{ borderBottom: "1px solid rgba(30,30,30,0.5)", fontFamily: "var(--cs-mono)" }}>
              <div className="flex items-center gap-2 mb-1">
                <span className="text-[9px] font-bold px-1.5 py-0.5 uppercase tracking-wide" style={{ background: `${DECISION_COLOR[r.decision] || "var(--cs-gray2)"}1a`, color: DECISION_COLOR[r.decision] || "var(--cs-gray2)", border: `1px solid ${DECISION_COLOR[r.decision] || "var(--cs-gray2)"}33` }}>
                  {r.decision}
                </span>
                <span className="text-[11px] font-medium" style={{ color: "var(--cs-text)" }}>{r.region_id}</span>
                <span className="flex-1" />
                <span className="text-[9px]" style={{ color: "var(--cs-gray3)" }}>
                  {new Date(r.timestamp).toLocaleString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}
                </span>
              </div>
              <p className="text-[10px] mb-1" style={{ color: "var(--cs-gray1)" }}>{r.rationale}</p>
              <div className="flex items-center gap-3">
                <span className="text-[9px]" style={{ color: "var(--cs-gray2)" }}>Score: {r.risk_score.toFixed(0)} · {r.risk_tier}</span>
                {r.overridden && (
                  <span className="text-[9px] font-bold px-1.5 py-0.5 uppercase tracking-wide" style={{ background: "rgba(245,158,11,0.08)", color: "var(--cs-amber)", border: "1px solid rgba(245,158,11,0.2)" }}>
                    OVERRIDDEN
                  </span>
                )}
              </div>
              {r.override_reason && <p className="text-[9px] mt-0.5" style={{ color: "var(--cs-amber)" }}>Override: {r.override_reason}</p>}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
