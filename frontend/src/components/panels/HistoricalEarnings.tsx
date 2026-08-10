"use client";

import { EventSparkline } from "@/components/EventSparkline";
import { Info } from "@/components/Info";
import { signedPct as fmtPct } from "@/lib/format";
import type { EarningsHistoryItem, EventTimeline } from "@/lib/types";

const fmtCr = (v: number | null | undefined) => {
  if (v == null) return "—";
  // Sign goes before the ₹ (not "₹-45"), and the k-abbreviation keys off magnitude so
  // loss quarters (negative PAT, e.g. HINDPETRO -12,265) render as "-₹12.27k Cr" rather
  // than a bare "₹-12265 Cr" (old code skipped the >=1000 branch for negatives).
  const sign = v < 0 ? "-" : "";
  const a = Math.abs(v);
  return a >= 1000 ? `${sign}₹${(a / 1000).toFixed(2)}k Cr` : `${sign}₹${a.toFixed(0)} Cr`;
};
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
            <th className="text-left px-3 py-2">
              <span className="inline-flex items-center">
                Quarter
                <Info>
                  Indian fiscal-year quarter. Q1 = Apr–Jun, Q2 = Jul–Sep, Q3 = Oct–Dec,
                  Q4 = Jan–Mar. "Q1FY27" means Apr–Jun 2026 (FY27 = the year ending Mar
                  2027).
                </Info>
              </span>
            </th>
            <th className="text-right px-3 py-2">Announced</th>
            <th className="text-right px-3 py-2">
              <span className="inline-flex items-center">
                Rev (Cr)
                <Info>Revenue for the quarter in ₹ Crore (1 Cr = ₹10,000,000).</Info>
              </span>
            </th>
            <th className="text-right px-3 py-2">
              <span className="inline-flex items-center">
                PAT (Cr)
                <Info>Profit After Tax for the quarter, in ₹ Crore.</Info>
              </span>
            </th>
            <th className="text-right px-3 py-2">
              <span className="inline-flex items-center">
                YoY PAT
                <Info>
                  Profit growth vs the same quarter in the previous fiscal year.
                  Positive = higher profit than a year ago.
                </Info>
              </span>
            </th>
            <th className="text-right px-3 py-2">
              <span className="inline-flex items-center">
                Gap %
                <Info>
                  How the stock opened on the result day vs the previous trading day's
                  close, in %. A positive gap = opened above pre-event close.
                </Info>
              </span>
            </th>
            <th className="text-right px-3 py-2">
              <span className="inline-flex items-center">
                1-day %
                <Info>
                  Where the stock closed on the result day itself, vs the pre-event
                  close. This is the same-day reaction the market delivered.
                </Info>
              </span>
            </th>
            <th className="text-right px-3 py-2">
              <span className="inline-flex items-center">
                5-day %
                <Info>
                  Where the stock closed 5 trading sessions after the pre-event close
                  (i.e. the result day plus 4 more sessions). Captures the post-result
                  drift, not just the same-day pop.
                </Info>
              </span>
            </th>
            <th className="text-right px-3 py-2">
              <span className="inline-flex items-center">
                Vol ×
                <Info>
                  Volume on the result day divided by the 20-session average volume.
                  2.0 = twice normal. Big prints usually spike above 1.5.
                </Info>
              </span>
            </th>
            <th className="text-right px-3 py-2">
              <span className="inline-flex items-center">
                Conf
                <Info>
                  Detection confidence — how much the price + volume signature on the
                  detected day stood out from the surrounding weeks. Higher = more
                  likely a real result day. Low confidence (&lt; 3) should be treated as
                  noisy.
                </Info>
              </span>
            </th>
            <th className="text-right px-3 py-2">
              <span className="inline-flex items-center">
                Path (±10d)
                <Info side="left">
                  Mini price chart from 10 trading days before to 10 after the result.
                  Dashed horizontal = pre-event close (0%). Dashed vertical = result
                  day. Line coloured green if it ended above pre-event close, red if
                  below.
                </Info>
              </span>
            </th>
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
