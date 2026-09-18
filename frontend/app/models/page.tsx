import { getModels } from "@/lib/api";

export default async function ModelsPage() {
  const models = await getModels();

  return (
    <main className="page">
      <h1 style={{ fontSize: "1.3rem", margin: 0 }}>Models</h1>
      <p style={{ color: "var(--text-muted)" }}>
        The configured model registry. Performance summaries are computed live from this
        database&apos;s recorded executions — empty until a benchmark or routed request has
        actually run against a model.
      </p>

      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Provider</th>
            <th>Model identifier</th>
            <th>Enabled</th>
            <th>Input $/1k</th>
            <th>Output $/1k</th>
            <th>V0 performance</th>
          </tr>
        </thead>
        <tbody>
          {models.map((model) => (
            <tr key={model.id}>
              <td className="mono">{model.id}</td>
              <td className="mono">{model.provider}</td>
              <td className="mono">{model.model_id}</td>
              <td>{model.enabled ? "yes" : "no"}</td>
              <td className="mono">${model.input_cost_per_1k.toFixed(6)}</td>
              <td className="mono">${model.output_cost_per_1k.toFixed(6)}</td>
              <td className="mono">
                {model.performance === null ? (
                  <span style={{ color: "var(--text-muted)" }}>no data yet</span>
                ) : (
                  `${model.performance.correct}/${model.performance.scored_executions} correct, ` +
                  `${model.performance.avg_latency_ms?.toFixed(0) ?? "—"}ms avg, ` +
                  `$${model.performance.total_cost_usd?.toFixed(6) ?? "—"} total`
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </main>
  );
}
