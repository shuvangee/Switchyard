"use client";

import { useState } from "react";
import { ConfidencePill, ExecutionStatusPill, Pill, ValidationStatusPill } from "@/components/Pill";
import { RequestTrace } from "@/components/RequestTrace";
import { ApiError, routeRequest } from "@/lib/api";
import type { RequestLog, RouterVersion, TaskCategory } from "@/types/api";

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

const PRIMARY_STRATEGIES: { value: RouterVersion; label: string }[] = [
  { value: "d2-baseline", label: "D2 baseline — preferred production strategy" },
  { value: "learned-v2", label: "Learned V3 (learned-v2) — trained escalation classifier" },
  { value: "always-20b", label: "always-20b — fixed baseline" },
  { value: "always-120b", label: "always-120b — fixed baseline" },
];

const LEGACY_STRATEGIES: { value: RouterVersion; label: string }[] = [
  { value: "v2", label: "v2 — rule-based (pre-V3, mock-tier models)" },
  { value: "learned-v1", label: "learned-v1 — earlier exploratory model (not recommended)" },
];

// A single, clearly-labeled illustrative example — not a captured real
// request. Shown only so a visitor with no Groq key configured can
// still see the shape of a full routed response. Values are
// representative, not measured; every field name/shape matches the
// real RequestLog exactly.
const EXAMPLE_RESULT: RequestLog = {
  id: "example",
  prompt: "Summarize this article about quarterly earnings and market trends.",
  category: "summarization",
  category_source: "heuristic",
  difficulty: "medium",
  structured_output_required: false,
  estimated_input_tokens: 62,
  confidence: "medium",
  initial_model_config_id: "groq-gpt-oss-120b",
  selected_model_config_id: "groq-gpt-oss-120b",
  selected_provider: "groq",
  router_version: "d2-baseline",
  rationale:
    "D2 baseline: category=summarization -> groq-gpt-oss-120b. This is the one category where the larger model showed a real, LOOCV-validated accuracy edge (see docs/case-study/DECISIONS.md, 2026-09-24).",
  matched_rule: "d2-summarization-override",
  router_score: null,
  escalated: false,
  attempt_count: 1,
  validation_status: "not_validated",
  validation_detail: null,
  status: "success",
  response_text:
    "Revenue grew 12% year-over-year, driven by strength in the core subscription segment. Operating margin held flat at 18% despite continued infrastructure investment. Management raised full-year guidance, citing durable enterprise demand.",
  error_message: null,
  latency_ms: 812,
  input_tokens: 78,
  output_tokens: 54,
  estimated_cost_usd: 0.000312,
  trace_events: [
    { event_type: "request_received", detail: "prompt received (78 chars)", timestamp: "12:00:00" },
    { event_type: "analyzed", detail: "category=summarization (heuristic), difficulty=medium, structured_output_required=False", timestamp: "12:00:00" },
    { event_type: "routed", detail: "selected groq-gpt-oss-120b (confidence=medium, rule=d2-summarization-override)", timestamp: "12:00:00" },
    { event_type: "model_completed", detail: "groq-gpt-oss-120b latency=812ms", timestamp: "12:00:01" },
    { event_type: "returned", detail: "response accepted", timestamp: "12:00:01" },
  ],
  created_at: new Date().toISOString(),
};

function ResultView({ result, isExample }: { result: RequestLog; isExample: boolean }) {
  return (
    <div>
      {isExample && (
        <div style={{ marginBottom: "1rem" }}>
          <Pill tone="warning">EXAMPLE — recorded illustration, not a live request</Pill>
        </div>
      )}
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
        {result.router_score !== null && (
          <div>
            <div className="section-label">Model score</div>
            <div className="mono">{result.router_score.toFixed(2)}</div>
          </div>
        )}
      </div>
      <p style={{ color: "var(--text-muted)", fontSize: "0.9rem", maxWidth: 700 }}>
        {result.rationale}
      </p>

      <h2 className="section-label">Response</h2>
      <div style={{ marginBottom: "0.5rem", display: "flex", gap: "0.5rem" }}>
        <ExecutionStatusPill status={result.status} />
        <ValidationStatusPill status={result.validation_status} />
      </div>
      {result.response_text !== null && <pre className="prompt-block">{result.response_text}</pre>}
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
            <td className="mono">{result.latency_ms !== null ? `${result.latency_ms.toFixed(0)} ms` : "—"}</td>
            <td className="mono">
              {result.input_tokens ?? "—"} / {result.output_tokens ?? "—"}
            </td>
            <td className="mono">
              {result.estimated_cost_usd !== null ? `$${result.estimated_cost_usd.toFixed(6)}` : "—"}
            </td>
            <td className="mono">{result.selected_provider}</td>
            <td className="mono">{result.router_version}</td>
          </tr>
        </tbody>
      </table>

      <h2 className="section-label">Request trace</h2>
      <RequestTrace events={result.trace_events} />
    </div>
  );
}

export function PlaygroundForm({ groqConfigured }: { groqConfigured: boolean }) {
  const [prompt, setPrompt] = useState("");
  const [categoryHint, setCategoryHint] = useState<string>("");
  const [routerVersion, setRouterVersion] = useState<RouterVersion>("d2-baseline");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<RequestLog | null>(null);
  const [showExample, setShowExample] = useState(false);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);

    if (!prompt.trim()) {
      setError("Enter a request to route.");
      return;
    }

    setSubmitting(true);
    setShowExample(false);
    try {
      const log = await routeRequest({
        prompt,
        category_hint: categoryHint ? (categoryHint as TaskCategory) : undefined,
        router_version: routerVersion,
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
      {!groqConfigured && (
        <div
          style={{
            border: "1px solid var(--border)",
            borderLeft: "3px solid var(--accent)",
            padding: "0.85rem 1rem",
            marginBottom: "1.25rem",
            maxWidth: 700,
            fontSize: "0.85rem",
          }}
        >
          <strong>Live routing requires a Groq API key.</strong> This deployment doesn&apos;t have
          one configured, so D2/learned-v2/always-20b/always-120b will route correctly but fall
          back to a mock model instead of calling Groq — the routing decision itself is real, the
          model response won&apos;t be.{" "}
          <button
            type="button"
            onClick={() => setShowExample((v) => !v)}
            style={{
              background: "none",
              border: "none",
              color: "var(--accent)",
              cursor: "pointer",
              padding: 0,
              font: "inherit",
              textDecoration: "underline",
            }}
          >
            {showExample ? "hide" : "see"} a recorded example instead
          </button>
        </div>
      )}

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

        <div className="field">
          <label htmlFor="router-strategy">Routing strategy</label>
          <select
            id="router-strategy"
            value={routerVersion}
            onChange={(event) => setRouterVersion(event.target.value as RouterVersion)}
            style={{
              fontFamily: "var(--sans)",
              fontSize: "0.85rem",
              padding: "0.35rem 0.4rem",
              border: "1px solid var(--border)",
              background: "var(--surface)",
              color: "var(--text)",
              maxWidth: 420,
            }}
          >
            <optgroup label="Production comparison (Groq)">
              {PRIMARY_STRATEGIES.map((strategy) => (
                <option key={strategy.value} value={strategy.value}>
                  {strategy.label}
                </option>
              ))}
            </optgroup>
            <optgroup label="Legacy / exploratory">
              {LEGACY_STRATEGIES.map((strategy) => (
                <option key={strategy.value} value={strategy.value}>
                  {strategy.label}
                </option>
              ))}
            </optgroup>
          </select>
        </div>

        {error && <p className="error-text">{error}</p>}

        <button type="submit" className="primary" disabled={submitting}>
          {submitting ? "Routing…" : "Run"}
        </button>
      </form>

      {showExample && !result && <ResultView result={EXAMPLE_RESULT} isExample />}
      {result && <ResultView result={result} isExample={false} />}
    </div>
  );
}
