"use client";

import { useState } from "react";

import { EventTimelineChart } from "@/components/panels/EventTimelineChart";
import { HistoricalEarnings } from "@/components/panels/HistoricalEarnings";
import type { EarningsHistoryItem, EventTimeline } from "@/lib/types";

/**
 * Shared state between the earnings history table and the event-timeline chart.
 * Hovering a row previews its timeline in the chart; clicking pins the selection
 * so it survives moving the mouse away.
 */
export function EarningsView({
  items,
  timelines,
}: {
  items: EarningsHistoryItem[];
  timelines: EventTimeline[];
}) {
  const [pinnedId, setPinnedId] = useState<number | null>(
    timelines[0]?.event_id ?? null,
  );
  const [hoverId, setHoverId] = useState<number | null>(null);
  const activeId = hoverId ?? pinnedId;

  return (
    <div className="space-y-6">
      <HistoricalEarnings
        items={items}
        timelines={timelines}
        selectedId={activeId}
        pinnedId={pinnedId}
        onHover={setHoverId}
        onPin={setPinnedId}
      />

      {timelines.length > 0 && (
        <div>
          <div className="flex items-baseline justify-between mb-3">
            <h3 className="text-base font-medium text-muted">
              Event timeline (±10 trading days)
            </h3>
            <div className="text-xs text-muted">
              hover a row above to preview · click to pin
            </div>
          </div>
          <EventTimelineChart
            timelines={timelines}
            selectedId={activeId}
            onSelect={setPinnedId}
          />
        </div>
      )}
    </div>
  );
}
