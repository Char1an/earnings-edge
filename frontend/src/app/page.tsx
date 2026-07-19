import { StockSearch } from "@/components/StockSearch";

export default function HomePage() {
  return (
    <div className="py-8">
      <h1 className="text-3xl font-semibold mb-3">
        Earnings analytics for the Nifty 500.
      </h1>
      <p className="text-muted mb-8 max-w-2xl">
        Historical base rates around quarterly results — gap, day-1/3/5 returns, and volume
        spikes — plus institutional positioning signals. Not a prediction tool. A quantified
        playbook.
      </p>

      <StockSearch />

      <div className="mt-12 grid grid-cols-1 md:grid-cols-3 gap-4">
        {[
          { t: "Historical", d: "Every past earnings event: gap, day1/3/5, volume spike, beat/miss." },
          { t: "Positioning", d: "Bulk & block deals, FII/DII flows, delivery %, insider trades (soon)." },
          { t: "Pattern match", d: "Similar past setups from this stock's own history (soon)." },
        ].map((c) => (
          <div key={c.t} className="border border-border rounded-md bg-panel p-4">
            <div className="text-sm font-medium mb-1">{c.t}</div>
            <div className="text-xs text-muted">{c.d}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
