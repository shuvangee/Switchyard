import Link from "next/link";
import { getBenchmarks } from "@/lib/api";
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

export default async function BenchmarksPage({
  searchParams,
}: {
  searchParams: Promise<{ category?: string; difficulty?: string }>;
}) {
  const params = await searchParams;
  const tasks = await getBenchmarks({ category: params.category, difficulty: params.difficulty });

  return (
    <main className="page">
      <h1 style={{ fontSize: "1.3rem", margin: 0 }}>Benchmarks</h1>
      <p style={{ color: "var(--text-muted)" }}>
        {tasks.length} task{tasks.length === 1 ? "" : "s"}
      </p>

      <form className="filters" method="get">
        <select name="category" defaultValue={params.category ?? ""}>
          <option value="">All categories</option>
          {CATEGORIES.map((category) => (
            <option key={category} value={category}>
              {category}
            </option>
          ))}
        </select>
        <select name="difficulty" defaultValue={params.difficulty ?? ""}>
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
              <th>Evaluation</th>
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
