"use client";

import { useState } from "react";
import NavHeader from "../../components/nav-header";
import { useInterventions, useScores } from "../../lib/hooks";
import { runSimulation } from "../../lib/api";
import type { SimulationResult } from "../../lib/api";

function PanelHeader({ title, meta }: { title: string; meta?: string }) {
  return (
    <div
      className="flex items-center justify-between px-3 shrink-0"
      style={{ height: 28, background: "var(--cs-panel)", borderBottom: "1px solid var(--cs-border)", fontFamily: "var(--cs-mono)" }}
    >
      <span className="text-[10px] font-bold tracking-[1.5px] uppercase" style={{ color: "var(--cs-accent)" }}>{title}</span>
      {meta && <span className="text-[9px] tracking-wide" style={{ color: "var(--cs-gray2)" }}>{meta}</span>}
    </div>
  );
}

export default function SimulatorPage() {
  const { data: interventions = [] } = useInterventions();
  const { data: scores = [] } = useScores();
  const [tractId, setTractId] = useState("17031839100");
  const [selected, setSelected] = useState<Record<string, number>>({});
  const [result, setResult] = useState<SimulationResult | null>(null);
  const [loading, setLoading] = useState(false);

  const toggleIntervention = (id: string) => {
    setSelected((prev) => {
      const next = { ...prev };
      if (id in next) delete next[id];
      else next[id] = 1.0;
      return next;
    });
  };

  const setIntensity = (id: string, val: number) => {
    setSelected((prev) => ({ ...prev, [id]: val }));
  };

  const handleRun = async () => {
    if (Object.keys(selected).length === 0) return;
    setLoading(true);
    try {
      const res = await runSimulation(
        tractId,
        Object.entries(selected).map(([id, intensity]) => ({ id, intensity })),
      );
      setResult(res);
    } catch {
      setResult(null);
    }
    setLoading(false);
  };

  const tract = scores.find((s) => s.tract_geoid === tractId);

  return (
    <div className="flex flex-col h-screen overflow-hidden" style={{ background: "var(--cs-bg)" }}>
      <NavHeader />

      <PanelHeader title="COUNTERFACTUAL ACTION SIMULATOR" meta="WHAT-IF SCENARIO MODELLING" />
      <div className="px-3.5 py-2 shrink-0" style={{ background: "var(--cs-bg)", borderBottom: "1px solid var(--cs-border)", fontFamily: "var(--cs-mono)" }}>
        <p className="text-[11px]" style={{ color: "var(--cs-gray1)" }}>
          Model how interventions could change a tract&apos;s risk score. Select a tract, choose interventions, adjust intensity, and run the simulation.
        </p>
      </div>

      <div className="flex flex-1 min-h-0 overflow-hidden">
        {/* Left: Configuration */}
        <div className="flex flex-col" style={{ width: "50%", borderRight: "1px solid var(--cs-border)" }}>
          {/* Tract Selector */}
          <div className="flex items-center gap-2 px-3 shrink-0" style={{ height: 36, background: "var(--cs-panel)", borderBottom: "1px solid var(--cs-border)", fontFamily: "var(--cs-mono)" }}>
            <span className="text-[9px] font-bold tracking-[1px] uppercase" style={{ color: "var(--cs-accent)" }}>TRACT:</span>
            <select
              value={tractId}
              onChange={(e) => { setTractId(e.target.value); setResult(null); }}
              className="flex-1 text-[11px] px-2 py-1 outline-none"
              style={{ background: "var(--cs-panel2)", border: "1px solid var(--cs-border)", color: "var(--cs-text)", fontFamily: "var(--cs-mono)" }}
            >
              {scores.slice(0, 100).map((s) => (
                <option key={s.tract_geoid} value={s.tract_geoid}>
                  {s.name || s.NAMELSAD || s.tract_geoid} — Score: {Math.round(s.risk_score)}
                </option>
              ))}
            </select>
          </div>

          {tract && (
            <div className="flex gap-3 px-3 py-2 shrink-0" style={{ borderBottom: "1px solid var(--cs-border)", fontFamily: "var(--cs-mono)" }}>
              <div className="text-[11px]"><span style={{ color: "var(--cs-gray2)" }}>CURRENT SCORE: </span><span className="font-bold" style={{ color: "var(--cs-amber)" }}>{Math.round(tract.risk_score)}</span></div>
              <div className="text-[11px]"><span style={{ color: "var(--cs-gray2)" }}>TIER: </span><span className="font-bold" style={{ color: "var(--cs-text)" }}>{tract.risk_tier}</span></div>
            </div>
          )}

          <PanelHeader title="SELECT INTERVENTIONS" meta={`${Object.keys(selected).length} ACTIVE`} />
          <div className="flex-1 overflow-y-auto">
            {interventions.map((iv) => {
              const active = iv.id in selected;
              return (
                <div key={iv.id} className="px-3 py-2" style={{ borderBottom: "1px solid rgba(30,30,30,0.5)", fontFamily: "var(--cs-mono)" }}>
                  <div className="flex items-center gap-2 mb-1">
                    <button onClick={() => toggleIntervention(iv.id)} className="w-3 h-3 flex items-center justify-center text-[8px] shrink-0" style={{ background: active ? "var(--cs-accent)" : "transparent", border: `1px solid ${active ? "var(--cs-accent)" : "var(--cs-gray3)"}`, color: active ? "#000" : "var(--cs-gray3)" }}>
                      {active ? "✓" : ""}
                    </button>
                    <span className="text-[11px] flex-1" style={{ color: active ? "var(--cs-text)" : "var(--cs-gray2)" }}>{iv.label}</span>
                    <span className="text-[9px] px-1.5 py-0.5" style={{ background: iv.direction === "decrease" ? "var(--cs-green-lo)" : "var(--cs-red-lo)", color: iv.direction === "decrease" ? "var(--cs-green)" : "var(--cs-red)", border: `1px solid ${iv.direction === "decrease" ? "var(--cs-green)" : "var(--cs-red)"}33` }}>
                      {iv.direction === "decrease" ? "▼" : "▲"} {iv.typical_impact_pct}%
                    </span>
                  </div>
                  {active && (
                    <div className="flex items-center gap-2 ml-5">
                      <span className="text-[9px]" style={{ color: "var(--cs-gray2)" }}>INTENSITY:</span>
                      <input type="range" min="0.25" max="2" step="0.25" value={selected[iv.id]} onChange={(e) => setIntensity(iv.id, parseFloat(e.target.value))} className="flex-1" style={{ accentColor: "var(--cs-accent)" }} />
                      <span className="text-[10px] font-bold w-10 text-right" style={{ color: "var(--cs-amber)" }}>{selected[iv.id]}x</span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          <div className="px-3 py-2.5 shrink-0" style={{ borderTop: "1px solid var(--cs-border)", background: "var(--cs-panel)" }}>
            <button onClick={handleRun} disabled={loading || Object.keys(selected).length === 0} className="w-full text-[11px] font-bold py-2 uppercase tracking-wide" style={{ background: Object.keys(selected).length > 0 ? "var(--cs-accent)" : "var(--cs-gray3)", color: "#000", fontFamily: "var(--cs-mono)", opacity: loading ? 0.6 : 1 }}>
              {loading ? "SIMULATING..." : "RUN SIMULATION"}
            </button>
          </div>
        </div>

        {/* Right: Results */}
        <div className="flex flex-col flex-1">
          {!result ? (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center" style={{ fontFamily: "var(--cs-mono)" }}>
                <div className="text-[11px] mb-1" style={{ color: "var(--cs-gray2)" }}>SELECT INTERVENTIONS AND RUN</div>
                <div className="text-[9px]" style={{ color: "var(--cs-gray3)" }}>RESULTS WILL APPEAR HERE</div>
              </div>
            </div>
          ) : (
            <div className="flex-1 overflow-y-auto">
              {/* Score Comparison */}
              <PanelHeader title="SIMULATION RESULT" meta={result.region_name} />
              <div className="flex gap-4 px-4 py-3" style={{ borderBottom: "1px solid var(--cs-border)", fontFamily: "var(--cs-mono)" }}>
                <div className="flex-1 text-center py-3" style={{ border: "1px solid var(--cs-border)", background: "var(--cs-panel2)" }}>
                  <div className="text-[8px] font-semibold tracking-[0.8px] mb-1" style={{ color: "var(--cs-gray2)" }}>ORIGINAL</div>
                  <div className="text-3xl font-bold" style={{ color: "var(--cs-amber)" }}>{result.original_score.toFixed(0)}</div>
                  <div className="text-[9px] mt-0.5" style={{ color: "var(--cs-gray2)" }}>{result.original_tier}</div>
                </div>
                <div className="flex items-center text-xl font-bold" style={{ color: "var(--cs-gray3)" }}>→</div>
                <div className="flex-1 text-center py-3" style={{ border: "1px solid var(--cs-border)", background: "var(--cs-panel2)" }}>
                  <div className="text-[8px] font-semibold tracking-[0.8px] mb-1" style={{ color: "var(--cs-gray2)" }}>SIMULATED</div>
                  <div className="text-3xl font-bold" style={{ color: result.delta < 0 ? "var(--cs-green)" : "var(--cs-red)" }}>{result.simulated_score.toFixed(0)}</div>
                  <div className="text-[9px] mt-0.5" style={{ color: "var(--cs-gray2)" }}>{result.simulated_tier}</div>
                </div>
                <div className="flex-1 text-center py-3" style={{ border: "1px solid var(--cs-border)", background: "var(--cs-panel2)" }}>
                  <div className="text-[8px] font-semibold tracking-[0.8px] mb-1" style={{ color: "var(--cs-gray2)" }}>DELTA</div>
                  <div className="text-3xl font-bold" style={{ color: result.delta < 0 ? "var(--cs-green)" : "var(--cs-red)" }}>
                    {result.delta > 0 ? "+" : ""}{result.delta.toFixed(0)}
                  </div>
                  <div className="text-[9px] mt-0.5" style={{ color: "var(--cs-gray2)" }}>POINTS</div>
                </div>
              </div>

              {/* Narrative */}
              <div className="px-4 py-3" style={{ borderBottom: "1px solid var(--cs-border)", fontFamily: "var(--cs-mono)" }}>
                <p className="text-[11px] leading-relaxed" style={{ color: "var(--cs-gray1)" }}>{result.narrative}</p>
              </div>

              {/* Breakdown */}
              <PanelHeader title="IMPACT BREAKDOWN" meta={`${result.breakdown.length} INTERVENTIONS`} />
              {result.breakdown.map((b, i) => (
                <div key={i} className="flex items-center gap-3 px-4 py-2" style={{ borderBottom: "1px solid rgba(30,30,30,0.5)", fontFamily: "var(--cs-mono)" }}>
                  <span className="text-[11px] flex-1" style={{ color: "var(--cs-text)" }}>{b.intervention}</span>
                  <span className="text-[9px]" style={{ color: "var(--cs-gray2)" }}>{b.intensity}x</span>
                  <span className="text-[11px] font-bold tabular-nums" style={{ color: b.score_impact < 0 ? "var(--cs-green)" : "var(--cs-red)" }}>
                    {b.score_impact > 0 ? "+" : ""}{b.score_impact.toFixed(1)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
