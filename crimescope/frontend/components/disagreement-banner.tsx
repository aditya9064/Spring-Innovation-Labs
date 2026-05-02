"use client";

const STATUS_CONFIG: Record<string, { color: string; bg: string; border: string }> = {
  aligned: {
    color: "var(--cs-green)",
    bg: "rgba(0,200,100,0.06)",
    border: "rgba(0,200,100,0.2)",
  },
  watch: {
    color: "var(--cs-amber)",
    bg: "rgba(255,180,0,0.06)",
    border: "rgba(255,180,0,0.2)",
  },
  divergent: {
    color: "var(--cs-red)",
    bg: "rgba(255,60,60,0.08)",
    border: "rgba(255,60,60,0.25)",
  },
};

export default function DisagreementBanner({
  disagreement,
}: {
  disagreement: { status: string; summary: string; delta: number };
}) {
  const config = STATUS_CONFIG[disagreement.status] ?? STATUS_CONFIG.aligned;
  const isNeutral = disagreement.status === "aligned";

  return (
    <div
      style={{
        border: `1px solid ${config.border}`,
        background: config.bg,
        fontFamily: "var(--cs-mono)",
      }}
    >
      <div
        className="flex items-center justify-between px-2.5"
        style={{
          height: 24,
          borderBottom: `1px solid ${config.border}`,
        }}
      >
        <span className="flex items-center gap-1.5">
          <span
            className="inline-block w-1.5 h-1.5 rounded-full"
            style={{
              background: config.color,
              animation: isNeutral ? "none" : "cs-pulse 2s ease-in-out infinite",
            }}
          />
          <span
            className="text-[9px] font-bold uppercase tracking-[1.5px]"
            style={{ color: config.color }}
          >
            VERIFIED vs LIVE: {disagreement.status.toUpperCase()}
          </span>
        </span>

        {disagreement.delta !== 0 && (
          <span
            className="text-[10px] font-bold tracking-wide"
            style={{ color: config.color }}
          >
            {disagreement.delta > 0 ? "+" : ""}
            {disagreement.delta}% DELTA
          </span>
        )}
      </div>

      <div className="px-2.5 py-2">
        <p
          className="text-[10px] leading-relaxed"
          style={{ color: "var(--cs-gray1)" }}
        >
          {disagreement.summary}
        </p>
      </div>
    </div>
  );
}
