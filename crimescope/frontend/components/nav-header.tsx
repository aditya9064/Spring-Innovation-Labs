"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { useSession, signOut } from "next-auth/react";
import { useLiveBanner } from "../lib/hooks";
import { useAppStore } from "../lib/store";

const TABS = [
  { key: "F1", label: "DASHBOARD", href: "/" },
  { key: "F2", label: "REPORTS", href: "/reports" },
  { key: "F3", label: "COMPARE", href: "/compare" },
  { key: "F4", label: "BLIND SPOTS", href: "/blindspots" },
  { key: "F5", label: "SIMULATOR", href: "/simulator" },
  { key: "F6", label: "AUDIT", href: "/audit" },
] as const;

const REGIONS = [
  { id: "chicago", label: "CHICAGO, IL", center: [-87.635, 41.878] },
  { id: "milwaukee", label: "MILWAUKEE, WI", center: [-87.906, 43.039] },
  { id: "nyc", label: "NEW YORK, NY", center: [-73.986, 40.748] },
] as const;

export default function NavHeader({
  children,
}: {
  children?: React.ReactNode;
}) {
  const pathname = usePathname();
  const [time, setTime] = useState("");
  const { data: banner } = useLiveBanner();
  const { data: session } = useSession();
  const setChatOpen = useAppStore((s) => s.setChatOpen);
  const chatOpen = useAppStore((s) => s.chatOpen);
  const region = useAppStore((s) => s.region);
  const setRegion = useAppStore((s) => s.setRegion);

  const userName = session?.user?.name;
  const userRole = (session?.user as { role?: string } | undefined)?.role;

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
    <>
      {/* Live Banner */}
      {banner && (
        <div
          className="flex items-center gap-3 px-3.5 shrink-0 overflow-hidden"
          style={{
            height: 24,
            background: "var(--cs-panel)",
            borderBottom: "1px solid var(--cs-border)",
            fontFamily: "var(--cs-mono)",
          }}
        >
          <span
            className="flex items-center gap-1.5 shrink-0"
          >
            <span
              className="inline-block w-1.5 h-1.5 rounded-full"
              style={{
                background: banner.status === "active" ? "var(--cs-green)" : "var(--cs-amber)",
                animation: "cs-pulse 2s ease-in-out infinite",
              }}
            />
            <span
              className="text-[9px] font-bold uppercase tracking-[1px]"
              style={{ color: banner.status === "active" ? "var(--cs-green)" : "var(--cs-amber)" }}
            >
              {banner.status === "active" ? "LIVE" : "ALERT"}
            </span>
          </span>
          <span
            className="text-[10px] truncate"
            style={{ color: "var(--cs-gray1)" }}
          >
            {banner.headline}
          </span>
          <span className="flex-1" />
          <span
            className="text-[9px] shrink-0"
            style={{ color: "var(--cs-gray2)" }}
          >
            {banner.updatedAt
              ? new Date(banner.updatedAt).toLocaleTimeString("en-US", {
                  hour: "2-digit",
                  minute: "2-digit",
                  hour12: false,
                })
              : ""}
          </span>
        </div>
      )}

      {/* Status Bar */}
      <div
        className="flex items-center justify-between px-3.5 shrink-0"
        style={{
          height: 28,
          background: "var(--cs-accent)",
          fontFamily: "var(--cs-mono)",
        }}
      >
        <div className="flex items-center gap-5">
          <span className="text-[13px] font-bold tracking-[2px] text-black">
            CRIMESCOPE
          </span>
          <span className="text-[11px] font-semibold text-black/80 tracking-wide hidden sm:inline">
            INTELLIGENCE TERMINAL
          </span>
          <select
            value={region}
            onChange={(e) => setRegion(e.target.value)}
            className="text-[11px] font-semibold text-black/80 tracking-wide hidden md:inline bg-transparent outline-none cursor-pointer"
            style={{ border: "none" }}
          >
            {REGIONS.map((r) => (
              <option key={r.id} value={r.id} style={{ background: "#000", color: "#fff" }}>
                ● {r.label}
              </option>
            ))}
          </select>
        </div>
        <div className="flex items-center gap-4">
          {children}
          {userName && (
            <button
              onClick={() => signOut({ callbackUrl: "/login" })}
              className="text-[10px] font-semibold text-black/70 tracking-wide hidden md:flex items-center gap-1.5"
              title={userRole ? `${userName} · ${userRole}` : userName}
            >
              <span className="w-4 h-4 flex items-center justify-center text-[8px] font-bold" style={{ background: "rgba(0,0,0,0.15)", borderRadius: 2 }}>
                {userName.split(" ").map((n) => n[0]).join("")}
              </span>
              {userName.split(" ")[0]}
            </button>
          )}
          <span
            className="text-[11px] font-bold tracking-[1px] text-black"
            suppressHydrationWarning
          >
            {time || "--:--:--"}
          </span>
        </div>
      </div>

      {/* Function Key Bar */}
      <div
        className="flex items-center px-3.5 shrink-0"
        style={{
          height: 32,
          background: "var(--cs-panel)",
          borderBottom: "1px solid var(--cs-border)",
          fontFamily: "var(--cs-mono)",
        }}
      >
        <div className="flex items-center gap-0.5">
          {TABS.map((t) => {
            const active = pathname === t.href;
            return (
              <Link
                key={t.href}
                href={t.href}
                className="flex items-center cursor-pointer"
              >
                <span
                  className="text-[10px] font-bold px-1.5 py-0.5 tracking-wide"
                  style={{
                    background: active
                      ? "var(--cs-amber)"
                      : "var(--cs-accent)",
                    color: "#000",
                  }}
                >
                  {t.key}
                </span>
                <span
                  className="text-[10px] font-medium px-2 py-0.5 tracking-wide transition-colors"
                  style={{
                    color: active ? "var(--cs-amber)" : "var(--cs-gray1)",
                    borderRight: "1px solid var(--cs-border)",
                  }}
                >
                  {t.label}
                </span>
              </Link>
            );
          })}
        </div>
        <div className="flex-1" />
        <button
          onClick={() => setChatOpen(!chatOpen)}
          className="text-[10px] font-bold px-2 py-0.5 tracking-wide mr-3 transition-colors"
          style={{
            background: chatOpen ? "var(--cs-amber)" : "var(--cs-panel2)",
            color: chatOpen ? "#000" : "var(--cs-gray1)",
            border: "1px solid var(--cs-border)",
          }}
        >
          AI CHAT
        </button>
        <span
          className="text-[10px] tracking-wide hidden sm:inline"
          style={{ color: "var(--cs-gray2)" }}
        >
          v0.1.0 · BETA
        </span>
      </div>
    </>
  );
}
