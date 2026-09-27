import Link from "next/link";
import { ExecutionStatusPill, RunStatusPill } from "@/components/Pill";
import {
  getAnalytics,
  getBenchmarks,
  getEvaluationCoverage,
  getExperiments,
  getModels,
  getRequests,
  getRouterComparison,
} from "@/lib/api";

export default async function Home() {
  const [tasks, models, runs, requests, analytics, coverage, comparison] = await Promise.all([
    getBenchmarks(),
    getModels(),
    getExperiments(),
    getRequests(),
    getAnalytics(),
    getEvaluationCoverage(),
    getRouterComparison(),
  ]);
  const enabledModels = models.filter((model) => model.enabled);
  const recentRuns = runs.slice(0, 5);
  const recentRequests = requests.slice(0, 5);

  const byName = Object.fromEntries(comparison.strategies.map((row) => [row.strategy, row]));
  const d2 = byName["d2-baseline"];
  const always120b = byName["always-120b"];
  const costReduction = d2 && always120b ? 1 - d2.nominal_cost_usd / always120b.nominal_cost_usd : null;
  const latencyReduction = d2 && always120b ? 1 - d2.avg_latency_ms / always120b.avg_latency_ms : null;

  return (
    <main className="page">
      <header style={{ marginBottom: "1.5rem" }}>
        <h1 style={{ fontSize: "1.6rem", margin: 0 }}>Switchyard</h1>
        <p style={{ color: "var(--text-muted)", marginTop: "0.4rem", maxWidth: 680 }}>
          Adaptive multi-model AI request routing — sends each request to the cheapest model that
          can handle it, escalating to a stronger one only when the evidence says it&apos;s worth it.
        </p>
      </header>

      {d2 && always120b && (
        <div
          style={{
            border: "1px solid var(--border)",
            borderLeft: "3px solid var(--accent)",
            padding: "1.1rem 1.25rem",
            marginBottom: "2rem",
            maxWidth: 760,
          }}
        >
          <div style={{ fontSize: "1.05rem", fontWeight: 600, marginBottom: "0.5rem" }}>
            D2 matches 120B accuracy ({(d2.accuracy * 100).toFixed(1)}%) while routing only{" "}
            {(d2.pct_120b * 100).toFixed(1)}% of requests to the larger model.
          </div>
          <p style={{ color: "var(--text-muted)", fontSize: "0.88rem", margin: "0 0 0.5rem" }}>
            Measured on Switchyard&apos;s {comparison.n_evaluated_tasks}-task automatically graded
            evaluation set (leave-one-out cross-validated) — not a claim that these percentages
            generalize to arbitrary production traffic.
          </p>
          <div className="stat-row" style={{ margin: "0.75rem 0 0" }}>
            <div>
              <div className="stat-value">
                {costReduction !== null ? `${(costReduction * 100).toFixed(1)}%` : "—"}
              </div>
              <div className="stat-label">Lower nominal cost vs always-120b</div>
            </div>
            <div>
              <div className="stat-value">
                {latencyReduction !== null ? `${(latencyReduction * 100).toFixed(1)}%` : "—"}
              </div>
              <div className="stat-label">Lower avg latency vs always-120b</div>
            </div>
            <div>
              <div className="stat-value">{(d2.pct_20b * 100).toFixed(1)}%</div>
              <div className="stat-label">Requests routed to 20b</div>
            </div>
          </div>
          <Link href="/compare" style={{ fontSize: "0.85rem" }}>
            Full strategy comparison, including the oracle ceiling and the learned router →
          </Link>
        </div>
      )}

      <div className="stat-row">
        <div>
          <div className="stat-value">{tasks.length}</div>
          <div className="stat-label">Benchmark tasks</div>
        </div>
        <div>
          <div className="stat-value">{coverage.auto_graded}</div>
          <div className="stat-label">
            Automatically graded ({coverage.automated_pct !== null ? `${(coverage.automated_pct * 100).toFixed(1)}%` : "—"})
          </div>
        </div>
        <div>
          <div className="stat-value">
            {enabledModels.length} / {models.length}
          </div>
          <div className="stat-label">Configured models enabled</div>
        </div>
        <div>
          <div className="stat-value">{requests.length}</div>
          <div className="stat-label">Requests routed (this deployment)</div>
        </div>
        <div>
          <div className="stat-value">
            {analytics.escalation_rate !== null ? `${(analytics.escalation_rate * 100).toFixed(0)}%` : "—"}
          </div>
          <div className="stat-label">Escalation rate (this deployment)</div>
        </div>
      </div>

      <div className="stat-row" style={{ marginTop: "-1.5rem" }}>
        <Link href="/playground" className="mono" style={{ fontSize: "0.85rem" }}>
          Playground — route a live request →
        </Link>
        <Link href="/compare" className="mono" style={{ fontSize: "0.85rem" }}>
          Compare — all 5 strategies →
        </Link>
        <Link href="/benchmarks" className="mono" style={{ fontSize: "0.85rem" }}>
          Benchmarks — methodology →
        </Link>
        <Link href="/models" className="mono" style={{ fontSize: "0.85rem" }}>
          Models — measured performance →
        </Link>
      </div>

      <section>
        <h2 className="section-label">Recent routed requests (this deployment)</h2>
        {recentRequests.length === 0 ? (
          <div className="empty-state">
            No requests routed yet on this deployment. Use the Playground to submit one.
          </div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Request</th>
                <th>Category</th>
                <th>Selected model</th>
                <th>Status</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {recentRequests.map((request) => (
                <tr key={request.id}>
                  <td>
                    <Link href={`/requests/${request.id}`}>{request.prompt_preview}</Link>
                  </td>
                  <td className="mono">{request.category}</td>
                  <td className="mono">{request.selected_model_config_id}</td>
                  <td>
                    <ExecutionStatusPill status={request.status} />
                  </td>
                  <td className="mono">{new Date(request.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section>
        <h2 className="section-label">Recent experiment runs</h2>
        {recentRuns.length === 0 ? (
          <div className="empty-state">
            No experiment runs recorded on this deployment yet — the real 92-task Groq benchmark
            that backs the numbers above was run offline; see the Experiments page for that
            history and the Benchmarks page for live task data.
          </div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Run</th>
                <th>Status</th>
                <th>Tasks</th>
                <th>Models</th>
                <th>Executions</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {recentRuns.map((run) => (
                <tr key={run.id}>
                  <td className="mono">
                    <Link href={`/experiments/${run.id}`}>{run.name ?? run.id.slice(0, 8)}</Link>
                  </td>
                  <td>
                    <RunStatusPill status={run.status} />
                  </td>
                  <td>{run.task_count}</td>
                  <td>{run.model_count}</td>
                  <td>{run.execution_count}</td>
                  <td className="mono">{new Date(run.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </main>
  );
}
