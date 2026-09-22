import json

import pytest

from app.experiments.loader import (
    BenchmarkLoadError,
    default_benchmarks_dir,
    load_benchmark_tasks,
    sync_benchmark_tasks,
)
from app.models.benchmark import BenchmarkTaskORM
from app.models.enums import TaskCategory, TaskDifficulty


def _write_task(directory, filename: str, data: dict) -> None:
    (directory / filename).write_text(json.dumps(data))


def test_loads_valid_task_file(tmp_path):
    _write_task(
        tmp_path,
        "math-001.json",
        {
            "id": "math-001",
            "title": "Addition",
            "category": "math",
            "difficulty": "easy",
            "prompt": "What is 2 + 2?",
            "evaluation_type": "exact_match",
            "expected_output": "4",
        },
    )
    tasks = load_benchmark_tasks(tmp_path)
    assert len(tasks) == 1
    assert tasks[0].id == "math-001"
    assert tasks[0].category == TaskCategory.MATH
    assert tasks[0].difficulty == TaskDifficulty.EASY


def test_missing_directory_raises(tmp_path):
    with pytest.raises(BenchmarkLoadError):
        load_benchmark_tasks(tmp_path / "does-not-exist")


def test_invalid_json_raises(tmp_path):
    (tmp_path / "broken.json").write_text("{not valid json")
    with pytest.raises(BenchmarkLoadError):
        load_benchmark_tasks(tmp_path)


def test_invalid_category_raises(tmp_path):
    _write_task(
        tmp_path,
        "bad-001.json",
        {
            "id": "bad-001",
            "title": "Bad",
            "category": "not-a-real-category",
            "difficulty": "easy",
            "prompt": "x",
            "evaluation_type": "manual",
        },
    )
    with pytest.raises(BenchmarkLoadError):
        load_benchmark_tasks(tmp_path)


def test_id_must_match_filename(tmp_path):
    _write_task(
        tmp_path,
        "math-001.json",
        {
            "id": "different-id",
            "title": "Addition",
            "category": "math",
            "difficulty": "easy",
            "prompt": "What is 2 + 2?",
            "evaluation_type": "exact_match",
            "expected_output": "4",
        },
    )
    with pytest.raises(BenchmarkLoadError, match="does not match filename"):
        load_benchmark_tasks(tmp_path)


def test_duplicate_ids_raise(tmp_path):
    task = {
        "id": "dup-001",
        "title": "Dup",
        "category": "math",
        "difficulty": "easy",
        "prompt": "x",
        "evaluation_type": "manual",
    }
    _write_task(tmp_path, "dup-001.json", task)
    # a second file that happens to declare the same id
    second = dict(task)
    (tmp_path / "dup-001-copy.json").write_text(json.dumps(second))
    with pytest.raises(BenchmarkLoadError):
        load_benchmark_tasks(tmp_path)


def test_sync_upserts_into_db(db_session, tmp_path):
    _write_task(
        tmp_path,
        "math-001.json",
        {
            "id": "math-001",
            "title": "Addition",
            "category": "math",
            "difficulty": "easy",
            "prompt": "What is 2 + 2?",
            "evaluation_type": "exact_match",
            "expected_output": "4",
        },
    )
    tasks = load_benchmark_tasks(tmp_path)
    sync_benchmark_tasks(db_session, tasks)

    row = db_session.get(BenchmarkTaskORM, "math-001")
    assert row is not None
    assert row.title == "Addition"

    # Change the file and re-sync: the DB row should update, not duplicate.
    _write_task(
        tmp_path,
        "math-001.json",
        {
            "id": "math-001",
            "title": "Addition (revised)",
            "category": "math",
            "difficulty": "medium",
            "prompt": "What is 2 + 2?",
            "evaluation_type": "exact_match",
            "expected_output": "4",
        },
    )
    tasks = load_benchmark_tasks(tmp_path)
    sync_benchmark_tasks(db_session, tasks)

    row = db_session.get(BenchmarkTaskORM, "math-001")
    assert row.title == "Addition (revised)"
    assert row.difficulty == "medium"
    assert db_session.query(BenchmarkTaskORM).count() == 1


def test_real_repo_benchmark_tasks_are_valid():
    """Regression check: the actual benchmarks/tasks/ content must load cleanly."""
    tasks = load_benchmark_tasks(default_benchmarks_dir())
    assert len(tasks) >= 8
    categories = {task.category for task in tasks}
    assert len(categories) == 8  # one of each TaskCategory represented
