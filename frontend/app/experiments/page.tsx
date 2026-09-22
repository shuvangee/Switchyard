import Link from "next/link";
import { NewExperimentForm } from "@/components/NewExperimentForm";
import { RunStatusPill } from "@/components/Pill";
import { getBenchmarks, getExperiments, getModels } from "@/lib/api";

export default async function ExperimentsPage() {
  const [runs, tasks, models] = await Promise.all([
    getExperiments(),
    getBenchmarks(),
    getModels(),
  ]);

  return (
    <main className="page">
      <h1 style={{ fontSize: "1.3rem", margin: 0 }}>Experiments</h1>
      <p style={{ color: "var(--text-muted)" }}>
        Select benchmark tasks and models, then run them against each other.
      </p>

      <NewExperimentForm tasks={tasks} models={models} />

      <h2 className="section-label">Previous runs</h2>
      {runs.length === 0 ? (
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
            {runs.map((run) => (
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
    </main>
  );
}
