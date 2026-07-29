"use client";

import { useMemo, useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { signedPct } from "@/lib/format";
import type { EventTimeline } from "@/lib/types";

/**
 * `selectedId` and `onSelect` make this a controlled component when passed
 * (used from EarningsView so hovering a table row updates the chart). Falls
 * back to internal state when used standalone.
 */
export function EventTimelineChart({
  timelines,
  selectedId,
  onSelect,
}: {
  timelines: EventTimeline[];
  selectedId?: number | null;
  onSelect?: (id: number) => void;
}) {
  const [internalId, setInternalId] = useState<number | null>(
    timelines[0]?.event_id ?? null,
  );
  const activeId = selectedId ?? internalId;
  const setActive = onSelect ?? setInternalId;

  const selected = useMemo(
    () => timelines.find((t) => t.event_id === activeId) ?? timelines[0],
    [timelines, activeId],
  );

  if (!timelines.length || !selected) {
    return (
      <div className="text-sm text-muted p-4 border border-border rounded-md bg-panel">
        No event timelines available yet — need earnings history with surrounding price data.
      </div>
    );
  }

  const data = selected.points.map((p) => ({
    offset: p.offset,
    pct: p.pct_from_pre,
    date: p.trade_date,
    close: p.close,
  }));

  const lastPct = data[data.length - 1]?.pct ?? 0;
  const stroke = lastPct > 0 ? "#3fb950" : lastPct < 0 ? "#f85149" : "#8b949e";

  return (
    <div className="border border-border rounded-md bg-panel p-3 space-y-3">
      <div className="flex flex-wrap gap-1.5">
        {timelines.map((t) => {
          const last = t.points[t.points.length - 1]?.pct_from_pre ?? 0;
          const dot = last > 0 ? "bg-accent" : last < 0 ? "bg-neg" : "bg-muted";
          const active = t.event_id === selected.event_id;
          return (
            <button
              key={t.event_id}
              onClick={() => setActive(t.event_id)}
              className={`text-xs font-mono px-2 py-1 rounded border transition-colors ${
                active
                  ? "bg-border border-border text-text"
                  : "border-border/40 text-muted hover:text-text hover:border-border"
              }`}
            >
              <span className={`inline-block w-1.5 h-1.5 rounded-full mr-1.5 ${dot}`} />
              {t.fiscal_period}
            </button>
          );
        })}
      </div>

      <div className="text-xs text-muted font-mono">
        {selected.fiscal_period} · announced {selected.announcement_date} · pre-event close ₹
        {selected.pre_close.toLocaleString("en-IN", { maximumFractionDigits: 2 })}
      </div>
      <div className="text-[11px] text-muted leading-snug">
        Y-axis = % change from the price the day before results.
        X-axis = trading days from the result day (labelled <span className="text-text">R</span>).
        A rising line to the right = the market kept liking the print after the initial reaction;
        a falling line = the initial reaction faded.
      </div>

      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 10 }}>
            <CartesianGrid stroke="#232a33" strokeDasharray="3 3" />
            <XAxis
              dataKey="offset"
              stroke="#7d8590"
              fontSize={10}
              tickLine={false}
              tickFormatter={(v) => (v === 0 ? "R" : v > 0 ? `+${v}` : `${v}`)}
              label={{
                value: "trading days from result",
                position: "insideBottom",
                offset: -5,
                fill: "#7d8590",
                fontSize: 10,
              }}
            />
            <YAxis
              stroke="#7d8590"
              fontSize={10}
              tickLine={false}
              width={45}
              tickFormatter={(v) => `${v > 0 ? "+" : ""}${v.toFixed(1)}%`}
            />
            <Tooltip
              cursor={{ stroke: "#8b949e", strokeDasharray: "3 3" }}
              contentStyle={{
                background: "#0b0d10",
                border: "1px solid #232a33",
                fontSize: 12,
              }}
              labelFormatter={(offset) => {
                const p = data.find((d) => d.offset === offset);
                return p ? `${p.date} (day ${offset > 0 ? `+${offset}` : offset})` : String(offset);
              }}
              formatter={(v: number, _name, item) => [
                `${signedPct(v)} · ₹${item.payload.close.toLocaleString("en-IN")}`,
                "vs pre-close",
              ]}
            />
            <ReferenceLine y={0} stroke="#3a3f47" strokeDasharray="3 3" />
            <ReferenceLine
              x={0}
              stroke="#f0883e"
              strokeDasharray="3 3"
              label={{ value: "result", position: "top", fill: "#f0883e", fontSize: 10 }}
            />
            <Line
              type="monotone"
              dataKey="pct"
              stroke={stroke}
              strokeWidth={2}
              dot={{ r: 2, fill: stroke }}
              activeDot={{ r: 4 }}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
