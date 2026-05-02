"use client";

import { useRegionBreakdown } from "../lib/hooks";

type Props = { regionId: string };

export default function BreakdownCard({ regionId }: Props) {
  const { data, isLoading, isError } = useRegionBreakdown(regionId);

  if (isLoading || !data) {
    return (
      <div className="px-3 py-2 text-[9px] uppercase tracking-[1px]" style={{ color: "var(--cs-gray3)", fontFamily: "var(--cs-mono)" }}>
        {isError ? "BREAKDOWN UNAVAILABLE" : "LOADING BREAKDOWN…"}
      </div>
    );
  }

  const max = Math.max(1, ...data.categories.map((c) => c.count30d));

  return (
    <div className="px-3 py-2" style={{ fontFamily: "var(--cs-mono)" }}>
      <div className="flex items-baseline justify-between mb-2">
        <span className="text-[9px] font-bold tracking-[1px] uppercase" style={{ color: "var(--cs-gray2)" }}>
          NEXT {data.windowDays}D · CATEGORIES
        </span>
        <span className="text-[9px] tabular-nums" style={{ color: "var(--cs-text)" }}>
          ≈ {data.total30d} INCIDENTS
        </span>
      </div>
      <div className="space-y-1.5">
        {data.categories.map((c) => {
          const pct = (c.count30d / max) * 100;
          const trendColor =
            c.trendDirection === "rising"
              ? "var(--cs-red)"
              : c.trendDirection === "falling"
                ? "var(--cs-green)"
                : "var(--cs-gray2)";
          const trendGlyph = c.trendDirection === "rising" ? "▲" : c.trendDirection === "falling" ? "▼" : "→";
          return (
            <div key={c.category}>
              <div className="flex items-baseline justify-between mb-0.5">
                <span className="text-[10px]" style={{ color: "var(--cs-text)" }}>{c.label}</span>
                <span className="text-[9px] tabular-nums" style={{ color: "var(--cs-gray2)" }}>
                  {c.count30d}
                  <span className="ml-1.5" style={{ color: trendColor }}>
                    {trendGlyph} {c.trendPct > 0 ? "+" : ""}{c.trendPct.toFixed(1)}%
                  </span>
                </span>
              </div>
              <div className="h-1.5 w-full" style={{ background: "rgba(30,30,30,0.6)" }}>
                <div
                  className="h-full"
                  style={{
                    width: `${pct}%`,
                    background:
                      c.trendDirection === "rising"
                        ? "var(--cs-red)"
                        : c.trendDirection === "falling"
                          ? "var(--cs-green)"
                          : "var(--cs-cyan)",
                    opacity: 0.8,
                  }}
                />
              </div>
            </div>
          );
        })}
      </div>
      <p className="text-[8px] mt-2 leading-snug" style={{ color: "var(--cs-gray3)" }}>
        <span className="font-bold" style={{ color: "var(--cs-gray2)" }}>SOURCE: </span>
        {data.note}
      </p>
    </div>
  );
}
