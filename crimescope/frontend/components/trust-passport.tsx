"use client";

import type { TrustPassport as TrustPassportType } from "../lib/contracts";

const LEVEL_COLORS: Record<string, string> = {
  high: "var(--cs-green)",
  strong: "var(--cs-green)",
  live: "var(--cs-green)",
  recent: "var(--cs-green)",
  low: "var(--cs-green)",
  moderate: "var(--cs-amber)",
  mixed: "var(--cs-amber)",
  stale: "var(--cs-red)",
  weak: "var(--cs-red)",
  unknown: "var(--cs-gray2)",
};

const LEVEL_DOTS: Record<string, number> = {
  high: 3, strong: 3, live: 3,
  recent: 2, moderate: 2, mixed: 2,
  low: 1, weak: 1, stale: 1,
  unknown: 0,
};

const FIELDS: { key: keyof TrustPassportType; label: string }[] = [
  { key: "confidence", label: "CONFIDENCE" },
  { key: "completeness", label: "COMPLETENESS" },
  { key: "freshness", label: "FRESHNESS" },
  { key: "sourceAgreement", label: "SOURCE AGREE" },
  { key: "underreportingRisk", label: "UNDERREPORT" },
];

function TrustDots({ value }: { value: string }) {
  const count = LEVEL_DOTS[value] ?? 0;
  const color = LEVEL_COLORS[value] ?? "var(--cs-gray2)";

  return (
    <span className="flex items-center gap-0.5">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="w-1.5 h-1.5 rounded-full"
          style={{
            background: i < count ? color : "var(--cs-border)",
          }}
        />
      ))}
    </span>
  );
}

function UnderreportDots({ value }: { value: string }) {
  const invertedColors: Record<string, string> = {
    low: "var(--cs-green)",
    moderate: "var(--cs-amber)",
    high: "var(--cs-red)",
  };
  const color = invertedColors[value] ?? "var(--cs-gray2)";
  const count = value === "high" ? 3 : value === "moderate" ? 2 : 1;

  return (
    <span className="flex items-center gap-0.5">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="w-1.5 h-1.5 rounded-full"
          style={{
            background: i < count ? color : "var(--cs-border)",
          }}
        />
      ))}
    </span>
  );
}

export default function TrustPassportCard({
  passport,
  compact,
}: {
  passport: TrustPassportType;
  compact?: boolean;
}) {
  const actionColor =
    passport.action === "standard processing"
      ? "var(--cs-green)"
      : passport.action === "conditional accept"
        ? "var(--cs-amber)"
        : "var(--cs-red)";

  return (
    <div
      style={{
        border: "1px solid var(--cs-border)",
        background: "var(--cs-panel)",
        fontFamily: "var(--cs-mono)",
      }}
    >
      <div
        className="flex items-center justify-between px-2.5"
        style={{
          height: 24,
          borderBottom: "1px solid var(--cs-border)",
          background: "var(--cs-panel2)",
        }}
      >
        <span
          className="text-[9px] font-bold uppercase tracking-[1.5px]"
          style={{ color: "var(--cs-accent)" }}
        >
          TRUST PASSPORT
        </span>
        <span
          className="text-[8px] font-bold uppercase tracking-[1px] px-1.5 py-0.5"
          style={{
            background: actionColor,
            color: "#000",
          }}
        >
          {passport.action}
        </span>
      </div>

      <div className="px-2.5 py-2 space-y-1.5">
        {FIELDS.map(({ key, label }) => {
          const value = passport[key];

          return (
            <div key={key} className="flex items-center justify-between">
              <span
                className="text-[9px] uppercase tracking-[0.8px]"
                style={{ color: "var(--cs-gray2)" }}
              >
                {label}
              </span>
              <span className="flex items-center gap-2">
                <span
                  className="text-[10px] font-medium uppercase tracking-wide"
                  style={{
                    color:
                      key === "underreportingRisk"
                        ? (value === "high"
                            ? "var(--cs-red)"
                            : value === "moderate"
                              ? "var(--cs-amber)"
                              : "var(--cs-green)")
                        : (LEVEL_COLORS[value] ?? "var(--cs-gray2)"),
                  }}
                >
                  {value}
                </span>
                {key === "underreportingRisk" ? (
                  <UnderreportDots value={value} />
                ) : (
                  <TrustDots value={value} />
                )}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
