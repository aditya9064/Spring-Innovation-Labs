"use client";

import { useState, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAppStore } from "../lib/store";
import { getCity } from "../lib/cities";

type NominatimResult = {
  place_id: number;
  display_name: string;
  lat: string;
  lon: string;
};

const TIER_COLOR: Record<string, string> = {
  Critical: "#ef4444",
  High: "#f97316",
  Elevated: "#eab308",
  Moderate: "#3b82f6",
  Low: "#22c55e",
};

export default function LocationSearch() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<NominatimResult[]>([]);
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [noTract, setNoTract] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout>>(undefined);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const router = useRouter();

  const setFlyTo = useAppStore((s) => s.setFlyTo);
  const searchResult = useAppStore((s) => s.searchResult);
  const setSearchResult = useAppStore((s) => s.setSearchResult);
  const setReportTract = useAppStore((s) => s.setReportTract);
  const city = useAppStore((s) => s.city);
  const cityCfg = getCity(city);

  const geocode = useCallback(
    (value: string) => {
      if (timerRef.current) clearTimeout(timerRef.current);
      if (value.length < 3) {
        setResults([]);
        setOpen(false);
        return;
      }
      const [lngMin, latMin, lngMax, latMax] = cityCfg.searchBbox;
      timerRef.current = setTimeout(async () => {
        setBusy(true);
        try {
          const url =
            `https://nominatim.openstreetmap.org/search?` +
            `q=${encodeURIComponent(value + cityCfg.searchSuffix)}&format=json&limit=6` +
            `&viewbox=${lngMin},${latMin},${lngMax},${latMax}&bounded=1`;
          const res = await fetch(url);
          const data: NominatimResult[] = await res.json();
          setResults(data);
          setOpen(data.length > 0);
        } catch {
          setResults([]);
        }
        setBusy(false);
      }, 400);
    },
    [cityCfg.searchBbox, cityCfg.searchSuffix],
  );

  const handleChange = (value: string) => {
    setQuery(value);
    setSearchResult(null);
    setNoTract(false);
    geocode(value);
  };

  const handleSelect = (r: NominatimResult) => {
    const lng = parseFloat(r.lon);
    const lat = parseFloat(r.lat);
    const short = r.display_name.split(",").slice(0, 3).join(",").trim();
    setQuery(short);
    setOpen(false);
    setResults([]);
    setNoTract(false);
    setFlyTo({ lng, lat, zoom: cityCfg.searchZoom, address: short });
  };

  const handleClear = () => {
    setQuery("");
    setResults([]);
    setOpen(false);
    setSearchResult(null);
    setNoTract(false);
  };

  const handleViewReport = () => {
    if (searchResult) {
      setReportTract(searchResult.geoid);
      router.push("/reports");
    }
  };

  const handleNoTract = useCallback(() => {
    setNoTract(true);
  }, []);

  // Expose the no-tract callback for the map to use
  // We store it on the store indirectly via a global ref
  if (typeof window !== "undefined") {
    (window as unknown as Record<string, unknown>).__csOnNoTract = handleNoTract;
  }

  const tc = searchResult ? TIER_COLOR[searchResult.tier] || "#64748b" : "";

  return (
    <div
      ref={wrapperRef}
      className="absolute top-3 left-1/2 -translate-x-1/2"
      style={{ width: "min(440px, calc(100% - 120px))", fontFamily: "var(--cs-mono)", zIndex: 9999 }}
    >
      {/* Search Input */}
      <div
        style={{
          background: "rgba(0,0,0,0.92)",
          border: "1px solid var(--cs-border-hi)",
          backdropFilter: "blur(12px)",
        }}
      >
        <div className="flex items-center">
          <span
            className="text-[9px] font-bold tracking-[1px] uppercase pl-3 pr-1 shrink-0"
            style={{ color: "var(--cs-accent)" }}
          >
            SEARCH
          </span>
          <input
            type="text"
            placeholder="ADDRESS, PLACE, OR NEIGHBORHOOD..."
            value={query}
            onChange={(e) => handleChange(e.target.value)}
            onFocus={() => results.length > 0 && setOpen(true)}
            onKeyDown={(e) => {
              if (e.key === "Escape") {
                setOpen(false);
                (e.target as HTMLInputElement).blur();
              }
            }}
            className="flex-1 text-[11px] px-2 py-2.5 outline-none"
            style={{ background: "transparent", color: "var(--cs-text)" }}
          />
          {busy && (
            <div
              className="w-3 h-3 border border-[var(--cs-accent)] border-t-transparent rounded-full mr-2.5 shrink-0"
              style={{ animation: "cs-spin 0.6s linear infinite" }}
            />
          )}
          {query && !busy && (
            <button
              onClick={handleClear}
              className="text-[10px] mr-2.5 shrink-0 transition-colors"
              style={{ color: "var(--cs-gray2)" }}
              onMouseEnter={(e) => {
                e.currentTarget.style.color = "var(--cs-text)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.color = "var(--cs-gray2)";
              }}
            >
              ESC
            </button>
          )}
        </div>
      </div>

      {/* Dropdown Results */}
      {open && (
        <div
          style={{
            background: "rgba(0,0,0,0.96)",
            border: "1px solid var(--cs-border-hi)",
            borderTop: "none",
            maxHeight: 240,
            overflowY: "auto",
            position: "relative",
            zIndex: 10000,
          }}
        >
          {results.map((r) => (
            <button
              key={r.place_id}
              onClick={() => handleSelect(r)}
              className="w-full text-left px-3 py-2 text-[11px] flex items-start gap-2 transition-colors"
              style={{
                color: "var(--cs-gray1)",
                borderBottom: "1px solid rgba(30,30,30,0.5)",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = "var(--cs-panel2)";
                e.currentTarget.style.color = "var(--cs-text)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = "transparent";
                e.currentTarget.style.color = "var(--cs-gray1)";
              }}
            >
              <span className="shrink-0 mt-0.5" style={{ color: "var(--cs-accent)" }}>
                {">"}
              </span>
              <span className="leading-snug">{r.display_name}</span>
            </button>
          ))}
        </div>
      )}

      {/* Result Card — shown when map found a tract */}
      {searchResult && (
        <div
          className="mt-1.5"
          style={{
            background: "rgba(0,0,0,0.94)",
            border: "1px solid var(--cs-border-hi)",
            backdropFilter: "blur(12px)",
          }}
        >
          <div className="px-3 py-2.5">
            <div className="flex items-center justify-between mb-1.5">
              <span
                className="text-[11px] font-semibold truncate"
                style={{ color: "var(--cs-text)" }}
              >
                {searchResult.address}
              </span>
              <button
                onClick={handleClear}
                className="text-xs ml-2 shrink-0 transition-colors"
                style={{ color: "var(--cs-gray2)" }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.color = "var(--cs-text)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.color = "var(--cs-gray2)";
                }}
              >
                ✕
              </button>
            </div>
            <div
              className="text-[10px] mb-2.5"
              style={{ color: "var(--cs-gray2)" }}
            >
              {cityCfg.geographyUnit.toUpperCase()} {searchResult.geoid} · {searchResult.name}
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span
                  className="text-[9px] font-bold px-1.5 py-0.5 uppercase tracking-wide"
                  style={{
                    color: "var(--cs-text)",
                    background: "var(--cs-panel2)",
                    border: "1px solid var(--cs-border-hi)",
                  }}
                >
                  SCORE {searchResult.score}
                </span>
                <span
                  className="text-[9px] font-bold px-1.5 py-0.5 uppercase tracking-wide"
                  style={{
                    color: tc,
                    background: `${tc}15`,
                    border: `1px solid ${tc}33`,
                  }}
                >
                  {searchResult.tier}
                </span>
              </div>
              <button
                onClick={handleViewReport}
                className="text-[9px] font-bold px-2.5 py-1 uppercase tracking-wide transition-colors"
                style={{ background: "var(--cs-accent)", color: "#000" }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = "#60a5fa";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = "var(--cs-accent)";
                }}
              >
                VIEW FULL REPORT →
              </button>
            </div>
          </div>
        </div>
      )}

      {/* No tract found message */}
      {noTract && !searchResult && (
        <div
          className="mt-1.5 px-3 py-2.5 text-[10px]"
          style={{
            background: "rgba(0,0,0,0.94)",
            border: "1px solid var(--cs-border-hi)",
            color: "var(--cs-gray2)",
          }}
        >
          {cityCfg.searchEmptyMessage}
          <br />
          <span style={{ color: "var(--cs-gray3)" }}>
            Try a different address within {cityCfg.scopeLabel}.
          </span>
        </div>
      )}
    </div>
  );
}
