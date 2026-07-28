import type {
  BaseRatesResponse,
  EarningsHistoryItem,
  Positioning as PositioningT,
  StockDetail,
} from "@/lib/types";

const fmtRs = (v: number | null | undefined) =>
  v == null ? "—" : `₹${v.toLocaleString("en-IN", { maximumFractionDigits: 2 })}`;

function pctSign(v: number | null | undefined) {
  if (v == null) return "text-muted";
  if (v > 0.5) return "text-accent";
  if (v < -0.5) return "text-neg";
  return "text-text";
}

function KpiTile({
  label,
  value,
  sub,
  tone,
}: {
  label: string;
  value: string;
  sub?: string;
  tone?: "pos" | "neg" | "neutral";
}) {
  const toneClass =
    tone === "pos" ? "text-accent" : tone === "neg" ? "text-neg" : "text-text";
  return (
    <div className="flex-1 min-w-[8rem] border border-border rounded-md bg-bg px-3 py-2">
      <div className="text-[10px] uppercase tracking-wider text-muted">{label}</div>
      <div className={`text-lg font-mono ${toneClass}`}>{value}</div>
      {sub && <div className="text-[10px] text-muted mt-0.5">{sub}</div>}
    </div>
  );
}

/**
 * Compute a short, opinion-free headline from the numbers. Deliberately hedged
 * language — "usually goes green" not "is bullish."
 */
function headline(
  stock: StockDetail,
  history: EarningsHistoryItem[],
  rates: BaseRatesResponse | null,
  positioning: PositioningT | null,
): string {
  const parts: string[] = [];

  const d5s = history
    .map((h) => h.reaction?.day5_close_pct)
    .filter((v): v is number => v != null);
  if (d5s.length >= 4) {
    const greens = d5s.filter((v) => v > 0).length;
    const total = d5s.length;
    parts.push(`${greens}/${total} past prints closed green day-5`);
  }
  const median = rates?.distributions?.day5_close_pct?.median;
  if (median != null && Math.abs(median) > 0.3) {
    parts.push(`median day-5 ${median > 0 ? "+" : ""}${median.toFixed(1)}%`);
  }

  const drift = positioning?.delivery_pct_delta;
  if (drift != null && Math.abs(drift) > 1) {
    parts.push(
      `delivery ${drift > 0 ? "running" : "fading"} ${drift > 0 ? "+" : ""}${drift.toFixed(1)}pt vs baseline`,
    );
  }

  return parts.length ? parts.join(" · ") : `${stock.symbol} — insufficient history for a headline yet.`;
}

export function StockHero({
  stock,
  history,
  rates,
  positioning,
}: {
  stock: StockDetail;
  history: EarningsHistoryItem[];
  rates: BaseRatesResponse | null;
  positioning: PositioningT | null;
}) {
  const d5s = history
    .map((h) => h.reaction?.day5_close_pct)
    .filter((v): v is number => v != null);
  const greens = d5s.filter((v) => v > 0).length;
  const total = d5s.length;
  const greenRate = total ? greens / total : null;
  const medianD5 = rates?.distributions?.day5_close_pct?.median ?? null;

  // 20-day drift for the current tape: use the pattern-match anchor's drift
  // if we've got it, else fall back to the latest historical event's
  // "pre-event drift" (approximated from the most recent event's day-5? no —
  // we don't have current-live drift on this page. Use delivery delta as the
  // freshest positioning signal instead).
  const deliveryDelta = positioning?.delivery_pct_delta ?? null;
  const latestReaction = history[0]?.reaction ?? null;

  return (
    <div className="border border-border rounded-md bg-panel p-4 space-y-3">
      <div className="flex items-baseline justify-between flex-wrap gap-3">
        <div>
          <div className="flex items-baseline gap-3 flex-wrap">
            <h1 className="text-2xl font-semibold font-mono">{stock.symbol}</h1>
            <span className="text-sm text-muted">
              {stock.name ?? ""}
              {stock.sector ? ` · ${stock.sector}` : ""}
              {stock.is_fno ? " · F&O" : ""}
            </span>
          </div>
        </div>
        <div className="text-right">
          <div className="text-lg font-mono">{fmtRs(stock.latest_close)}</div>
          <div className="text-xs text-muted">
            as of {stock.latest_trade_date ?? "—"}
            {stock.latest_delivery_pct != null
              ? ` · delivery ${stock.latest_delivery_pct.toFixed(1)}%`
              : ""}
          </div>
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        <KpiTile
          label="Green day-5"
          value={total ? `${greens} / ${total}` : "—"}
          sub={greenRate != null ? `${Math.round(greenRate * 100)}% hit rate` : "insufficient history"}
          tone={greenRate == null ? "neutral" : greenRate >= 0.6 ? "pos" : greenRate <= 0.4 ? "neg" : "neutral"}
        />
        <KpiTile
          label="Median day-5"
          value={medianD5 != null ? `${medianD5 > 0 ? "+" : ""}${medianD5.toFixed(2)}%` : "—"}
          tone={medianD5 == null ? "neutral" : medianD5 > 0.5 ? "pos" : medianD5 < -0.5 ? "neg" : "neutral"}
        />
        <KpiTile
          label="Last event day-5"
          value={
            latestReaction?.day5_close_pct != null
              ? `${latestReaction.day5_close_pct > 0 ? "+" : ""}${latestReaction.day5_close_pct.toFixed(2)}%`
              : "—"
          }
          sub={history[0]?.event?.fiscal_period}
          tone={
            latestReaction?.day5_close_pct == null
              ? "neutral"
              : latestReaction.day5_close_pct > 0.5
                ? "pos"
                : latestReaction.day5_close_pct < -0.5
                  ? "neg"
                  : "neutral"
          }
        />
        <KpiTile
          label="Delivery vs baseline"
          value={
            deliveryDelta != null
              ? `${deliveryDelta > 0 ? "+" : ""}${deliveryDelta.toFixed(1)}pt`
              : "—"
          }
          sub="30d recent vs 90d baseline"
          tone={
            deliveryDelta == null
              ? "neutral"
              : deliveryDelta > 1
                ? "pos"
                : deliveryDelta < -1
                  ? "neg"
                  : "neutral"
          }
        />
      </div>

      <div className={`text-sm ${pctSign(medianD5)}`}>
        {headline(stock, history, rates, positioning)}
      </div>
    </div>
  );
}
