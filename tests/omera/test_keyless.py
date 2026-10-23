import httpx
import pytest

from xavani_omera import keyless
from xavani_omera.research import Hit, Page, ResearchResult


@pytest.fixture(autouse=True)
def reset_breaker():
    keyless.clear_keyless_breaker()
    yield
    keyless.clear_keyless_breaker()


def result() -> ResearchResult:
    return ResearchResult(
        status="ok", provider="ddgs", query="cipc annual return", elapsed_ms=10,
        hits=[
            Hit("CIPC annual returns", "https://cipc.example/a", "Annual return."),
            Hit("Deadlines", "https://sars.example/b", "Tax dates."),
        ],
        pages=[
            Page("https://cipc.example/a", "CIPC annual returns",
                 "Every company must file an annual return within 30 days of "
                 "its anniversary date. The fee is R100 for a standard company."),
            Page("https://sars.example/b", "Deadlines", "Tax season runs from July."),
        ],
    )


def test_composes_a_cited_answer():
    text = keyless.compose_research_answer("When is the CIPC annual return due?", result())
    assert "Research mode" in text
    assert "annual return" in text.lower()
    assert "https://cipc.example/a" in text
    assert "[1]" in text


def test_without_sources_it_says_so():
    text = keyless.compose_research_answer("Anything?", None)
    assert "Research mode" in text
    assert "No live sources" in text


def test_a_failed_result_is_treated_as_empty():
    failed = ResearchResult(status="failed", provider="ddgs", query="q")
    text = keyless.compose_research_answer("q", failed)
    assert "No live sources" in text


def test_mode_selection():
    assert keyless.mode_for({}) == "research"
    assert keyless.mode_for({"KEYLESS_MODEL": "on"}) == "keyless"
    assert keyless.mode_for({
        "INFERENCE_API_KEY": "k", "INFERENCE_MODEL": "m",
    }) == "model"


@pytest.mark.asyncio
async def test_model_complete_parses_the_openai_shape(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://text.pollinations.ai/openai"
        return httpx.Response(200, json={
            "choices": [{"message": {"content": "  Answer text.  "}}],
        })

    monkeypatch.setattr(
        keyless, "_client",
        lambda: httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    assert await keyless.model_complete([{"role": "user", "content": "Hi"}]) == \
        "Answer text."


@pytest.mark.asyncio
async def test_answer_falls_back_when_the_model_fails(monkeypatch):
    async def boom(messages, env=None):
        raise RuntimeError("KEYLESS_500")

    monkeypatch.setattr(keyless, "model_complete", boom)
    text = await keyless.answer("When is the CIPC annual return due?", result(),
                                env={"KEYLESS_MODEL": "on"})
    assert "Research mode" in text
    assert "https://cipc.example/a" in text


@pytest.mark.asyncio
async def test_answer_uses_the_model_when_it_works(monkeypatch):
    async def fine(messages, env=None):
        return "Model answer."

    monkeypatch.setattr(keyless, "model_complete", fine)
    assert await keyless.answer("Hi", result(), env={"KEYLESS_MODEL": "on"}) == \
        "Model answer."


def test_a_caller_system_prompt_is_kept():
    messages = keyless.build_messages("Hi", None, "Caller rules.")
    assert "Caller rules." in messages[0]["content"]
    assert messages[1] == {"role": "user", "content": "Hi"}


@pytest.mark.asyncio
async def test_a_failed_model_is_skipped_for_two_minutes(monkeypatch):
    calls = []

    async def boom(messages, env=None):
        calls.append(1)
        raise RuntimeError("KEYLESS_402")

    monkeypatch.setattr(keyless, "model_complete", boom)
    env = {"KEYLESS_MODEL": "on"}
    await keyless.answer("q", None, env=env)
    await keyless.answer("q", None, env=env)
    assert len(calls) == 1
    assert keyless.mode_for(env) == "research"


def test_marketing_snippets_are_skipped():
    result = ResearchResult(
        status="ok", provider="ddgs", query="cipc annual return", elapsed_ms=1,
        hits=[Hit(
            "Company Partners", "https://partners.example/a",
            "We begin with a free consultation, offering tailored support "
            "to align with your business objectives.",
        )],
        pages=[],
    )
    text = keyless.compose_research_answer("CIPC annual return", result)
    assert "free consultation" not in text.lower()
    assert "No live sources" in text


def test_a_factual_sentence_beats_marketing():
    result = ResearchResult(
        status="ok", provider="ddgs", query="cipc annual return", elapsed_ms=1,
        hits=[Hit("CIPC", "https://cipc.example/a", "Annual return.")],
        pages=[Page(
            "https://cipc.example/a", "CIPC",
            "We offer a free consultation for every new client. "
            "A company must file its annual return within 30 days of the "
            "anniversary of its incorporation date.",
        )],
    )
    text = keyless.compose_research_answer("When is the annual return due?", result)
    assert "within 30 days" in text
    assert "free consultation" not in text.lower()
