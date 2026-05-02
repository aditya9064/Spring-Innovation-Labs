import type { Metadata } from "next";
import "./globals.css";
import "maplibre-gl/dist/maplibre-gl.css";
import { Providers } from "../lib/providers";
import AppShellWrapper from "../components/app-shell-wrapper";

export const metadata: Metadata = {
  title: "CRIMESCOPE — Intelligence Terminal",
  description: "Crime risk intelligence and analytics platform",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          rel="preconnect"
          href="https://fonts.gstatic.com"
          crossOrigin="anonymous"
        />
        <link
          href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;500;600;700&family=Inter:wght@400;500;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="antialiased">
        <Providers>
          <AppShellWrapper>{children}</AppShellWrapper>
        </Providers>
      </body>
    </html>
  );
}
