"""Generate real Gemini responses for the 20 manual-eval-type benchmark
tasks (coding, debugging, reasoning, summarization) so they can actually
be graded — MockProvider's response to these is always its generic
templated fallback string, not a real answer, so there's nothing useful
to grade there.

Writes both a machine-readable JSON file (task metadata + rubric +
response + latency/tokens/cost) and a human-readable Markdown file
pairing each prompt, its grading rubric, and the response for someone to
actually read through and grade.

Retries on rate limits, same as run_gemini_baseline.py. Requires
GOOGLE_API_KEY (backend/.env) and costs real money — see the cost
estimate in docs/case-study/EXPERIMENTS.md made before this was run.

Run from the repo root:

    cd backend && source .venv/bin/activate
    python ../scripts/generate_manual_grading_responses.py
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.core.config import get_settings  # noqa: E402
from app.experiments.loader import default_benchmarks_dir, load_benchmark_tasks  # noqa: E402
from app.providers.base import ProviderError  # noqa: E402
from app.providers.pricing import estimate_cost_usd  # noqa: E402
from app.providers.registry import get_model_registry, get_provider  # noqa: E402

MODEL_CONFIG_ID = "gemini-3.6-flash"
CATEGORIES = ["coding", "debugging", "reasoning", "summarization"]
MAX_RETRY_ROUNDS = 2
RETRY_BACKOFF_SECONDS = 20
REPO_ROOT = Path(__file__).resolve().parents[1]


def _call(provider, task, model_config) -> dict:
    try:
        result = provider.generate(MODEL_CONFIG_ID, task.prompt)
        cost = estimate_cost_usd(
            input_cost_per_1k=model_config.input_cost_per_1k,
            output_cost_per_1k=model_config.output_cost_per_1k,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
        )
        return {
            "task_id": task.id,
            "category": task.category.value,
            "difficulty": task.difficulty.value,
            "prompt": task.prompt,
            "rubric": task.metadata.get("notes", ""),
            "status": "success",
            "response_text": result.text,
            "latency_ms": result.latency_ms,
            "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens,
            "estimated_cost_usd": cost,
            "error_message": None,
        }
    except ProviderError as exc:
        return {
            "task_id": task.id,
            "category": task.category.value,
            "difficulty": task.difficulty.value,
            "prompt": task.prompt,
            "rubric": task.metadata.get("notes", ""),
            "status": "error",
            "response_text": None,
            "latency_ms": None,
            "input_tokens": None,
            "output_tokens": None,
            "estimated_cost_usd": None,
            "error_message": str(exc),
        }


def main() -> None:
    settings = get_settings()
    if not settings.google_api_key:
        raise SystemExit("GOOGLE_API_KEY is not set (backend/.env) — aborting before any call.")

    tasks = [t for t in load_benchmark_tasks(default_benchmarks_dir()) if t.category.value in CATEGORIES]
    provider = get_provider("gemini", settings)
    model_config = next(m for m in get_model_registry(settings) if m.id == MODEL_CONFIG_ID)

    rows_by_id = {t.id: _call(provider, t, model_config) for t in tasks}
    tasks_by_id = {t.id: t for t in tasks}

    for round_num in range(1, MAX_RETRY_ROUNDS + 1):
        failed_ids = [tid for tid, r in rows_by_id.items() if r["status"] != "success"]
        if not failed_ids:
            break
        print(f"retry round {round_num}: {len(failed_ids)} task(s) failed, waiting {RETRY_BACKOFF_SECONDS}s...")
        time.sleep(RETRY_BACKOFF_SECONDS)
        for tid in failed_ids:
            rows_by_id[tid] = _call(provider, tasks_by_id[tid], model_config)

    rows = [rows_by_id[t.id] for t in tasks]

    json_path = REPO_ROOT / "experiments/results/manual-grading-gemini-3.6-flash.json"
    json_path.write_text(json.dumps({"model_id": MODEL_CONFIG_ID, "tasks": rows}, indent=2) + "\n")

    md_lines = [
        "# Manual grading — gemini-3.6-flash",
        "",
        "One entry per task: prompt, grading rubric (from the benchmark task's",
        "`metadata.notes`), and the real Gemini response. Grade each against its",
        "rubric — no automated evaluator scores these (`evaluation_type: manual`).",
        "",
    ]
    for r in rows:
        md_lines.append(f"## {r['task_id']} ({r['category']}, {r['difficulty']})")
        md_lines.append("")
        md_lines.append(f"**Prompt:**\n\n```\n{r['prompt']}\n```")
        md_lines.append("")
        md_lines.append(f"**Rubric:** {r['rubric']}")
        md_lines.append("")
        if r["status"] == "success":
            md_lines.append(f"**Response:**\n\n```\n{r['response_text']}\n```")
        else:
            md_lines.append(f"**FAILED:** {r['error_message']}")
        md_lines.append("")
        md_lines.append("**Grade:** _(fill in: correct / partially correct / incorrect, plus why)_")
        md_lines.append("")
        md_lines.append("---")
        md_lines.append("")

    md_path = REPO_ROOT / "experiments/results/manual-grading-gemini-3.6-flash.md"
    md_path.write_text("\n".join(md_lines))

    succeeded = sum(1 for r in rows if r["status"] == "success")
    total_cost = sum(r["estimated_cost_usd"] for r in rows if r["estimated_cost_usd"])
    total_in = sum(r["input_tokens"] for r in rows if r["input_tokens"])
    total_out = sum(r["output_tokens"] for r in rows if r["output_tokens"])
    print(f"\nwrote {json_path.relative_to(REPO_ROOT)}")
    print(f"wrote {md_path.relative_to(REPO_ROOT)}")
    print(f"succeeded: {succeeded}/{len(rows)}")
    print(f"total input tokens: {total_in}  total output tokens: {total_out}")
    print(f"total estimated cost: ${total_cost:.6f}")


if __name__ == "__main__":
    main()
