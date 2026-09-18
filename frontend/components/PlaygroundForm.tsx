"use client";

import { useState } from "react";
import { ConfidencePill, ExecutionStatusPill, ValidationStatusPill } from "@/components/Pill";
import { RequestTrace } from "@/components/RequestTrace";
import { ApiError, routeRequest } from "@/lib/api";
import type { RequestLog, TaskCategory } from "@/types/api";

const CATEGORIES: TaskCategory[] = [
  "extraction",
  "classification",
  "summarization",
  "math",
  "reasoning",
  "coding",
  "debugging",
  "structured_output",
];

export function PlaygroundForm() {
  const [prompt, setPrompt] = useState("");
  const [categoryHint, setCategoryHint] = useState<string>("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<RequestLog | null>(null);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);

    if (!prompt.trim()) {
      setError("Enter a request to route.");
      return;
    }

    setSubmitting(true);
    try {
      const log = await routeRequest({
        prompt,
        category_hint: categoryHint ? (categoryHint as TaskCategory) : undefined,
      });
      setResult(log);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to route request.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div>
      <form className="card-form" onSubmit={handleSubmit}>
        <div className="field">
          <label htmlFor="playground-prompt">Request</label>
          <textarea
            id="playground-prompt"
            value={prompt}
            onChange={(event) => setPrompt(event.target.value)}
            rows={5}
            style={{
              width: "100%",
              maxWidth: 640,
              fontFamily: "var(--sans)",
              fontSize: "0.9rem",
              padding: "0.5rem 0.6rem",
              border: "1px solid var(--border)",
              background: "var(--surface)",
              color: "var(--text)",
            }}
            placeholder="e.g. What is 17 * 6?"
          />
        </div>

        <div className="field">
          <label htmlFor="category-hint">Category hint (optional — overrides auto-detection)</label>
          <select
            id="category-hint"
            value={categoryHint}
            onChange={(event) => setCategoryHint(event.target.value)}
            style={{
              fontFamily: "var(--sans)",
              fontSize: "0.85rem",
              padding: "0.35rem 0.4rem",
              border: "1px solid var(--border)",
              background: "var(--surface)",
              color: "var(--text)",
            }}
          >
            <option value="">Auto-detect</option>
            {CATEGORIES.map((category) => (
              <option key={category} value={category}>
                {category}
              </option>
            ))}
          </select>
        </div>

        {error && <p className="error-text">{error}</p>}

        <button type="submit" className="primary" disabled={submitting}>
          {submitting ? "Routing…" : "Run"}
        </button>
      </form>

      {result && (
        <div>
          <h2 className="section-label">Request analysis</h2>
          <div className="stat-row" style={{ marginTop: 0 }}>
            <div>
              <div className="section-label">Category</div>
              <div className="mono">
                {result.category}{" "}
                <span style={{ color: "var(--text-muted)" }}>({result.category_source})</span>
              </div>
            </div>
            <div>
              <div className="section-label">Difficulty</div>
              <div className="mono">{result.difficulty}</div>
            </div>
            <div>
              <div className="section-label">Structured output required</div>
              <div className="mono">{result.structured_output_required ? "yes" : "no"}</div>
            </div>
            <div>
              <div className="section-label">Estimated input tokens</div>
              <div className="mono">{result.estimated_input_tokens}</div>
            </div>
          </div>

          <h2 className="section-label">Routing decision</h2>
          <div className="stat-row" style={{ marginTop: 0 }}>
            <div>
              <div className="section-label">Confidence</div>
              <ConfidencePill level={result.confidence} />
            </div>
            <div>
              <div className="section-label">Initial model</div>
              <div className="mono">{result.initial_model_config_id}</div>
            </div>
            <div>
              <div className="section-label">Final model</div>
              <div className="mono">{result.selected_model_config_id}</div>
            </div>
            <div>
              <div className="section-label">Escalated</div>
              <div className="mono">{result.escalated ? `yes (${result.attempt_count} attempts)` : "no"}</div>
            </div>
            <div>
              <div className="section-label">Router version</div>
              <div className="mono">{result.router_version}</div>
            </div>
          </div>
          <p style={{ color: "var(--text-muted)", fontSize: "0.9rem", maxWidth: 700 }}>
            {result.rationale}
          </p>

          <h2 className="section-label">Response</h2>
          <div style={{ marginBottom: "0.5rem", display: "flex", gap: "0.5rem" }}>
            <ExecutionStatusPill status={result.status} />
            <ValidationStatusPill status={result.validation_status} />
          </div>
          {result.response_text !== null && (
            <pre className="prompt-block">{result.response_text}</pre>
          )}
          {result.error_message !== null && <pre className="prompt-block">{result.error_message}</pre>}
          {result.validation_detail !== null && (
            <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>
              Validation: {result.validation_detail}
            </p>
          )}

          <h2 className="section-label">Technical metadata</h2>
          <table>
            <thead>
              <tr>
                <th>Latency</th>
                <th>Tokens (in/out)</th>
                <th>Estimated cost</th>
                <th>Provider</th>
                <th>Router version</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td className="mono">
                  {result.latency_ms !== null ? `${result.latency_ms.toFixed(0)} ms` : "—"}
                </td>
                <td className="mono">
                  {result.input_tokens ?? "—"} / {result.output_tokens ?? "—"}
                </td>
                <td className="mono">
                  {result.estimated_cost_usd !== null
                    ? `$${result.estimated_cost_usd.toFixed(6)}`
                    : "—"}
                </td>
                <td className="mono">{result.selected_provider}</td>
                <td className="mono">{result.router_version}</td>
              </tr>
            </tbody>
          </table>

          <h2 className="section-label">Request trace</h2>
          <RequestTrace events={result.trace_events} />
        </div>
      )}
    </div>
  );
}
