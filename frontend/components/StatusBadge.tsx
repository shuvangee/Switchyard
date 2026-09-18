type Status = "done" | "in-progress" | "planned";

const LABEL: Record<Status, string> = {
  done: "done",
  "in-progress": "in progress",
  planned: "planned",
};

const COLOR: Record<Status, string> = {
  done: "#2f6f4f",
  "in-progress": "#b45309",
  planned: "#5f5b54",
};

export function StatusBadge({ status }: { status: Status }) {
  return (
    <span
      className="mono"
      style={{
        color: COLOR[status],
        border: `1px solid ${COLOR[status]}`,
        borderRadius: 2,
        padding: "0.1rem 0.4rem",
        fontSize: "0.75rem",
      }}
    >
      {LABEL[status]}
    </span>
  );
}
