import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "earnings-edge",
  description:
    "Indian equity earnings analytics — base rates, positioning, and pattern matching around quarterly results.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <header className="border-b border-border">
          <div className="mx-auto max-w-6xl px-6 py-4 flex items-center justify-between">
            <Link href="/" className="font-mono text-lg tracking-tight">
              earnings-<span className="text-accent">edge</span>
            </Link>
            <span className="text-xs text-muted">
              educational / research · not investment advice
            </span>
          </div>
        </header>
        <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
        <footer className="border-t border-border mt-16">
          <div className="mx-auto max-w-6xl px-6 py-4 text-xs text-muted flex justify-between">
            <span>Nifty 500 · data lags EOD by 1 trading day</span>
            <a
              href="https://github.com/Char1an/earnings-edge"
              className="hover:text-text"
              target="_blank"
              rel="noreferrer"
            >
              github
            </a>
          </div>
        </footer>
      </body>
    </html>
  );
}
