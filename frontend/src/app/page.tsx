import Link from "next/link";

import { FlowsChart } from "@/components/panels/FlowsChart";
import { StockSearch } from "@/components/StockSearch";
import { api } from "@/lib/api";
import type { NotableDeal, UpcomingEarning } from "@/lib/types";

const fmtCr = (v: number | null | undefined) => {
  if (v == null) return "—";
  return `₹${Math.abs(v).toLocaleString("en-IN", { maximumFractionDigits: 1 })} Cr`;
};

export default async function HomePage() {
  const home = await api.home().catch(() => null);

  return (
    <div className="space-y-10 py-4">
      <section>
        <h1 className="text-3xl font-semibold mb-3">
          Earnings analytics for the Nifty 500.
        </h1>
        <p className="text-muted mb-6 max-w-2xl">
          Historical base rates around quarterly results, positioning signals, and pattern
          matching. Not a prediction tool — a quantified playbook.
        </p>
        <StockSearch />
      </section>

      <section>
        <div className="flex items-baseline justify-between mb-3">
          <h2 className="text-lg font-medium">Upcoming earnings (next 14 days)</h2>
          <div className="text-xs text-muted">
            estimated: last announcement + 91 days
          </div>
        </div>
        <UpcomingList items={home?.upcoming ?? []} />
      </section>

      <section>
        <div className="flex items-baseline justify-between mb-3">
          <h2 className="text-lg font-medium">Notable deals (last 7 days)</h2>
          <div className="text-xs text-muted">top 15 bulk + block by value</div>
        </div>
        <NotableDealsList items={home?.notable_deals ?? []} />
      </section>

      <section>
        <div className="flex items-baseline justify-between mb-3">
          <h2 className="text-lg font-medium">FII / DII cash flow (30d)</h2>
          <div className="text-xs text-muted">market-wide net buying (₹ Cr)</div>
        </div>
        <FlowsChart points={home?.fii_dii_series ?? []} />
      </section>
    </div>
  );
}

function UpcomingList({ items }: { items: UpcomingEarning[] }) {
  if (items.length === 0) {
    return (
      <div className="text-sm text-muted p-4 border border-border rounded-md bg-panel">
        No stocks estimated to announce in the next 14 days.
      </div>
    );
  }
  return (
    <div className="border border-border rounded-md bg-panel overflow-x-auto">
      <table className="w-full text-sm font-mono">
        <thead className="text-xs text-muted">
          <tr className="border-b border-border">
            <th className="text-left px-3 py-2">Symbol</th>
            <th className="text-left px-3 py-2">Sector</th>
            <th className="text-right px-3 py-2">Expected date</th>
            <th className="text-right px-3 py-2">In days</th>
            <th className="text-left px-3 py-2">Last Q announced</th>
          </tr>
        </thead>
        <tbody>
          {items.slice(0, 20).map((u) => (
            <tr key={u.symbol} className="border-b border-border/60 last:border-b-0">
              <td className="px-3 py-2">
                <Link
                  href={`/stock/${encodeURIComponent(u.symbol)}`}
                  className="text-accent hover:underline"
                >
                  {u.symbol}
                </Link>
              </td>
              <td className="px-3 py-2 text-xs text-muted truncate max-w-[14rem]">
                {u.sector ?? "—"}
              </td>
              <td className="px-3 py-2 text-right">{u.expected_next_date}</td>
              <td className="px-3 py-2 text-right text-muted">{u.days_until}</td>
              <td className="px-3 py-2 text-xs text-muted">
                {u.last_fiscal_period} · {u.last_announcement_date}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {items.length > 20 && (
        <div className="px-3 py-2 text-xs text-muted border-t border-border">
          showing 20 of {items.length}
        </div>
      )}
    </div>
  );
}

function NotableDealsList({ items }: { items: NotableDeal[] }) {
  if (items.length === 0) {
    return (
      <div className="text-sm text-muted p-4 border border-border rounded-md bg-panel">
        No bulk / block deals reported yet — will populate after the next weekday ingest.
      </div>
    );
  }
  return (
    <div className="border border-border rounded-md bg-panel overflow-x-auto">
      <table className="w-full text-sm font-mono">
        <thead className="text-xs text-muted">
          <tr className="border-b border-border">
            <th className="text-left px-3 py-2">Date</th>
            <th className="text-left px-3 py-2">Symbol</th>
            <th className="text-left px-3 py-2">Type</th>
            <th className="text-left px-3 py-2">Side</th>
            <th className="text-left px-3 py-2">Client</th>
            <th className="text-right px-3 py-2">Value</th>
          </tr>
        </thead>
        <tbody>
          {items.map((d, i) => (
            <tr key={i} className="border-b border-border/60 last:border-b-0">
              <td className="px-3 py-2 text-muted">{d.trade_date}</td>
              <td className="px-3 py-2">
                <Link
                  href={`/stock/${encodeURIComponent(d.symbol)}`}
                  className="text-accent hover:underline"
                >
                  {d.symbol}
                </Link>
              </td>
              <td className="px-3 py-2 text-muted text-xs">{d.deal_type}</td>
              <td
                className={`px-3 py-2 ${
                  d.buy_sell === "BUY" ? "text-accent" : "text-neg"
                }`}
              >
                {d.buy_sell}
              </td>
              <td className="px-3 py-2 text-xs truncate max-w-[22rem]">
                {d.client_name || "—"}
              </td>
              <td className="px-3 py-2 text-right">{fmtCr(d.value_cr)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
