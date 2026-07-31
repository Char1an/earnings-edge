import { Info } from "@/components/Info";
import { signedPct } from "@/lib/format";
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
  info,
  value,
  sub,
  tone,
}: {
  label: string;
  info?: React.ReactNode;
  value: string;
  sub?: string;
  tone?: "pos" | "neg" | "neutral";
}) {
  const toneClass =
    tone === "pos" ? "text-accent" : tone === "neg" ? "text-neg" : "text-text";
  return (
    <div className="flex-1 min-w-[8rem] border border-border rounded-md bg-bg px-3 py-2">
      <div className="text-[10px] uppercase tracking-wider text-muted flex items-center">
        {label}
        {info && <Info>{info}</Info>}
      </div>
      <div className={`text-lg font-mono ${toneClass}`}>{value}</div>
      {sub && <div className="text-[10px] text-muted mt-0.5">{sub}</div>}
    </div>
  );
}

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
    parts.push(
      `${greens}/${total} past quarterly results ended above pre-event price 5 trading days later`,
    );
  }
  const median = rates?.distributions?.day5_close_pct?.median;
  if (median != null && Math.abs(median) > 0.3) {
    parts.push(`median 5-day move ${median > 0 ? "+" : ""}${median.toFixed(1)}%`);
  }

  const drift = positioning?.delivery_pct_delta;
  if (drift != null && Math.abs(drift) > 1) {
    parts.push(
      `delivery-% ${drift > 0 ? "running" : "fading"} ${drift > 0 ? "+" : ""}${drift.toFixed(1)}pt vs its recent baseline`,
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
  const deliveryDelta = positioning?.delivery_pct_delta ?? null;
  const latestReaction = history[0]?.reaction ?? null;
  const latestPeriod = history[0]?.event?.fiscal_period ?? null;

  // Detect stale scraped data: a quarterly reporter's most recent quarter_end
  // should never be much more than ~4 months old. If it's over ~10 months old,
  // the Screener scrape almost certainly matched the wrong / an outdated page
  // (affects a handful of stocks like TATAELXSI, TTML, BAYERCROP).
  const latestQuarterEnd = history[0]?.event?.quarter_end ?? null;
  let staleAsOf: string | null = null;
  if (latestQuarterEnd) {
    const ageDays = (Date.now() - new Date(latestQuarterEnd).getTime()) / 86_400_000;
    if (ageDays > 300) staleAsOf = latestQuarterEnd;
  }

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
          label="Green after 5 days"
          info={
            <>
              How often the stock closed <em>above</em> its pre-result price 5 trading days
              after the quarterly earnings announcement, across past events. A quick base
              rate — not a prediction.
            </>
          }
          value={total ? `${greens} / ${total}` : "—"}
          sub={greenRate != null ? `${Math.round(greenRate * 100)}% hit rate` : "insufficient history"}
          tone={greenRate == null ? "neutral" : greenRate >= 0.6 ? "pos" : greenRate <= 0.4 ? "neg" : "neutral"}
        />
        <KpiTile
          label="Median 5-day move"
          info={
            <>
              Middle of the distribution of 5-day post-result moves across past events.
              Half the time the stock did better, half the time worse.
            </>
          }
          value={signedPct(medianD5)}
          tone={medianD5 == null ? "neutral" : medianD5 > 0.5 ? "pos" : medianD5 < -0.5 ? "neg" : "neutral"}
        />
        <KpiTile
          label="Last result: 5-day move"
          info={
            <>
              Where the stock closed 5 trading sessions after the pre-event close around
              its most recent quarterly result (the result day plus 4 more sessions).
              Useful as a "was it a normal outcome" reference — compare with the median
              and the histograms below.
            </>
          }
          value={signedPct(latestReaction?.day5_close_pct)}
          sub={latestPeriod ?? undefined}
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
          info={
            <>
              <b>Delivery %</b> = shares actually taken delivery of (settled to demat) as a
              share of the day's traded volume. High delivery = genuine buying/holding;
              low = day-trading churn.
              <br />
              This tile shows the last 20 trading sessions' average minus the 60 sessions
              before that, in percentage points. Positive = accumulation trend; negative =
              churn.
            </>
          }
          value={
            deliveryDelta != null
              ? `${deliveryDelta > 0 ? "+" : ""}${deliveryDelta.toFixed(1)}pt`
              : "—"
          }
          sub="last 20 sessions vs prior 60"
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

      {staleAsOf ? (
        <div className="text-xs text-neg border border-neg/40 bg-neg/10 rounded px-3 py-2">
          ⚠ Earnings data looks stale — the most recent quarter on file ended{" "}
          <span className="font-mono">{staleAsOf}</span>. This stock's data likely didn't
          map correctly during ingest; the numbers below are historical, not current.
        </div>
      ) : (
        <div className={`text-sm ${pctSign(medianD5)}`}>
          {headline(stock, history, rates, positioning)}
        </div>
      )}
    </div>
  );
}
