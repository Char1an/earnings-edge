import type {
  BaseRatesResponse,
  EarningsHistoryItem,
  FiiDiiPoint,
  PatternsResponse,
  Positioning,
  StockDetail,
  StockSummary,
} from "./types";

const BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

async function get<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}/api/v1${path}`, {
    cache: "no-store",
    ...init,
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`GET ${path} → ${res.status} ${body.slice(0, 200)}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  listStocks: (params: { q?: string; sector?: string; in_fno?: boolean; limit?: number } = {}) => {
    const qs = new URLSearchParams();
    if (params.q) qs.set("q", params.q);
    if (params.sector) qs.set("sector", params.sector);
    if (params.in_fno !== undefined) qs.set("in_fno", String(params.in_fno));
    if (params.limit) qs.set("limit", String(params.limit));
    const q = qs.toString();
    return get<StockSummary[]>(`/stocks${q ? `?${q}` : ""}`);
  },
  getStock: (symbol: string) => get<StockDetail>(`/stocks/${encodeURIComponent(symbol)}`),
  earningsHistory: (symbol: string, limit = 20) =>
    get<EarningsHistoryItem[]>(
      `/stocks/${encodeURIComponent(symbol)}/earnings/history?limit=${limit}`,
    ),
  baseRates: (
    symbol: string,
    opts: { min_confidence?: number; only_beat_yoy_pat?: boolean; only_miss_yoy_pat?: boolean } = {},
  ) => {
    const qs = new URLSearchParams();
    if (opts.min_confidence !== undefined) qs.set("min_confidence", String(opts.min_confidence));
    if (opts.only_beat_yoy_pat) qs.set("only_beat_yoy_pat", "true");
    if (opts.only_miss_yoy_pat) qs.set("only_miss_yoy_pat", "true");
    const q = qs.toString();
    return get<BaseRatesResponse>(
      `/stocks/${encodeURIComponent(symbol)}/base-rates${q ? `?${q}` : ""}`,
    );
  },
  positioning: (symbol: string, window_days = 30) =>
    get<Positioning>(
      `/stocks/${encodeURIComponent(symbol)}/positioning?window_days=${window_days}`,
    ),
  patterns: (symbol: string, k = 5) =>
    get<PatternsResponse>(`/stocks/${encodeURIComponent(symbol)}/patterns?k=${k}`),
  marketFlows: (days = 90) => get<FiiDiiPoint[]>(`/market/flows?days=${days}`),
};
