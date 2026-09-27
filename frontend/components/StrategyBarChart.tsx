import type { RouterStrategyMetrics } from "@/types/api";

interface StrategyBarChartProps {
  title: string;
  rows: RouterStrategyMetrics[];
  value: (row: RouterStrategyMetrics) => number;
  format: (row: RouterStrategyMetrics) => string;
  // Higher-is-better metrics scale bars against the max; lower-is-better
  // (cost, latency) also scale against the max so the reader compares
  // bar LENGTH the same way for every chart on the page.
  max?: number;
}

export function StrategyBarChart({ title, rows, value, format, max }: StrategyBarChartProps) {
  const scaleMax = max ?? Math.max(...rows.map(value));
  return (
    <div>
      <div className="section-label" style={{ marginBottom: "0.35rem" }}>
        {title}
      </div>
      <div className="bar-chart">
        {rows.map((row) => {
          const pct = scaleMax > 0 ? Math.max((value(row) / scaleMax) * 100, 2) : 0;
          const fillClass = row.is_theoretical_upper_bound
            ? "bar-fill bar-fill-theoretical"
            : row.strategy === "d2-baseline"
              ? "bar-fill bar-fill-accent"
              : "bar-fill";
          return (
            <div className="bar-row" key={row.strategy}>
              <div className="bar-row-label" title={row.strategy}>
                {row.strategy}
              </div>
              <div className="bar-track" title={`${row.strategy}: ${format(row)}`}>
                <div className={fillClass} style={{ width: `${pct}%` }} />
              </div>
              <div className="bar-row-value">{format(row)}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
