"""Check API agent construction policy without calling a model provider."""

import inspect
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from gateway.config import PlatformConfig
from gateway.platforms import api_server as api


@pytest.fixture
def make_adapter(monkeypatch):
    store = api.ResponseStore
    monkeypatch.setattr(api, "ResponseStore", lambda: store(db_path=":memory:"))
    instances = []

    def create(extra):
        instance = api.APIServerAdapter(PlatformConfig(enabled=True, extra={
            "key": "unit-service-key", "model_name": "omera", "port": 0,
            **extra,
        }))
        instances.append(instance)
        return instance

    yield create
    for instance in instances:
        instance._response_store.close()


@pytest.mark.parametrize("extra, expected", [
    ({}, False),
    ({"omera_mode": False}, False),
    ({"omera_mode": True}, True),
])
def test_mode_requires_explicit_config(make_adapter, monkeypatch, extra, expected):
    monkeypatch.setenv("API_SERVER_OMERA_MODE", "true")
    adapter = make_adapter(extra)
    assert adapter._omera_mode is expected


@pytest.fixture
def factory_spy(monkeypatch):
    import run_agent
    from gateway import run
    from xavani_cli import runtime_provider, tools_config

    signature = inspect.signature(run_agent.AIAgent)
    constructed = []

    def construct(**kwargs):
        signature.bind(**kwargs)
        agent = SimpleNamespace(
            kwargs=kwargs, tools=[{"name": "terminal"}],
            valid_tool_names={"terminal"}, session_log_file="private.json",
            _persist_disabled=False, _fallback_chain=[{"model": "other"}],
        )
        constructed.append(agent)
        return agent

    runtime = {
        "api_key": "unit-model-key", "base_url": "https://model.invalid/v1",
        "provider": "custom", "api_mode": "chat_completions",
        "command": None, "args": [], "credential_pool": None,
    }
    reasoning = {"enabled": False}
    fallback = {"model": "other"}
    config_loader = Mock(return_value={})
    tools_loader = Mock(return_value={"web", "terminal"})
    fallback_loader = Mock(return_value=fallback)
    real_gateway_resolver = run._resolve_runtime_agent_kwargs
    gateway_resolver = Mock(side_effect=lambda: runtime.copy())
    primary_resolver = Mock(side_effect=lambda **kwargs: runtime.copy())
    constructor = Mock(side_effect=construct)
    monkeypatch.setattr(run_agent, "AIAgent", constructor)
    monkeypatch.setattr(run, "_resolve_runtime_agent_kwargs", gateway_resolver)
    monkeypatch.setattr(runtime_provider, "resolve_runtime_provider", primary_resolver)
    monkeypatch.setattr(run, "_resolve_gateway_model", lambda: "actual-model")
    monkeypatch.setattr(run, "_load_gateway_config", config_loader)
    monkeypatch.setattr(tools_config, "_get_platform_tools", tools_loader)
    monkeypatch.setattr(run.GatewayRunner, "_load_reasoning_config",
                        staticmethod(lambda: reasoning))
    monkeypatch.setattr(run.GatewayRunner, "_load_fallback_model",
                        staticmethod(fallback_loader))
    monkeypatch.setenv("XAVANI_MAX_ITERATIONS", "73")
    monkeypatch.setenv("XAVANI_INFERENCE_PROVIDER", "custom")
    return SimpleNamespace(
        runtime=runtime, reasoning=reasoning, fallback=fallback,
        config_loader=config_loader, tools_loader=tools_loader,
        fallback_loader=fallback_loader, constructed=constructed,
        constructor=constructor, primary_resolver=primary_resolver,
        gateway_resolver=gateway_resolver,
        real_gateway_resolver=real_gateway_resolver,
    )


@pytest.fixture
def request_args():
    headers = {
        "X-Xavani-Session-Id": "caller-session-id",
        "X-Xavani-Session-Key": "caller-session-key",
    }
    return {
        "ephemeral_system_prompt": "Business rules.",
        "session_id": headers["X-Xavani-Session-Id"],
        "gateway_session_key": headers["X-Xavani-Session-Key"],
        "stream_delta_callback": object(),
        "tool_progress_callback": object(),
        "tool_start_callback": object(),
        "tool_complete_callback": object(),
    }


def test_restricted_primary_auth_failure_never_uses_fallback(
        make_adapter, factory_spy, request_args, monkeypatch):
    from gateway import run
    from xavani_cli.auth import AuthError

    adapter = make_adapter({"omera_mode": True})
    failure = AuthError("SYNTHETIC_PRIVATE_AUTH_MARKER", provider="custom")
    factory_spy.primary_resolver.side_effect = failure
    monkeypatch.setattr(run, "_resolve_runtime_agent_kwargs",
                        factory_spy.real_gateway_resolver)
    fallback_resolver = Mock(side_effect=AssertionError("FALLBACK_MUST_NOT_RUN"))
    monkeypatch.setattr(run, "_try_resolve_fallback_provider", fallback_resolver)

    with pytest.raises(RuntimeError, match="^PRIMARY_PROVIDER_UNAVAILABLE$") as error:
        adapter._create_agent(**request_args)

    assert error.value.__cause__ is failure
    factory_spy.primary_resolver.assert_called_once_with(requested="custom")
    fallback_resolver.assert_not_called()
    factory_spy.fallback_loader.assert_not_called()
    factory_spy.constructor.assert_not_called()


def test_restricted_constructor_policy(make_adapter, factory_spy, request_args,
                                       monkeypatch):
    adapter = make_adapter({"omera_mode": True})
    session_db = Mock(return_value=object())
    monkeypatch.setattr(adapter, "_ensure_session_db", session_db)
    agent = adapter._create_agent(**request_args)
    assert agent.kwargs == {
        **factory_spy.runtime,
        "model": "actual-model",
        "max_iterations": 1,
        "max_tokens": 2048,
        "quiet_mode": True,
        "verbose_logging": False,
        "save_trajectories": False,
        "ephemeral_system_prompt": request_args["ephemeral_system_prompt"],
        "enabled_toolsets": [],
        "disabled_toolsets": ["all"],
        "session_id": None,
        "session_db": None,
        "gateway_session_key": None,
        "fallback_model": None,
        "platform": "omera",
        "skip_memory": True,
        "skip_context_files": True,
        "load_soul_identity": False,
        "prefill_messages": [],
        "stream_delta_callback": request_args["stream_delta_callback"],
        "tool_progress_callback": None,
        "tool_start_callback": None,
        "tool_complete_callback": None,
        "reasoning_config": factory_spy.reasoning,
    }
    session_db.assert_not_called()
    factory_spy.config_loader.assert_not_called()
    factory_spy.tools_loader.assert_not_called()
    factory_spy.fallback_loader.assert_not_called()
    factory_spy.primary_resolver.assert_called_once_with(requested="custom")
    factory_spy.gateway_resolver.assert_not_called()
    assert factory_spy.constructed == [agent]


def test_restricted_agent_has_no_tools(make_adapter, factory_spy, request_args,
                                      monkeypatch):
    adapter = make_adapter({"omera_mode": True})
    session_db = Mock(return_value=object())
    monkeypatch.setattr(adapter, "_ensure_session_db", session_db)
    agent = adapter._create_agent(**request_args)
    assert agent.tools == []
    assert agent.valid_tool_names == set()
    session_db.assert_not_called()
    factory_spy.primary_resolver.assert_called_once_with(requested="custom")
    factory_spy.gateway_resolver.assert_not_called()


@pytest.mark.parametrize("requested, args, expected_args", [
    (None, None, []),
    ("custom", ("--unit-arg",), ["--unit-arg"]),
])
def test_restricted_primary_result_keeps_only_provider_fields(
        make_adapter, factory_spy, request_args, monkeypatch,
        requested, args, expected_args):
    if requested is None:
        monkeypatch.delenv("XAVANI_INFERENCE_PROVIDER", raising=False)
    else:
        monkeypatch.setenv("XAVANI_INFERENCE_PROVIDER", requested)
    factory_spy.primary_resolver.side_effect = None
    factory_spy.primary_resolver.return_value = {
        **factory_spy.runtime,
        "args": args,
        "model": "unexpected-provider-model",
        "unexpected": "must-not-reach-constructor",
        "max_iterations": 99,
    }

    agent = make_adapter({"omera_mode": True})._create_agent(**request_args)

    assert agent.kwargs["model"] == "actual-model"
    assert agent.kwargs["args"] == expected_args
    assert agent.kwargs["max_iterations"] == 1
    assert "unexpected" not in agent.kwargs
    for key in factory_spy.runtime.keys() - {"args"}:
        assert agent.kwargs[key] == factory_spy.runtime[key]
    factory_spy.primary_resolver.assert_called_once_with(requested=requested)
    factory_spy.gateway_resolver.assert_not_called()
    factory_spy.fallback_loader.assert_not_called()
    factory_spy.constructor.assert_called_once()


def test_restricted_primary_non_auth_failure_is_neutral(
        make_adapter, factory_spy, request_args, monkeypatch):
    from gateway import run

    failure = ValueError("SYNTHETIC_PRIVATE_PROVIDER_MARKER")
    factory_spy.primary_resolver.side_effect = failure
    monkeypatch.setattr(run, "_resolve_runtime_agent_kwargs",
                        factory_spy.real_gateway_resolver)
    fallback_resolver = Mock(side_effect=AssertionError("FALLBACK_MUST_NOT_RUN"))
    monkeypatch.setattr(run, "_try_resolve_fallback_provider", fallback_resolver)

    with pytest.raises(RuntimeError, match="^PRIMARY_PROVIDER_UNAVAILABLE$") as error:
        make_adapter({"omera_mode": True})._create_agent(**request_args)

    assert error.value.__cause__ is failure
    factory_spy.primary_resolver.assert_called_once_with(requested="custom")
    fallback_resolver.assert_not_called()
    factory_spy.fallback_loader.assert_not_called()
    factory_spy.constructor.assert_not_called()


@pytest.mark.parametrize("extra", [{}, {"omera_mode": False}])
def test_ordinary_factory_compatibility(make_adapter, factory_spy, request_args,
                                        monkeypatch, extra):
    adapter = make_adapter(extra)
    shared_db = object()
    session_db = Mock(return_value=shared_db)
    monkeypatch.setattr(adapter, "_ensure_session_db", session_db)
    agent = adapter._create_agent(**request_args)
    assert agent.kwargs == {
        **factory_spy.runtime,
        **request_args,
        "model": "actual-model",
        "max_iterations": 73,
        "quiet_mode": True,
        "verbose_logging": False,
        "enabled_toolsets": ["terminal", "web"],
        "platform": "api_server",
        "session_db": shared_db,
        "fallback_model": factory_spy.fallback,
        "reasoning_config": factory_spy.reasoning,
    }
    assert agent.tools == [{"name": "terminal"}]
    assert agent.valid_tool_names == {"terminal"}
    assert agent.session_log_file == "private.json"
    assert agent._persist_disabled is False
    assert agent._fallback_chain == [{"model": "other"}]
    session_db.assert_called_once_with()
    factory_spy.config_loader.assert_called_once_with()
    factory_spy.tools_loader.assert_called_once_with({}, "api_server")
    factory_spy.fallback_loader.assert_called_once_with()
    factory_spy.gateway_resolver.assert_called_once_with()
    factory_spy.primary_resolver.assert_not_called()


def make_persistence_agent(tmp_path, *, disabled):
    from datetime import datetime, timezone
    from threading import Lock
    from run_agent import AIAgent

    agent = object.__new__(AIAgent)
    agent._persist_disabled = disabled
    agent.session_log_file = tmp_path / "customer.json"
    agent.session_id = "unit-customer-session"
    agent.model = "unit-model"
    agent.base_url = "https://model.invalid/v1"
    agent.platform = "omera" if disabled else "api_server"
    agent.session_start = datetime.now(timezone.utc)
    agent._cached_system_prompt = "unit-system-prompt"
    agent.tools = []
    agent.verbose_logging = False
    agent._session_messages = []
    agent._session_db = SimpleNamespace(
        create_session=Mock(), append_message=Mock(),
    )
    agent._session_db_created = False
    agent._session_init_model_config = {}
    agent._parent_session_id = None
    agent._last_flushed_db_idx = 0
    agent._session_persist_lock = Lock()
    return agent


def persistence_messages():
    return [{"role": "user", "content": "SYNTHETIC_OMERA_PRIVACY_CANARY"}]


def test_restricted_factory_disables_all_persistence(
        make_adapter, factory_spy, request_args):
    agent = make_adapter({"omera_mode": True})._create_agent(**request_args)
    assert agent._persist_disabled is True
    assert agent.session_log_file is None
    assert agent._session_db is None
    assert agent._fallback_chain == []


def test_disabled_json_writer_skips_content_and_io(tmp_path, monkeypatch):
    import run_agent

    agent = make_persistence_agent(tmp_path, disabled=True)
    clean = Mock(wraps=agent._clean_session_content)
    write = Mock(wraps=run_agent.atomic_json_write)
    monkeypatch.setattr(agent, "_clean_session_content", clean)
    monkeypatch.setattr(run_agent, "atomic_json_write", write)
    messages = [{"role": "assistant", "content": "SYNTHETIC_OMERA_PRIVACY_CANARY"}]
    agent._save_session_log(messages)
    clean.assert_not_called()
    write.assert_not_called()
    assert not agent.session_log_file.exists()


def test_disabled_db_writer_skips_content_and_io(tmp_path, monkeypatch):
    agent = make_persistence_agent(tmp_path, disabled=True)
    override = Mock(wraps=agent._apply_persist_user_message_override)
    monkeypatch.setattr(agent, "_apply_persist_user_message_override", override)
    agent._flush_messages_to_session_db_unlocked(persistence_messages())
    override.assert_not_called()
    agent._session_db.create_session.assert_not_called()
    agent._session_db.append_message.assert_not_called()
    assert agent._last_flushed_db_idx == 0
