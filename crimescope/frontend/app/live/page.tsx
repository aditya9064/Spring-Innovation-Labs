"use client";

import { useState } from "react";
import { useLiveEvents, useLiveBanner, useScores } from "../../lib/hooks";
import { useAppStore } from "../../lib/store";

const SOURCE_COLORS: Record<string, string> = {
  official_bulletin: "var(--cs-green)",
  public_alert: "var(--cs-amber)",
  news_rss: "var(--cs-cyan)",
  dispatch: "var(--cs-accent)",
};

const CONFIDENCE_COLORS: Record<string, string> = {
  high: "var(--cs-green)",
  medium: "var(--cs-amber)",
  low: "var(--cs-red)",
};

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

export default function LivePage() {
  const { data: events = [], isLoading } = useLiveEvents();
  const { data: banner } = useLiveBanner();
  const { data: scores = [] } = useScores();
  const viewMode = useAppStore((s) => s.viewMode);
  const [selectedEvent, setSelectedEvent] = useState<string | null>(null);
  const [sourceFilter, setSourceFilter] = useState<string>("all");
  const [confidenceFilter, setConfidenceFilter] = useState<string>("all");

  const filtered = events.filter((e) => {
    if (sourceFilter !== "all" && e.sourceType !== sourceFilter) return false;
    if (confidenceFilter !== "all" && e.confidence !== confidenceFilter) return false;
    return true;
  });

  const sources = Array.from(new Set(events.map((e) => e.sourceType)));
  const selectedEvt = events.find((e) => e.id === selectedEvent);

  const verified = events.filter((e) => e.status === "verified").length;
  const reported = events.filter((e) => e.status === "reported").length;
  const unresolved = events.filter((e) => e.status !== "verified" && e.status !== "reported").length;

  return (
    <div className="flex flex-col flex-1 overflow-hidden" style={{ background: "var(--cs-bg)" }}>
      {/* Live Banner */}
      {banner && (
        <div
          className="flex items-center gap-3 px-4 py-2 shrink-0"
          style={{
            background: banner.status === "active" ? "rgba(34,197,94,0.06)" : "rgba(245,158,11,0.06)",
            borderBottom: `1px solid ${banner.status === "active" ? "rgba(34,197,94,0.2)" : "rgba(245,158,11,0.2)"}`,
            fontFamily: "var(--cs-mono)",
          }}
        >
          <span
            className="w-2 h-2 rounded-full shrink-0"
            style={{ background: banner.status === "active" ? "var(--cs-green)" : "var(--cs-amber)", animation: "cs-pulse 2s ease-in-out infinite" }}
          />
          <span className="text-[11px] font-bold" style={{ color: banner.status === "active" ? "var(--cs-green)" : "var(--cs-amber)" }}>
            {banner.headline}
          </span>
          <span className="flex-1" />
          <span className="text-[9px]" style={{ color: "var(--cs-gray2)" }}>{banner.summary}</span>
        </div>
      )}

      {/* KPI Strip */}
      <div className="flex shrink-0" style={{ borderBottom: "1px solid var(--cs-border)", fontFamily: "var(--cs-mono)" }}>
        {[
          { label: "TOTAL EVENTS", value: String(events.length), color: "var(--cs-text)" },
          { label: "VERIFIED", value: String(verified), color: "var(--cs-green)" },
          { label: "REPORTED", value: String(reported), color: "var(--cs-amber)" },
          { label: "UNRESOLVED", value: String(unresolved), color: "var(--cs-red)" },
          { label: "SOURCES", value: String(sources.length), color: "var(--cs-cyan)" },
          { label: "MODE", value: viewMode.toUpperCase(), color: viewMode === "verified" ? "var(--cs-green)" : viewMode === "live" ? "var(--cs-amber)" : "var(--cs-accent)" },
        ].map((k) => (
          <div key={k.label} className="flex-1 px-3 py-2" style={{ borderRight: "1px solid var(--cs-border)" }}>
            <div className="text-[8px] font-semibold uppercase tracking-[1.2px] mb-0.5" style={{ color: "var(--cs-gray2)" }}>{k.label}</div>
            <div className="text-lg font-bold tracking-tight leading-none" style={{ color: k.color }}>{k.value}</div>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 px-4 py-1.5 shrink-0" style={{ borderBottom: "1px solid var(--cs-border)", fontFamily: "var(--cs-mono)" }}>
        <span className="text-[8px] font-bold tracking-[1px]" style={{ color: "var(--cs-gray2)" }}>SOURCE</span>
        <select
          value={sourceFilter}
          onChange={(e) => setSourceFilter(e.target.value)}
          className="text-[10px] px-1.5 py-0.5 outline-none"
          style={{ background: "var(--cs-panel2)", border: "1px solid var(--cs-border)", color: "var(--cs-text)" }}
        >
          <option value="all">ALL</option>
          {sources.map((s) => (
            <option key={s} value={s}>{s.toUpperCase().replace(/_/g, " ")}</option>
          ))}
        </select>
        <span className="text-[8px] font-bold tracking-[1px]" style={{ color: "var(--cs-gray2)" }}>CONFIDENCE</span>
        <select
          value={confidenceFilter}
          onChange={(e) => setConfidenceFilter(e.target.value)}
          className="text-[10px] px-1.5 py-0.5 outline-none"
          style={{ background: "var(--cs-panel2)", border: "1px solid var(--cs-border)", color: "var(--cs-text)" }}
        >
          <option value="all">ALL</option>
          <option value="high">HIGH</option>
          <option value="medium">MEDIUM</option>
          <option value="low">LOW</option>
        </select>
        <span className="flex-1" />
        <span className="text-[9px]" style={{ color: "var(--cs-gray2)" }}>{filtered.length} EVENTS</span>
      </div>

      {/* Main: Event Feed + Detail Drawer */}
      <div className="flex flex-1 min-h-0 overflow-hidden">
        {/* Event feed */}
        <div className="flex-1 overflow-y-auto" style={{ fontFamily: "var(--cs-mono)" }}>
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <span className="text-[10px] uppercase tracking-[1px]" style={{ color: "var(--cs-gray2)" }}>LOADING LIVE FEED...</span>
            </div>
          ) : filtered.length === 0 ? (
            <div className="flex items-center justify-center py-12">
              <span className="text-[10px] uppercase tracking-[1px]" style={{ color: "var(--cs-gray3)" }}>NO EVENTS MATCH FILTERS</span>
            </div>
          ) : (
            filtered.map((ev) => (
              <button
                key={ev.id}
                onClick={() => setSelectedEvent(selectedEvent === ev.id ? null : ev.id)}
                className="w-full text-left flex items-start gap-3 px-4 py-2.5 transition-colors"
                style={{
                  borderBottom: "1px solid var(--cs-border)",
                  background: selectedEvent === ev.id ? "var(--cs-accent-lo)" : "transparent",
                }}
              >
                <span
                  className="w-2 h-2 rounded-full shrink-0 mt-1"
                  style={{ background: SOURCE_COLORS[ev.sourceType] || "var(--cs-gray2)" }}
                />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-0.5">
                    <span
                      className="text-[8px] font-bold uppercase px-1 py-0.5"
                      style={{
                        background: ev.status === "verified" ? "var(--cs-green-lo)" : "rgba(245,158,11,0.1)",
                        color: ev.status === "verified" ? "var(--cs-green)" : "var(--cs-amber)",
                      }}
                    >
                      {ev.status}
                    </span>
                    <span
                      className="text-[8px] font-bold uppercase px-1 py-0.5"
                      style={{ background: "rgba(100,116,139,0.08)", color: CONFIDENCE_COLORS[ev.confidence] || "var(--cs-gray2)" }}
                    >
                      {ev.confidence} CONF
                    </span>
                    <span className="text-[8px] uppercase" style={{ color: "var(--cs-gray3)" }}>
                      {ev.sourceType.replace(/_/g, " ")}
                    </span>
                  </div>
                  <div className="text-[11px] font-medium truncate" style={{ color: "var(--cs-text)" }}>{ev.title}</div>
                  <div className="text-[9px] mt-0.5" style={{ color: "var(--cs-gray2)" }}>
                    {new Date(ev.occurredAt).toLocaleString()}
                  </div>
                </div>
              </button>
            ))
          )}
        </div>

        {/* Event Detail Drawer */}
        {selectedEvt && (
          <div className="flex flex-col overflow-y-auto" style={{ width: 360, borderLeft: "1px solid var(--cs-border)", fontFamily: "var(--cs-mono)" }}>
            <SectionHeader title="EVENT DETAIL" meta={selectedEvt.id} />
            <div className="px-4 py-3 space-y-3">
              <div>
                <div className="text-[8px] font-bold tracking-[1px] mb-0.5" style={{ color: "var(--cs-gray2)" }}>TITLE</div>
                <div className="text-[11px] font-medium" style={{ color: "var(--cs-text)" }}>{selectedEvt.title}</div>
              </div>
              <div>
                <div className="text-[8px] font-bold tracking-[1px] mb-0.5" style={{ color: "var(--cs-gray2)" }}>SUMMARY</div>
                <div className="text-[10px]" style={{ color: "var(--cs-gray1)" }}>{selectedEvt.summary}</div>
              </div>
              <div className="flex gap-3">
                <div>
                  <div className="text-[8px] font-bold tracking-[1px] mb-0.5" style={{ color: "var(--cs-gray2)" }}>STATUS</div>
                  <span className="text-[9px] font-bold uppercase px-1.5 py-0.5" style={{
                    background: selectedEvt.status === "verified" ? "var(--cs-green-lo)" : "rgba(245,158,11,0.1)",
                    color: selectedEvt.status === "verified" ? "var(--cs-green)" : "var(--cs-amber)",
                  }}>
                    {selectedEvt.status}
                  </span>
                </div>
                <div>
                  <div className="text-[8px] font-bold tracking-[1px] mb-0.5" style={{ color: "var(--cs-gray2)" }}>CONFIDENCE</div>
                  <span className="text-[9px] font-bold uppercase" style={{ color: CONFIDENCE_COLORS[selectedEvt.confidence] || "var(--cs-gray2)" }}>
                    {selectedEvt.confidence}
                  </span>
                </div>
                <div>
                  <div className="text-[8px] font-bold tracking-[1px] mb-0.5" style={{ color: "var(--cs-gray2)" }}>SOURCE</div>
                  <span className="text-[9px] uppercase" style={{ color: SOURCE_COLORS[selectedEvt.sourceType] || "var(--cs-gray2)" }}>
                    {selectedEvt.sourceType.replace(/_/g, " ")}
                  </span>
                </div>
              </div>
              <div>
                <div className="text-[8px] font-bold tracking-[1px] mb-0.5" style={{ color: "var(--cs-gray2)" }}>OCCURRED</div>
                <div className="text-[10px]" style={{ color: "var(--cs-text)" }}>{new Date(selectedEvt.occurredAt).toLocaleString()}</div>
              </div>
              <div className="pt-2" style={{ borderTop: "1px solid var(--cs-border)" }}>
                <div className="text-[8px] font-bold tracking-[1px] mb-1" style={{ color: "var(--cs-gray2)" }}>NOTE</div>
                <p className="text-[9px]" style={{ color: "var(--cs-gray2)" }}>
                  Live signals are governed and separated from verified historical scores. This event provides freshness context but does not directly alter the tract risk score.
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
