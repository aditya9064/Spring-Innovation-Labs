"use client";

import { useState, useRef, useEffect } from "react";
import { useScores } from "../../lib/hooks";
import { useAppStore } from "../../lib/store";
import { getCity } from "../../lib/cities";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const PROMPT_TEMPLATES = [
  { label: "Explain this region", prompt: "Explain the risk profile for {UNIT} {TRACT}. What are the main drivers and how confident should I be?" },
  { label: "Compare regions", prompt: "Compare {UNIT_PLURAL} {TRACT_A} and {TRACT_B}. What are the key differences in risk and drivers?" },
  { label: "Recent changes", prompt: "What has changed in the last 30 days for {UNIT} {TRACT}? Summarize the key shifts." },
  { label: "Persona summary", prompt: "As an {PERSONA}, what should I know about {UNIT} {TRACT}? Give me an actionable recommendation." },
  { label: "Underreporting", prompt: "What is the underreporting risk for {UNIT} {TRACT}? What data gaps exist?" },
  { label: "Draft report", prompt: "Draft a brief risk assessment report for {UNIT} {TRACT} suitable for an insurer review." },
];

type Message = { role: "user" | "assistant"; content: string; citations?: string[] };

function SectionHeader({ title, meta }: { title: string; meta?: string }) {
  return (
    <div
      className="flex items-center justify-between px-3 shrink-0"
      style={{ height: 28, background: "var(--cs-panel)", borderBottom: "1px solid var(--cs-border)", fontFamily: "var(--cs-mono)" }}
    >
      <span className="text-[10px] font-bold tracking-[1.5px] uppercase" style={{ color: "var(--cs-accent)" }}>{title}</span>
      {meta && <span className="text-[9px] tracking-wide" style={{ color: "var(--cs-gray2)" }}>{meta}</span>}
    </div>
  );
}

export default function AnalystPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const { data: scores = [] } = useScores();
  const selectedTract = useAppStore((s) => s.selectedTract);
  const persona = useAppStore((s) => s.persona);
  const city = useAppStore((s) => s.city);
  const cityCfg = getCity(city);

  useEffect(() => {
    scrollRef.current?.scrollTo(0, scrollRef.current.scrollHeight);
  }, [messages]);

  const send = async (text: string) => {
    if (!text.trim() || loading) return;
    const userMsg: Message = { role: "user", content: text.trim() };
    setMessages((m) => [...m, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch(`${API}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: text.trim(),
          region_id: selectedTract,
          city,
          history: messages.slice(-6).map((m) => ({ role: m.role, content: m.content })),
        }),
      });
      if (!res.ok) throw new Error(`API ${res.status}`);
      const data = await res.json();
      const assistantMsg: Message = {
        role: "assistant",
        content: data.response || data.message || "No response.",
        citations: data.citations || [],
      };
      setMessages((m) => [...m, assistantMsg]);
    } catch {
      setMessages((m) => [...m, { role: "assistant", content: "Error: Unable to reach the AI service. Please try again." }]);
    } finally {
      setLoading(false);
    }
  };

  const applyTemplate = (template: string) => {
    const fallbackA = selectedTract || scores[0]?.tract_geoid || cityCfg.defaultRegionId;
    const fallbackB = scores[1]?.tract_geoid || scores[0]?.tract_geoid || cityCfg.defaultRegionId;
    const filled = template
      .replace(/\{TRACT\}/g, fallbackA)
      .replace(/\{TRACT_A\}/g, fallbackA)
      .replace(/\{TRACT_B\}/g, fallbackB)
      .replace(/\{UNIT\}/g, cityCfg.geographyUnit)
      .replace(/\{UNIT_PLURAL\}/g, cityCfg.geographyUnitPlural)
      .replace(/\{PERSONA\}/g, persona);
    setInput(filled);
  };

  return (
    <div className="flex flex-col flex-1 overflow-hidden" style={{ background: "var(--cs-bg)" }}>
      <div className="flex flex-1 min-h-0 overflow-hidden">
        {/* Left: Prompt Templates + Context */}
        <div className="flex flex-col shrink-0" style={{ width: 260, borderRight: "1px solid var(--cs-border)" }}>
          <SectionHeader title="PROMPT TEMPLATES" />
          <div className="flex-1 overflow-y-auto" style={{ fontFamily: "var(--cs-mono)" }}>
            {PROMPT_TEMPLATES.map((t, i) => (
              <button
                key={i}
                onClick={() => applyTemplate(t.prompt)}
                className="w-full text-left px-3 py-2 transition-colors"
                style={{ borderBottom: "1px solid var(--cs-border)" }}
              >
                <div className="text-[10px] font-medium" style={{ color: "var(--cs-text)" }}>{t.label}</div>
                <div className="text-[8px] mt-0.5 truncate" style={{ color: "var(--cs-gray3)" }}>{t.prompt}</div>
              </button>
            ))}
          </div>

          <SectionHeader title="CONTEXT" />
          <div className="px-3 py-2 space-y-2" style={{ fontFamily: "var(--cs-mono)" }}>
            <div>
              <div className="text-[8px] font-bold tracking-[1px] mb-0.5" style={{ color: "var(--cs-gray2)" }}>SELECTED {cityCfg.geographyUnit.toUpperCase()}</div>
              <div className="text-[10px]" style={{ color: selectedTract ? "var(--cs-text)" : "var(--cs-gray3)" }}>
                {selectedTract || "None — select from dashboard"}
              </div>
            </div>
            <div>
              <div className="text-[8px] font-bold tracking-[1px] mb-0.5" style={{ color: "var(--cs-gray2)" }}>PERSONA</div>
              <div className="text-[10px] uppercase" style={{ color: "var(--cs-accent)" }}>{persona}</div>
            </div>
            <div>
              <div className="text-[8px] font-bold tracking-[1px] mb-0.5" style={{ color: "var(--cs-gray2)" }}>{cityCfg.geographyUnitPlural.toUpperCase()} LOADED</div>
              <div className="text-[10px]" style={{ color: "var(--cs-text)" }}>{scores.length}</div>
            </div>
          </div>

          {/* Saved investigations placeholder */}
          <SectionHeader title="SAVED" />
          <div className="px-3 py-3 text-center">
            <div className="text-[9px]" style={{ color: "var(--cs-gray3)", fontFamily: "var(--cs-mono)" }}>No saved investigations yet</div>
          </div>
        </div>

        {/* Chat area */}
        <div className="flex-1 flex flex-col">
          <SectionHeader title="ANALYST WORKSPACE" meta={`${messages.length} MESSAGES`} />

          {/* Messages */}
          <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-3 space-y-3" style={{ fontFamily: "var(--cs-mono)" }}>
            {messages.length === 0 && (
              <div className="text-center py-12">
                <div className="text-[11px] font-bold mb-2" style={{ color: "var(--cs-gray2)" }}>ANALYST WORKSPACE</div>
                <div className="text-[10px]" style={{ color: "var(--cs-gray3)" }}>
                  Ask questions about regions, compare tracts, summarize changes, or draft reports.
                  Use the prompt templates on the left to get started.
                </div>
              </div>
            )}
            {messages.map((m, i) => (
              <div
                key={i}
                className="flex gap-2"
                style={{ justifyContent: m.role === "user" ? "flex-end" : "flex-start" }}
              >
                <div
                  className="max-w-[80%] px-3 py-2"
                  style={{
                    background: m.role === "user" ? "var(--cs-accent-lo)" : "var(--cs-panel2)",
                    border: `1px solid ${m.role === "user" ? "var(--cs-accent-md)" : "var(--cs-border)"}`,
                  }}
                >
                  <div className="text-[8px] font-bold mb-1" style={{ color: m.role === "user" ? "var(--cs-accent)" : "var(--cs-green)" }}>
                    {m.role === "user" ? "YOU" : "ANALYST"}
                  </div>
                  <div className="text-[10px] whitespace-pre-wrap leading-relaxed" style={{ color: "var(--cs-text)" }}>
                    {m.content}
                  </div>
                  {m.citations && m.citations.length > 0 && (
                    <div className="mt-2 pt-1.5" style={{ borderTop: "1px solid var(--cs-border)" }}>
                      <div className="text-[8px] font-bold mb-0.5" style={{ color: "var(--cs-gray2)" }}>CITATIONS</div>
                      {m.citations.map((c, ci) => (
                        <div key={ci} className="text-[9px]" style={{ color: "var(--cs-gray2)" }}>• {c}</div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
            {loading && (
              <div className="text-[10px]" style={{ color: "var(--cs-gray2)" }}>
                <span style={{ animation: "cs-pulse 1.5s ease-in-out infinite" }}>Analyzing...</span>
              </div>
            )}
          </div>

          {/* Input */}
          <div className="shrink-0 px-4 py-2" style={{ borderTop: "1px solid var(--cs-border)" }}>
            <div className="flex gap-2">
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && send(input)}
                placeholder="Ask about a region, compare tracts, or draft a report..."
                className="flex-1 text-[11px] px-3 py-2 outline-none"
                style={{
                  background: "var(--cs-panel2)",
                  border: "1px solid var(--cs-border)",
                  color: "var(--cs-text)",
                  fontFamily: "var(--cs-mono)",
                }}
              />
              <button
                onClick={() => send(input)}
                disabled={loading || !input.trim()}
                className="text-[10px] font-bold px-4 py-2 uppercase tracking-wide"
                style={{
                  background: loading ? "var(--cs-panel2)" : "var(--cs-accent)",
                  color: loading ? "var(--cs-gray2)" : "#000",
                }}
              >
                SEND
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
