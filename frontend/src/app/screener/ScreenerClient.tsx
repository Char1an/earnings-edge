"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import { api } from "@/lib/api";
import { signedPct as fmtPct } from "@/lib/format";
import type { ScreenerFilters, ScreenerResponse, ScreenerRow } from "@/lib/types";

const SORT_OPTIONS = [
  { v: "days_since_announcement", l: "Days since announcement" },
  { v: "drift_20d", l: "20-day drift" },
  { v: "last_yoy_pat_growth", l: "YoY PAT growth" },
  { v: "last_yoy_revenue_growth", l: "YoY revenue growth" },
  { v: "last_day5_close_pct", l: "Last day-5 reaction" },
  { v: "n_reactions", l: "History depth" },
  { v: "symbol", l: "Symbol" },
];

const fmtInt = (v: number | null | undefined) =>
  v == null ? "—" : v.toLocaleString("en-IN");
const fmtRs = (v: number | null | undefined) =>
  v == null ? "—" : `₹${v.toLocaleString("en-IN", { maximumFractionDigits: 2 })}`;
function pctClass(v: number | null | undefined) {
  if (v == null) return "text-muted";
  if (v > 0.5) return "text-accent";
  if (v < -0.5) return "text-neg";
  return "text-text";
}

function readFilters(sp: URLSearchParams): ScreenerFilters {
  const f: ScreenerFilters = {};
  const num = (k: keyof ScreenerFilters) => {
    const v = sp.get(k as string);
    if (v == null || v === "") return;
    const n = Number(v);
    if (Number.isFinite(n)) (f as Record<string, unknown>)[k as string] = n;
  };
  const s = sp.get("sector"); if (s) f.sector = s;
  if (sp.get("fno_only") === "true") f.fno_only = true;
  num("min_yoy_pat_growth");
  num("min_yoy_revenue_growth");
  num("max_days_since_announcement");
  num("min_drift_20d");
  num("min_n_reactions");
  const sb = sp.get("sort_by"); if (sb) f.sort_by = sb;
  if (sp.get("sort_desc") === "true") f.sort_desc = true;
  num("limit");
  return f;
}

export default function ScreenerClient() {
  const router = useRouter();
  const sp = useSearchParams();
  const initial = useMemo(() => readFilters(sp), [sp]);
  const [filters, setFilters] = useState<ScreenerFilters>({
    sort_by: "days_since_announcement",
    sort_desc: false,
    limit: 50,
    ...initial,
  });
  const [data, setData] = useState<ScreenerResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  // Runs the screen for a specific filter set (defaults to current state) and
  // syncs the URL to match. Taking an explicit argument lets Reset run with the
  // fresh defaults without waiting for the async setFilters to settle.
  const run = useCallback(
    async (override?: ScreenerFilters) => {
      const active = override ?? filters;
      setBusy(true);
      setErr(null);
      try {
        const res = await api.screener(active);
        setData(res);
        // URL-sync
        const params = new URLSearchParams();
        for (const [k, v] of Object.entries(active)) {
          if (v === undefined || v === null || v === "" || v === false) continue;
          params.set(k, String(v));
        }
        const qs = params.toString();
        router.replace(qs ? `/screener?${qs}` : "/screener", { scroll: false });
      } catch (e) {
        setErr(e instanceof Error ? e.message : String(e));
      } finally {
        setBusy(false);
      }
    },
    [filters, router],
  );

  useEffect(() => {
    run();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const set = <K extends keyof ScreenerFilters>(k: K, v: ScreenerFilters[K]) =>
    setFilters((f) => ({ ...f, [k]: v }));

  const reset = () => {
    const defaults: ScreenerFilters = {
      sort_by: "days_since_announcement",
      sort_desc: false,
      limit: 50,
    };
    setFilters(defaults);
    run(defaults);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Screener</h1>
        <p className="text-sm text-muted mt-1">
          Filter the Nifty 500 by recent-earnings metrics and 20-day drift. Sort to rank.
        </p>
      </div>

      <div className="border border-border rounded-md bg-panel p-4 grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-4">
        <Field
          label="Min YoY PAT growth (%)"
          value={filters.min_yoy_pat_growth}
          onChange={(v) => set("min_yoy_pat_growth", v)}
          placeholder="e.g. 10"
        />
        <Field
          label="Min YoY revenue growth (%)"
          value={filters.min_yoy_revenue_growth}
          onChange={(v) => set("min_yoy_revenue_growth", v)}
          placeholder="e.g. 5"
        />
        <Field
          label="Max days since announcement"
          value={filters.max_days_since_announcement}
          onChange={(v) => set("max_days_since_announcement", v)}
          placeholder="e.g. 30"
        />
        <Field
          label="Min 20-day drift (%)"
          value={filters.min_drift_20d}
          onChange={(v) => set("min_drift_20d", v)}
          placeholder="e.g. 3"
        />
        <Field
          label="Min prior reactions"
          value={filters.min_n_reactions}
          onChange={(v) => set("min_n_reactions", v)}
          placeholder="e.g. 5"
        />
        <div>
          <div className="text-[10px] uppercase tracking-wide text-muted mb-1">
            Sort by
          </div>
          <select
            className="w-full bg-bg border border-border rounded px-2 py-1.5 text-sm"
            value={filters.sort_by ?? "days_since_announcement"}
            onChange={(e) => set("sort_by", e.target.value)}
          >
            {SORT_OPTIONS.map((o) => (
              <option key={o.v} value={o.v}>
                {o.l}
              </option>
            ))}
          </select>
        </div>
        <label className="flex items-end gap-2 text-sm pb-2">
          <input
            type="checkbox"
            checked={!!filters.sort_desc}
            onChange={(e) => set("sort_desc", e.target.checked)}
          />
          descending
        </label>
        <label className="flex items-end gap-2 text-sm pb-2">
          <input
            type="checkbox"
            checked={!!filters.fno_only}
            onChange={(e) => set("fno_only", e.target.checked)}
          />
          F&amp;O stocks only
        </label>
      </div>

      <div className="flex items-center gap-3">
        <button
          onClick={() => run()}
          disabled={busy}
          className="px-4 py-2 bg-accent/90 hover:bg-accent text-bg font-medium rounded text-sm disabled:opacity-50"
        >
          {busy ? "running…" : "Run screener"}
        </button>
        <button
          onClick={reset}
          disabled={busy}
          className="px-3 py-2 border border-border rounded text-sm hover:bg-panel disabled:opacity-50"
        >
          Reset
        </button>
        <span className="text-xs text-muted">
          {data ? `${data.n} match${data.n === 1 ? "" : "es"}` : ""}
        </span>
      </div>

      {err && (
        <div className="text-sm text-neg border border-neg/40 bg-neg/10 rounded-md p-3">
          {err}
        </div>
      )}

      <ResultTable rows={data?.rows ?? []} />
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string;
  value: number | undefined;
  onChange: (v: number | undefined) => void;
  placeholder?: string;
}) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-wide text-muted mb-1">{label}</div>
      <input
        type="number"
        step="any"
        value={value ?? ""}
        placeholder={placeholder}
        onChange={(e) => {
          const s = e.target.value;
          if (s === "") return onChange(undefined);
          const n = Number(s);
          onChange(Number.isFinite(n) ? n : undefined);
        }}
        className="w-full bg-bg border border-border rounded px-2 py-1.5 text-sm font-mono"
      />
    </div>
  );
}

function ResultTable({ rows }: { rows: ScreenerRow[] }) {
  if (rows.length === 0) {
    return (
      <div className="text-sm text-muted p-4 border border-border rounded-md bg-panel">
        No stocks match. Loosen the filters.
      </div>
    );
  }
  return (
    <div className="border border-border rounded-md bg-panel overflow-x-auto">
      <table className="w-full text-sm font-mono">
        <thead className="text-xs text-muted">
          <tr className="border-b border-border">
            <th className="text-left px-3 py-2">Symbol</th>
            <th className="text-left px-3 py-2">Sector</th>
            <th className="text-right px-3 py-2">Close</th>
            <th className="text-right px-3 py-2">20d drift</th>
            <th className="text-left px-3 py-2">Last Q</th>
            <th className="text-right px-3 py-2">Days ago</th>
            <th className="text-right px-3 py-2">YoY PAT</th>
            <th className="text-right px-3 py-2">Gap</th>
            <th className="text-right px-3 py-2">Day5</th>
            <th className="text-right px-3 py-2">n</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.symbol} className="border-b border-border/60 last:border-b-0">
              <td className="px-3 py-2">
                <Link
                  href={`/stock/${encodeURIComponent(r.symbol)}`}
                  className="text-accent hover:underline"
                >
                  {r.symbol}
                </Link>
              </td>
              <td className="px-3 py-2 text-xs text-muted truncate max-w-[10rem]">
                {r.sector ?? "—"}
              </td>
              <td className="px-3 py-2 text-right">{fmtRs(r.latest_close)}</td>
              <td className={`px-3 py-2 text-right ${pctClass(r.drift_20d)}`}>
                {fmtPct(r.drift_20d)}
              </td>
              <td className="px-3 py-2 text-xs">{r.last_fiscal_period ?? "—"}</td>
              <td className="px-3 py-2 text-right text-muted">
                {fmtInt(r.days_since_announcement)}
              </td>
              <td className={`px-3 py-2 text-right ${pctClass(r.last_yoy_pat_growth)}`}>
                {fmtPct(r.last_yoy_pat_growth)}
              </td>
              <td className={`px-3 py-2 text-right ${pctClass(r.last_gap_open_pct)}`}>
                {fmtPct(r.last_gap_open_pct)}
              </td>
              <td className={`px-3 py-2 text-right ${pctClass(r.last_day5_close_pct)}`}>
                {fmtPct(r.last_day5_close_pct)}
              </td>
              <td className="px-3 py-2 text-right text-muted">{r.n_reactions}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
