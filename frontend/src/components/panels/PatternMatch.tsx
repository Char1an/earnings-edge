import type { PatternsResponse } from "@/lib/types";

const FEATURE_LABELS: Record<string, string> = {
  yoy_revenue_growth: "YoY rev",
  yoy_pat_growth: "YoY PAT",
  qoq_revenue_growth: "QoQ rev",
  qoq_pat_growth: "QoQ PAT",
  drift_20d: "20d drift",
};

const fmtPct = (v: number | null | undefined) => {
  if (v == null || Number.isNaN(v)) return "—";
  return `${v > 0 ? "+" : ""}${v.toFixed(2)}%`;
};
const fmtSim = (v: number) => v.toFixed(3);

function pctClass(v: number | null | undefined) {
  if (v == null) return "text-muted";
  if (v > 0.5) return "text-accent";
  if (v < -0.5) return "text-neg";
  return "text-text";
}

export function PatternMatch({ data }: { data: PatternsResponse }) {
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
        <div className="text-xs text-muted uppercase tracking-wide mb-2">
          Anchor setup (most recent event)
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
              <th className="text-left px-3 py-2">Sim</th>
              <th className="text-left px-3 py-2">Quarter</th>
              <th className="text-right px-3 py-2">Announced</th>
              <th className="text-right px-3 py-2">YoY PAT</th>
              <th className="text-right px-3 py-2">Drift 20d</th>
              <th className="text-right px-3 py-2">Gap</th>
              <th className="text-right px-3 py-2">Day1</th>
              <th className="text-right px-3 py-2">Day5</th>
            </tr>
          </thead>
          <tbody>
            {data.matches.map((m) => (
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
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
