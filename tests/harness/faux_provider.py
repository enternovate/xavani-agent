# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Faux provider harness for agent-loop tests (Task 24, pi harness pattern).

Scripts the REAL ``run_agent`` loop with a fake OpenAI client so tests
exercise the loop's actual transport seam (``_interruptible_api_call`` →
``chat.completions.create``), real tool dispatch, and retry paths — with
zero API keys and zero network.

Seam: ``agent.agent_runtime_helpers.create_openai_client`` constructs the
client via ``_ra().OpenAI(**client_kwargs)`` (resolved lazily through the
module ``__getattr__``), so patching ``run_agent.OpenAI`` with
:meth:`FauxProvider.client_factory` redirects every client the loop builds
(primary + per-request) to one shared scripted provider.

Shapes mimic the OpenAI SDK objects the loop reads: a completion has
``choices[0].message`` (``content`` / ``tool_calls``), ``usage`` and
``model``; streaming returns an iterable of chunk objects whose
``choices[0].delta`` carries ``content`` / ``tool_calls``.  Only the
attributes the loop actually reads are implemented — enough for the smoke
tests, nothing more.
"""

from __future__ import annotations

import json
from typing import Any, Callable, Dict, List, Optional


class _Delta:
    """Streaming chunk delta."""

    def __init__(self, content: str = "", tool_calls: Optional[list] = None) -> None:
        self.content = content
        self.tool_calls = tool_calls or []


class _Choice:
    """One completion choice (final or per-chunk)."""

    def __init__(self, message: Optional[Any] = None, delta: Optional[Any] = None,
                 finish_reason: Optional[str] = None) -> None:
        self.message = message
        self.delta = delta
        self.finish_reason = finish_reason


class _Message:
    """Assistant message payload."""

    def __init__(self, content: str = "", tool_calls: Optional[list] = None) -> None:
        self.content = content
        self.tool_calls = tool_calls or []


class _Usage:
    """Minimal usage block (the loop reads prompt/completion tokens)."""

    def __init__(self, prompt_tokens: int = 10, completion_tokens: int = 10,
                 total_tokens: int = 20) -> None:
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_tokens = total_tokens


class _ToolCall:
    """Assistant tool-call payload (id/function name+args)."""

    def __init__(self, name: str, arguments: dict, index: int = 0) -> None:
        self.id = f"call_{index}"
        self.type = "function"
        self.function = _FunctionCall(name, arguments)


class _FunctionCall:
    def __init__(self, name: str, arguments: dict) -> None:
        self.name = name
        self.arguments = json.dumps(arguments)


class _Completion:
    """Non-streaming completion object."""

    def __init__(self, content: str, tool_calls: Optional[list], model: str) -> None:
        self.choices = [_Choice(message=_Message(content=content, tool_calls=tool_calls),
                                finish_reason="stop" if not tool_calls else "tool_calls")]
        self.usage = _Usage()
        self.model = model


class _Chunk:
    """One streaming chunk."""

    def __init__(self, content: str = "", tool_calls: Optional[list] = None,
                 finish_reason: Optional[str] = None) -> None:
        self.choices = [_Choice(delta=_Delta(content=content, tool_calls=tool_calls),
                                finish_reason=finish_reason)]
        self.usage = None


class _ToolCallDelta:
    """Streaming tool-call delta (attribute-shaped, like the OpenAI SDK)."""

    def __init__(self, name: str, arguments: str, call_id: str = "call_0",
                 index: int = 0) -> None:
        self.index = index
        self.id = call_id
        self.type = "function"
        self.function = _FunctionDelta(name, arguments)


class _FunctionDelta:
    def __init__(self, name: str, arguments: str) -> None:
        self.name = name
        self.arguments = arguments


class FauxProvider:
    """A fake OpenAI client that replays a scripted response sequence.

    ``calls`` records every ``chat.completions.create`` invocation as
    ``{"kwargs": ..., "messages": [...], "tools": [...]}`` so tests can
    assert what the loop sent (e.g. that a tool result was fed back).
    """

    def __init__(self, script: List[Callable[[], Any]]) -> None:
        self._script = list(script)
        self._idx = 0
        self.calls: List[Dict[str, Any]] = []

    class _Completions:
        def __init__(self, provider: "FauxProvider") -> None:
            self._provider = provider

        def create(self, **kwargs: Any) -> Any:
            return self._provider._create(**kwargs)

    class _Chat:
        def __init__(self, provider: "FauxProvider") -> None:
            self.completions = FauxProvider._Completions(provider)

    @property
    def chat(self) -> "_Chat":
        return FauxProvider._Chat(self)

    def _create(self, **kwargs: Any) -> Any:
        self.calls.append({
            "kwargs": kwargs,
            "messages": kwargs.get("messages", []),
            "tools": kwargs.get("tools", []),
        })
        if self._idx >= len(self._script):
            raise AssertionError(
                f"faux provider script exhausted ({self._idx} responses played)"
            )
        step = self._script[self._idx]
        self._idx += 1
        result = step()
        if kwargs.get("stream"):
            # The loop's streaming path iterates the returned object; wrap
            # the scripted response into SDK-shaped chunks.
            return self._as_stream(result)
        return result

    @staticmethod
    def _as_stream(result: Any) -> List[_Chunk]:
        """Convert a scripted completion into a chunked stream."""
        if isinstance(result, (list, tuple)) and result and isinstance(result[0], _Chunk):
            return list(result)
        if isinstance(result, _Completion):
            choice = result.choices[0]
            message = choice.message
            chunks: List[_Chunk] = []
            if message.tool_calls:
                for tc in message.tool_calls:
                    chunks.append(_Chunk(
                        tool_calls=[_ToolCallDelta(
                            name=tc.function.name,
                            arguments=tc.function.arguments,
                            call_id=tc.id,
                            index=0,
                        )],
                    ))
            else:
                chunks.append(_Chunk(content=message.content or ""))
            chunks.append(_Chunk(finish_reason=choice.finish_reason or "stop"))
            return chunks
        if isinstance(result, _Chunk):
            return [result]
        raise TypeError(f"cannot stream faux response of type {type(result).__name__}")

    def client_factory(self) -> Callable[..., "FauxProvider"]:
        """Return a callable usable as a patch target for ``run_agent.OpenAI``.

        ``OpenAI(**client_kwargs)`` is invoked for every client the loop
        builds; the factory ignores the kwargs and returns this provider.
        """
        def _factory(*args: Any, **kwargs: Any) -> FauxProvider:
            return self
        return _factory


class ScriptedSession:
    """Builder for a scripted provider turn sequence.

    Usage::

        session = ScriptedSession()
        session.tool_call("skills_list", {})   # turn 1: tool call
        session.text("all done, boss")          # turn 2: final text
        agent = make_agent(session)
        result = agent.run_conversation("...")
    """

    def __init__(self) -> None:
        self._script: List[Callable[[], Any]] = []
        self.provider: Optional[FauxProvider] = None

    def text(self, content: str, model: str = "faux-model") -> None:
        """Script one assistant text response."""
        self._script.append(
            lambda c=content, m=model: _Completion(content=c, tool_calls=None, model=m)
        )

    def tool_call(self, name: str, arguments: dict, model: str = "faux-model") -> None:
        """Script one assistant tool-call response."""
        self._script.append(
            lambda n=name, a=arguments, m=model: _Completion(
                content="", tool_calls=[_ToolCall(n, a)], model=m
            )
        )

    def stream_text(self, content: str, model: str = "faux-model") -> None:
        """Script a streaming text response (chunked deltas)."""
        def _stream() -> List[_Chunk]:
            chunks = [_Chunk(content=content)]
            chunks.append(_Chunk(finish_reason="stop"))
            return chunks
        self._script.append(_stream)

    def raise_(self, exc: Exception) -> None:
        """Script a provider exception (e.g. a 429) at this position."""
        def _raise() -> Any:
            raise exc
        self._script.append(_raise)

    def client_factory(self) -> Callable[..., FauxProvider]:
        """Build the provider and return its client factory.

        Call AFTER scripting is complete (the provider snapshots the
        script list at construction).
        """
        self.provider = FauxProvider(self._script)
        return self.provider.client_factory()
