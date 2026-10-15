"use client";

import { useEffect, useId, useRef, useState } from "react";
import { createPortal } from "react-dom";
import type { ReactNode } from "react";

/** Small, accessible help tooltip that works with mouse, touch, and keyboard. */
export function Info({
  children,
  side = "right",
  width = "w-64",
}: {
  children: ReactNode;
  side?: "left" | "right";
  width?: string;
}) {
  const tooltipId = useId();
  const triggerRef = useRef<HTMLButtonElement>(null);
  const tooltipRef = useRef<HTMLSpanElement>(null);
  const closeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [open, setOpen] = useState(false);
  const [pinned, setPinned] = useState(false);
  const [position, setPosition] = useState({ left: 8, top: 8 });

  const cancelScheduledClose = () => {
    if (closeTimer.current) clearTimeout(closeTimer.current);
    closeTimer.current = null;
  };

  const scheduleClose = () => {
    cancelScheduledClose();
    closeTimer.current = setTimeout(() => {
      if (!pinned) setOpen(false);
    }, 300);
  };

  useEffect(() => {
    if (!open) return;

    const updatePosition = () => {
      const trigger = triggerRef.current;
      if (!trigger) return;
      const rect = trigger.getBoundingClientRect();
      const tip = tooltipRef.current;
      const tipWidth = tip?.offsetWidth ?? 256;
      const tipHeight = tip?.offsetHeight ?? 100;
      const desiredLeft = side === "right" ? rect.left : rect.right - tipWidth;
      const left = Math.max(8, Math.min(desiredLeft, window.innerWidth - tipWidth - 8));
      const above = rect.top - tipHeight - 8;
      const top = above >= 8
        ? above
        : Math.max(8, Math.min(rect.bottom + 8, window.innerHeight - tipHeight - 8));
      setPosition({ left, top });
    };

    updatePosition();
    const frame = window.requestAnimationFrame(updatePosition);
    const onOutsidePointer = (event: PointerEvent) => {
      const target = event.target;
      if (
        target instanceof Node &&
        !triggerRef.current?.contains(target) &&
        !tooltipRef.current?.contains(target)
      ) {
        setOpen(false);
        setPinned(false);
      }
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
        setPinned(false);
      }
    };
    window.addEventListener("resize", updatePosition);
    window.addEventListener("scroll", updatePosition, true);
    document.addEventListener("pointerdown", onOutsidePointer);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      window.cancelAnimationFrame(frame);
      window.removeEventListener("resize", updatePosition);
      window.removeEventListener("scroll", updatePosition, true);
      document.removeEventListener("pointerdown", onOutsidePointer);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open, side]);

  useEffect(() => () => {
    if (closeTimer.current) clearTimeout(closeTimer.current);
  }, []);

  return (
    <>
      <button
        ref={triggerRef}
        type="button"
        aria-label="Show explanation"
        aria-expanded={open}
        aria-describedby={open ? tooltipId : undefined}
        onMouseEnter={() => {
          cancelScheduledClose();
          setOpen(true);
        }}
        onMouseLeave={scheduleClose}
        onFocus={(event) => {
          if (event.currentTarget.matches(":focus-visible")) setOpen(true);
        }}
        onBlur={() => {
          setOpen(false);
          setPinned(false);
        }}
        onClick={() => {
          cancelScheduledClose();
          setPinned((wasPinned) => {
            const next = !wasPinned;
            setOpen(next);
            return next;
          });
        }}
        className="ml-1 inline-flex h-3 w-3 shrink-0 items-center justify-center rounded-full border border-muted/50 font-mono text-[9px] leading-none text-muted align-middle"
      >
        ?
      </button>
      {open && typeof document !== "undefined" && createPortal(
        <span
          ref={tooltipRef}
          id={tooltipId}
          role="tooltip"
          onMouseEnter={cancelScheduledClose}
          onMouseLeave={scheduleClose}
          style={{ left: position.left, top: position.top }}
          className={`pointer-events-auto fixed z-[1000] ${width} max-w-[calc(100vw-1rem)] rounded-md border border-border bg-bg p-2 text-left text-[11px] leading-snug normal-case tracking-normal font-normal text-text shadow-xl`}
        >
          {children}
        </span>,
        document.body,
      )}
    </>
  );
}
