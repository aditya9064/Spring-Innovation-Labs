"use client";

import { useState, useEffect, useRef } from "react";
import { useLiveEvents } from "../lib/hooks";
import type { LiveEvent } from "../lib/api";
import { WS_URL } from "../lib/api";

const STATUS_STYLE: Record<string, { bg: string; fg: string }> = {
  verified: { bg: "var(--cs-green-lo)", fg: "var(--cs-green)" },
  reported: { bg: "var(--cs-accent-lo)", fg: "var(--cs-accent)" },
  unverified: { bg: "var(--cs-red-lo)", fg: "var(--cs-red)" },
};

export default function LiveFeed() {
  const { data: apiEvents = [], isLoading } = useLiveEvents();
  const [wsEvents, setWsEvents] = useState<LiveEvent[]>([]);
  const [mode, setMode] = useState<"all" | "verified">("all");
  const [expanded, setExpanded] = useState(true);
  const [wsConnected, setWsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    let ws: WebSocket;
    let reconnectTimer: ReturnType<typeof setTimeout>;
    const connect = () => {
      try {
        ws = new WebSocket(`${WS_URL}/ws/live`);
        wsRef.current = ws;
        ws.onopen = () => setWsConnected(true);
        ws.onclose = () => {
          setWsConnected(false);
          reconnectTimer = setTimeout(connect, 5000);
        };
        ws.onerror = () => ws.close();
        ws.onmessage = (e) => {
          try {
            const evt = JSON.parse(e.data) as LiveEvent;
            setWsEvents((prev) => [evt, ...prev].slice(0, 50));
          } catch { /* ignore malformed */ }
        };
      } catch { /* connection failed, retry */ }
    };
    connect();
    return () => {
      clearTimeout(reconnectTimer);
      ws?.close();
    };
  }, []);

  const events = [...wsEvents, ...apiEvents];
  const filtered =
    mode === "verified"
      ? events.filter((e) => e.status === "verified")
      : events;

  return (
    <div
      className="flex flex-col shrink-0"
      style={{
        width: 340,
        background: "var(--cs-bg)",
        borderLeft: "1px solid var(--cs-border)",
      }}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-2.5 shrink-0"
        style={{
          height: 28,
          background: "var(--cs-panel)",
          borderBottom: "1px solid var(--cs-border)",
          fontFamily: "var(--cs-mono)",
        }}
      >
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-1.5"
        >
          <span
            className="text-[10px] font-bold tracking-[1.5px] uppercase"
            style={{ color: "var(--cs-accent)" }}
          >
            LIVE FEED
          </span>
          <span
            className="inline-block w-1.5 h-1.5 rounded-full"
            style={{
              background: wsConnected ? "var(--cs-green)" : "var(--cs-red)",
              animation: wsConnected ? "cs-pulse 2s ease-in-out infinite" : "none",
            }}
          />
          {wsEvents.length > 0 && (
            <span className="text-[8px] font-bold px-1 py-0.5" style={{ background: "var(--cs-green-lo)", color: "var(--cs-green)", border: "1px solid var(--cs-green)33" }}>
              +{wsEvents.length}
            </span>
          )}
        </button>
        <div className="flex items-center gap-1">
          <button
            onClick={() => setMode("all")}
            className="text-[9px] px-1.5 py-0.5 tracking-wide"
            style={{
              background:
                mode === "all" ? "var(--cs-accent)" : "transparent",
              color: mode === "all" ? "#000" : "var(--cs-gray2)",
            }}
          >
            ALL
          </button>
          <button
            onClick={() => setMode("verified")}
            className="text-[9px] px-1.5 py-0.5 tracking-wide"
            style={{
              background:
                mode === "verified" ? "var(--cs-green)" : "transparent",
              color: mode === "verified" ? "#000" : "var(--cs-gray2)",
            }}
          >
            VERIFIED
          </button>
        </div>
      </div>

      {expanded && (
        <div className="flex-1 overflow-y-auto">
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <div
                className="w-4 h-4 border border-[var(--cs-accent)] border-t-transparent rounded-full"
                style={{ animation: "cs-spin 0.8s linear infinite" }}
              />
            </div>
          ) : filtered.length === 0 ? (
            <div
              className="text-center py-6 text-[10px] uppercase tracking-[1px]"
              style={{
                color: "var(--cs-gray3)",
                fontFamily: "var(--cs-mono)",
              }}
            >
              {mode === "verified"
                ? "NO VERIFIED EVENTS"
                : "NO EVENTS"}
            </div>
          ) : (
            filtered.map((evt) => {
              const st =
                STATUS_STYLE[evt.status] || STATUS_STYLE.unverified;
              return (
                <div
                  key={evt.id}
                  className="px-2.5 py-2"
                  style={{
                    borderBottom: "1px solid rgba(30,30,30,0.5)",
                    fontFamily: "var(--cs-mono)",
                  }}
                >
                  <div className="flex items-start justify-between gap-2 mb-1">
                    <span
                      className="text-[11px] font-medium leading-tight"
                      style={{ color: "var(--cs-text)" }}
                    >
                      {evt.title}
                    </span>
                    <span
                      className="text-[8px] font-bold px-1 py-0.5 uppercase tracking-wide shrink-0"
                      style={{
                        background: st.bg,
                        color: st.fg,
                        border: `1px solid ${st.fg}33`,
                      }}
                    >
                      {evt.status}
                    </span>
                  </div>
                  {evt.summary && (
                    <p
                      className="text-[10px] mb-1 leading-relaxed"
                      style={{ color: "var(--cs-gray2)" }}
                    >
                      {evt.summary}
                    </p>
                  )}
                  <div className="flex items-center gap-2">
                    <span
                      className="text-[9px]"
                      style={{ color: "var(--cs-gray3)" }}
                    >
                      {evt.sourceType.replace(/_/g, " ")}
                    </span>
                    <span
                      className="text-[9px]"
                      style={{ color: "var(--cs-gray3)" }}
                    >
                      ·
                    </span>
                    <span
                      className="text-[9px]"
                      style={{ color: "var(--cs-gray3)" }}
                    >
                      {evt.confidence} conf
                    </span>
                    <span className="flex-1" />
                    <span
                      className="text-[9px]"
                      style={{ color: "var(--cs-gray3)" }}
                    >
                      {new Date(evt.occurredAt).toLocaleString("en-US", {
                        month: "short",
                        day: "numeric",
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </span>
                  </div>
                </div>
              );
            })
          )}
        </div>
      )}
    </div>
  );
}
