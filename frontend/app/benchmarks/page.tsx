import Link from "next/link";
import { getBenchmarks, getEvaluationCoverage } from "@/lib/api";
import type { TaskCategory, TaskDifficulty } from "@/types/api";

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

const DIFFICULTIES: TaskDifficulty[] = ["easy", "medium", "hard"];

const EVALUATION_METHODS = [
  { name: "exact_match", description: "Normalized string equality against a pre-authored expected answer (math, some reasoning)." },
  { name: "classification_label", description: "Checked against an explicit label list, when the prompt names one." },
  { name: "valid_json", description: "The response must parse as valid, well-formed JSON matching the requested structure." },
  { name: "execution-based (sandboxed)", description: "Coding/debugging: candidate code runs in an isolated subprocess (no network, no filesystem access outside a temp dir) against real test cases — never eval()/exec() in the main process." },
  { name: "required-fact checks", description: "Summarization: a zero-cost deterministic presence check for specific facts a correct summary must include — not an LLM judge." },
  { name: "manual", description: "No deterministic grader was defensible for this task (see below) — graded by a human, or not yet graded." },
];

export default async function BenchmarksPage({
  searchParams,
}: {
  searchParams: Promise<{ category?: string; difficulty?: string }>;
}) {
  const params = await searchParams;
  const [tasks, coverage] = await Promise.all([
    getBenchmarks({ category: params.category, difficulty: params.difficulty }),
    getEvaluationCoverage(),
  ]);

  return (
    <main className="page">
      <h1 style={{ fontSize: "1.3rem", margin: 0 }}>Benchmarks</h1>
      <p style={{ color: "var(--text-muted)", maxWidth: 760 }}>
        {coverage.total_tasks} tasks across 8 categories, evaluated against groq-gpt-oss-20b and
        groq-gpt-oss-120b. This is the same benchmark that produces every number on Overview and
        Compare.
      </p>

      <div className="stat-row">
        <div>
          <div className="stat-value">{coverage.total_tasks}</div>
          <div className="stat-label">Total tasks</div>
        </div>
        <div>
          <div className="stat-value">{coverage.auto_graded}</div>
          <div className="stat-label">Automatically graded</div>
        </div>
        <div>
          <div className="stat-value">{coverage.manual_only}</div>
          <div className="stat-label">Manual-only</div>
        </div>
        <div>
          <div className="stat-value">{coverage.ungraded}</div>
          <div className="stat-label">Ungraded</div>
        </div>
        <div>
          <div className="stat-value">
            {coverage.automated_pct !== null ? `${(coverage.automated_pct * 100).toFixed(1)}%` : "—"}
          </div>
          <div className="stat-label">Automated coverage</div>
        </div>
      </div>

      <h2 className="section-label">Coverage by category</h2>
      <table style={{ maxWidth: 640, marginBottom: "2rem" }}>
        <thead>
          <tr>
            <th>Category</th>
            <th>Total</th>
            <th>Auto-graded</th>
            <th>Manual-only</th>
            <th>Ungraded</th>
          </tr>
        </thead>
        <tbody>
          {coverage.by_category.map((row) => (
            <tr key={row.category}>
              <td className="mono">{row.category}</td>
              <td className="mono">{row.total}</td>
              <td className="mono">{row.auto_graded}</td>
              <td className="mono">{row.manual_only}</td>
              <td className="mono">{row.ungraded}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h2 className="section-label">Why some tasks stay manual-only</h2>
      <p style={{ color: "var(--text-muted)", fontSize: "0.88rem", maxWidth: 760 }}>
        This is a deliberate limitation, not something hidden: a task stays manual-only when no
        deterministic grader can distinguish a correct answer from an incorrect one without
        either resolving a genuine specification ambiguity or fabricating a rubric. Debugging-007
        is the clearest example — its only discriminating test input has an undefined correct
        output, so grading it automatically would mean silently deciding the ambiguity rather than
        testing the model. Several summarization tasks are similar: attribution tasks where a
        fact-presence check would defeat the point of the test, or rubrics too paraphrase-prone to
        check reliably. Full reasoning per task: <code className="mono">metadata</code> on each
        task&apos;s detail page, and <code className="mono">docs/case-study/DECISIONS.md</code>.
      </p>

      <h2 className="section-label">Evaluation methods</h2>
      <table style={{ maxWidth: 820, marginBottom: "1rem" }}>
        <thead>
          <tr>
            <th>Method</th>
            <th>How it works</th>
          </tr>
        </thead>
        <tbody>
          {EVALUATION_METHODS.map((method) => (
            <tr key={method.name}>
              <td className="mono">{method.name}</td>
              <td style={{ fontSize: "0.85rem" }}>{method.description}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p style={{ color: "var(--text-muted)", fontSize: "0.8rem", maxWidth: 760, marginBottom: "2rem" }}>
        Note: the <code className="mono">evaluation_type</code> field on each task below reflects
        its authored grading method — execution-based and required-fact grading are applied
        separately and don&apos;t change that field, so some tasks shown as{" "}
        <code className="mono">manual</code> below are in fact automatically graded (that&apos;s
        what the coverage table above reflects; this list shows the underlying field as-authored).
      </p>

      <h2 className="section-label">Tasks</h2>
      <form className="filters" method="get">
        <select name="category" aria-label="Filter by category" defaultValue={params.category ?? ""}>
          <option value="">All categories</option>
          {CATEGORIES.map((category) => (
            <option key={category} value={category}>
              {category}
            </option>
          ))}
        </select>
        <select name="difficulty" aria-label="Filter by difficulty" defaultValue={params.difficulty ?? ""}>
          <option value="">All difficulties</option>
          {DIFFICULTIES.map((difficulty) => (
            <option key={difficulty} value={difficulty}>
              {difficulty}
            </option>
          ))}
        </select>
        <button type="submit" className="primary">
          Filter
        </button>
      </form>

      {tasks.length === 0 ? (
        <div className="empty-state">No benchmark tasks match this filter.</div>
      ) : (
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Task</th>
              <th>Category</th>
              <th>Difficulty</th>
              <th>evaluation_type</th>
            </tr>
          </thead>
          <tbody>
            {tasks.map((task) => (
              <tr key={task.id}>
                <td className="mono">
                  <Link href={`/benchmarks/${task.id}`}>{task.id}</Link>
                </td>
                <td>{task.title}</td>
                <td>{task.category}</td>
                <td>{task.difficulty}</td>
                <td className="mono">{task.evaluation_type}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </main>
  );
}
