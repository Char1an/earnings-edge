export type StockSummary = {
  id: number;
  symbol: string;
  name: string | null;
  sector: string | null;
  industry: string | null;
  in_nifty50: boolean;
  in_nifty500: boolean;
  is_fno: boolean;
};

export type StockDetail = StockSummary & {
  isin: string | null;
  market_cap_cr: number | null;
  latest_close: number | null;
  latest_trade_date: string | null;
  latest_delivery_pct: number | null;
};

export type EarningsEvent = {
  id: number;
  fiscal_period: string;
  quarter_end: string;
  announcement_date: string | null;
  revenue_cr: number | null;
  pat_cr: number | null;
  eps: number | null;
  opm_pct: number | null;
  yoy_revenue_growth: number | null;
  yoy_pat_growth: number | null;
  qoq_revenue_growth: number | null;
  qoq_pat_growth: number | null;
};

export type EarningsReaction = {
  pre_close: number | null;
  gap_open_pct: number | null;
  day1_close_pct: number | null;
  day3_close_pct: number | null;
  day5_close_pct: number | null;
  day1_high_pct: number | null;
  day1_low_pct: number | null;
  volume_spike: number | null;
  detection_method: string | null;
  detection_confidence: number | null;
};

export type EarningsHistoryItem = {
  event: EarningsEvent;
  reaction: EarningsReaction | null;
};

export type Distribution = {
  metric: string;
  n: number;
  mean: number | null;
  median: number | null;
  p25: number | null;
  p75: number | null;
  min: number | null;
  max: number | null;
  hist_bin_edges: number[];
  hist_counts: number[];
};

export type BaseRatesResponse = {
  stock_id: number;
  n_events: number;
  filters_applied: Record<string, unknown>;
  distributions: Record<string, Distribution>;
};

export type Deal = {
  trade_date: string;
  deal_type: string;
  exchange: string;
  client_name: string | null;
  buy_sell: string;
  quantity: number;
  price: number;
  value_cr: number | null;
};

export type Positioning = {
  stock_id: number;
  window_days: number;
  recent_deals: Deal[];
  deals_buy_count: number;
  deals_sell_count: number;
  deals_net_value_cr: number;
  fii_net_window_cr: number | null;
  dii_net_window_cr: number | null;
  delivery_pct_recent: number | null;
  delivery_pct_baseline: number | null;
  delivery_pct_delta: number | null;
};

export type FiiDiiPoint = {
  trade_date: string;
  fii_cash_net_cr: number | null;
  dii_cash_net_cr: number | null;
};
