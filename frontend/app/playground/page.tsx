import { PlaygroundForm } from "@/components/PlaygroundForm";

export default function PlaygroundPage() {
  return (
    <main className="page">
      <h1 style={{ fontSize: "1.3rem", margin: 0 }}>Playground</h1>
      <p style={{ color: "var(--text-muted)" }}>
        Submit a request and see how the router analyzes and routes it — not a chat interface,
        a view into the routing decision.
      </p>
      <PlaygroundForm />
    </main>
  );
}
