"use client";

import { useScores, useLiveEvents } from "../../lib/hooks";
import { useAppStore } from "../../lib/store";
import Link from "next/link";

type Alert = {
  id: string;
  type: "near_repeat" | "rising_activity" | "confidence_drop" | "missingness_spike" | "source_conflict";
  severity: "critical" | "high" | "medium" | "low";
  regionId: string;
  regionName: string;
  title: string;
  detail: string;
  time: string;
};

const SEVERITY_COLORS: Record<string, string> = {
  critical: "var(--cs-red)",
  high: "var(--cs-orange)",
  medium: "var(--cs-amber)",
  low: "var(--cs-green)",
};

const TYPE_LABELS: Record<string, string> = {
  near_repeat: "NEAR-REPEAT CLUSTER",
  rising_activity: "RISING ACTIVITY",
  confidence_drop: "CONFIDENCE DROP",
  missingness_spike: "MISSINGNESS SPIKE",
  source_conflict: "SOURCE CONFLICT",
};

function SectionHeader({ title, meta }: { title: string; meta?: string }) {
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

export default function AlertsPage() {
  const { data: scores = [] } = useScores();
  const { data: events = [] } = useLiveEvents();
  const watchlist = useAppStore((s) => s.watchlist);
  const addToWatchlist = useAppStore((s) => s.addToWatchlist);
  const removeFromWatchlist = useAppStore((s) => s.removeFromWatchlist);

  const alerts: Alert[] = [];
  const critical = scores.filter((s) => s.risk_tier === "Critical");
  const rising = scores.filter((s) => s.trend_direction === "rising");

  for (const t of critical.slice(0, 3)) {
    alerts.push({
      id: `nr-${t.tract_geoid}`,
      type: "near_repeat",
      severity: "critical",
      regionId: t.tract_geoid,
      regionName: t.name || `Tract ${t.tract_geoid.slice(-6)}`,
      title: `Critical risk detected in ${t.name || t.tract_geoid}`,
      detail: `Risk score ${t.risk_score.toFixed(0)} exceeds critical threshold. Immediate monitoring recommended.`,
      time: new Date().toISOString(),
    });
  }

  for (const t of rising.slice(0, 3)) {
    alerts.push({
      id: `ra-${t.tract_geoid}`,
      type: "rising_activity",
      severity: "high",
      regionId: t.tract_geoid,
      regionName: t.name || `Tract ${t.tract_geoid.slice(-6)}`,
      title: `Rising trend in ${t.name || t.tract_geoid}`,
      detail: `Score ${t.risk_score.toFixed(0)} with upward trend direction. Watch for escalation.`,
      time: new Date().toISOString(),
    });
  }

  if (scores.length > 0) {
    const low = scores.filter((s) => s.incident_count < 5).slice(0, 2);
    for (const t of low) {
      alerts.push({
        id: `ms-${t.tract_geoid}`,
        type: "missingness_spike",
        severity: "medium",
        regionId: t.tract_geoid,
        regionName: t.name || `Tract ${t.tract_geoid.slice(-6)}`,
        title: `Low incident count in ${t.name || t.tract_geoid}`,
        detail: `Only ${t.incident_count} incidents recorded. Possible underreporting.`,
        time: new Date().toISOString(),
      });
    }
  }

  const watchedScores = scores.filter((s) => watchlist.includes(s.tract_geoid));
  const unwatchedCritical = scores.filter((s) => s.risk_tier === "Critical" && !watchlist.includes(s.tract_geoid));

  return (
    <div className="flex flex-col flex-1 overflow-hidden" style={{ background: "var(--cs-bg)" }}>
      {/* KPI */}
      <div className="flex shrink-0" style={{ borderBottom: "1px solid var(--cs-border)", fontFamily: "var(--cs-mono)" }}>
        {[
          { label: "ACTIVE ALERTS", value: String(alerts.length), color: "var(--cs-red)" },
          { label: "CRITICAL", value: String(alerts.filter((a) => a.severity === "critical").length), color: "var(--cs-red)" },
          { label: "HIGH", value: String(alerts.filter((a) => a.severity === "high").length), color: "var(--cs-orange)" },
          { label: "WATCHLIST", value: String(watchlist.length), color: "var(--cs-cyan)" },
          { label: "LIVE EVENTS", value: String(events.length), color: "var(--cs-green)" },
        ].map((k) => (
          <div key={k.label} className="flex-1 px-3.5 py-2" style={{ borderRight: "1px solid var(--cs-border)" }}>
            <div className="text-[8px] font-semibold uppercase tracking-[1.2px] mb-0.5" style={{ color: "var(--cs-gray2)" }}>{k.label}</div>
            <div className="text-lg font-bold tracking-tight leading-none" style={{ color: k.color }}>{k.value}</div>
          </div>
        ))}
      </div>

      <div className="flex flex-1 min-h-0 overflow-hidden">
        {/* Alerts feed */}
        <div className="flex-1 flex flex-col overflow-hidden" style={{ borderRight: "1px solid var(--cs-border)" }}>
          <SectionHeader title="ALERTS" meta={`${alerts.length} ACTIVE`} />
          <div className="flex-1 overflow-y-auto" style={{ fontFamily: "var(--cs-mono)" }}>
            {alerts.length === 0 ? (
              <div className="text-center py-12 text-[10px]" style={{ color: "var(--cs-gray3)" }}>NO ACTIVE ALERTS</div>
            ) : (
              alerts.map((a) => (
                <div key={a.id} className="px-4 py-2.5" style={{ borderBottom: "1px solid var(--cs-border)" }}>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="w-2 h-2 rounded-full" style={{ background: SEVERITY_COLORS[a.severity], animation: a.severity === "critical" ? "cs-pulse 2s ease-in-out infinite" : "none" }} />
                    <span className="text-[8px] font-bold uppercase px-1.5 py-0.5" style={{ background: `${SEVERITY_COLORS[a.severity]}18`, color: SEVERITY_COLORS[a.severity] }}>
                      {a.severity}
                    </span>
                    <span className="text-[8px] uppercase tracking-wide" style={{ color: "var(--cs-gray2)" }}>{TYPE_LABELS[a.type]}</span>
                    <span className="flex-1" />
                    <Link href={`/dashboard/region/${a.regionId}`} className="text-[8px] font-bold uppercase tracking-wide" style={{ color: "var(--cs-accent)" }}>
                      VIEW →
                    </Link>
                  </div>
                  <div className="text-[11px] font-medium" style={{ color: "var(--cs-text)" }}>{a.title}</div>
                  <div className="text-[9px] mt-0.5" style={{ color: "var(--cs-gray2)" }}>{a.detail}</div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Watchlist */}
        <div className="flex flex-col overflow-hidden" style={{ width: 320 }}>
          <SectionHeader title="WATCHLIST" meta={`${watchlist.length} TRACTS`} />
          <div className="flex-1 overflow-y-auto" style={{ fontFamily: "var(--cs-mono)" }}>
            {watchedScores.length === 0 ? (
              <div className="text-center py-8">
                <div className="text-[10px] mb-2" style={{ color: "var(--cs-gray3)" }}>NO WATCHED TRACTS</div>
                <div className="text-[9px]" style={{ color: "var(--cs-gray3)" }}>Add tracts from the dashboard to monitor them here.</div>
              </div>
            ) : (
              watchedScores.map((s) => (
                <div key={s.tract_geoid} className="flex items-center gap-2 px-3 py-2" style={{ borderBottom: "1px solid var(--cs-border)" }}>
                  <span className="text-[11px] font-bold" style={{
                    color: s.risk_score >= 75 ? "var(--cs-red)" : s.risk_score >= 50 ? "var(--cs-orange)" : "var(--cs-green)",
                  }}>
                    {s.risk_score.toFixed(0)}
                  </span>
                  <div className="flex-1 min-w-0">
                    <div className="text-[10px] truncate" style={{ color: "var(--cs-text)" }}>{s.name || s.tract_geoid}</div>
                    <div className="text-[8px] uppercase" style={{ color: "var(--cs-gray2)" }}>{s.risk_tier} · {s.trend_direction || "stable"}</div>
                  </div>
                  <button
                    onClick={() => removeFromWatchlist(s.tract_geoid)}
                    className="text-[8px] font-bold px-1.5 py-0.5"
                    style={{ color: "var(--cs-red)", background: "var(--cs-red-lo)", border: "1px solid rgba(239,68,68,0.2)" }}
                  >
                    ✕
                  </button>
                </div>
              ))
            )}
          </div>

          {/* Suggest adding critical tracts */}
          {unwatchedCritical.length > 0 && (
            <>
              <SectionHeader title="SUGGESTED" meta="CRITICAL TRACTS" />
              <div className="overflow-y-auto" style={{ maxHeight: 200, fontFamily: "var(--cs-mono)" }}>
                {unwatchedCritical.slice(0, 5).map((s) => (
                  <div key={s.tract_geoid} className="flex items-center gap-2 px-3 py-1.5" style={{ borderBottom: "1px solid var(--cs-border)" }}>
                    <span className="text-[10px] font-bold" style={{ color: "var(--cs-red)" }}>{s.risk_score.toFixed(0)}</span>
                    <span className="text-[9px] flex-1 truncate" style={{ color: "var(--cs-text)" }}>{s.name || s.tract_geoid}</span>
                    <button
                      onClick={() => addToWatchlist(s.tract_geoid)}
                      className="text-[8px] font-bold px-1.5 py-0.5"
                      style={{ color: "var(--cs-accent)", background: "var(--cs-accent-lo)", border: "1px solid var(--cs-accent-md)" }}
                    >
                      + WATCH
                    </button>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
