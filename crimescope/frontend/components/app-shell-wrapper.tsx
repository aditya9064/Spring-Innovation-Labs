"use client";

import dynamic from "next/dynamic";

const AppShell = dynamic(() => import("./app-shell"), { ssr: false });

export default function AppShellWrapper({ children }: { children: React.ReactNode }) {
  return <AppShell>{children}</AppShell>;
}
