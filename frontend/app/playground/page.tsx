import { PlaygroundForm } from "@/components/PlaygroundForm";
import { getModels } from "@/lib/api";

export default async function PlaygroundPage() {
  const models = await getModels();
  const groq20b = models.find((m) => m.id === "groq-gpt-oss-20b");
  const groq120b = models.find((m) => m.id === "groq-gpt-oss-120b");
  const groqConfigured = Boolean(groq20b?.enabled && groq120b?.enabled);

  return (
    <main className="page">
      <h1 style={{ fontSize: "1.3rem", margin: 0 }}>Playground</h1>
      <p style={{ color: "var(--text-muted)" }}>
        Submit a request and see how the router analyzes and routes it — not a chat interface,
        a view into the routing decision.
      </p>
      <PlaygroundForm groqConfigured={groqConfigured} />
    </main>
  );
}
