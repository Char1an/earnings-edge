import { notFound } from "next/navigation";

import { StockHero } from "@/components/StockHero";
import { BaseRates } from "@/components/panels/BaseRates";
import { EarningsView } from "@/components/panels/EarningsView";
import { PatternMatch } from "@/components/panels/PatternMatch";
import { Positioning } from "@/components/panels/Positioning";
import { api } from "@/lib/api";

type Props = { params: { symbol: string } };

export default async function StockPage({ params }: Props) {
  const symbol = decodeURIComponent(params.symbol).toUpperCase();

  let stock;
  try {
    stock = await api.getStock(symbol);
  } catch {
    notFound();
  }

  const [history, rates, positioning, patterns, timelines] = await Promise.all([
    api.earningsHistory(symbol, 20).catch(() => []),
    api.baseRates(symbol).catch(() => null),
    api.positioning(symbol, 30).catch(() => null),
    api.patterns(symbol, 5).catch(() => null),
    api.earningsTimelines(symbol, 10, 40).catch(() => []),
  ]);

  const latestReaction = history[0]?.reaction ?? null;
  const baseRateMarkers = latestReaction
    ? {
        gap_open_pct: latestReaction.gap_open_pct,
        day1_close_pct: latestReaction.day1_close_pct,
        day3_close_pct: latestReaction.day3_close_pct,
        day5_close_pct: latestReaction.day5_close_pct,
      }
    : undefined;

  return (
    <div className="space-y-8">
      <StockHero
        stock={stock}
        history={history}
        rates={rates}
        positioning={positioning}
      />

      <section>
        <div className="mb-3">
          <h2 className="text-lg font-medium">Positioning (last 30 days)</h2>
          <div className="text-xs text-muted">
            What the tape has been doing recently — big single trades in this stock, plus the
            broader institutional cash-flow backdrop across the whole market.
          </div>
        </div>
        {positioning ? (
          <Positioning data={positioning} />
        ) : (
          <div className="text-sm text-muted p-4 border border-border rounded-md bg-panel">
            positioning unavailable — deals / FII-DII / delivery ingests haven't run yet
          </div>
        )}
      </section>

      <section>
        <div className="mb-3">
          <h2 className="text-lg font-medium">Earnings history &amp; timeline ({history.length})</h2>
          <div className="text-xs text-muted">
            Each past quarterly result: the numbers reported and how the stock moved around it.
            Hover any row to preview its price path in the chart below; click to pin.
          </div>
        </div>
        <EarningsView items={history} timelines={timelines} />
      </section>

      <section>
        <div className="mb-3">
          <h2 className="text-lg font-medium">
            Base rates {rates ? `(${rates.n_events} past events)` : ""}
          </h2>
          <div className="text-xs text-muted">
            The <em>distribution</em> of past reactions — not a prediction. Each histogram
            shows how often the stock landed in each % range after past results. The orange
            vertical marks where the most recent event's outcome sat.
          </div>
        </div>
        {rates ? (
          <BaseRates data={rates} markers={baseRateMarkers} />
        ) : (
          <div className="text-sm text-muted p-4 border border-border rounded-md bg-panel">
            base rates unavailable — reactions have not been computed yet
          </div>
        )}
      </section>

      <section>
        <div className="mb-3">
          <h2 className="text-lg font-medium">Similar past setups</h2>
          <div className="text-xs text-muted">
            The 5 past quarterly results whose growth &amp; drift signature most closely
            resembles the most recent one — and what actually happened afterwards. Analogues,
            not forecasts.
          </div>
        </div>
        {patterns ? (
          <PatternMatch data={patterns} timelines={timelines} />
        ) : (
          <div className="text-sm text-muted p-4 border border-border rounded-md bg-panel">
            pattern match unavailable — need more earnings history + reactions
          </div>
        )}
      </section>
    </div>
  );
}
