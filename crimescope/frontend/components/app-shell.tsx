"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { useAppStore, type Persona, type ViewMode } from "../lib/store";
import { ALL_CITIES, getCity, type CityId } from "../lib/cities";
import ProvenanceDrawer from "./provenance-drawer";

const NAV_ITEMS = [
  { label: "DASH", href: "/", icon: "◈" },
  { label: "LIVE", href: "/live", icon: "◉" },
  { label: "COMPARE", href: "/compare", icon: "⇔" },
  { label: "SIM", href: "/simulator", icon: "△" },
  { label: "REPORT", href: "/reports", icon: "▤" },
  { label: "ALERTS", href: "/alerts", icon: "⚠" },
  { label: "BLIND", href: "/blindspots", icon: "◐" },
  { label: "AUDIT", href: "/audit", icon: "≡" },
  { label: "ANALYST", href: "/analyst", icon: "✦" },
] as const;

const PERSONAS: { id: Persona; label: string; short: string }[] = [
  { id: "insurer", label: "INSURER", short: "INS" },
  { id: "resident", label: "RESIDENT", short: "RES" },
  { id: "buyer", label: "BUYER", short: "BUY" },
  { id: "business", label: "BUSINESS", short: "BIZ" },
  { id: "planner", label: "PLANNER", short: "PLN" },
];

// Visible per-persona framing — surfaced in a slim context bar so the
// topbar PERSONA toggle has an immediate, global, non-layout-dependent
// effect on the UI.
const PERSONA_CONTEXT: Record<Persona, { headline: string; framing: string; tone: string }> = {
  insurer: {
    headline: "UNDERWRITER VIEW",
    framing: "Pricing-first · premium multiplier · decline thresholds",
    tone: "var(--cs-amber)",
  },
  resident: {
    headline: "RESIDENT VIEW",
    framing: "Household safety · contents/home risk · recommended actions",
    tone: "var(--cs-green)",
  },
  buyer: {
    headline: "BUYER / REAL-ESTATE VIEW",
    framing: "Investment stability · 12-month trend · comparable areas",
    tone: "var(--cs-cyan)",
  },
  business: {
    headline: "BUSINESS OPERATOR VIEW",
    framing: "Commercial exposure · continuity loading · site risk",
    tone: "var(--cs-orange)",
  },
  planner: {
    headline: "URBAN PLANNER VIEW",
    framing: "Intervention priority · underreporting risk · blind spots",
    tone: "var(--cs-accent)",
  },
};

const MODES: { id: ViewMode; label: string; color: string }[] = [
  { id: "verified", label: "VERIFIED", color: "var(--cs-green)" },
  { id: "blended", label: "BLENDED", color: "var(--cs-accent)" },
  { id: "live", label: "LIVE", color: "var(--cs-amber)" },
];

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [time, setTime] = useState("");
  const chatOpen = useAppStore((s) => s.chatOpen);
  const setChatOpen = useAppStore((s) => s.setChatOpen);
  const persona = useAppStore((s) => s.persona);
  const setPersona = useAppStore((s) => s.setPersona);
  const viewMode = useAppStore((s) => s.viewMode);
  const setViewMode = useAppStore((s) => s.setViewMode);
  const city = useAppStore((s) => s.city);
  const setCity = useAppStore((s) => s.setCity);
  const cityCfg = getCity(city);

  useEffect(() => {
    const tick = () =>
      setTime(
        new Date().toLocaleTimeString("en-US", {
          hour12: false,
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        }),
      );
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="flex flex-col h-screen overflow-hidden" style={{ background: "var(--cs-bg)" }}>
      {/* Top Bar */}
      <div
        className="flex items-center justify-between px-3.5 shrink-0"
        style={{ height: 32, background: "var(--cs-accent)", fontFamily: "var(--cs-mono)" }}
      >
        <div className="flex items-center gap-3">
          <span className="text-[13px] font-bold tracking-[2px] text-black">CRIMESCOPE</span>
          <select
            value={city}
            onChange={(e) => setCity(e.target.value as CityId)}
            className="text-[10px] font-semibold text-black/60 tracking-wide bg-transparent outline-none cursor-pointer"
            style={{ border: "none" }}
            aria-label="City selector"
          >
            {ALL_CITIES.map((c) => (
              <option key={c.id} value={c.id} style={{ background: "#000", color: "#fff" }}>
                {c.label}
              </option>
            ))}
          </select>
          <span className="text-[9px] font-bold text-black/40 tracking-[1px] hidden lg:inline">
            · {cityCfg.geographyUnitPlural.toUpperCase()}
          </span>
        </div>
        <span className="text-[11px] font-bold tracking-[1px] text-black" suppressHydrationWarning>
          {time || "--:--:--"}
        </span>
      </div>

      {/* Context Bar: Persona + Mode */}
      <div
        className="flex items-center gap-1 px-3.5 shrink-0"
        style={{
          height: 28,
          background: "var(--cs-panel)",
          borderBottom: "1px solid var(--cs-border)",
          fontFamily: "var(--cs-mono)",
        }}
      >
        {/* Persona selector */}
        <div className="flex items-center gap-0.5 mr-3">
          <span className="text-[8px] font-bold tracking-[1px] mr-1.5" style={{ color: "var(--cs-gray2)" }}>PERSONA</span>
          {PERSONAS.map((p) => (
            <button
              key={p.id}
              onClick={() => setPersona(p.id)}
              className="text-[9px] font-bold px-1.5 py-0.5 tracking-wide transition-colors"
              style={{
                background: persona === p.id ? "var(--cs-accent)" : "transparent",
                color: persona === p.id ? "#000" : "var(--cs-gray2)",
                border: `1px solid ${persona === p.id ? "var(--cs-accent)" : "var(--cs-border)"}`,
              }}
            >
              {p.short}
            </button>
          ))}
        </div>

        <div className="w-px h-4 mx-1" style={{ background: "var(--cs-border)" }} />

        {/* Mode toggle */}
        <div className="flex items-center gap-0.5">
          {MODES.map((m) => (
            <button
              key={m.id}
              onClick={() => setViewMode(m.id)}
              className="text-[9px] font-bold px-1.5 py-0.5 tracking-wide transition-colors"
              style={{
                background: viewMode === m.id ? m.color : "transparent",
                color: viewMode === m.id ? "#000" : "var(--cs-gray2)",
                border: `1px solid ${viewMode === m.id ? m.color : "var(--cs-border)"}`,
              }}
            >
              {m.label}
            </button>
          ))}
        </div>

        <div className="flex-1" />

        <button
          onClick={() => setChatOpen(!chatOpen)}
          className="text-[9px] font-bold px-2 py-0.5 tracking-wide transition-colors"
          style={{
            background: chatOpen ? "var(--cs-amber)" : "var(--cs-panel2)",
            color: chatOpen ? "#000" : "var(--cs-gray1)",
            border: "1px solid var(--cs-border)",
          }}
        >
          AI ANALYST
        </button>
      </div>

      {/* Persona context bar — visible global signal that PERSONA changed.
          Renders the persona's headline + one-line framing on every page. */}
      <div
        className="flex items-center px-3.5 shrink-0"
        style={{
          height: 22,
          background: "var(--cs-bg)",
          borderBottom: "1px solid var(--cs-border)",
          fontFamily: "var(--cs-mono)",
        }}
      >
        <span
          className="text-[8px] font-bold tracking-[1px] px-1.5 py-0.5 mr-2"
          style={{
            background: PERSONA_CONTEXT[persona].tone,
            color: "#000",
          }}
        >
          {PERSONA_CONTEXT[persona].headline}
        </span>
        <span
          className="text-[9px] tracking-wide truncate"
          style={{ color: "var(--cs-gray1)" }}
        >
          {PERSONA_CONTEXT[persona].framing}
        </span>
      </div>

      {/* Main area: Left Nav Rail + Content */}
      <div className="flex flex-1 min-h-0 overflow-hidden">
        {/* Left Navigation Rail */}
        <nav
          className="flex flex-col shrink-0 cs-no-print"
          style={{
            width: 52,
            background: "var(--cs-panel)",
            borderRight: "1px solid var(--cs-border)",
            fontFamily: "var(--cs-mono)",
          }}
        >
          {NAV_ITEMS.map((item) => {
            const active = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));
            return (
              <Link
                key={item.href}
                href={item.href}
                className="flex flex-col items-center justify-center py-2 transition-colors group relative"
                style={{
                  background: active ? "var(--cs-accent-lo)" : "transparent",
                  borderLeft: active ? "2px solid var(--cs-accent)" : "2px solid transparent",
                  borderBottom: "1px solid var(--cs-border)",
                }}
                title={item.label}
              >
                <span
                  className="text-sm leading-none mb-0.5"
                  style={{ color: active ? "var(--cs-accent)" : "var(--cs-gray2)" }}
                >
                  {item.icon}
                </span>
                <span
                  className="text-[7px] font-bold tracking-[0.5px] leading-tight text-center"
                  style={{ color: active ? "var(--cs-accent)" : "var(--cs-gray3)" }}
                >
                  {item.label.length > 6 ? item.label.slice(0, 6) : item.label}
                </span>
              </Link>
            );
          })}
          <div className="flex-1" />
          <div
            className="flex flex-col items-center py-2"
            style={{ borderTop: "1px solid var(--cs-border)" }}
          >
            <span className="text-[7px] font-bold tracking-[0.5px]" style={{ color: "var(--cs-gray3)" }}>v0.1</span>
          </div>
        </nav>

        {/* Page content */}
        <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
          {children}
        </div>
      </div>

      {/* Provenance Drawer (global overlay) */}
      <ProvenanceDrawer />
    </div>
  );
}
