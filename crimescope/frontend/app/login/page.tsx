"use client";

import { useState } from "react";
import { signIn } from "next-auth/react";
import { useRouter } from "next/navigation";

const DEMO_USERS = [
  { name: "Sarah Chen", role: "Senior Underwriter", email: "s.chen@insurecorp.com" },
  { name: "Marcus Rivera", role: "Risk Analyst", email: "m.rivera@insurecorp.com" },
  { name: "Dr. Aisha Patel", role: "Data Scientist", email: "a.patel@insurecorp.com" },
  { name: "James O'Brien", role: "Claims Adjuster", email: "j.obrien@insurecorp.com" },
];

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    const res = await signIn("credentials", {
      email,
      password,
      redirect: false,
    });

    setLoading(false);

    if (res?.error) {
      setError("Invalid credentials. Use a demo email and any 4+ char password.");
    } else {
      router.push("/");
      router.refresh();
    }
  };

  const handleDemoLogin = async (user: (typeof DEMO_USERS)[0]) => {
    setLoading(true);
    const res = await signIn("credentials", {
      email: user.email,
      password: "demo",
      redirect: false,
    });
    setLoading(false);

    if (!res?.error) {
      router.push("/");
      router.refresh();
    }
  };

  return (
    <div className="flex items-center justify-center h-screen" style={{ background: "var(--cs-bg)" }}>
      <div style={{ width: 420, fontFamily: "var(--cs-mono)" }}>
        {/* Header */}
        <div className="text-center mb-6">
          <div className="text-[13px] font-bold tracking-[3px] mb-1" style={{ color: "var(--cs-accent)" }}>CRIMESCOPE</div>
          <div className="text-[10px] tracking-[2px]" style={{ color: "var(--cs-gray2)" }}>INTELLIGENCE TERMINAL v0.1.0</div>
        </div>

        {/* Login Form */}
        <div style={{ border: "1px solid var(--cs-border)", background: "var(--cs-panel)" }}>
          <div className="px-3" style={{ height: 28, display: "flex", alignItems: "center", borderBottom: "1px solid var(--cs-border)" }}>
            <span className="text-[10px] font-bold tracking-[1.5px] uppercase" style={{ color: "var(--cs-accent)" }}>AUTHENTICATE</span>
          </div>

          <form onSubmit={handleLogin} className="px-4 py-4 space-y-3">
            <div>
              <label className="text-[9px] font-bold uppercase tracking-[1px] block mb-1" style={{ color: "var(--cs-gray2)" }}>EMAIL</label>
              <input type="email" value={email} onChange={(e) => { setEmail(e.target.value); setError(""); }} placeholder="analyst@insurecorp.com" className="w-full text-[11px] px-2.5 py-1.5 outline-none" style={{ background: "var(--cs-panel2)", border: "1px solid var(--cs-border)", color: "var(--cs-text)" }} />
            </div>
            <div>
              <label className="text-[9px] font-bold uppercase tracking-[1px] block mb-1" style={{ color: "var(--cs-gray2)" }}>PASSWORD</label>
              <input type="password" value={password} onChange={(e) => { setPassword(e.target.value); setError(""); }} placeholder="••••••••" className="w-full text-[11px] px-2.5 py-1.5 outline-none" style={{ background: "var(--cs-panel2)", border: "1px solid var(--cs-border)", color: "var(--cs-text)" }} />
            </div>
            {error && <div className="text-[10px]" style={{ color: "var(--cs-red)" }}>{error}</div>}
            <button type="submit" disabled={loading} className="w-full text-[11px] font-bold py-2 uppercase tracking-wide" style={{ background: loading ? "var(--cs-gray2)" : "var(--cs-accent)", color: "#000", opacity: loading ? 0.6 : 1 }}>
              {loading ? "AUTHENTICATING..." : "LOGIN"}
            </button>
          </form>
        </div>

        {/* Demo Users */}
        <div className="mt-4" style={{ border: "1px solid var(--cs-border)", background: "var(--cs-panel)" }}>
          <div className="px-3" style={{ height: 28, display: "flex", alignItems: "center", borderBottom: "1px solid var(--cs-border)" }}>
            <span className="text-[10px] font-bold tracking-[1.5px] uppercase" style={{ color: "var(--cs-amber)" }}>DEMO ACCOUNTS</span>
          </div>
          {DEMO_USERS.map((u) => (
            <button key={u.email} onClick={() => handleDemoLogin(u)} disabled={loading} className="w-full flex items-center gap-3 px-4 py-2 text-left" style={{ borderBottom: "1px solid rgba(30,30,30,0.5)" }}>
              <div className="w-7 h-7 flex items-center justify-center text-[10px] font-bold shrink-0" style={{ background: "var(--cs-accent-lo)", color: "var(--cs-accent)", border: "1px solid var(--cs-accent-md)" }}>
                {u.name.split(" ").map((n) => n[0]).join("")}
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-[11px] font-medium" style={{ color: "var(--cs-text)" }}>{u.name}</div>
                <div className="text-[9px]" style={{ color: "var(--cs-gray2)" }}>{u.role} · {u.email}</div>
              </div>
              <span className="text-[9px] px-1.5 py-0.5" style={{ background: "var(--cs-panel2)", color: "var(--cs-gray1)", border: "1px solid var(--cs-border)" }}>LOGIN</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
