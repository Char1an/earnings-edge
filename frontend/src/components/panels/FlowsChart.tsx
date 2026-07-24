"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { FiiDiiPoint } from "@/lib/types";

export function FlowsChart({ points }: { points: FiiDiiPoint[] }) {
  if (points.length === 0) {
    return (
      <div className="text-sm text-muted p-4 border border-border rounded-md bg-panel">
        No FII/DII data yet — will populate after the next weekday ingest.
      </div>
    );
  }

  const data = points.map((p) => ({
    date: p.trade_date.slice(5),
    FII: p.fii_cash_net_cr ?? 0,
    DII: p.dii_cash_net_cr ?? 0,
  }));

  return (
    <div className="border border-border rounded-md bg-panel p-3">
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} stackOffset="sign">
            <CartesianGrid stroke="#232a33" strokeDasharray="3 3" />
            <XAxis dataKey="date" stroke="#7d8590" fontSize={10} tickLine={false} />
            <YAxis stroke="#7d8590" fontSize={10} tickLine={false} width={50} />
            <Tooltip
              cursor={{ fill: "rgba(255,255,255,0.05)" }}
              contentStyle={{
                background: "#0b0d10",
                border: "1px solid #232a33",
                fontSize: 12,
              }}
              formatter={(v: number) => `${v > 0 ? "+" : ""}₹${v.toFixed(0)} Cr`}
            />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            <Bar dataKey="FII" fill="#f85149" stackId="net" />
            <Bar dataKey="DII" fill="#3fb950" stackId="net" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
