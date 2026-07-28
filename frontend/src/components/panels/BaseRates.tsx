"use client";

import { Bar, BarChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { Info } from "@/components/Info";
import type { BaseRatesResponse, Distribution } from "@/lib/types";

const METRIC_LABELS: Record<string, string> = {
  gap_open_pct: "Gap open",
  day1_close_pct: "1-day close",
  day3_close_pct: "3-day close",
  day5_close_pct: "5-day close",
};

const METRIC_TIPS: Record<string, string> = {
  gap_open_pct:
    "How the stock opened on the result day vs the previous close, in %. Each bar counts past events that fell into that range.",
  day1_close_pct:
    "Close on the result day vs pre-event close. Each bar counts past events in that % range.",
  day3_close_pct:
    "Close 3 trading days after the result vs pre-event close.",
  day5_close_pct:
    "Close 5 trading days after the result vs pre-event close.",
};

function toChart(d: Distribution) {
  return d.hist_counts.map((c, i) => {
    const edge = d.hist_bin_edges[i];
    // Normalize negative zero → 0 to avoid "-0.0" bin labels on the axis.
    const normalized = edge != null && Object.is(edge, -0) ? 0 : edge;
    return {
      bin: normalized != null ? normalized.toFixed(1) : "",
      binVal: normalized,
      count: c,
    };
  });
}

/**
 * Closest histogram bin label for a value — used to position a ReferenceLine
 * on a Recharts BarChart with categorical XAxis.
 */
function nearestBinLabel(d: Distribution, value: number): string | null {
  if (d.hist_bin_edges.length === 0) return null;
  let bestIdx = 0;
  let bestDist = Infinity;
  for (let i = 0; i < d.hist_bin_edges.length; i++) {
    const dist = Math.abs(d.hist_bin_edges[i] - value);
    if (dist < bestDist) {
      bestDist = dist;
      bestIdx = i;
    }
  }
  const raw = d.hist_bin_edges[bestIdx];
  const normalized = raw != null && Object.is(raw, -0) ? 0 : raw;
  return normalized != null ? normalized.toFixed(1) : null;
}

function StatRow({ d, marker }: { d: Distribution; marker: number | null }) {
  const label = METRIC_LABELS[d.metric] ?? d.metric;
  const markerLabel = marker != null && d.n > 0 ? nearestBinLabel(d, marker) : null;
  const markerPercentile =
    marker != null && d.n > 0 && d.min != null && d.max != null && d.max > d.min
      ? Math.round(((marker - d.min) / (d.max - d.min)) * 100)
      : null;
  return (
    <div className="border border-border rounded-md bg-panel">
      <div className="flex items-baseline justify-between px-3 py-2 border-b border-border">
        <div className="text-sm font-medium inline-flex items-center">
          {label}
          <Info>{METRIC_TIPS[d.metric] ?? ""}</Info>
        </div>
        <div className="text-xs text-muted font-mono inline-flex items-center">
          n = {d.n}
          <Info side="left">Number of past events with a computed reaction.</Info>
        </div>
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
                {markerLabel != null && (
                  <ReferenceLine
                    x={markerLabel}
                    stroke="#f0883e"
                    strokeWidth={2}
                    strokeDasharray="3 3"
                    label={{
                      value: "last",
                      position: "top",
                      fill: "#f0883e",
                      fontSize: 9,
                    }}
                  />
                )}
                <Bar dataKey="count" fill="#3fb950" />
              </BarChart>
            </ResponsiveContainer>
          </div>
          {marker != null && markerPercentile != null && (
            <div className="px-3 py-2 border-t border-border text-[11px] text-muted font-mono">
              last event: {marker > 0 ? "+" : ""}
              {marker.toFixed(2)}% · sits at ~{markerPercentile}th percentile of history
            </div>
          )}
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

export function BaseRates({
  data,
  markers,
}: {
  data: BaseRatesResponse;
  markers?: Record<string, number | null>;
}) {
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
        return <StatRow key={m} d={d} marker={markers?.[m] ?? null} />;
      })}
    </div>
  );
}
