import Link from "next/link";
import { ExecutionStatusPill, ValidationStatusPill } from "@/components/Pill";
import { getRequests } from "@/lib/api";
import type { RequestLogSummary, TaskCategory, TaskDifficulty } from "@/types/api";

const CATEGORIES: TaskCategory[] = [
  "extraction", "classification", "summarization", "math",
  "reasoning", "coding", "debugging", "structured_output",
];
const DIFFICULTIES: TaskDifficulty[] = ["easy", "medium", "hard"];

interface Filters {
  router_version?: string;
  model?: string;
  category?: string;
  difficulty?: string;
  status?: string;
  provider?: string;
  escalated?: string;
  since?: string;
}

function applyFilters(requests: RequestLogSummary[], filters: Filters): RequestLogSummary[] {
  return requests.filter((r) => {
    if (filters.router_version && r.router_version !== filters.router_version) return false;
    if (filters.model && r.selected_model_config_id !== filters.model) return false;
    if (filters.category && r.category !== filters.category) return false;
    if (filters.difficulty && r.difficulty !== filters.difficulty) return false;
    if (filters.status && r.status !== filters.status) return false;
    if (filters.provider && r.selected_provider !== filters.provider) return false;
    if (filters.escalated === "yes" && !r.escalated) return false;
    if (filters.escalated === "no" && r.escalated) return false;
    if (filters.since && new Date(r.created_at) < new Date(filters.since)) return false;
    return true;
  });
}

export default async function RequestsPage({
  searchParams,
}: {
  searchParams: Promise<Filters>;
}) {
  const filters = await searchParams;
  const allRequests = await getRequests();
  const requests = applyFilters(allRequests, filters);

  const routerVersions = Array.from(new Set(allRequests.map((r) => r.router_version))).sort();
  const models = Array.from(new Set(allRequests.map((r) => r.selected_model_config_id))).sort();
  const providers = Array.from(new Set(allRequests.map((r) => r.selected_provider))).sort();

  return (
    <main className="page">
      <h1 style={{ fontSize: "1.3rem", margin: 0 }}>Request history</h1>
      <p style={{ color: "var(--text-muted)" }}>
        Every request routed on this deployment, in order. {requests.length} of {allRequests.length}
        {allRequests.length !== requests.length ? " match the current filter" : ""}.
      </p>

      {allRequests.length > 0 && (
        <form className="filters" method="get" style={{ flexWrap: "wrap" }}>
          <select name="router_version" aria-label="Filter by router version" defaultValue={filters.router_version ?? ""}>
            <option value="">All router versions</option>
            {routerVersions.map((v) => (
              <option key={v} value={v}>{v}</option>
            ))}
          </select>
          <select name="model" aria-label="Filter by selected model" defaultValue={filters.model ?? ""}>
            <option value="">All models</option>
            {models.map((m) => (
              <option key={m} value={m}>{m}</option>
            ))}
          </select>
          <select name="provider" aria-label="Filter by provider" defaultValue={filters.provider ?? ""}>
            <option value="">All providers</option>
            {providers.map((p) => (
              <option key={p} value={p}>{p}</option>
            ))}
          </select>
          <select name="category" aria-label="Filter by category" defaultValue={filters.category ?? ""}>
            <option value="">All categories</option>
            {CATEGORIES.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
          <select name="difficulty" aria-label="Filter by difficulty" defaultValue={filters.difficulty ?? ""}>
            <option value="">All difficulties</option>
            {DIFFICULTIES.map((d) => (
              <option key={d} value={d}>{d}</option>
            ))}
          </select>
          <select name="status" aria-label="Filter by status" defaultValue={filters.status ?? ""}>
            <option value="">Any status</option>
            <option value="success">success</option>
            <option value="error">error</option>
          </select>
          <select name="escalated" aria-label="Filter by escalation" defaultValue={filters.escalated ?? ""}>
            <option value="">Escalated: any</option>
            <option value="yes">Escalated: yes</option>
            <option value="no">Escalated: no</option>
          </select>
          <input
            type="date"
            name="since"
            defaultValue={filters.since ?? ""}
            title="Since date"
            aria-label="Filter by date, requests on or after"
          />
          <button type="submit" className="primary">
            Filter
          </button>
          {Object.values(filters).some(Boolean) && (
            <Link href="/requests" className="mono" style={{ fontSize: "0.82rem", alignSelf: "center" }}>
              clear
            </Link>
          )}
        </form>
      )}

      {allRequests.length === 0 ? (
        <div className="empty-state">
          No requests routed yet on this deployment. Use the Playground to submit one.
        </div>
      ) : requests.length === 0 ? (
        <div className="empty-state">No requests match this filter.</div>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Request</th>
              <th>Category</th>
              <th>Router</th>
              <th>Initial model</th>
              <th>Final model</th>
              <th>Provider</th>
              <th>Status</th>
              <th>Validation</th>
              <th>Latency</th>
              <th>Cost</th>
              <th>Created</th>
            </tr>
          </thead>
          <tbody>
            {requests.map((request) => (
              <tr key={request.id}>
                <td>
                  <Link href={`/requests/${request.id}`}>{request.prompt_preview}</Link>
                </td>
                <td className="mono">{request.category}</td>
                <td className="mono">{request.router_version}</td>
                <td className="mono">{request.initial_model_config_id}</td>
                <td className="mono">
                  {request.selected_model_config_id}
                  {request.escalated && (
                    <span style={{ color: "var(--accent)" }}> ↑</span>
                  )}
                </td>
                <td className="mono">{request.selected_provider}</td>
                <td>
                  <ExecutionStatusPill status={request.status} />
                </td>
                <td>
                  <ValidationStatusPill status={request.validation_status} />
                </td>
                <td className="mono">
                  {request.latency_ms !== null ? `${request.latency_ms.toFixed(0)} ms` : "—"}
                </td>
                <td className="mono">
                  {request.estimated_cost_usd !== null
                    ? `$${request.estimated_cost_usd.toFixed(6)}`
                    : "—"}
                </td>
                <td className="mono">{new Date(request.created_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </main>
  );
}
