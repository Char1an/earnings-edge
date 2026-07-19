"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { api } from "@/lib/api";
import type { StockSummary } from "@/lib/types";

export function StockSearch() {
  const router = useRouter();
  const [q, setQ] = useState("");
  const [results, setResults] = useState<StockSummary[]>([]);
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const wrap = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!q) {
      setResults([]);
      return;
    }
    let cancelled = false;
    setBusy(true);
    const t = setTimeout(async () => {
      try {
        const rows = await api.listStocks({ q: q.toUpperCase(), limit: 8 });
        if (!cancelled) setResults(rows);
      } catch {
        if (!cancelled) setResults([]);
      } finally {
        if (!cancelled) setBusy(false);
      }
    }, 150);
    return () => {
      cancelled = true;
      clearTimeout(t);
    };
  }, [q]);

  useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      if (wrap.current && !wrap.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  const go = (sym: string) => {
    setOpen(false);
    router.push(`/stock/${encodeURIComponent(sym)}`);
  };

  return (
    <div ref={wrap} className="relative w-full max-w-xl">
      <input
        value={q}
        onChange={(e) => {
          setQ(e.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && results.length) go(results[0].symbol);
        }}
        placeholder="Search a Nifty 500 symbol — e.g. RELIANCE, TCS, INFY"
        className="w-full bg-panel border border-border rounded-md px-4 py-3 font-mono text-sm outline-none focus:border-muted"
      />
      {open && q && (
        <div className="absolute z-10 mt-1 w-full bg-panel border border-border rounded-md shadow-xl overflow-hidden">
          {busy && <div className="px-4 py-2 text-xs text-muted">searching…</div>}
          {!busy && results.length === 0 && (
            <div className="px-4 py-2 text-xs text-muted">no matches</div>
          )}
          {results.map((r) => (
            <button
              key={r.id}
              onClick={() => go(r.symbol)}
              className="w-full text-left px-4 py-2 hover:bg-border/40 flex items-baseline justify-between border-b border-border last:border-b-0"
            >
              <span className="font-mono text-sm">{r.symbol}</span>
              <span className="text-xs text-muted truncate ml-3">
                {r.name ?? ""} {r.is_fno ? "· F&O" : ""}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
