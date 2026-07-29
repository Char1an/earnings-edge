import { Info } from "@/components/Info";
import { signed, signedCr as fmtCr } from "@/lib/format";
import type { Positioning as PositioningData } from "@/lib/types";

const fmtPp = (v: number | null | undefined) => signed(v, { suffix: " pp" });

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

export function Positioning({ data, symbol = "this stock" }: { data: PositioningData; symbol?: string }) {
  const dealTone =
    data.deals_net_value_cr > 5 ? "pos" : data.deals_net_value_cr < -5 ? "neg" : "muted";
  const deliveryTone =
    (data.delivery_pct_delta ?? 0) > 2
      ? "pos"
      : (data.delivery_pct_delta ?? 0) < -2
        ? "neg"
        : "muted";

  // Plain-English read of the stock-specific signals.
  const delta = data.delivery_pct_delta;
  const readParts: string[] = [];
  if (delta != null && delta > 1)
    readParts.push("more of the volume is being taken to demat (accumulation)");
  else if (delta != null && delta < -1)
    readParts.push("less of the volume is being held (more intraday churn)");
  if (data.deals_net_value_cr > 5) readParts.push("net large-trade buying");
  else if (data.deals_net_value_cr < -5) readParts.push("net large-trade selling");
  else if (data.recent_deals.length === 0) readParts.push("no notable large trades");
  const readLine = readParts.length
    ? `For ${symbol}: ${readParts.join(", ")}.`
    : null;

  return (
    <div className="space-y-4">
      {/* Stock-specific signals — the ones that are actually about this stock. */}
      <div>
        <div className="text-[10px] uppercase tracking-wider text-muted mb-2">
          {symbol} specifically
        </div>
        <div className="grid grid-cols-2 gap-3">
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
        </div>
        {readLine && <div className="text-xs text-muted mt-2">{readLine}</div>}
      </div>

      {/* Market backdrop — deliberately muted so it doesn't read as a signal
          about this stock. Same numbers for every stock on the site. */}
      <div className="border border-border/60 rounded-md bg-bg/40 p-3">
        <div className="text-[10px] uppercase tracking-wider text-muted mb-2 flex items-center">
          Market backdrop — the whole market, not {symbol}
          <Info>
            These two figures are the net cash flow of institutions across the
            <em> entire Indian market</em> over the window — identical on every stock&apos;s
            page. Per-stock institutional flow isn&apos;t available on free data, so treat
            this only as overall market mood, never as buying/selling in {symbol}.
          </Info>
        </div>
        <div className="grid grid-cols-2 gap-3 text-muted">
          <div>
            <div className="text-[10px] uppercase tracking-wide text-muted">
              FII cash ({data.window_days}d)
            </div>
            <div className="font-mono text-sm">{fmtCr(data.fii_net_window_cr)}</div>
            <div className="text-[10px]">foreign institutions, market-wide</div>
          </div>
          <div>
            <div className="text-[10px] uppercase tracking-wide text-muted">
              DII cash ({data.window_days}d)
            </div>
            <div className="font-mono text-sm">{fmtCr(data.dii_net_window_cr)}</div>
            <div className="text-[10px]">domestic institutions, market-wide</div>
          </div>
        </div>
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
