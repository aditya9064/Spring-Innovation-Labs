"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAppStore } from "../lib/store";
import type { TractScore } from "../lib/api";

const TIER_COLOR: Record<string, string> = {
  Critical: "var(--cs-red)",
  High: "var(--cs-orange)",
  Elevated: "var(--cs-yellow)",
  Moderate: "var(--cs-accent)",
  Low: "var(--cs-green)",
};

export function TractPanel({
  scores,
  loading,
}: {
  scores: TractScore[];
  loading: boolean;
}) {
  const setSelectedTract = useAppStore((s) => s.setSelectedTract);
  const selectedTract = useAppStore((s) => s.selectedTract);
  const setCompareLeft = useAppStore((s) => s.setCompareLeft);
  const setCompareRight = useAppStore((s) => s.setCompareRight);
  const setReportTract = useAppStore((s) => s.setReportTract);
  const router = useRouter();
  const [query, setQuery] = useState("");

  const filtered = query
    ? scores.filter(
        (s) =>
          (s.name || s.tract_geoid)
            .toLowerCase()
            .includes(query.toLowerCase()) ||
          s.risk_tier.toLowerCase().startsWith(query.toLowerCase()),
      )
    : scores;

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="flex flex-col items-center gap-2">
          <div
            className="w-5 h-5 border-2 rounded-full"
            style={{
              borderColor: "var(--cs-accent)",
              borderTopColor: "transparent",
              animation: "cs-spin 0.8s linear infinite",
            }}
          />
          <span
            className="text-[10px] uppercase tracking-[1px]"
            style={{ color: "var(--cs-gray2)", fontFamily: "var(--cs-mono)" }}
          >
            LOADING DATA...
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col flex-1 min-h-0">
      {/* Search Input */}
      <div
        className="px-2.5 py-2 shrink-0"
        style={{
          background: "var(--cs-panel)",
          borderBottom: "1px solid var(--cs-border)",
        }}
      >
        <input
          type="text"
          placeholder="FILTER TRACTS..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="w-full text-[11px] px-2 py-1 outline-none"
          style={{
            background: "var(--cs-panel2)",
            border: "1px solid var(--cs-border)",
            color: "var(--cs-text)",
            fontFamily: "var(--cs-mono)",
          }}
        />
        <div className="flex items-center justify-between mt-1.5">
          <span
            className="text-[8px] font-bold uppercase tracking-[1px]"
            style={{ color: "var(--cs-accent)", fontFamily: "var(--cs-mono)" }}
          >
            RANKED BY RISK
          </span>
          <span
            className="text-[9px] tabular-nums"
            style={{ color: "var(--cs-gray2)", fontFamily: "var(--cs-mono)" }}
          >
            {filtered.length === scores.length
              ? scores.length
              : `${filtered.length}/${scores.length}`}
          </span>
        </div>
      </div>

      {/* Tract List */}
      <div className="flex-1 overflow-y-auto">
        {filtered.map((s) => {
          const active = selectedTract === s.tract_geoid;
          return (
            <button
              key={s.tract_geoid}
              onClick={() => setSelectedTract(s.tract_geoid)}
              className="w-full flex items-center gap-2 px-2.5 py-1.5 text-left transition-colors"
              style={{
                background: active ? "var(--cs-panel2)" : "transparent",
                borderBottom: "1px solid rgba(30,30,30,0.5)",
                borderLeft: active ? "2px solid var(--cs-accent)" : "2px solid transparent",
              }}
            >
              {/* Score badge */}
              <div
                className="w-8 h-8 flex items-center justify-center text-[11px] font-bold tabular-nums shrink-0"
                style={{
                  border: `1px solid ${TIER_COLOR[s.risk_tier] || "var(--cs-gray3)"}33`,
                  background: `${TIER_COLOR[s.risk_tier] || "var(--cs-gray3)"}0d`,
                  color: TIER_COLOR[s.risk_tier] || "var(--cs-gray2)",
                  fontFamily: "var(--cs-mono)",
                }}
              >
                {Math.round(s.risk_score)}
              </div>
              {/* Name + meta */}
              <div className="flex-1 min-w-0">
                <div
                  className="text-[11px] font-medium truncate leading-tight"
                  style={{ color: "var(--cs-text)" }}
                >
                  {s.name || `Tract ${s.tract_geoid.slice(-6)}`}
                </div>
                <div
                  className="text-[9px] mt-px tabular-nums"
                  style={{ color: "var(--cs-gray2)", fontFamily: "var(--cs-mono)" }}
                >
                  {s.predicted_next_30d.toFixed(0)} pred · {s.incident_count} recent
                </div>
              </div>
              {/* Tier + trend + actions */}
              <div className="flex flex-col items-end gap-0.5 shrink-0">
                <span
                  className="text-[9px] font-bold uppercase tracking-wide"
                  style={{
                    color: TIER_COLOR[s.risk_tier] || "var(--cs-gray2)",
                    fontFamily: "var(--cs-mono)",
                  }}
                >
                  {s.risk_tier}
                </span>
                {s.trend_direction && (
                  <span
                    className="text-[8px]"
                    style={{
                      color:
                        s.trend_direction === "rising"
                          ? "var(--cs-red)"
                          : s.trend_direction === "falling"
                            ? "var(--cs-green)"
                            : "var(--cs-gray2)",
                      fontFamily: "var(--cs-mono)",
                    }}
                  >
                    {s.trend_direction === "rising"
                      ? "▲ RISING"
                      : s.trend_direction === "falling"
                        ? "▼ FALLING"
                        : "→ STABLE"}
                  </span>
                )}
                {active && (
                  <div className="flex gap-1 mt-0.5">
                    <span
                      onClick={(e) => { e.stopPropagation(); setReportTract(s.tract_geoid); router.push("/reports"); }}
                      className="text-[7px] px-1 py-0.5 cursor-pointer"
                      style={{ background: "var(--cs-accent-lo)", color: "var(--cs-accent)", border: "1px solid var(--cs-accent-md)" }}
                    >
                      RPT
                    </span>
                    <span
                      onClick={(e) => { e.stopPropagation(); setCompareLeft(s.tract_geoid); router.push("/compare"); }}
                      className="text-[7px] px-1 py-0.5 cursor-pointer"
                      style={{ background: "var(--cs-accent-lo)", color: "var(--cs-accent)", border: "1px solid var(--cs-accent-md)" }}
                    >
                      CMP
                    </span>
                  </div>
                )}
              </div>
            </button>
          );
        })}

        {filtered.length === 0 && (
          <div
            className="text-center py-8 text-[11px] uppercase tracking-[1px]"
            style={{ color: "var(--cs-gray3)", fontFamily: "var(--cs-mono)" }}
          >
            NO MATCHING TRACTS
          </div>
        )}
      </div>
    </div>
  );
}
