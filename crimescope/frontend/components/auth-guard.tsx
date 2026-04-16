"use client";

import { useSession } from "next-auth/react";
import { useRouter, usePathname } from "next/navigation";
import { useEffect } from "react";

const PUBLIC_PATHS = ["/login"];

export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const { status } = useSession();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (status === "unauthenticated" && !PUBLIC_PATHS.includes(pathname)) {
      router.push("/login");
    }
  }, [status, pathname, router]);

  if (status === "loading") {
    return (
      <div
        className="flex items-center justify-center h-screen"
        style={{ background: "var(--cs-bg)" }}
      >
        <div style={{ fontFamily: "var(--cs-mono)", textAlign: "center" }}>
          <div
            className="text-[13px] font-bold tracking-[3px] mb-2"
            style={{ color: "var(--cs-accent)" }}
          >
            CRIMESCOPE
          </div>
          <div className="text-[10px] tracking-[2px]" style={{ color: "var(--cs-gray2)" }}>
            AUTHENTICATING...
          </div>
        </div>
      </div>
    );
  }

  if (status === "unauthenticated" && !PUBLIC_PATHS.includes(pathname)) {
    return null;
  }

  return <>{children}</>;
}
