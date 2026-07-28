import { Info } from "@/components/Info";
import type { Positioning as PositioningData } from "@/lib/types";

const fmtCr = (v: number | null | undefined) => {
  if (v == null) return "—";
  const sign = v > 0 ? "+" : v < 0 ? "-" : "";
  return `${sign}₹${Math.abs(v).toLocaleString("en-IN", { maximumFractionDigits: 2 })} Cr`;
};

const fmtPp = (v: number | null | undefined) =>
  v == null ? "—" : `${v > 0 ? "+" : ""}${v.toFixed(2)} pp`;

function Tile({
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
  tone?: "pos" | "neg" | "muted";
}) {
  const color =
    tone === "pos"
      ? "text-accent"
      : tone === "neg"
        ? "text-neg"
        : tone === "muted"
          ? "text-muted"
          : "text-text";
  return (
    <div className="border border-border rounded-md bg-panel p-3">
      <div className="text-[10px] uppercase tracking-wide text-muted flex items-center">
        {label}
        {info && <Info>{info}</Info>}
      </div>
      <div className={`font-mono text-lg ${color}`}>{value}</div>
      {sub && <div className="text-xs text-muted mt-1">{sub}</div>}
    </div>
  );
}

export function Positioning({ data }: { data: PositioningData }) {
  const dealTone =
    data.deals_net_value_cr > 5 ? "pos" : data.deals_net_value_cr < -5 ? "neg" : "muted";
  const deliveryTone =
    (data.delivery_pct_delta ?? 0) > 2
      ? "pos"
      : (data.delivery_pct_delta ?? 0) < -2
        ? "neg"
        : "muted";
  const fiiTone =
    (data.fii_net_window_cr ?? 0) > 0 ? "pos" : (data.fii_net_window_cr ?? 0) < 0 ? "neg" : "muted";

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Tile
          label={`Big-trade net (${data.window_days}d)`}
          info={
            <>
              Net value of <b>bulk</b> and <b>block</b> deals in this stock over the last
              {" "}{data.window_days} days. Bulk = a single trade above 0.5% of listed
              shares; block = a pre-negotiated trade above ₹5 Cr, reported to the
              exchange. Positive = more/larger buys than sells.
            </>
          }
          value={fmtCr(data.deals_net_value_cr)}
          sub={`${data.deals_buy_count} buys · ${data.deals_sell_count} sells`}
          tone={dealTone}
        />
        <Tile
          label="Delivery % trend"
          info={
            <>
              <b>Delivery %</b> = shares that were actually taken delivery of (settled to
              a demat account), as a fraction of the day's total traded volume. Rest is
              intraday churn.
              <br />
              Value here is the last 20 trading sessions' average minus the 60 sessions
              before that, in percentage points. Rising = accumulation; falling = churn.
            </>
          }
          value={fmtPp(data.delivery_pct_delta)}
          sub={
            data.delivery_pct_recent != null && data.delivery_pct_baseline != null
              ? `${data.delivery_pct_recent.toFixed(1)}% vs ${data.delivery_pct_baseline.toFixed(1)}% baseline`
              : "insufficient history"
          }
          tone={deliveryTone}
        />
        <Tile
          label={`FII cash (market, ${data.window_days}d)`}
          info={
            <>
              <b>FII</b> = Foreign Institutional Investors. Net cash flow across the
              <em> whole Indian equity market</em>, not this stock specifically —
              per-stock FII data isn't public on free feeds. Read as macro backdrop.
              <br />
              Positive = FIIs net buyers; negative = net sellers.
            </>
          }
          value={fmtCr(data.fii_net_window_cr)}
          sub="market-wide, not stock-specific"
          tone={fiiTone}
        />
        <Tile
          label={`DII cash (market, ${data.window_days}d)`}
          info={
            <>
              <b>DII</b> = Domestic Institutional Investors (mutual funds, insurance,
              banks). Same market-wide caveat as FII. Often moves in the opposite
              direction to FII — when FIIs sell, DIIs frequently absorb it.
            </>
          }
          value={fmtCr(data.dii_net_window_cr)}
          sub="market-wide, not stock-specific"
          tone={
            data.dii_net_window_cr == null
              ? "muted"
              : data.dii_net_window_cr > 0
                ? "pos"
                : "neg"
          }
        />
      </div>

      <div>
        <div className="text-xs text-muted mb-2 uppercase tracking-wide flex items-center">
          Recent bulk &amp; block deals
          <Info>
            Individual reported large trades in this stock (bulk ≥0.5% of listed shares,
            block ≥₹5 Cr pre-negotiated). Empty = no notable single trades in the window,
            which is common for many stocks. Watch for named institutional buyers/sellers.
          </Info>
        </div>
        {data.recent_deals.length === 0 ? (
          <div className="text-sm text-muted p-4 border border-border rounded-md bg-panel">
            no reported deals in the last {data.window_days} days
          </div>
        ) : (
          <div className="border border-border rounded-md bg-panel overflow-x-auto">
            <table className="w-full text-sm font-mono">
              <thead className="text-xs text-muted">
                <tr className="border-b border-border">
                  <th className="text-left px-3 py-2">Date</th>
                  <th className="text-left px-3 py-2">Type</th>
                  <th className="text-left px-3 py-2">Side</th>
                  <th className="text-left px-3 py-2">Client</th>
                  <th className="text-right px-3 py-2">Qty</th>
                  <th className="text-right px-3 py-2">Price</th>
                  <th className="text-right px-3 py-2">Value (Cr)</th>
                </tr>
              </thead>
              <tbody>
                {data.recent_deals.slice(0, 15).map((d, i) => (
                  <tr key={i} className="border-b border-border/60 last:border-b-0">
                    <td className="px-3 py-2">{d.trade_date}</td>
                    <td className="px-3 py-2 text-muted">{d.deal_type}</td>
                    <td
                      className={`px-3 py-2 ${
                        d.buy_sell === "BUY" ? "text-accent" : "text-neg"
                      }`}
                    >
                      {d.buy_sell}
                    </td>
                    <td className="px-3 py-2 text-xs">
                      {d.client_name || <span className="text-muted">—</span>}
                    </td>
                    <td className="px-3 py-2 text-right">
                      {d.quantity.toLocaleString("en-IN")}
                    </td>
                    <td className="px-3 py-2 text-right">₹{d.price.toFixed(2)}</td>
                    <td className="px-3 py-2 text-right">
                      {d.value_cr == null ? "—" : d.value_cr.toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {data.recent_deals.length > 15 && (
              <div className="px-3 py-2 text-xs text-muted border-t border-border">
                showing 15 of {data.recent_deals.length}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
