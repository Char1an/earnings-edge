import { notFound } from "next/navigation";

import { BaseRates } from "@/components/panels/BaseRates";
import { HistoricalEarnings } from "@/components/panels/HistoricalEarnings";
import { Positioning } from "@/components/panels/Positioning";
import { api } from "@/lib/api";

type Props = { params: { symbol: string } };

const fmtRs = (v: number | null | undefined) =>
  v == null ? "—" : `₹${v.toLocaleString("en-IN", { maximumFractionDigits: 2 })}`;

export default async function StockPage({ params }: Props) {
  const symbol = decodeURIComponent(params.symbol).toUpperCase();

  let stock;
  try {
    stock = await api.getStock(symbol);
  } catch {
    notFound();
  }

  const [history, rates, positioning] = await Promise.all([
    api.earningsHistory(symbol, 20).catch(() => []),
    api.baseRates(symbol).catch(() => null),
    api.positioning(symbol, 30).catch(() => null),
  ]);

  return (
    <div className="space-y-8">
      <div className="flex items-baseline justify-between flex-wrap gap-2">
        <div>
          <h1 className="text-2xl font-semibold font-mono">{stock.symbol}</h1>
          <div className="text-sm text-muted">
            {stock.name ?? ""} {stock.sector ? `· ${stock.sector}` : ""}{" "}
            {stock.is_fno ? "· F&O" : ""}
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
          <h2 className="text-lg font-medium">Historical earnings ({history.length})</h2>
          <div className="text-xs text-muted">
            reactions with low confidence should be treated as noise
          </div>
        </div>
        <HistoricalEarnings items={history} />
      </section>

      <section>
        <div className="flex items-baseline justify-between mb-3">
          <h2 className="text-lg font-medium">
            Base rates {rates ? `(${rates.n_events} events)` : ""}
          </h2>
          <div className="text-xs text-muted">
            distribution of past reactions — median &amp; quartiles
          </div>
        </div>
        {rates ? (
          <BaseRates data={rates} />
        ) : (
          <div className="text-sm text-muted p-4 border border-border rounded-md bg-panel">
            base rates unavailable — reactions have not been computed yet
          </div>
        )}
      </section>
    </div>
  );
}
