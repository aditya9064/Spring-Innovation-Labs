"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { SessionProvider } from "next-auth/react";
import { useState } from "react";
import AuthGuard from "../components/auth-guard";

export function Providers({ children }: { children: React.ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30_000,
            retry: 1,
            refetchOnWindowFocus: false,
          },
        },
      }),
  );
  return (
    <SessionProvider>
      <QueryClientProvider client={client}>
        <AuthGuard>{children}</AuthGuard>
      </QueryClientProvider>
    </SessionProvider>
  );
}
