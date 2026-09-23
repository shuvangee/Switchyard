"""Exports response_text for every remaining task whose ORIGINAL Groq
run response is still gradeable as-is - no prompt changed, so no new
API call is needed, just reading it back out of the local database.

Covers: reasoning-001/002/003 (converted to exact_match) and all 13
summarization tasks (6 now auto-gradeable via required_facts, 7 stay
manual but still worth having the real response text for human review).
Does NOT cover reasoning-005 or debugging-001-008 - those had their
PROMPTS revised, so their original responses don't match the new
format and need an actual new Groq call instead (see
scripts/run_groq_revision_batch.py).

Same rationale as export_groq_code_responses.py: response_text was
never saved to experiments/results/groq-gpt-oss-expansion.json, so it
has to be read back out of the local database from the original run.

Run this on the SAME machine (and same backend/switchyard.db) the
original Groq run happened on:

    cd backend && source .venv/bin/activate
    python ../scripts/export_original_run_extras.py

Then commit and push the resulting experiments/results/groq-remaining-
responses.json.
"""

import json
import sqlite3
from pathlib import Path

TASK_IDS = (
    ["reasoning-001", "reasoning-002", "reasoning-003"]
    + [f"summarization-{i:03d}" for i in range(1, 14)]
)
MODEL_IDS = ["groq-gpt-oss-20b", "groq-gpt-oss-120b"]


def main() -> None:
    db_path = Path(__file__).resolve().parents[1] / "backend" / "switchyard.db"
    if not db_path.exists():
        raise SystemExit(f"{db_path} not found - run this on the machine the Groq run happened on.")

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    placeholders_task = ",".join("?" * len(TASK_IDS))
    placeholders_model = ",".join("?" * len(MODEL_IDS))
    rows = conn.execute(
        f"""
        SELECT task_id, model_config_id, status, response_text, error_message
        FROM model_executions
        WHERE task_id IN ({placeholders_task})
          AND model_config_id IN ({placeholders_model})
        ORDER BY task_id, model_config_id, id
        """,
        [*TASK_IDS, *MODEL_IDS],
    ).fetchall()
    conn.close()

    if not rows:
        raise SystemExit("no matching rows found - wrong database, or this table has since been cleared.")

    latest: dict[tuple[str, str], dict] = {}
    for row in rows:
        latest[(row["task_id"], row["model_config_id"])] = dict(row)

    records = list(latest.values())
    missing = [(tid, mid) for tid in TASK_IDS for mid in MODEL_IDS if (tid, mid) not in latest]

    output = {
        "note": "response_text export from local switchyard.db - no new API calls",
        "task_count": len(TASK_IDS),
        "model_ids": MODEL_IDS,
        "executions": records,
    }
    results_path = Path(__file__).resolve().parents[1] / "experiments" / "results" / "groq-remaining-responses.json"
    results_path.parent.mkdir(parents=True, exist_ok=True)
    results_path.write_text(json.dumps(output, indent=2) + "\n")

    print(f"wrote {results_path.relative_to(Path(__file__).resolve().parents[1])}")
    print(f"found: {len(records)}/{len(TASK_IDS) * len(MODEL_IDS)} (task, model) rows")
    if missing:
        print(f"missing ({len(missing)}):")
        for tid, mid in missing:
            print(f"  {tid} / {mid}")


if __name__ == "__main__":
    main()
