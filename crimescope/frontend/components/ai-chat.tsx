"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { useAppStore } from "../lib/store";
import { useScores } from "../lib/hooks";
import type { TractScore } from "../lib/api";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function generateFallback(query: string, scores: TractScore[], selectedTract: string | null): string {
  const q = query.toLowerCase();
  const selected = selectedTract ? scores.find((s) => s.tract_geoid === selectedTract) : null;

  if (q.includes("risk") && q.includes("score") && selected) {
    return `Tract ${selected.name || selected.tract_geoid} has a risk score of ${Math.round(selected.risk_score)}/100 (${selected.risk_tier} tier). The model predicts approximately ${selected.predicted_next_30d.toFixed(0)} incidents over the next 30 days.`;
  }
  if ((q.includes("highest") || q.includes("top") || q.includes("worst")) && q.includes("risk")) {
    const top5 = [...scores].sort((a, b) => b.risk_score - a.risk_score).slice(0, 5);
    const lines = top5.map((s, i) => `${i + 1}. ${s.name || s.tract_geoid} — Score: ${Math.round(s.risk_score)} (${s.risk_tier})`);
    return `Top 5 highest-risk tracts:\n\n${lines.join("\n")}`;
  }
  if (q.includes("safest") || q.includes("lowest") || q.includes("best")) {
    const bottom5 = [...scores].sort((a, b) => a.risk_score - b.risk_score).slice(0, 5);
    const lines = bottom5.map((s, i) => `${i + 1}. ${s.name || s.tract_geoid} — Score: ${Math.round(s.risk_score)} (${s.risk_tier})`);
    return `Top 5 lowest-risk tracts:\n\n${lines.join("\n")}`;
  }
  if (selected) {
    return `Viewing Tract ${selected.name || selected.tract_geoid}.\nRisk Score: ${Math.round(selected.risk_score)}/100 (${selected.risk_tier})\nPredicted (30d): ${selected.predicted_next_30d.toFixed(0)} incidents`;
  }
  return `CrimeScope AI is analyzing ${scores.length} census tracts. Try:\n> "What are the highest risk areas?"\n> "Show tier breakdown"\n> "Portfolio overview"`;
}

export default function AIChatPanel() {
  const chatOpen = useAppStore((s) => s.chatOpen);
  const messages = useAppStore((s) => s.chatMessages);
  const addMessage = useAppStore((s) => s.addChatMessage);
  const selectedTract = useAppStore((s) => s.selectedTract);
  const { data: scores = [] } = useScores();
  const [input, setInput] = useState("");
  const [typing, setTyping] = useState(false);
  const [streamText, setStreamText] = useState("");
  const [llmAvailable, setLlmAvailable] = useState<boolean | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamText]);

  useEffect(() => {
    fetch(`${API}/api/chat/status`)
      .then((r) => r.json())
      .then((d) => setLlmAvailable(d.configured === true))
      .catch(() => setLlmAvailable(false));
  }, []);

  const streamFromBackend = useCallback(
    async (userMsg: string) => {
      const selected = selectedTract ? scores.find((s) => s.tract_geoid === selectedTract) : null;

      const tractCtx = selected
        ? {
            geoid: selected.tract_geoid,
            score: selected.risk_score,
            tier: selected.risk_tier,
            drivers: selected.top_drivers_json,
          }
        : undefined;

      const history = messages.slice(-10).map((m) => ({
        role: m.role,
        content: m.content,
      }));

      const controller = new AbortController();
      abortRef.current = controller;

      const res = await fetch(`${API}/api/chat/message`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: userMsg,
          tract_context: tractCtx,
          history,
        }),
        signal: controller.signal,
      });

      if (!res.ok || !res.body) {
        throw new Error(`${res.status}`);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let full = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split("\n");

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const payload = line.slice(6).trim();
          if (payload === "[DONE]") continue;
          try {
            const parsed = JSON.parse(payload);
            if (parsed.error) throw new Error(parsed.error);
            if (parsed.content) {
              full += parsed.content;
              setStreamText(full);
            }
          } catch {
            // skip unparseable lines
          }
        }
      }

      return full;
    },
    [selectedTract, scores, messages],
  );

  if (!chatOpen) return null;

  const handleSend = async () => {
    const trimmed = input.trim();
    if (!trimmed || typing) return;

    addMessage({ role: "user", content: trimmed, timestamp: Date.now() });
    setInput("");
    setTyping(true);
    setStreamText("");

    if (llmAvailable) {
      try {
        const response = await streamFromBackend(trimmed);
        addMessage({ role: "assistant", content: response || "No response received.", timestamp: Date.now() });
      } catch (err) {
        if ((err as Error).name === "AbortError") return;
        const fallback = generateFallback(trimmed, scores, selectedTract);
        addMessage({
          role: "assistant",
          content: `[LLM unavailable — using local analysis]\n\n${fallback}`,
          timestamp: Date.now(),
        });
      }
    } else {
      await new Promise((r) => setTimeout(r, 400 + Math.random() * 600));
      const response = generateFallback(trimmed, scores, selectedTract);
      addMessage({ role: "assistant", content: response, timestamp: Date.now() });
    }

    setStreamText("");
    setTyping(false);
    abortRef.current = null;
  };

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
        className="flex items-center justify-between px-3 shrink-0"
        style={{
          height: 28,
          background: "var(--cs-panel)",
          borderBottom: "1px solid var(--cs-border)",
          fontFamily: "var(--cs-mono)",
        }}
      >
        <span
          className="text-[10px] font-bold tracking-[1.5px] uppercase"
          style={{ color: "var(--cs-accent)" }}
        >
          AI INTELLIGENCE CHAT
        </span>
        <span className="flex items-center gap-1.5">
          {llmAvailable && (
            <span
              className="inline-block w-1.5 h-1.5 rounded-full"
              style={{ background: "var(--cs-green)", animation: "cs-pulse 2s ease-in-out infinite" }}
            />
          )}
          <span className="text-[9px]" style={{ color: "var(--cs-gray2)" }}>
            {llmAvailable ? "GPT-4o mini" : "LOCAL"}
          </span>
        </span>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-2.5 py-2 space-y-2">
        {messages.length === 0 && (
          <div
            className="text-[10px] py-4 text-center"
            style={{ color: "var(--cs-gray2)", fontFamily: "var(--cs-mono)" }}
          >
            {llmAvailable
              ? "AI-powered analysis. Ask about crime risk, tracts, trends, or underwriting."
              : "Local analysis mode. Ask about crime risk, tracts, trends, or underwriting."}
          </div>
        )}
        {messages.map((msg, i) => (
          <div
            key={i}
            className="px-2.5 py-2"
            style={{
              background: msg.role === "user" ? "var(--cs-accent-lo)" : "var(--cs-panel2)",
              border: `1px solid ${msg.role === "user" ? "var(--cs-accent-md)" : "var(--cs-border)"}`,
              fontFamily: "var(--cs-mono)",
            }}
          >
            <div
              className="text-[8px] font-bold uppercase tracking-[1px] mb-1"
              style={{
                color: msg.role === "user" ? "var(--cs-accent)" : "var(--cs-amber)",
              }}
            >
              {msg.role === "user" ? "YOU" : "CRIMESCOPE AI"}
            </div>
            <div
              className="text-[11px] whitespace-pre-wrap leading-relaxed"
              style={{ color: "var(--cs-text)" }}
            >
              {msg.content}
            </div>
          </div>
        ))}
        {typing && (
          <div
            className="px-2.5 py-2"
            style={{
              background: "var(--cs-panel2)",
              border: "1px solid var(--cs-border)",
              fontFamily: "var(--cs-mono)",
            }}
          >
            <div
              className="text-[8px] font-bold uppercase tracking-[1px] mb-1"
              style={{ color: "var(--cs-amber)" }}
            >
              CRIMESCOPE AI
            </div>
            {streamText ? (
              <div
                className="text-[11px] whitespace-pre-wrap leading-relaxed"
                style={{ color: "var(--cs-text)" }}
              >
                {streamText}
                <span className="inline-block w-1.5 h-3 ml-0.5" style={{ background: "var(--cs-accent)", animation: "cs-pulse 1s ease-in-out infinite" }} />
              </div>
            ) : (
              <div className="flex items-center gap-1">
                {[0, 1, 2].map((d) => (
                  <div
                    key={d}
                    className="w-1.5 h-1.5 rounded-full"
                    style={{
                      background: "var(--cs-gray2)",
                      animation: `cs-pulse 1.2s ease-in-out ${d * 0.2}s infinite`,
                    }}
                  />
                ))}
              </div>
            )}
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div
        className="flex items-center gap-2 px-2.5 py-2 shrink-0"
        style={{
          borderTop: "1px solid var(--cs-border)",
          background: "var(--cs-panel)",
        }}
      >
        <input
          type="text"
          placeholder="ASK ABOUT RISK, TRACTS, TRENDS..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSend()}
          className="flex-1 text-[11px] px-2 py-1.5 outline-none"
          style={{
            background: "var(--cs-panel2)",
            border: "1px solid var(--cs-border)",
            color: "var(--cs-text)",
            fontFamily: "var(--cs-mono)",
          }}
        />
        <button
          onClick={handleSend}
          disabled={typing}
          className="text-[10px] font-bold px-2.5 py-1.5 uppercase tracking-wide shrink-0"
          style={{
            background: typing ? "var(--cs-gray2)" : "var(--cs-accent)",
            color: "#000",
            opacity: typing ? 0.5 : 1,
          }}
        >
          SEND
        </button>
      </div>
    </div>
  );
}
