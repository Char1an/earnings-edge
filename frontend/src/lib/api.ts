import type {
  BaseRatesResponse,
  EarningsHistoryItem,
  FiiDiiPoint,
  HomeResponse,
  PatternsResponse,
  Positioning,
  ScreenerFilters,
  ScreenerResponse,
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
  screener: (filters: ScreenerFilters = {}) => {
    const qs = new URLSearchParams();
    for (const [k, v] of Object.entries(filters)) {
      if (v === undefined || v === null || v === "" || v === false) continue;
      qs.set(k, String(v));
    }
    const q = qs.toString();
    return get<ScreenerResponse>(`/screener${q ? `?${q}` : ""}`);
  },
  marketFlows: (days = 90) => get<FiiDiiPoint[]>(`/market/flows?days=${days}`),
  home: (opts: { upcoming_days?: number; deals_days?: number; flows_days?: number } = {}) => {
    const qs = new URLSearchParams();
    if (opts.upcoming_days) qs.set("upcoming_days", String(opts.upcoming_days));
    if (opts.deals_days) qs.set("deals_days", String(opts.deals_days));
    if (opts.flows_days) qs.set("flows_days", String(opts.flows_days));
    const q = qs.toString();
    return get<HomeResponse>(`/home${q ? `?${q}` : ""}`);
  },
};
