import pytest

from app.core.config import Settings
from app.models.model_config import ModelConfigORM
from app.providers.base import Provider
from app.providers.registry import get_model_registry, get_provider, sync_model_configs


def test_mock_models_enabled_without_any_settings():
    registry = get_model_registry(Settings(openai_api_key=None))
    mock_models = [m for m in registry if m.provider == "mock"]
    assert len(mock_models) == 3
    assert all(m.enabled for m in mock_models)


def test_openai_model_disabled_without_key():
    registry = get_model_registry(Settings(openai_api_key=None))
    openai_model = next(m for m in registry if m.provider == "openai")
    assert openai_model.enabled is False


def test_openai_model_enabled_with_key():
    registry = get_model_registry(Settings(openai_api_key="sk-fake"))
    openai_model = next(m for m in registry if m.provider == "openai")
    assert openai_model.enabled is True


def test_gemini_model_disabled_without_key():
    registry = get_model_registry(Settings(google_api_key=None))
    gemini_model = next(m for m in registry if m.provider == "gemini")
    assert gemini_model.enabled is False


def test_gemini_model_enabled_with_key():
    registry = get_model_registry(Settings(google_api_key="fake-key"))
    gemini_model = next(m for m in registry if m.provider == "gemini")
    assert gemini_model.enabled is True


def test_grok_model_disabled_without_key():
    registry = get_model_registry(Settings(xai_api_key=None))
    grok_model = next(m for m in registry if m.provider == "grok")
    assert grok_model.enabled is False


def test_grok_model_enabled_with_key():
    registry = get_model_registry(Settings(xai_api_key="fake-key"))
    grok_model = next(m for m in registry if m.provider == "grok")
    assert grok_model.enabled is True


def test_groq_models_disabled_without_key():
    registry = get_model_registry(Settings(groq_api_key=None))
    groq_models = [m for m in registry if m.provider == "groq"]
    assert len(groq_models) == 3
    assert all(m.enabled is False for m in groq_models)


def test_groq_models_enabled_with_key():
    registry = get_model_registry(Settings(groq_api_key="gsk-fake"))
    groq_models = [m for m in registry if m.provider == "groq"]
    assert len(groq_models) == 3
    assert all(m.enabled is True for m in groq_models)


def test_get_provider_returns_provider_instance():
    assert isinstance(get_provider("mock"), Provider)
    assert isinstance(get_provider("openai", Settings(openai_api_key="sk-fake")), Provider)
    assert isinstance(get_provider("gemini", Settings(google_api_key="fake-key")), Provider)
    assert isinstance(get_provider("grok", Settings(xai_api_key="fake-key")), Provider)
    assert isinstance(get_provider("groq", Settings(groq_api_key="gsk-fake")), Provider)


def test_get_provider_rejects_unknown_name():
    with pytest.raises(ValueError):
        get_provider("not-a-provider")


def test_sync_model_configs_upserts_registry(db_session):
    sync_model_configs(db_session, Settings(openai_api_key=None))
    rows = db_session.query(ModelConfigORM).all()
    assert len(rows) == len(get_model_registry(Settings(openai_api_key=None)))
    openai_row = db_session.get(ModelConfigORM, "openai-gpt-4o-mini")
    assert openai_row.enabled is False

    # Re-sync with a key now set: existing row updates rather than duplicating.
    sync_model_configs(db_session, Settings(openai_api_key="sk-fake"))
    assert db_session.query(ModelConfigORM).count() == len(
        get_model_registry(Settings(openai_api_key=None))
    )
    openai_row = db_session.get(ModelConfigORM, "openai-gpt-4o-mini")
    assert openai_row.enabled is True
