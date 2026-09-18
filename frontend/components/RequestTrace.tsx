import type { TraceEvent } from "@/types/api";

function formatTime(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleTimeString(undefined, { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

export function RequestTrace({ events }: { events: TraceEvent[] }) {
  if (events.length === 0) {
    return <div className="empty-state">No trace recorded.</div>;
  }

  return (
    <ol className="trace">
      {events.map((event, index) => (
        <li key={index} className="trace-event">
          <span className="trace-time mono">{formatTime(event.timestamp)}</span>
          <span className="trace-type mono">{event.event_type}</span>
          <span className="trace-detail">{event.detail}</span>
        </li>
      ))}
    </ol>
  );
}
