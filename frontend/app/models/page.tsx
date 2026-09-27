import { getModels } from "@/lib/api";
import type { ModelConfig } from "@/types/api";

// Static project-narrative metadata — not a measured result, just what
// role each configured model plays in the story. Kept here (not in the
// API) since it's descriptive text about the project, not data.
const MODEL_ROLES: Record<string, string> = {
  "groq-gpt-oss-20b": "Cheap/fast default — D2 and learned-v2's baseline choice for most requests.",
  "groq-gpt-oss-120b": "Escalation target — D2 routes summarization here; the strongest single-model baseline.",
  "mock-fast-v1": "V0/V1 mock baseline — cheap simulated tier, no real inference.",
  "mock-accurate-v1": "V0/V1 mock baseline — accurate simulated tier, no real inference.",
  "mock-flaky-v1": "V0/V1 mock baseline — simulates an unreliable provider for escalation testing.",
  "openai-gpt-4o-mini": "Registered adapter, no key configured this deployment — never benchmarked.",
  "gemini-3.6-flash": "Registered adapter — used for early real-provider validation, not part of the routing benchmark.",
  "gemini-3.1-pro-preview": "Registered as a candidate stronger model, explicitly never called (see docs/case-study/DECISIONS.md).",
  "grok-4.1-fast": "Registered adapter, no key configured this deployment — never benchmarked.",
  "groq-qwen3.8-27b": "Registered as a proposed third Groq model — not yet called (see PROJECT_STATE.md).",
};

function roleFor(model: ModelConfig): string {
  return MODEL_ROLES[model.id] ?? "Configured, not part of the core routing benchmark.";
}

const CATEGORY_MODELS = ["groq-gpt-oss-20b", "groq-gpt-oss-120b"];

export default async function ModelsPage() {
  const rawModels = await getModels();
  // Benchmarked models first (the actual product story), then the rest
  // alphabetically — an alphabetical-only sort buries groq-gpt-oss-20b/
  // 120b in the middle of the table.
  const models = [...rawModels].sort((a, b) => {
    const aBench = a.benchmark_performance ? 0 : 1;
    const bBench = b.benchmark_performance ? 0 : 1;
    if (aBench !== bBench) return aBench - bBench;
    return a.id.localeCompare(b.id);
  });
  const categoryModels = models.filter((m) => CATEGORY_MODELS.includes(m.id) && m.benchmark_performance_by_category);
  const allCategories = Array.from(
    new Set(categoryModels.flatMap((m) => (m.benchmark_performance_by_category ?? []).map((c) => c.category)))
  ).sort();

  return (
    <main className="page">
      <h1 style={{ fontSize: "1.3rem", margin: 0 }}>Models</h1>
      <p style={{ color: "var(--text-muted)", maxWidth: 760 }}>
        Configured model registry, plus real measured results from the 92-task offline Groq
        benchmark for the two models that were actually benchmarked. Benchmark accuracy is not a
        claim of universal model quality — it reflects this specific 92-task set, evaluated with
        this project&apos;s specific prompts and graders.
      </p>

      <h2 className="section-label" style={{ marginTop: "1.5rem" }}>
        Configured models
      </h2>
      <table>
        <thead>
          <tr>
            <th>Model</th>
            <th>Provider</th>
            <th>Enabled</th>
            <th>Role in project</th>
            <th>Benchmark accuracy</th>
            <th>Benchmark avg latency</th>
            <th>Benchmark nominal cost</th>
            <th>Sample size</th>
          </tr>
        </thead>
        <tbody>
          {models.map((model) => (
            <tr key={model.id}>
              <td className="mono">{model.id}</td>
              <td className="mono">{model.provider}</td>
              <td>{model.enabled ? "yes" : "no"}</td>
              <td style={{ fontSize: "0.85rem", maxWidth: 280 }}>{roleFor(model)}</td>
              {model.benchmark_performance ? (
                <>
                  <td className="mono">
                    {model.benchmark_performance.accuracy !== null
                      ? `${(model.benchmark_performance.accuracy * 100).toFixed(1)}%`
                      : "—"}
                  </td>
                  <td className="mono">
                    {model.benchmark_performance.avg_latency_ms !== null
                      ? `${model.benchmark_performance.avg_latency_ms.toFixed(0)}ms`
                      : "—"}
                  </td>
                  <td className="mono">
                    {model.benchmark_performance.nominal_cost_usd !== null
                      ? `$${model.benchmark_performance.nominal_cost_usd.toFixed(6)}`
                      : "—"}
                  </td>
                  <td className="mono">{model.benchmark_performance.n_graded}</td>
                </>
              ) : (
                <td colSpan={4} style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>
                  not part of the 92-task benchmark
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>

      {allCategories.length > 0 && (
        <>
          <h2 className="section-label" style={{ marginTop: "2rem" }}>
            Per-category benchmark accuracy
          </h2>
          <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", maxWidth: 700 }}>
            Only the two models actually included in the 92-task benchmark have this data.
            Summarization is where the gap is largest — see /compare and the case study for why.
          </p>
          <table style={{ maxWidth: 560 }}>
            <thead>
              <tr>
                <th>Category</th>
                {categoryModels.map((m) => (
                  <th key={m.id} className="mono">
                    {m.id.replace("groq-gpt-oss-", "")}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {allCategories.map((category) => (
                <tr key={category}>
                  <td className="mono">{category}</td>
                  {categoryModels.map((m) => {
                    const entry = m.benchmark_performance_by_category?.find((c) => c.category === category);
                    return (
                      <td key={m.id} className="mono">
                        {entry ? `${(entry.accuracy * 100).toFixed(1)}% (${entry.n_correct}/${entry.n_graded})` : "—"}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}

      <h2 className="section-label" style={{ marginTop: "2rem" }}>
        This deployment&apos;s live traffic
      </h2>
      <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", maxWidth: 700 }}>
        Computed live from this deployment&apos;s own request history — distinct from the
        benchmark numbers above, and typically empty on a fresh install.
      </p>
      <table>
        <thead>
          <tr>
            <th>Model</th>
            <th>Live performance</th>
          </tr>
        </thead>
        <tbody>
          {models.map((model) => (
            <tr key={model.id}>
              <td className="mono">{model.id}</td>
              <td className="mono">
                {model.performance === null ? (
                  <span style={{ color: "var(--text-muted)" }}>no data yet</span>
                ) : (
                  `${model.performance.correct}/${model.performance.scored_executions} correct, ` +
                  `${model.performance.avg_latency_ms?.toFixed(0) ?? "—"}ms avg, ` +
                  `$${model.performance.total_cost_usd?.toFixed(6) ?? "—"} total`
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </main>
  );
}
