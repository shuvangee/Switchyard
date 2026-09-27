import { Pill } from "@/components/Pill";
import { StrategyBarChart } from "@/components/StrategyBarChart";
import { getRouterComparison } from "@/lib/api";
import type { RouterStrategyMetrics } from "@/types/api";

function StrategyRow({ row, best }: { row: RouterStrategyMetrics; best: boolean }) {
  return (
    <tr>
      <td className="mono">
        {row.strategy}
        {best && (
          <span style={{ marginLeft: "0.4rem" }}>
            <Pill tone="success">best real strategy</Pill>
          </span>
        )}
        {row.is_theoretical_upper_bound && (
          <span style={{ marginLeft: "0.4rem" }}>
            <Pill tone="warning">THEORETICAL UPPER BOUND</Pill>
          </span>
        )}
      </td>
      <td className="mono">{(row.accuracy * 100).toFixed(1)}%</td>
      <td className="mono">
        {row.correct}/{row.n}
      </td>
      <td className="mono">{(row.pct_20b * 100).toFixed(1)}%</td>
      <td className="mono">{(row.pct_120b * 100).toFixed(1)}%</td>
      <td className="mono">${row.nominal_cost_usd.toFixed(6)}</td>
      <td className="mono">{row.avg_latency_ms.toFixed(0)} ms</td>
      <td>
        {row.is_theoretical_upper_bound ? (
          <span style={{ color: "var(--text-muted)", fontSize: "0.8rem" }}>
            requires already knowing the answer — not implementable
          </span>
        ) : row.is_out_of_sample ? (
          <span style={{ color: "var(--text-muted)", fontSize: "0.8rem" }}>
            out-of-sample (leave-one-out cross-validated)
          </span>
        ) : (
          <span style={{ color: "var(--text-muted)", fontSize: "0.8rem" }}>in-sample</span>
        )}
      </td>
    </tr>
  );
}

export default async function ComparePage() {
  const comparison = await getRouterComparison();

  const realStrategies = comparison.strategies.filter((row) => !row.is_theoretical_upper_bound);
  const bestAccuracy = Math.max(...realStrategies.map((row) => row.accuracy));
  const oracle = comparison.strategies.find((row) => row.is_theoretical_upper_bound);

  return (
    <main className="page">
      <h1 style={{ fontSize: "1.3rem", margin: 0 }}>Router comparison</h1>
      <p style={{ color: "var(--text-muted)", maxWidth: 760 }}>
        Real, measured results on the {comparison.n_evaluated_tasks} benchmark tasks with ground
        truth for both Groq models — not a live/production number (there isn&apos;t enough real
        Playground traffic yet for that to mean anything). Trained {new Date(comparison.trained_at).toLocaleString()}.
      </p>

      <div
        style={{
          border: "1px solid var(--border)",
          padding: "0.75rem 1rem",
          maxWidth: 760,
          fontSize: "0.85rem",
          marginTop: "0.5rem",
        }}
      >
        <strong>Evaluation method:</strong> {comparison.evaluation_method}
      </div>

      <div
        style={{
          border: "1px solid var(--border)",
          padding: "0.75rem 1rem",
          maxWidth: 760,
          fontSize: "0.85rem",
          marginTop: "0.75rem",
        }}
      >
        <strong>V3 result:</strong>{" "}
        {comparison.learned_beats_d2
          ? "the learned router (learned-v2) beats the D2 baseline on this data."
          : "the learned router (learned-v2) does NOT currently beat the D2 baseline — D2 remains the preferred strategy."}{" "}
        Chosen algorithm: <span className="mono">{comparison.chosen_algorithm}</span>.
        <div style={{ color: "var(--text-muted)", marginTop: "0.4rem" }}>
          {comparison.chosen_algorithm_reason}
        </div>
      </div>

      <h2 className="section-label" style={{ marginTop: "1.75rem" }}>
        Visual comparison
      </h2>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0 2.5rem", maxWidth: 880 }}>
        <StrategyBarChart
          title="Accuracy"
          rows={comparison.strategies}
          value={(row) => row.accuracy}
          format={(row) => `${(row.accuracy * 100).toFixed(1)}%`}
          max={1}
        />
        <StrategyBarChart
          title="Nominal cost"
          rows={comparison.strategies}
          value={(row) => row.nominal_cost_usd}
          format={(row) => `$${row.nominal_cost_usd.toFixed(6)}`}
        />
        <StrategyBarChart
          title="Average latency"
          rows={comparison.strategies}
          value={(row) => row.avg_latency_ms}
          format={(row) => `${row.avg_latency_ms.toFixed(0)}ms`}
        />
        <StrategyBarChart
          title="120b usage"
          rows={comparison.strategies}
          value={(row) => row.pct_120b}
          format={(row) => `${(row.pct_120b * 100).toFixed(1)}%`}
          max={1}
        />
      </div>
      <p style={{ color: "var(--text-muted)", fontSize: "0.78rem", maxWidth: 760, marginTop: "-1rem" }}>
        D2 highlighted in the accent color; the oracle&apos;s bar is hatched to mark it as a
        theoretical ceiling, not a real option.
      </p>

      <table style={{ marginTop: "1.25rem" }}>
        <thead>
          <tr>
            <th>Strategy</th>
            <th>Accuracy</th>
            <th>Correct</th>
            <th>20b usage</th>
            <th>120b usage</th>
            <th>Nominal cost</th>
            <th>Avg latency</th>
            <th>Basis</th>
          </tr>
        </thead>
        <tbody>
          {comparison.strategies.map((row) => (
            <StrategyRow
              key={row.strategy}
              row={row}
              best={!row.is_theoretical_upper_bound && row.accuracy === bestAccuracy}
            />
          ))}
        </tbody>
      </table>

      {oracle && (
        <p style={{ color: "var(--text-muted)", fontSize: "0.8rem", maxWidth: 760, marginTop: "0.5rem" }}>
          The oracle ({(oracle.accuracy * 100).toFixed(1)}%) always picks whichever model is
          actually correct for a given task — it requires ground truth that doesn&apos;t exist at
          request time, so it is reported only as a ceiling on what any router (rule-based or
          learned) could achieve on this exact task set, never as something you could run.
        </p>
      )}

      <p style={{ color: "var(--text-muted)", fontSize: "0.8rem", maxWidth: 760, marginTop: "0.5rem" }}>
        Actual billed cost for every strategy above: $0.00 (Groq free tier, no payment method on
        the account). Nominal cost is registry per-1k pricing × real recorded token counts.
      </p>
    </main>
  );
}
