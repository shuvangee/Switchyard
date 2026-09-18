"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { ApiError, createExperiment } from "@/lib/api";
import type { BenchmarkTask, ModelConfig } from "@/types/api";

export function NewExperimentForm({
  tasks,
  models,
}: {
  tasks: BenchmarkTask[];
  models: ModelConfig[];
}) {
  const router = useRouter();
  const [selectedTaskIds, setSelectedTaskIds] = useState<string[]>([]);
  const [selectedModelIds, setSelectedModelIds] = useState<string[]>([]);
  const [name, setName] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function toggle(list: string[], setList: (value: string[]) => void, id: string) {
    setList(list.includes(id) ? list.filter((existing) => existing !== id) : [...list, id]);
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);

    if (selectedTaskIds.length === 0) {
      setError("Select at least one benchmark task.");
      return;
    }
    if (selectedModelIds.length === 0) {
      setError("Select at least one model.");
      return;
    }

    setSubmitting(true);
    try {
      const run = await createExperiment({
        task_ids: selectedTaskIds,
        model_config_ids: selectedModelIds,
        name: name || undefined,
      });
      router.push(`/experiments/${run.id}`);
      router.refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to start experiment.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="card-form" onSubmit={handleSubmit}>
      <div className="field">
        <label htmlFor="run-name">Run name (optional)</label>
        <input
          id="run-name"
          type="text"
          value={name}
          onChange={(event) => setName(event.target.value)}
        />
      </div>

      <div className="field">
        <label>Benchmark tasks ({selectedTaskIds.length} selected)</label>
        <div className="checkbox-list">
          {tasks.map((task) => (
            <label key={task.id} className="checkbox-row">
              <input
                type="checkbox"
                checked={selectedTaskIds.includes(task.id)}
                onChange={() => toggle(selectedTaskIds, setSelectedTaskIds, task.id)}
              />
              <span className="mono">{task.id}</span> — {task.title} ({task.category}/
              {task.difficulty})
            </label>
          ))}
        </div>
      </div>

      <div className="field">
        <label>Models ({selectedModelIds.length} selected)</label>
        <div className="checkbox-list">
          {models.map((model) => (
            <label
              key={model.id}
              className="checkbox-row"
              style={{ opacity: model.enabled ? 1 : 0.5 }}
            >
              <input
                type="checkbox"
                disabled={!model.enabled}
                checked={selectedModelIds.includes(model.id)}
                onChange={() => toggle(selectedModelIds, setSelectedModelIds, model.id)}
              />
              <span className="mono">{model.id}</span> — {model.display_name}
              {!model.enabled && " (disabled — missing credentials)"}
            </label>
          ))}
        </div>
      </div>

      {error && <p className="error-text">{error}</p>}

      <button type="submit" className="primary" disabled={submitting}>
        {submitting ? "Running…" : "Run experiment"}
      </button>
    </form>
  );
}
