"use client";

import { useState } from "react";

export default function WhatChangedCard({
  whatChanged,
}: {
  whatChanged: { summary: string; topChanges: string[] };
}) {
  const [expanded, setExpanded] = useState(true);

  return (
    <div
      style={{
        border: "1px solid var(--cs-border)",
        background: "var(--cs-panel)",
        fontFamily: "var(--cs-mono)",
      }}
    >
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-2.5"
        style={{
          height: 24,
          borderBottom: expanded ? "1px solid var(--cs-border)" : "none",
          background: "var(--cs-panel2)",
        }}
      >
        <span
          className="text-[9px] font-bold uppercase tracking-[1.5px]"
          style={{ color: "var(--cs-accent)" }}
        >
          WHAT CHANGED & WHY
        </span>
        <span
          className="text-[10px]"
          style={{ color: "var(--cs-gray2)" }}
        >
          {expanded ? "▾" : "▸"}
        </span>
      </button>

      {expanded && (
        <div className="px-2.5 py-2 space-y-2">
          <p
            className="text-[10px] leading-relaxed font-medium"
            style={{ color: "var(--cs-text)" }}
          >
            {whatChanged.summary}
          </p>

          {whatChanged.topChanges.length > 0 && (
            <div className="space-y-1.5">
              {whatChanged.topChanges.map((change, i) => (
                <div key={i} className="flex gap-2">
                  <span
                    className="text-[9px] font-bold shrink-0 mt-0.5"
                    style={{ color: "var(--cs-accent)" }}
                  >
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  <span
                    className="text-[10px] leading-relaxed"
                    style={{ color: "var(--cs-gray1)" }}
                  >
                    {change}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
