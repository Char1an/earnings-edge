"use client";

import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import type { BaseRatesResponse, Distribution } from "@/lib/types";

const METRIC_LABELS: Record<string, string> = {
  gap_open_pct: "Gap open",
  day1_close_pct: "Day 1 close",
  day3_close_pct: "Day 3 close",
  day5_close_pct: "Day 5 close",
};

function toChart(d: Distribution) {
  return d.hist_counts.map((c, i) => ({
    bin: `${d.hist_bin_edges[i]?.toFixed(1) ?? ""}`,
    count: c,
  }));
}

function StatRow({ d }: { d: Distribution }) {
  const label = METRIC_LABELS[d.metric] ?? d.metric;
  return (
    <div className="border border-border rounded-md bg-panel">
      <div className="flex items-baseline justify-between px-3 py-2 border-b border-border">
        <div className="text-sm font-medium">{label}</div>
        <div className="text-xs text-muted font-mono">n = {d.n}</div>
      </div>
      {d.n === 0 ? (
        <div className="px-3 py-6 text-xs text-muted">insufficient history</div>
      ) : (
        <>
          <div className="grid grid-cols-5 text-xs font-mono px-3 py-2 gap-2 border-b border-border">
            <Stat k="median" v={d.median} pct />
            <Stat k="mean" v={d.mean} pct />
            <Stat k="p25" v={d.p25} pct />
            <Stat k="p75" v={d.p75} pct />
            <Stat k="range" v={d.max != null && d.min != null ? d.max - d.min : null} pct />
          </div>
          <div className="h-32 px-1">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={toChart(d)}>
                <XAxis
                  dataKey="bin"
                  stroke="#7d8590"
                  fontSize={10}
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis hide />
                <Tooltip
                  cursor={{ fill: "rgba(255,255,255,0.05)" }}
                  contentStyle={{
                    background: "#0b0d10",
                    border: "1px solid #232a33",
                    fontSize: 12,
                  }}
                />
                <Bar dataKey="count" fill="#3fb950" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </>
      )}
    </div>
  );
}

function Stat({ k, v, pct }: { k: string; v: number | null; pct?: boolean }) {
  return (
    <div>
      <div className="text-muted uppercase tracking-wide text-[10px]">{k}</div>
      <div>{v == null ? "—" : `${v > 0 && pct ? "+" : ""}${v.toFixed(2)}${pct ? "%" : ""}`}</div>
    </div>
  );
}

export function BaseRates({ data }: { data: BaseRatesResponse }) {
  const metrics = ["gap_open_pct", "day1_close_pct", "day3_close_pct", "day5_close_pct"];
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {metrics.map((m) => {
        const d = data.distributions[m];
        if (!d) {
          return (
            <div
              key={m}
              className="border border-border rounded-md bg-panel p-3 text-xs text-muted"
            >
              {METRIC_LABELS[m] ?? m}: no distribution returned
            </div>
          );
        }
        return <StatRow key={m} d={d} />;
      })}
    </div>
  );
}
