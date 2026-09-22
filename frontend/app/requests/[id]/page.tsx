import Link from "next/link";
import { notFound } from "next/navigation";
import { ConfidencePill, ExecutionStatusPill, ValidationStatusPill } from "@/components/Pill";
import { RequestTrace } from "@/components/RequestTrace";
import { ApiError, getRequest } from "@/lib/api";

export default async function RequestDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  let log;
  try {
    log = await getRequest(id);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      notFound();
    }
    throw error;
  }

  return (
    <main className="page">
      <p>
        <Link href="/requests">&larr; Request history</Link>
      </p>
      <h1 style={{ fontSize: "1.3rem", marginBottom: "0.2rem" }}>Request</h1>
      <p className="mono" style={{ color: "var(--text-muted)" }}>
        {log.id}
      </p>

      <h2 className="section-label">Original request</h2>
      <pre className="prompt-block">{log.prompt}</pre>

      <h2 className="section-label">Request analysis</h2>
      <div className="stat-row" style={{ marginTop: 0 }}>
        <div>
          <div className="section-label">Category</div>
          <div className="mono">
            {log.category} <span style={{ color: "var(--text-muted)" }}>({log.category_source})</span>
          </div>
        </div>
        <div>
          <div className="section-label">Difficulty</div>
          <div className="mono">{log.difficulty}</div>
        </div>
        <div>
          <div className="section-label">Structured output required</div>
          <div className="mono">{log.structured_output_required ? "yes" : "no"}</div>
        </div>
      </div>

      <h2 className="section-label">Routing decision</h2>
      <div className="stat-row" style={{ marginTop: 0 }}>
        <div>
          <div className="section-label">Confidence</div>
          <ConfidencePill level={log.confidence} />
        </div>
        <div>
          <div className="section-label">Initial model</div>
          <div className="mono">{log.initial_model_config_id}</div>
        </div>
        <div>
          <div className="section-label">Final model</div>
          <div className="mono">{log.selected_model_config_id}</div>
        </div>
        <div>
          <div className="section-label">Escalated</div>
          <div className="mono">{log.escalated ? `yes (${log.attempt_count} attempts)` : "no"}</div>
        </div>
        <div>
          <div className="section-label">Router version</div>
          <div className="mono">{log.router_version}</div>
        </div>
      </div>
      <p style={{ color: "var(--text-muted)", fontSize: "0.9rem", maxWidth: 700 }}>
        {log.rationale}
      </p>

      <h2 className="section-label">Response</h2>
      <div style={{ marginBottom: "0.5rem", display: "flex", gap: "0.5rem" }}>
        <ExecutionStatusPill status={log.status} />
        <ValidationStatusPill status={log.validation_status} />
      </div>
      {log.response_text !== null && <pre className="prompt-block">{log.response_text}</pre>}
      {log.error_message !== null && <pre className="prompt-block">{log.error_message}</pre>}
      {log.validation_detail !== null && (
        <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>
          Validation: {log.validation_detail}
        </p>
      )}

      <h2 className="section-label">Technical metadata</h2>
      <table>
        <thead>
          <tr>
            <th>Latency</th>
            <th>Tokens (in/out)</th>
            <th>Estimated cost</th>
            <th>Created</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td className="mono">{log.latency_ms !== null ? `${log.latency_ms.toFixed(0)} ms` : "—"}</td>
            <td className="mono">
              {log.input_tokens ?? "—"} / {log.output_tokens ?? "—"}
            </td>
            <td className="mono">
              {log.estimated_cost_usd !== null ? `$${log.estimated_cost_usd.toFixed(6)}` : "—"}
            </td>
            <td className="mono">{new Date(log.created_at).toLocaleString()}</td>
          </tr>
        </tbody>
      </table>

      <h2 className="section-label">Request trace</h2>
      <RequestTrace events={log.trace_events} />
    </main>
  );
}
