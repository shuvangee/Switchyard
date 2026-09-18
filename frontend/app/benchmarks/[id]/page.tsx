import Link from "next/link";
import { notFound } from "next/navigation";
import { ApiError, getBenchmark } from "@/lib/api";

export default async function BenchmarkDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  let task;
  try {
    task = await getBenchmark(id);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      notFound();
    }
    throw error;
  }

  const hasMetadata = Object.keys(task.metadata).length > 0;

  return (
    <main className="page">
      <p>
        <Link href="/benchmarks">&larr; Benchmarks</Link>
      </p>
      <h1 style={{ fontSize: "1.3rem", marginBottom: "0.2rem" }}>{task.title}</h1>
      <p className="mono" style={{ color: "var(--text-muted)" }}>
        {task.id}
      </p>

      <div className="stat-row" style={{ marginTop: "1rem" }}>
        <div>
          <div className="section-label">Category</div>
          <div>{task.category}</div>
        </div>
        <div>
          <div className="section-label">Difficulty</div>
          <div>{task.difficulty}</div>
        </div>
        <div>
          <div className="section-label">Evaluation type</div>
          <div className="mono">{task.evaluation_type}</div>
        </div>
      </div>

      <h2 className="section-label">Prompt</h2>
      <pre className="prompt-block">{task.prompt}</pre>

      {task.expected_output !== null && (
        <>
          <h2 className="section-label">Expected output</h2>
          <pre className="prompt-block">{task.expected_output}</pre>
        </>
      )}

      {hasMetadata && (
        <>
          <h2 className="section-label">Metadata</h2>
          <pre className="prompt-block">{JSON.stringify(task.metadata, null, 2)}</pre>
        </>
      )}
    </main>
  );
}
