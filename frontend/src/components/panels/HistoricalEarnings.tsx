"use client";

import { EventSparkline } from "@/components/EventSparkline";
import type { EarningsHistoryItem, EventTimeline } from "@/lib/types";

const fmtPct = (v: number | null | undefined) =>
  v == null ? "—" : `${v > 0 ? "+" : ""}${v.toFixed(2)}%`;
const fmtCr = (v: number | null | undefined) =>
  v == null ? "—" : v >= 1000 ? `₹${(v / 1000).toFixed(2)}k Cr` : `₹${v.toFixed(0)} Cr`;
const fmtNum = (v: number | null | undefined) =>
  v == null ? "—" : v.toFixed(2);

function pctClass(v: number | null | undefined) {
  if (v == null) return "text-muted";
  if (v > 0.5) return "text-accent";
  if (v < -0.5) return "text-neg";
  return "text-text";
}

export function HistoricalEarnings({
  items,
  timelines = [],
  selectedId = null,
  pinnedId = null,
  onHover,
  onPin,
}: {
  items: EarningsHistoryItem[];
  timelines?: EventTimeline[];
  selectedId?: number | null;
  pinnedId?: number | null;
  onHover?: (id: number | null) => void;
  onPin?: (id: number) => void;
}) {
  const timelineById = new Map(timelines.map((t) => [t.event_id, t]));
  if (!items.length) {
    return (
      <div className="text-sm text-muted p-4 border border-border rounded-md bg-panel">
        No earnings history yet for this stock. Run the Screener scraper (weekly job) and
        the compute_reactions step.
      </div>
    );
  }

  return (
    <div className="border border-border rounded-md bg-panel overflow-x-auto">
      <table className="w-full text-sm font-mono">
        <thead className="text-xs text-muted">
          <tr className="border-b border-border">
            <th className="text-left px-3 py-2">Quarter</th>
            <th className="text-right px-3 py-2">Announced</th>
            <th className="text-right px-3 py-2">Rev (Cr)</th>
            <th className="text-right px-3 py-2">PAT (Cr)</th>
            <th className="text-right px-3 py-2">YoY PAT</th>
            <th className="text-right px-3 py-2">Gap</th>
            <th className="text-right px-3 py-2">Day1</th>
            <th className="text-right px-3 py-2">Day5</th>
            <th className="text-right px-3 py-2">Vol×</th>
            <th className="text-right px-3 py-2">Conf</th>
            <th className="text-right px-3 py-2">Path (±10d)</th>
          </tr>
        </thead>
        <tbody>
          {items.map(({ event: e, reaction: r }) => {
            const tl = timelineById.get(e.id);
            const isSelected = e.id === selectedId;
            const isPinned = e.id === pinnedId;
            const interactive = tl != null && (onHover || onPin);
            return (
              <tr
                key={e.id}
                onMouseEnter={interactive && onHover ? () => onHover(e.id) : undefined}
                onMouseLeave={interactive && onHover ? () => onHover(null) : undefined}
                onClick={interactive && onPin ? () => onPin(e.id) : undefined}
                className={[
                  "border-b border-border/60 last:border-b-0 transition-colors",
                  interactive ? "cursor-pointer" : "",
                  isSelected ? "bg-border/50" : "hover:bg-border/25",
                ].join(" ")}
                title={interactive ? "hover to preview timeline, click to pin" : undefined}
              >
                <td className="px-3 py-2">
                  <span className="inline-flex items-center gap-1.5">
                    {isPinned && (
                      <span
                        className="inline-block w-1.5 h-1.5 rounded-full bg-accent"
                        aria-label="pinned"
                      />
                    )}
                    {e.fiscal_period}
                  </span>
                </td>
                <td className="px-3 py-2 text-right text-muted">
                  {e.announcement_date ?? "—"}
                </td>
                <td className="px-3 py-2 text-right">{fmtCr(e.revenue_cr)}</td>
                <td className="px-3 py-2 text-right">{fmtCr(e.pat_cr)}</td>
                <td className={`px-3 py-2 text-right ${pctClass(e.yoy_pat_growth)}`}>
                  {fmtPct(e.yoy_pat_growth)}
                </td>
                <td className={`px-3 py-2 text-right ${pctClass(r?.gap_open_pct)}`}>
                  {fmtPct(r?.gap_open_pct ?? null)}
                </td>
                <td className={`px-3 py-2 text-right ${pctClass(r?.day1_close_pct)}`}>
                  {fmtPct(r?.day1_close_pct ?? null)}
                </td>
                <td className={`px-3 py-2 text-right ${pctClass(r?.day5_close_pct)}`}>
                  {fmtPct(r?.day5_close_pct ?? null)}
                </td>
                <td className="px-3 py-2 text-right text-muted">{fmtNum(r?.volume_spike)}</td>
                <td className="px-3 py-2 text-right text-muted">
                  {fmtNum(r?.detection_confidence)}
                </td>
                <td className="px-3 py-2 text-right">
                  {tl ? <EventSparkline points={tl.points} /> : <span className="text-muted">—</span>}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
