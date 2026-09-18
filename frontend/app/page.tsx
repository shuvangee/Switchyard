import { StatusBadge } from "@/components/StatusBadge";

const ROADMAP: Array<{
  version: string;
  name: string;
  status: "done" | "in-progress" | "planned";
}> = [
  { version: "V0", name: "Model performance benchmarking", status: "planned" },
  { version: "V1", name: "Rule-based multi-model routing", status: "planned" },
  { version: "V2", name: "Evaluation, confidence, fallback, escalation", status: "planned" },
  { version: "V3", name: "Learned routing", status: "planned" },
  { version: "V4", name: "Production-style analytics & observability", status: "planned" },
];

export default function Home() {
  return (
    <main
      style={{
        maxWidth: 760,
        margin: "0 auto",
        padding: "3rem 1.5rem 4rem",
      }}
    >
      <header style={{ marginBottom: "2.5rem" }}>
        <h1 style={{ fontSize: "1.6rem", margin: 0 }}>Switchyard</h1>
        <p style={{ color: "var(--text-muted)", marginTop: "0.4rem" }}>
          Adaptive multi-model AI routing — research workstation.
        </p>
      </header>

      <section style={{ marginBottom: "2.5rem" }}>
        <h2 style={{ fontSize: "1rem", textTransform: "uppercase", letterSpacing: "0.03em", color: "var(--text-muted)" }}>
          Research question
        </h2>
        <p>
          Can an intelligent routing system significantly reduce AI inference
          cost and latency without meaningfully reducing answer quality?
        </p>
      </section>

      <section style={{ marginBottom: "2.5rem" }}>
        <h2 style={{ fontSize: "1rem", textTransform: "uppercase", letterSpacing: "0.03em", color: "var(--text-muted)" }}>
          Development stages
        </h2>
        <table>
          <thead>
            <tr>
              <th>Version</th>
              <th>Scope</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {ROADMAP.map((row) => (
              <tr key={row.version}>
                <td className="mono">{row.version}</td>
                <td>{row.name}</td>
                <td>
                  <StatusBadge status={row.status} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section>
        <h2 style={{ fontSize: "1rem", textTransform: "uppercase", letterSpacing: "0.03em", color: "var(--text-muted)" }}>
          Current stage
        </h2>
        <p>
          Project bootstrap — architecture, tooling, and documentation
          conventions only. No routing, benchmarking, or provider logic is
          implemented yet. See{" "}
          <code className="mono">PROJECT_STATE.md</code> in the repository
          root for the current objective.
        </p>
      </section>
    </main>
  );
}
