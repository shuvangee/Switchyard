import Link from "next/link";
import { ExecutionStatusPill } from "@/components/Pill";
import { getRequests } from "@/lib/api";

export default async function RequestsPage() {
  const requests = await getRequests();

  return (
    <main className="page">
      <h1 style={{ fontSize: "1.3rem", margin: 0 }}>Request history</h1>
      <p style={{ color: "var(--text-muted)" }}>
        Every request that has gone through the router, in order.
      </p>

      {requests.length === 0 ? (
        <div className="empty-state">
          No requests routed yet. Use the Playground to submit one.
        </div>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Request</th>
              <th>Category</th>
              <th>Difficulty</th>
              <th>Selected model</th>
              <th>Status</th>
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
                <td className="mono">{request.difficulty}</td>
                <td className="mono">{request.selected_model_config_id}</td>
                <td>
                  <ExecutionStatusPill status={request.status} />
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
