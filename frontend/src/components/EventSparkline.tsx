import type { TimelinePoint } from "@/lib/types";

/**
 * Compact price-path around one earnings event. Y = pct vs pre_close (baseline 0%).
 * Green if it ended above 0 at last point, red if below. Vertical dashed line at
 * offset 0 (result day).
 */
export function EventSparkline({
  points,
  width = 120,
  height = 32,
}: {
  points: TimelinePoint[];
  width?: number;
  height?: number;
}) {
  if (points.length < 2) {
    return <span className="text-muted text-xs">—</span>;
  }

  const xs = points.map((p) => p.offset);
  const ys = points.map((p) => p.pct_from_pre);
  const xMin = Math.min(...xs);
  const xMax = Math.max(...xs);
  const yMin = Math.min(...ys, 0);
  const yMax = Math.max(...ys, 0);
  const yPad = (yMax - yMin) * 0.1 || 0.5;
  const y0 = yMin - yPad;
  const y1 = yMax + yPad;

  const sx = (x: number) => ((x - xMin) / (xMax - xMin || 1)) * (width - 2) + 1;
  const sy = (y: number) => height - ((y - y0) / (y1 - y0 || 1)) * (height - 2) - 1;

  const path = points
    .map((p, i) => `${i === 0 ? "M" : "L"}${sx(p.offset).toFixed(2)},${sy(p.pct_from_pre).toFixed(2)}`)
    .join(" ");

  const lastPct = ys[ys.length - 1];
  const stroke = lastPct > 0 ? "#3fb950" : lastPct < 0 ? "#f85149" : "#888";
  const zeroY = sy(0);
  const eventX = sx(0);

  return (
    <svg width={width} height={height} className="inline-block align-middle">
      {/* baseline (pre_close = 0%) */}
      <line
        x1={0}
        y1={zeroY}
        x2={width}
        y2={zeroY}
        stroke="#3a3f47"
        strokeWidth={0.5}
        strokeDasharray="2 2"
      />
      {/* announcement day marker */}
      <line
        x1={eventX}
        y1={0}
        x2={eventX}
        y2={height}
        stroke="#f0883e"
        strokeWidth={0.75}
        strokeDasharray="2 2"
      />
      <path d={path} stroke={stroke} strokeWidth={1.25} fill="none" />
    </svg>
  );
}
