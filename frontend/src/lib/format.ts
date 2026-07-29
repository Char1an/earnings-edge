// Shared number formatters. Centralized so the negative-zero guard lives in one
// place: v.toFixed(n) can yield "-0.00" for small negatives (e.g. -0.004), which
// renders as a nonsensical "-0.00%". `Number(fixed) || 0` coerces -0 → 0.

export function signed(
  v: number | null | undefined,
  opts: { decimals?: number; suffix?: string } = {},
): string {
  const { decimals = 2, suffix = "%" } = opts;
  if (v == null || Number.isNaN(v)) return "—";
  const r = Number(v.toFixed(decimals)) || 0; // -0 → 0
  return `${r > 0 ? "+" : ""}${r.toFixed(decimals)}${suffix}`;
}

/** Signed percentage, e.g. +5.44% / -3.53% / 0.00% (never "-0.00%"). */
export const signedPct = (v: number | null | undefined, decimals = 2): string =>
  signed(v, { decimals });

/** Signed ₹ Crore, e.g. +₹1,234 Cr / -₹56 Cr. */
export function signedCr(v: number | null | undefined, decimals = 2): string {
  if (v == null || Number.isNaN(v)) return "—";
  const r = Number(v.toFixed(decimals)) || 0;
  const sign = r > 0 ? "+" : r < 0 ? "-" : "";
  return `${sign}₹${Math.abs(r).toLocaleString("en-IN", { maximumFractionDigits: decimals })} Cr`;
}
