"use client";

import { useMemo } from "react";
import {
  Area,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useRegionTrend } from "../lib/hooks";

type Props = {
  regionId: string;
  horizonDays?: number;
  metric?: "incident_rate" | "risk_score";
  /** Show the methodology line under the chart. Defaults to true. */
  showMethod?: boolean;
};

/**
 * Real per-region trend + forecast chart, fed by `/api/regions/trend`.
 *
 * The history line is rendered as a solid line; the forecast is shown as a
 * dashed line with an 80% confidence band drawn behind it.
 */
export default function RegionTrendChart({
  regionId,
  horizonDays = 30,
  metric = "incident_rate",
  showMethod = true,
}: Props) {
  const { data, isLoading, isError } = useRegionTrend(regionId, { horizonDays, metric });

  const series = useMemo(() => {
    if (!data) return [];
    const out: {
      date: string;
      history?: number;
      forecast?: number;
      lo?: number;
      hi?: number;
      band?: [number, number];
    }[] = [];
    for (const p of data.history) {
      out.push({ date: p.date.slice(0, 7), history: p.value });
    }
    // Bridge: repeat last history point as forecast start so the dashed line touches.
    if (data.history.length > 0 && data.forecast.length > 0) {
      const last = data.history[data.history.length - 1];
      out.push({ date: last.date.slice(0, 7), forecast: last.value, lo: last.value, hi: last.value });
    }
    for (const p of data.forecast) {
      out.push({
        date: p.date.slice(0, 7),
        forecast: p.value,
        lo: p.lo,
        hi: p.hi,
        band: [p.lo, p.hi],
      });
    }
    return out;
  }, [data]);

  const yLabel = metric === "risk_score" ? "Risk score" : "Incidents / month";
  const direction = data?.trendDirection ?? "stable";
  const directionColor =
    direction === "rising" ? "var(--cs-red)" : direction === "falling" ? "var(--cs-green)" : "var(--cs-gray2)";
  const directionGlyph = direction === "rising" ? "▲" : direction === "falling" ? "▼" : "→";

  return (
    <div className="flex flex-col h-full" style={{ fontFamily: "var(--cs-mono)" }}>
      <div className="flex items-center justify-between px-3 pt-1 pb-1.5 shrink-0">
        <div className="flex items-baseline gap-3">
          <span className="text-[8px] font-bold tracking-[1px] uppercase" style={{ color: "var(--cs-gray2)" }}>
            {yLabel} · 12mo HISTORY → {horizonDays}d FORECAST
          </span>
          <span className="text-[9px] font-bold uppercase tracking-wide" style={{ color: directionColor }}>
            {directionGlyph} {direction}
          </span>
        </div>
        {data && (
          <span className="text-[9px]" style={{ color: "var(--cs-gray2)" }}>
            EXPECTED: <span style={{ color: "var(--cs-text)" }}>{data.next30dExpected.toFixed(1)}</span>{" "}
            <span style={{ color: "var(--cs-gray3)" }}>[{data.next30dLo.toFixed(1)}–{data.next30dHi.toFixed(1)}]</span>
          </span>
        )}
      </div>

      <div className="flex-1 min-h-0">
        {isLoading || !data ? (
          <div className="h-full flex items-center justify-center text-[9px] uppercase tracking-[1px]" style={{ color: "var(--cs-gray3)" }}>
            {isError ? "TREND UNAVAILABLE" : "LOADING TREND…"}
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={series} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
              <defs>
                <linearGradient id="forecastBand" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#3b82f6" stopOpacity={0.28} />
                  <stop offset="100%" stopColor="#3b82f6" stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="date" tick={{ fontSize: 8, fill: "#64748b" }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 8, fill: "#64748b" }} axisLine={false} tickLine={false} />
              <Tooltip
                contentStyle={{
                  background: "rgba(0,0,0,0.92)",
                  border: "1px solid #1e1e1e",
                  fontSize: 10,
                  fontFamily: "var(--cs-mono)",
                  color: "#e5e7eb",
                }}
                formatter={(v: unknown, name) => {
                  if (Array.isArray(v)) {
                    const [lo, hi] = v as [number, number];
                    return [`${lo.toFixed(2)} – ${hi.toFixed(2)}`, "80% band"];
                  }
                  return [typeof v === "number" ? v.toFixed(2) : String(v), name];
                }}
              />
              <Legend wrapperStyle={{ fontSize: 9, color: "#94a3b8" }} iconSize={8} />
              <Area
                type="monotone"
                dataKey="band"
                stroke="none"
                fill="url(#forecastBand)"
                isAnimationActive={false}
                name="80% band"
              />
              <Line
                type="monotone"
                dataKey="history"
                stroke="#3b82f6"
                strokeWidth={1.6}
                dot={false}
                isAnimationActive={false}
                name="History"
                connectNulls={false}
              />
              <Line
                type="monotone"
                dataKey="forecast"
                stroke="#3b82f6"
                strokeDasharray="3 3"
                strokeWidth={1.6}
                dot={false}
                isAnimationActive={false}
                name="Forecast"
                connectNulls={false}
              />
            </ComposedChart>
          </ResponsiveContainer>
        )}
      </div>

      {showMethod && data && (
        <div className="px-3 pt-1 pb-1.5 shrink-0">
          <p className="text-[8px] leading-snug" style={{ color: "var(--cs-gray3)" }}>
            <span className="font-bold" style={{ color: "var(--cs-gray2)" }}>METHOD: </span>
            {data.method}
          </p>
        </div>
      )}
    </div>
  );
}
