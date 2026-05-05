"use client";

import { Card } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";
import { EVENT_COLORS } from "@/lib/utils";

const ICONS = { danger: "🔴", warn: "🟡", safe: "🔵" };

function EventItem({ event }) {
  const c = EVENT_COLORS[event.level];

  return (
    <div className="flex items-start gap-3 border-b border-accent/15 py-2.5 last:border-b-0">
      <div
        className={`mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border text-sm ${c.bg} ${c.border}`}
      >
        {ICONS[event.level]}
      </div>
      <div>
        <p className="text-[13px] font-semibold text-brand-cream">
          {event.title}
        </p>
        <p className="mt-0.5 font-mono text-[11px] text-brand-muted">
          {event.desc}
        </p>
      </div>
    </div>
  );
}

export function EventsList({ events }) {
  return (
    <Card className="flex-1 p-4">
      <p className="mb-3 text-[11px] font-bold uppercase tracking-[.08em] text-brand-muted">
        Histórico de Eventos
      </p>

      {!events?.length ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-10 w-full" />
          ))}
        </div>
      ) : (
        events.map((ev, i) => <EventItem key={i} event={ev} />)
      )}
    </Card>
  );
}
