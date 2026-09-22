from app.core.time import utcnow
from app.models import BenchmarkTaskORM, ExperimentRunORM, ModelConfigORM, ModelExecutionORM


def test_benchmark_task_round_trip(db_session):
    now = utcnow()
    task = BenchmarkTaskORM(
        id="math-001",
        title="Simple multiplication",
        category="math",
        difficulty="easy",
        prompt="What is 17 * 6?",
        evaluation_type="exact_match",
        expected_output="102",
        task_metadata={},
        created_at=now,
        updated_at=now,
    )
    db_session.add(task)
    db_session.commit()

    fetched = db_session.get(BenchmarkTaskORM, "math-001")
    assert fetched is not None
    assert fetched.title == "Simple multiplication"
    assert fetched.category == "math"


def test_experiment_run_and_execution_relationship(db_session):
    now = utcnow()
    task = BenchmarkTaskORM(
        id="math-001",
        title="Simple multiplication",
        category="math",
        difficulty="easy",
        prompt="What is 17 * 6?",
        evaluation_type="exact_match",
        expected_output="102",
        task_metadata={},
        created_at=now,
        updated_at=now,
    )
    model = ModelConfigORM(
        id="mock-fast-v1",
        provider="mock",
        model_id="mock-fast-v1",
        display_name="Mock Fast",
        enabled=True,
        input_cost_per_1k=0.0001,
        output_cost_per_1k=0.0002,
        capabilities={},
        updated_at=now,
    )
    run = ExperimentRunORM(
        id="run-1",
        name="test run",
        status="completed",
        task_ids=["math-001"],
        model_config_ids=["mock-fast-v1"],
        created_at=now,
        completed_at=now,
    )
    execution = ModelExecutionORM(
        run_id="run-1",
        task_id="math-001",
        model_config_id="mock-fast-v1",
        status="success",
        response_text="102",
        latency_ms=42.0,
        input_tokens=10,
        output_tokens=1,
        estimated_cost_usd=0.0000012,
        evaluation_status="correct",
        started_at=now,
        completed_at=now,
    )
    db_session.add_all([task, model, run, execution])
    db_session.commit()

    fetched_run = db_session.get(ExperimentRunORM, "run-1")
    assert fetched_run is not None
    assert len(fetched_run.executions) == 1
    assert fetched_run.executions[0].response_text == "102"
