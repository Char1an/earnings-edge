import { signedPct } from "@/lib/format";
import type {
  BaseRatesResponse,
  EarningsHistoryItem,
  Positioning as PositioningT,
  StockDetail,
} from "@/lib/types";

/**
 * Plain-English synthesis of the earnings-reaction signals for a first-time
 * reader. Strictly descriptive (base rates, not a forecast or recommendation) —
 * it translates the numbers the hero shows into sentences a non-analyst reads.
 */
export function ReadingCard({
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
  const sym = stock.symbol;
  const d5s = history
    .map((h) => h.reaction?.day5_close_pct)
    .filter((v): v is number => v != null);
  const total = d5s.length;

  // Not enough to say anything useful.
  if (total < 4) {
    return (
      <div className="border border-border rounded-md bg-panel p-4">
        <div className="text-sm font-medium mb-1">What the history says</div>
        <p className="text-sm text-muted">
          Not enough past earnings on file for {sym} to describe a reliable pattern yet.
        </p>
      </div>
    );
  }

  const greens = d5s.filter((v) => v > 0).length;
  const greenPct = Math.round((greens / total) * 100);
  const dist = rates?.distributions?.day5_close_pct ?? null;
  const median = dist?.median ?? null;
  const dMin = dist?.min ?? null;
  const dMax = dist?.max ?? null;

  // Classification — describes the historical earnings reaction, not the stock.
  let verdict: { label: string; tone: "pos" | "neg" | "neutral" };
  if (greenPct >= 60 && (median ?? 0) > 0.5) {
    verdict = { label: `${sym} has usually risen after results`, tone: "pos" };
  } else if (greenPct <= 40 && (median ?? 0) < -0.5) {
    verdict = { label: `${sym} has usually fallen after results`, tone: "neg" };
  } else {
    verdict = { label: `${sym} has been a coin-flip after results`, tone: "neutral" };
  }
  const pill =
    verdict.tone === "pos"
      ? "bg-accent/15 text-accent border-accent/40"
      : verdict.tone === "neg"
        ? "bg-neg/15 text-neg border-neg/40"
        : "bg-border text-text border-border";

  const sizeWord =
    median == null ? "" : Math.abs(median) < 2 ? "small" : Math.abs(median) < 5 ? "moderate" : "large";

  // Most recent result vs the usual pattern.
  const last = history[0]?.reaction?.day5_close_pct ?? null;
  const lastPeriod = history[0]?.event?.fiscal_period ?? null;
  let lastVsUsual: string | null = null;
  if (last != null && median != null) {
    if (last > median + 1) lastVsUsual = "stronger than its usual reaction";
    else if (last < median - 1) lastVsUsual = "weaker than its usual reaction";
    else lastVsUsual = "in line with its usual reaction";
  }

  // Delivery lean.
  const delta = positioning?.delivery_pct_delta ?? null;
  let deliveryNote: string | null = null;
  if (delta != null && delta > 1) {
    deliveryNote = `Delivery volume has been rising (${signedPct(delta, 1).replace("%", "pt")}) — often a sign buyers are holding, not just trading.`;
  } else if (delta != null && delta < -1) {
    deliveryNote = `Delivery volume has been fading (${signedPct(delta, 1).replace("%", "pt")}) — can signal weaker conviction behind recent buying.`;
  }

  const bullets: string[] = [];
  bullets.push(
    `After its last ${total} earnings, ${sym} was higher 5 trading days later ${greens} time${greens === 1 ? "" : "s"} (${greenPct}%).`,
  );
  if (median != null) {
    const range =
      dMin != null && dMax != null
        ? ` Past 5-day moves ranged from ${signedPct(dMin)} to ${signedPct(dMax)}.`
        : "";
    bullets.push(
      `The typical 5-day move was ${signedPct(median)} (a ${sizeWord} swing).${range}`,
    );
  }
  if (last != null && lastVsUsual) {
    bullets.push(
      `Its most recent result${lastPeriod ? ` (${lastPeriod})` : ""} moved ${signedPct(last)} over 5 days — ${lastVsUsual}.`,
    );
  }
  if (deliveryNote) bullets.push(deliveryNote);

  return (
    <div className="border border-border rounded-md bg-panel p-4 space-y-3">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="text-sm font-medium">What the history says</div>
        <span className={`text-xs px-2 py-1 rounded-full border ${pill}`}>{verdict.label}</span>
      </div>

      <ul className="space-y-1.5 text-sm text-text">
        {bullets.map((b, i) => (
          <li key={i} className="flex gap-2">
            <span className="text-muted select-none">•</span>
            <span>{b}</span>
          </li>
        ))}
      </ul>

      <p className="text-[11px] text-muted border-t border-border pt-2 leading-snug">
        This describes how {sym} has <em>reacted to past earnings</em> — a historical base
        rate, not a prediction of what happens next and not a recommendation to buy or sell.
        A high hit-rate does not mean the stock is a good long-term investment.
      </p>
    </div>
  );
}
