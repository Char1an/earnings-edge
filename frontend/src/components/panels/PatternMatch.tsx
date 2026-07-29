import { EventSparkline } from "@/components/EventSparkline";
import { Info } from "@/components/Info";
import { signedPct as fmtPct } from "@/lib/format";
import type { EventTimeline, PatternsResponse } from "@/lib/types";

const FEATURE_LABELS: Record<string, string> = {
  yoy_revenue_growth: "YoY rev",
  yoy_pat_growth: "YoY PAT",
  qoq_revenue_growth: "QoQ rev",
  qoq_pat_growth: "QoQ PAT",
  drift_20d: "20d drift",
};

const fmtSim = (v: number) => v.toFixed(3);

function pctClass(v: number | null | undefined) {
  if (v == null) return "text-muted";
  if (v > 0.5) return "text-accent";
  if (v < -0.5) return "text-neg";
  return "text-text";
}

export function PatternMatch({
  data,
  timelines = [],
}: {
  data: PatternsResponse;
  timelines?: EventTimeline[];
}) {
  const timelineById = new Map(timelines.map((t) => [t.event_id, t]));

  if (data.anchor_event_id == null || data.matches.length === 0) {
    return (
      <div className="text-sm text-muted p-4 border border-border rounded-md bg-panel">
        Not enough earnings history yet to find similar setups. Need at least a
        few completed events with reactions.
      </div>
    );
  }

  const featureKeys = ["yoy_revenue_growth", "yoy_pat_growth", "qoq_revenue_growth", "qoq_pat_growth", "drift_20d"];

  return (
    <div className="space-y-3">
      <div className="border border-border rounded-md bg-panel p-3">
        <div className="text-xs text-muted uppercase tracking-wide mb-2 inline-flex items-center">
          This quarter's setup (most recent event)
          <Info>
            The growth and price-drift numbers going into the most recent result. The
            table below finds the 5 past events whose setup most closely resembles this
            one, and shows what actually happened afterwards.
          </Info>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3 font-mono text-sm">
          {featureKeys.map((k) => (
            <div key={k}>
              <div className="text-[10px] uppercase tracking-wide text-muted">
                {FEATURE_LABELS[k] ?? k}
              </div>
              <div className={pctClass(data.anchor_features[k])}>
                {fmtPct(data.anchor_features[k])}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="border border-border rounded-md bg-panel overflow-x-auto">
        <table className="w-full text-sm font-mono">
          <thead className="text-xs text-muted">
            <tr className="border-b border-border">
              <th className="text-left px-3 py-2">
                <span className="inline-flex items-center">
                  Match
                  <Info>
                    Similarity score from 0 (nothing in common) to 1 (identical growth
                    signature). Rows sorted best match first.
                  </Info>
                </span>
              </th>
              <th className="text-left px-3 py-2">Quarter</th>
              <th className="text-right px-3 py-2">Announced</th>
              <th className="text-right px-3 py-2">YoY PAT</th>
              <th className="text-right px-3 py-2">
                <span className="inline-flex items-center">
                  Drift 20d
                  <Info>
                    Stock's % return over the 20 trading days leading into the result —
                    i.e., how the tape was leaning heading in.
                  </Info>
                </span>
              </th>
              <th className="text-right px-3 py-2">Gap %</th>
              <th className="text-right px-3 py-2">1-day %</th>
              <th className="text-right px-3 py-2">5-day %</th>
              <th className="text-right px-3 py-2">Path (±10d)</th>
            </tr>
          </thead>
          <tbody>
            {data.matches.map((m) => {
              const tl = timelineById.get(m.event_id);
              return (
                <tr key={m.event_id} className="border-b border-border/60 last:border-b-0">
                  <td className="px-3 py-2">{fmtSim(m.similarity)}</td>
                  <td className="px-3 py-2">{m.fiscal_period}</td>
                  <td className="px-3 py-2 text-right text-muted">
                    {m.announcement_date ?? "—"}
                  </td>
                  <td className={`px-3 py-2 text-right ${pctClass(m.features.yoy_pat_growth)}`}>
                    {fmtPct(m.features.yoy_pat_growth)}
                  </td>
                  <td className={`px-3 py-2 text-right ${pctClass(m.features.drift_20d)}`}>
                    {fmtPct(m.features.drift_20d)}
                  </td>
                  <td className={`px-3 py-2 text-right ${pctClass(m.reaction?.gap_open_pct)}`}>
                    {fmtPct(m.reaction?.gap_open_pct ?? null)}
                  </td>
                  <td className={`px-3 py-2 text-right ${pctClass(m.reaction?.day1_close_pct)}`}>
                    {fmtPct(m.reaction?.day1_close_pct ?? null)}
                  </td>
                  <td className={`px-3 py-2 text-right ${pctClass(m.reaction?.day5_close_pct)}`}>
                    {fmtPct(m.reaction?.day5_close_pct ?? null)}
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
    </div>
  );
}
