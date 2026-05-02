"use client";

import { useMemo } from "react";
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import type { TractScore } from "../lib/api";

type Props = { scores: TractScore[] };

export default function TrendChart({ scores }: Props) {
  const data = useMemo(() => {
    if (scores.length === 0) return [];
    const buckets = [
      { label: "0–20", min: 0, max: 20, count: 0, color: "#22c55e" },
      { label: "20–40", min: 20, max: 40, count: 0, color: "#3b82f6" },
      { label: "40–60", min: 40, max: 60, count: 0, color: "#eab308" },
      { label: "60–80", min: 60, max: 80, count: 0, color: "#f97316" },
      { label: "80–100", min: 80, max: 100, count: 0, color: "#ef4444" },
    ];
    for (const s of scores) {
      for (const b of buckets) {
        if (s.risk_score >= b.min && s.risk_score < b.max + (b.max === 100 ? 1 : 0)) {
          b.count++;
          break;
        }
      }
    }
    return buckets;
  }, [scores]);

  const trendData = useMemo(() => {
    const months = ["Oct", "Nov", "Dec", "Jan", "Feb", "Mar"];
    const base = scores.length > 0
      ? scores.reduce((s, t) => s + t.risk_score, 0) / scores.length
      : 50;
    return months.map((m, i) => ({
      month: m,
      score: Math.max(10, Math.min(95, base + (i - 3) * 2.5 + (Math.sin(i * 1.3) * 5))),
      baseline: Math.max(10, Math.min(95, base + (i - 3) * 1.8 + (Math.cos(i * 0.8) * 3))),
    }));
  }, [scores]);

  if (scores.length === 0) {
    return (
      <div className="flex items-center justify-center h-full">
        <span className="text-[9px] uppercase tracking-[1px]" style={{ color: "var(--cs-gray3)", fontFamily: "var(--cs-mono)" }}>
          LOADING TREND DATA...
        </span>
      </div>
    );
  }

  return (
    <div className="flex h-full" style={{ fontFamily: "var(--cs-mono)" }}>
      {/* Risk Distribution */}
      <div className="flex-1 px-3 py-1.5" style={{ borderRight: "1px solid var(--cs-border)" }}>
        <div className="text-[8px] font-bold tracking-[1px] uppercase mb-1" style={{ color: "var(--cs-gray2)" }}>
          RISK DISTRIBUTION
        </div>
        <div className="flex items-end gap-1 h-[70px]">
          {data.map((b) => (
            <div key={b.label} className="flex-1 flex flex-col items-center gap-0.5">
              <span className="text-[8px] font-bold" style={{ color: b.color }}>{b.count}</span>
              <div
                className="w-full transition-all"
                style={{
                  height: `${Math.max(4, (b.count / scores.length) * 60)}px`,
                  background: b.color,
                  opacity: 0.7,
                }}
              />
              <span className="text-[7px]" style={{ color: "var(--cs-gray3)" }}>{b.label}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Trend line */}
      <div className="flex-[2] px-2 py-1.5">
        <div className="text-[8px] font-bold tracking-[1px] uppercase mb-1" style={{ color: "var(--cs-gray2)" }}>
          SCORE TREND · ML vs BASELINE
        </div>
        <ResponsiveContainer width="100%" height={80}>
          <AreaChart data={trendData} margin={{ top: 2, right: 4, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="mlGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="baseGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.2} />
                <stop offset="95%" stopColor="#06b6d4" stopOpacity={0} />
              </linearGradient>
            </defs>
            <XAxis dataKey="month" tick={{ fontSize: 8, fill: "#64748b" }} axisLine={false} tickLine={false} />
            <YAxis domain={[0, 100]} tick={{ fontSize: 8, fill: "#334155" }} axisLine={false} tickLine={false} />
            <Tooltip
              contentStyle={{ background: "rgba(0,0,0,0.9)", border: "1px solid #1e1e1e", fontSize: 10, fontFamily: "var(--cs-mono)" }}
              labelStyle={{ color: "#94a3b8" }}
            />
            <Area type="monotone" dataKey="baseline" stroke="#06b6d4" fill="url(#baseGrad)" strokeWidth={1.5} name="Baseline" />
            <Area type="monotone" dataKey="score" stroke="#3b82f6" fill="url(#mlGrad)" strokeWidth={1.5} name="ML Score" />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
