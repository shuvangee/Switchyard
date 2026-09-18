import Link from "next/link";
import { notFound } from "next/navigation";
import { Fragment } from "react";
import { EvaluationStatusPill, ExecutionStatusPill, RunStatusPill } from "@/components/Pill";
import { ApiError, getExperiment } from "@/lib/api";

export default async function ExperimentDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  let run;
  try {
    run = await getExperiment(id);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      notFound();
    }
    throw error;
  }

  return (
    <main className="page">
      <p>
        <Link href="/experiments">&larr; Experiments</Link>
      </p>
      <h1 style={{ fontSize: "1.3rem", marginBottom: "0.2rem" }}>{run.name ?? run.id}</h1>
      <p className="mono" style={{ color: "var(--text-muted)" }}>
        {run.id}
      </p>

      <div className="stat-row" style={{ marginTop: "1rem" }}>
        <div>
          <div className="section-label">Status</div>
          <RunStatusPill status={run.status} />
        </div>
        <div>
          <div className="section-label">Created</div>
          <div className="mono">{new Date(run.created_at).toLocaleString()}</div>
        </div>
        <div>
          <div className="section-label">Executions</div>
          <div>{run.executions.length}</div>
        </div>
      </div>

      <h2 className="section-label">Executions</h2>
      <table>
        <thead>
          <tr>
            <th>Task</th>
            <th>Model</th>
            <th>Provider</th>
            <th>Status</th>
            <th>Latency</th>
            <th>Tokens (in/out)</th>
            <th>Cost</th>
            <th>Evaluation</th>
          </tr>
        </thead>
        <tbody>
          {run.executions.map((execution) => (
            <Fragment key={execution.id}>
              <tr>
                <td className="mono">
                  <Link href={`/benchmarks/${execution.task_id}`}>{execution.task_id}</Link>
                </td>
                <td className="mono">{execution.model_config_id}</td>
                <td className="mono">{execution.provider}</td>
                <td>
                  <ExecutionStatusPill status={execution.status} />
                </td>
                <td className="mono">
                  {execution.latency_ms !== null ? `${execution.latency_ms.toFixed(0)} ms` : "—"}
                </td>
                <td className="mono">
                  {execution.input_tokens ?? "—"} / {execution.output_tokens ?? "—"}
                </td>
                <td className="mono">
                  {execution.estimated_cost_usd !== null
                    ? `$${execution.estimated_cost_usd.toFixed(6)}`
                    : "—"}
                </td>
                <td>
                  <EvaluationStatusPill status={execution.evaluation_status} />
                </td>
              </tr>
              <tr>
                <td colSpan={8} style={{ paddingTop: 0 }}>
                  <details>
                    <summary
                      style={{ cursor: "pointer", color: "var(--text-muted)", fontSize: "0.85rem" }}
                    >
                      response / error / evaluation detail
                    </summary>
                    {execution.response_text !== null && (
                      <pre className="prompt-block">{execution.response_text}</pre>
                    )}
                    {execution.error_message !== null && (
                      <pre className="prompt-block">{execution.error_message}</pre>
                    )}
                    {execution.evaluation_detail !== null && (
                      <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>
                        {execution.evaluation_detail}
                      </p>
                    )}
                  </details>
                </td>
              </tr>
            </Fragment>
          ))}
        </tbody>
      </table>
    </main>
  );
}
