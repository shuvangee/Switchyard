import Link from "next/link";
import { RunStatusPill } from "@/components/Pill";
import { getBenchmarks, getExperiments, getModels } from "@/lib/api";

export default async function Home() {
  const [tasks, models, runs] = await Promise.all([getBenchmarks(), getModels(), getExperiments()]);
  const enabledModels = models.filter((model) => model.enabled);
  const recentRuns = runs.slice(0, 5);

  return (
    <main className="page">
      <header style={{ marginBottom: "1rem" }}>
        <h1 style={{ fontSize: "1.6rem", margin: 0 }}>Switchyard</h1>
        <p style={{ color: "var(--text-muted)", marginTop: "0.4rem" }}>
          Model performance lab — router version V0. No routing logic yet;
          this measures raw model performance across benchmark tasks.
        </p>
      </header>

      <div className="stat-row">
        <div>
          <div className="stat-value">{tasks.length}</div>
          <div className="stat-label">Benchmark tasks</div>
        </div>
        <div>
          <div className="stat-value">
            {enabledModels.length} / {models.length}
          </div>
          <div className="stat-label">Configured models enabled</div>
        </div>
        <div>
          <div className="stat-value">{runs.length}</div>
          <div className="stat-label">Experiment runs</div>
        </div>
      </div>

      <section>
        <h2 className="section-label">Recent experiment runs</h2>
        {recentRuns.length === 0 ? (
          <div className="empty-state">
            No experiment runs yet. Run a benchmark to begin comparing model performance.
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
