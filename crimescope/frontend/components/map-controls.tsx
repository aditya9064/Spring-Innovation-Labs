"use client";

import { useAppStore, type MapLayers } from "../lib/store";

const TIERS = ["Critical", "High", "Elevated", "Moderate", "Low"] as const;
const TIER_COLOR: Record<string, string> = {
  Critical: "var(--cs-red)",
  High: "var(--cs-orange)",
  Elevated: "var(--cs-yellow)",
  Moderate: "var(--cs-accent)",
  Low: "var(--cs-green)",
};

const LAYER_LABELS: { key: keyof MapLayers; label: string }[] = [
  { key: "heatmap", label: "HEATMAP" },
  { key: "buildings", label: "3D BLDGS" },
  { key: "boundaries", label: "BORDERS" },
  { key: "glow", label: "GLOW" },
];

export default function MapControls() {
  const tierFilter = useAppStore((s) => s.tierFilter);
  const setTierFilter = useAppStore((s) => s.setTierFilter);
  const mapLayers = useAppStore((s) => s.mapLayers);
  const toggleMapLayer = useAppStore((s) => s.toggleMapLayer);

  const toggleTier = (tier: string) => {
    const next = new Set(tierFilter);
    if (next.has(tier)) {
      if (next.size > 1) next.delete(tier);
    } else {
      next.add(tier);
    }
    setTierFilter(next);
  };

  const allSelected = tierFilter.size === TIERS.length;

  return (
    <div
      className="absolute top-3 right-3 z-10 flex flex-col gap-1.5"
      style={{ fontFamily: "var(--cs-mono)" }}
    >
      {/* Risk Tier Filter */}
      <div
        className="px-2.5 py-2"
        style={{
          background: "rgba(0,0,0,0.88)",
          border: "1px solid var(--cs-border-hi)",
        }}
      >
        <div className="flex items-center justify-between mb-1.5">
          <span
            className="text-[8px] font-bold uppercase tracking-[1px]"
            style={{ color: "var(--cs-accent)" }}
          >
            FILTER TIERS
          </span>
          <button
            onClick={() =>
              setTierFilter(
                allSelected
                  ? new Set(["Critical", "High"])
                  : new Set(TIERS),
              )
            }
            className="text-[8px] uppercase tracking-wide"
            style={{ color: "var(--cs-gray2)" }}
          >
            {allSelected ? "HIGH ONLY" : "ALL"}
          </button>
        </div>
        {TIERS.map((tier) => {
          const active = tierFilter.has(tier);
          return (
            <button
              key={tier}
              onClick={() => toggleTier(tier)}
              className="flex items-center gap-1.5 w-full py-0.5"
            >
              <span
                className="w-2.5 h-2.5 shrink-0 flex items-center justify-center text-[7px]"
                style={{
                  background: active ? TIER_COLOR[tier] : "transparent",
                  border: `1px solid ${TIER_COLOR[tier]}`,
                  color: active ? "#000" : TIER_COLOR[tier],
                }}
              >
                {active ? "✓" : ""}
              </span>
              <span
                className="text-[9px] tracking-wide"
                style={{
                  color: active ? "var(--cs-gray1)" : "var(--cs-gray3)",
                }}
              >
                {tier.toUpperCase()}
              </span>
            </button>
          );
        })}
      </div>

      {/* Map Layers */}
      <div
        className="px-2.5 py-2"
        style={{
          background: "rgba(0,0,0,0.88)",
          border: "1px solid var(--cs-border-hi)",
        }}
      >
        <span
          className="text-[8px] font-bold uppercase tracking-[1px] mb-1.5 block"
          style={{ color: "var(--cs-accent)" }}
        >
          LAYERS
        </span>
        {LAYER_LABELS.map(({ key, label }) => {
          const active = mapLayers[key];
          return (
            <button
              key={key}
              onClick={() => toggleMapLayer(key)}
              className="flex items-center gap-1.5 w-full py-0.5"
            >
              <span
                className="w-2.5 h-2.5 shrink-0 flex items-center justify-center text-[7px]"
                style={{
                  background: active ? "var(--cs-accent)" : "transparent",
                  border: `1px solid ${active ? "var(--cs-accent)" : "var(--cs-gray3)"}`,
                  color: active ? "#000" : "var(--cs-gray3)",
                }}
              >
                {active ? "✓" : ""}
              </span>
              <span
                className="text-[9px] tracking-wide"
                style={{
                  color: active ? "var(--cs-gray1)" : "var(--cs-gray3)",
                }}
              >
                {label}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
