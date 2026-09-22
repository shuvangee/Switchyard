import { getAnalytics } from "@/lib/api";

function ModelCountTable({ title, counts }: { title: string; counts: Record<string, number> }) {
  const entries = Object.entries(counts).sort((a, b) => b[1] - a[1]);
  return (
    <div>
      <h2 className="section-label">{title}</h2>
      {entries.length === 0 ? (
        <div className="empty-state">No data yet.</div>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Model</th>
              <th>Requests</th>
            </tr>
          </thead>
          <tbody>
            {entries.map(([modelId, count]) => (
              <tr key={modelId}>
                <td className="mono">{modelId}</td>
                <td className="mono">{count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

export default async function AnalyticsPage() {
  const analytics = await getAnalytics();

  return (
    <main className="page">
      <h1 style={{ fontSize: "1.3rem", margin: 0 }}>Routing analytics</h1>
      <p style={{ color: "var(--text-muted)" }}>
        Computed live from every request routed so far — never a fixed snapshot.
      </p>

      {analytics.total_requests === 0 ? (
        <div className="empty-state">
          No requests routed yet. Use the Playground to submit one.
        </div>
      ) : (
        <>
          <div className="stat-row">
            <div>
              <div className="stat-value">{analytics.total_requests}</div>
              <div className="stat-label">Total requests</div>
            </div>
            <div>
              <div className="stat-value">{(analytics.escalation_rate! * 100).toFixed(0)}%</div>
              <div className="stat-label">Escalation rate ({analytics.escalation_count} escalated)</div>
            </div>
            <div>
              <div className="stat-value">{analytics.provider_error_count}</div>
              <div className="stat-label">Provider errors</div>
            </div>
            <div>
              <div className="stat-value">
                {analytics.avg_latency_ms !== null ? `${analytics.avg_latency_ms.toFixed(0)} ms` : "—"}
              </div>
              <div className="stat-label">Avg latency</div>
            </div>
            <div>
              <div className="stat-value">
                {analytics.total_cost_usd !== null ? `$${analytics.total_cost_usd.toFixed(6)}` : "—"}
              </div>
              <div className="stat-label">Total estimated cost</div>
            </div>
          </div>

          <h2 className="section-label">Validation outcomes</h2>
          <table>
            <thead>
              <tr>
                <th>Passed</th>
                <th>Failed</th>
                <th>Not validated</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td className="mono">{analytics.validation_passed}</td>
                <td className="mono">{analytics.validation_failed}</td>
                <td className="mono">{analytics.validation_not_validated}</td>
              </tr>
            </tbody>
          </table>

          <ModelCountTable title="Initial model selection" counts={analytics.initial_model_counts} />
          <ModelCountTable title="Final model selection" counts={analytics.final_model_counts} />
        </>
      )}
    </main>
  );
}
