import pytest

from app.core.config import Settings
from app.core.time import utcnow
from app.experiments.runner import ExperimentRunnerError, run_experiment
from app.models.benchmark import BenchmarkTaskORM
from app.models.enums import EvaluationStatus, ExecutionStatus
from app.models.experiment import ExperimentRunORM, ModelExecutionORM
from app.providers.registry import sync_model_configs


@pytest.fixture()
def seeded_session(db_session):
    now = utcnow()
    db_session.add_all(
        [
            BenchmarkTaskORM(
                id="math-001",
                title="Multiplication",
                category="math",
                difficulty="easy",
                prompt="What is 17 * 6?",
                evaluation_type="exact_match",
                expected_output="102",
                task_metadata={},
                created_at=now,
                updated_at=now,
            ),
            BenchmarkTaskORM(
                id="reasoning-001",
                title="Manual reasoning task",
                category="reasoning",
                difficulty="medium",
                prompt="Explain why the sky is blue.",
                evaluation_type="manual",
                expected_output=None,
                task_metadata={},
                created_at=now,
                updated_at=now,
            ),
        ]
    )
    sync_model_configs(db_session, Settings(openai_api_key=None))
    db_session.commit()
    return db_session


def test_run_creates_one_execution_per_task_model_pair(seeded_session):
    run = run_experiment(
        seeded_session,
        task_ids=["math-001", "reasoning-001"],
        model_config_ids=["mock-fast-v1", "mock-accurate-v1"],
        name="smoke test",
    )
    assert run.status == "completed"
    executions = (
        seeded_session.query(ModelExecutionORM).filter(ModelExecutionORM.run_id == run.id).all()
    )
    assert len(executions) == 4  # 2 tasks x 2 models


def test_deterministic_exact_match_task_evaluates_correctly(seeded_session):
    run = run_experiment(
        seeded_session,
        task_ids=["math-001"],
        model_config_ids=["mock-accurate-v1"],
    )
    execution = (
        seeded_session.query(ModelExecutionORM).filter(ModelExecutionORM.run_id == run.id).one()
    )
    assert execution.status == ExecutionStatus.SUCCESS.value
    assert execution.response_text == "102"
    assert execution.evaluation_status == EvaluationStatus.CORRECT.value
    assert execution.estimated_cost_usd is not None
    assert execution.latency_ms is not None


def test_manual_task_is_not_evaluated(seeded_session):
    run = run_experiment(
        seeded_session,
        task_ids=["reasoning-001"],
        model_config_ids=["mock-fast-v1"],
    )
    execution = (
        seeded_session.query(ModelExecutionORM).filter(ModelExecutionORM.run_id == run.id).one()
    )
    assert execution.evaluation_status == EvaluationStatus.NOT_EVALUATED.value


def test_flaky_model_failure_does_not_stop_other_executions(seeded_session):
    run = run_experiment(
        seeded_session,
        task_ids=["math-001", "reasoning-001"],
        model_config_ids=["mock-flaky-v1", "mock-accurate-v1"],
    )
    executions = (
        seeded_session.query(ModelExecutionORM).filter(ModelExecutionORM.run_id == run.id).all()
    )
    # All 4 combinations are recorded regardless of whether the flaky model
    # errored on any given task.
    assert len(executions) == 4
    statuses = {e.status for e in executions}
    assert statuses <= {ExecutionStatus.SUCCESS.value, ExecutionStatus.ERROR.value}
    accurate_executions = [e for e in executions if e.model_config_id == "mock-accurate-v1"]
    assert all(e.status == ExecutionStatus.SUCCESS.value for e in accurate_executions)


def test_error_execution_has_no_evaluation_and_no_response(seeded_session):
    # mock-flaky-v1 is deterministic; find a task prompt that trips its
    # simulated error for this test rather than relying on our two fixed
    # sample tasks to happen to trigger it.
    from app.providers.mock import MockProvider
    from app.providers.base import ProviderError

    provider = MockProvider()
    flaky_prompt = None
    for i in range(50):
        candidate = f"trigger search {i}"
        try:
            provider.generate("mock-flaky-v1", candidate)
        except ProviderError:
            flaky_prompt = candidate
            break
    assert flaky_prompt is not None

    now = utcnow()
    seeded_session.add(
        BenchmarkTaskORM(
            id="flaky-trigger",
            title="Flaky trigger",
            category="reasoning",
            difficulty="easy",
            prompt=flaky_prompt,
            evaluation_type="manual",
            expected_output=None,
            task_metadata={},
            created_at=now,
            updated_at=now,
        )
    )
    seeded_session.commit()

    run = run_experiment(
        seeded_session,
        task_ids=["flaky-trigger"],
        model_config_ids=["mock-flaky-v1"],
    )
    execution = (
        seeded_session.query(ModelExecutionORM).filter(ModelExecutionORM.run_id == run.id).one()
    )
    assert execution.status == ExecutionStatus.ERROR.value
    assert execution.error_message is not None
    assert execution.response_text is None
    assert execution.evaluation_status == EvaluationStatus.NOT_EVALUATED.value
    assert execution.estimated_cost_usd is None


def test_unknown_task_id_raises(seeded_session):
    with pytest.raises(ExperimentRunnerError, match="unknown task ids"):
        run_experiment(seeded_session, task_ids=["not-a-task"], model_config_ids=["mock-fast-v1"])


def test_unknown_model_id_raises(seeded_session):
    with pytest.raises(ExperimentRunnerError, match="unknown model_config ids"):
        run_experiment(seeded_session, task_ids=["math-001"], model_config_ids=["not-a-model"])


def test_disabled_model_raises(seeded_session):
    with pytest.raises(ExperimentRunnerError, match="disabled"):
        run_experiment(
            seeded_session, task_ids=["math-001"], model_config_ids=["openai-gpt-4o-mini"]
        )


def test_empty_task_ids_raises(seeded_session):
    with pytest.raises(ExperimentRunnerError):
        run_experiment(seeded_session, task_ids=[], model_config_ids=["mock-fast-v1"])


def test_run_is_persisted_and_queryable(seeded_session):
    run = run_experiment(
        seeded_session,
        task_ids=["math-001"],
        model_config_ids=["mock-fast-v1"],
        name="persistence check",
    )
    fetched = seeded_session.get(ExperimentRunORM, run.id)
    assert fetched is not None
    assert fetched.name == "persistence check"
    assert fetched.task_ids == ["math-001"]
    assert fetched.model_config_ids == ["mock-fast-v1"]
    assert fetched.completed_at is not None
