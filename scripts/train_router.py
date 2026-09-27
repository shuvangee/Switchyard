"""Retrain the V3 escalation router (learned-v2) from the real, committed
Groq evaluation data — a thin, convenience wrapper. The actual training
logic lives in backend/app/routing/learned/train_escalation.py (also
runnable directly as `python -m app.routing.learned.train_escalation`
from inside backend/); this script exists so retraining has one obvious,
memorable entry point from the repo root, no venv path juggling required
beyond the one below.

Deterministic: same input data + the pipeline's fixed random_state=0
always produces the same chosen algorithm and the same fitted artifact.

Run from the repo root:

    cd backend && source .venv/bin/activate
    python ../scripts/train_router.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.routing.learned.train_escalation import run  # noqa: E402

if __name__ == "__main__":
    manifest = run()
    print(json.dumps(manifest, indent=2))
