"use client";

import type { ReactNode } from "react";

/**
 * Small `?` icon that reveals a plain-English tooltip on hover. Used to
 * explain jargon inline without cluttering every label with a paragraph.
 *
 * Positioning: tooltip appears above by default, right-anchored so it stays
 * on-screen in the right-hand columns of tables. Pass `side="left"` to flip
 * for elements near the right edge of the viewport.
 */
export function Info({
  children,
  side = "right",
  width = "w-64",
}: {
  children: ReactNode;
  side?: "left" | "right";
  width?: string;
}) {
  return (
    <span className="relative inline-flex items-center align-middle ml-1 group">
      <span
        className="text-[9px] font-mono border border-muted/50 text-muted rounded-full w-3 h-3 flex items-center justify-center cursor-help select-none"
        aria-hidden
      >
        ?
      </span>
      <span
        role="tooltip"
        className={[
          "pointer-events-none absolute z-30 bottom-full mb-1.5",
          side === "right" ? "left-0" : "right-0",
          width,
          "rounded-md border border-border bg-bg p-2 text-[11px] leading-snug text-text shadow-xl",
          // Cancel the ALL CAPS / tracking that most label parents inherit.
          "normal-case tracking-normal font-normal",
          "opacity-0 translate-y-1 group-hover:opacity-100 group-hover:translate-y-0",
          "transition-all",
        ].join(" ")}
      >
        {children}
      </span>
    </span>
  );
}
