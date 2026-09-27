import Link from "next/link";
import { NewExperimentForm } from "@/components/NewExperimentForm";
import { RunStatusPill } from "@/components/Pill";
import { getBenchmarks, getExperiments, getModels } from "@/lib/api";

interface Milestone {
  name: string;
  purpose: string;
  models: string;
  taskCount: string;
  coverage: string;
  result: string;
  conclusion: string;
  source: string;
}

// Real project history, curated from docs/case-study/ - not "live"
// experiment-run rows (those are DB-backed and typically empty on a
// fresh deployment, since this history was produced by standalone
// scripts, see docs/case-study/DECISIONS.md 2026-09-28). Every number
// here traces to a committed artifact named in "source".
const MILESTONES: Milestone[] = [
  {
    name: "V0 — mock baseline",
    purpose: "Establish the routing/evaluation pipeline end-to-end at zero cost before spending on real providers.",
    models: "mock-fast-v1, mock-accurate-v1, mock-flaky-v1",
    taskCount: "104",
    coverage: "n/a (simulated)",
    result: "Pipeline proven correct on simulated data.",
    conclusion: "Real infrastructure validated before any real API spend.",
    source: "experiments/results/v0-mock-baseline.json",
  },
  {
    name: "Real Groq benchmark",
    purpose: "Measure real model behavior on the full 104-task set.",
    models: "groq-gpt-oss-20b, groq-gpt-oss-120b",
    taskCount: "104 (208 executions)",
    coverage: "75/104 (72.1%) at the time",
    result: "208/208 calls succeeded; $0 actual cost (Groq free tier).",
    conclusion: "First real routing-opportunity signal, though coverage was still incomplete.",
    source: "experiments/results/groq-gpt-oss-expansion.json",
  },
  {
    name: "Evaluation coverage expansion",
    purpose: "Close the evaluation gap with sandboxed code execution and required-fact checks, so routing conclusions rest on more real ground truth.",
    models: "groq-gpt-oss-20b, groq-gpt-oss-120b",
    taskCount: "104",
    coverage: "72.1% → 88.5% (92/104)",
    result: "The earlier apparent 20b/120b tie (68/75) broke once coverage expanded — 88.0% vs 90.2%.",
    conclusion: "A routing-opportunity conclusion on partial coverage is provisional, not final.",
    source: "docs/case-study/EXPERIMENTS.md (2026-09-24)",
  },
  {
    name: "Simple-routing baseline (D2)",
    purpose: "Test whether a one-sentence rule already captures most of the routing opportunity, before training anything.",
    models: "groq-gpt-oss-20b, groq-gpt-oss-120b",
    taskCount: "92 (auto-graded)",
    coverage: "88.5%",
    result: "D2 (summarization→120b, else→20b): 90.2% accuracy, identical in-sample and LOOCV.",
    conclusion: "A fuller category rule scored higher in-sample (91.3%) but collapsed under LOOCV to 88.0% — caught by honest out-of-fold testing, not trusted at face value.",
    source: "experiments/results/simple-routing-baselines.md",
  },
  {
    name: "Learned router (V3, learned-v2)",
    purpose: "Build and evaluate a genuine trained escalation classifier — V3's actual research question.",
    models: "groq-gpt-oss-20b, groq-gpt-oss-120b",
    taskCount: "92",
    coverage: "88.5%",
    result: "88.0% LOOCV accuracy — does not beat D2 (90.2%) or always-120b (90.2%).",
    conclusion: "Only 8 disagreement tasks (5 positive-labeled) — not enough signal for learned selection to beat the simple rule. Reported plainly, not spun.",
    source: "docs/case-study/EXPERIMENTS.md (2026-09-27)",
  },
];

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

      <h2 className="section-label">Project history</h2>
      <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", maxWidth: 760 }}>
        The real stages that produced every result on this site — not DB-backed experiment runs
        (below), which reflect only this deployment&apos;s own activity. Each row traces to a
        committed artifact.
      </p>
      <table style={{ marginBottom: "2rem" }}>
        <thead>
          <tr>
            <th>Stage</th>
            <th>Purpose</th>
            <th>Task count</th>
            <th>Coverage</th>
            <th>Result</th>
            <th>Conclusion</th>
          </tr>
        </thead>
        <tbody>
          {MILESTONES.map((m) => (
            <tr key={m.name}>
              <td className="mono" style={{ fontSize: "0.82rem" }}>
                {m.name}
                <div style={{ color: "var(--text-muted)", fontWeight: 400 }}>{m.models}</div>
              </td>
              <td style={{ fontSize: "0.82rem", maxWidth: 200 }}>{m.purpose}</td>
              <td className="mono" style={{ fontSize: "0.82rem" }}>{m.taskCount}</td>
              <td className="mono" style={{ fontSize: "0.82rem" }}>{m.coverage}</td>
              <td style={{ fontSize: "0.82rem", maxWidth: 220 }}>{m.result}</td>
              <td style={{ fontSize: "0.82rem", maxWidth: 240, color: "var(--text-muted)" }}>
                {m.conclusion}
                <div className="mono" style={{ marginTop: "0.25rem", fontSize: "0.72rem" }}>
                  {m.source}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <NewExperimentForm tasks={tasks} models={models} />

      <h2 className="section-label">Experiment runs recorded on this deployment</h2>
      {runs.length === 0 ? (
        <div className="empty-state">
          No experiment runs recorded on this deployment yet. Run a benchmark above, or see
          Project history above for the real research this project&apos;s results are based on.
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
