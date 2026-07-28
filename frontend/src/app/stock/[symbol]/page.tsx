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
        <div className="flex items-baseline justify-between mb-3">
          <h2 className="text-lg font-medium">Positioning (30d)</h2>
          <div className="text-xs text-muted">
            FII/DII shown are market-wide, not stock-specific
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
        <div className="flex items-baseline justify-between mb-3">
          <h2 className="text-lg font-medium">Earnings history &amp; timeline ({history.length})</h2>
          <div className="text-xs text-muted">
            hover any row to preview its price path · click to pin
          </div>
        </div>
        <EarningsView items={history} timelines={timelines} />
      </section>

      <section>
        <div className="flex items-baseline justify-between mb-3">
          <h2 className="text-lg font-medium">
            Base rates {rates ? `(${rates.n_events} events)` : ""}
          </h2>
          <div className="text-xs text-muted">
            distribution of past reactions · orange line = last event's outcome
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
        <div className="flex items-baseline justify-between mb-3">
          <h2 className="text-lg font-medium">Similar past setups</h2>
          <div className="text-xs text-muted">
            cosine similarity on standardized features · anchored on the latest event
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
