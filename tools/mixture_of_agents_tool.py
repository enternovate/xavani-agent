# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Mixture-of-Agents Tool — Route problems through multiple models collaboratively.

Makes N parallel model calls (reference models) then passes all responses
to an aggregator model that synthesizes the best answer. Useful for complex
reasoning, math, and multi-perspective analysis.

Configurable: models list, number of rounds, aggregator model.
"""

from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    from xavani_cli.safe_logging import SafeLogFilter
    SafeLogFilter.install()
except Exception:
    pass


# ---------------------------------------------------------------------------
# Reference models — defaults that work across providers
# ---------------------------------------------------------------------------

DEFAULT_REFERENCE_MODELS = [
    "gpt-4o-mini",
    "claude-3-5-haiku-20241022",
    "gemini-2.5-flash",
]

DEFAULT_AGGREGATOR_MODEL = "gpt-4o"


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------


def _call_model(
    model: str,
    prompt: str,
    system: str = "",
    provider: Optional[str] = None,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    timeout: int = 60,
) -> Dict[str, Any]:
    """Call a single model and return its response."""
    try:
        # Use the existing agent infrastructure for API calls
        from agent.model_client import create_client

        client = create_client(
            model=model,
            provider=provider,
            base_url=base_url,
            api_key=api_key,
        )

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = client.chat(messages=messages, model=model, timeout=timeout)

        return {
            "model": model,
            "response": response.get("content", ""),
            "ok": True,
        }
    except Exception as exc:
        return {
            "model": model,
            "response": "",
            "ok": False,
            "error": str(exc),
        }


def mixture_of_agents(
    prompt: str,
    system: str = "",
    reference_models: Optional[List[str]] = None,
    aggregator_model: str = DEFAULT_AGGREGATOR_MODEL,
    rounds: int = 1,
    provider: Optional[str] = None,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Run the Mixture-of-Agents pipeline.

    1. Send the prompt to N reference models in parallel.
    2. Collect all responses.
    3. Pass all responses to the aggregator model for synthesis.
    4. Return the synthesized answer with metadata.
    """
    if reference_models is None:
        reference_models = DEFAULT_REFERENCE_MODELS

    all_rounds = []

    for round_num in range(rounds):
        # Phase 1: Parallel reference calls
        ref_responses = []
        with ThreadPoolExecutor(max_workers=len(reference_models)) as executor:
            futures = {
                executor.submit(
                    _call_model, model, prompt, system, provider, base_url, api_key
                ): model
                for model in reference_models
            }
            for future in as_completed(futures):
                ref_responses.append(future.result())

        successful = [r for r in ref_responses if r["ok"]]
        failed = [r for r in ref_responses if not r["ok"]]

        if not successful:
            return {
                "ok": False,
                "error": "All reference models failed.",
                "rounds": all_rounds + [{"round": round_num + 1, "ref_responses": ref_responses}],
            }

        # Phase 2: Aggregation
        synthesis_prompt = (
            f"Multiple models were asked the following question:\n\n"
            f"QUESTION: {prompt}\n\n"
            f"Here are their responses:\n\n"
        )
        for i, resp in enumerate(successful, 1):
            synthesis_prompt += f"--- Model {i} ({resp['model']}) ---\n{resp['response']}\n\n"

        synthesis_prompt += (
            "Synthesize the best answer from these responses. "
            "Identify points of agreement and disagreement. "
            "Provide a single, well-reasoned answer that incorporates "
            "the strongest elements from each response."
        )

        aggregator_response = _call_model(
            aggregator_model, synthesis_prompt, system, provider, base_url, api_key
        )

        round_result = {
            "round": round_num + 1,
            "ref_responses": ref_responses,
            "ref_success": len(successful),
            "ref_failed": len(failed),
            "aggregator": aggregator_response,
        }
        all_rounds.append(round_result)

        # For multi-round, use the aggregator's output as the new prompt
        if rounds > 1 and round_num < rounds - 1:
            prompt = aggregator_response.get("response", prompt)

    return {
        "ok": True,
        "answer": all_rounds[-1]["aggregator"].get("response", ""),
        "aggregator_model": aggregator_model,
        "reference_models": reference_models,
        "rounds": all_rounds,
        "total_rounds": rounds,
    }


# ---------------------------------------------------------------------------
# Tool handler
# ---------------------------------------------------------------------------


def _handle_mixture_of_agents(args: Dict[str, Any]) -> str:
    """Tool handler for mixture-of-agents."""
    prompt = args.get("prompt", "")
    if not prompt:
        return json.dumps({"error": "No prompt provided."})

    result = mixture_of_agents(
        prompt=prompt,
        system=args.get("system", ""),
        reference_models=args.get("reference_models"),
        aggregator_model=args.get("aggregator_model", DEFAULT_AGGREGATOR_MODEL),
        rounds=args.get("rounds", 1),
        provider=args.get("provider"),
        base_url=args.get("base_url"),
        api_key=args.get("api_key"),
    )
    return json.dumps(result, indent=2, default=str)


# ---------------------------------------------------------------------------
# Tool schema
# ---------------------------------------------------------------------------

MIXTURE_OF_AGENTS_SCHEMA: Dict[str, Any] = {
    "name": "mixture_of_agents",
    "description": (
        "Route a complex problem through multiple AI models collaboratively. "
        "Sends the prompt to N reference models in parallel, then synthesizes "
        "the best answer via an aggregator model. Best for complex reasoning, "
        "math, multi-perspective analysis, and problems benefiting from diverse viewpoints."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "The complex query or problem to solve.",
            },
            "system": {
                "type": "string",
                "description": "Optional system prompt for all models.",
            },
            "reference_models": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Models to use as reference (default: gpt-4o-mini, claude-3-5-haiku, gemini-2.5-flash).",
            },
            "aggregator_model": {
                "type": "string",
                "description": "Model to synthesize the final answer (default: gpt-4o).",
            },
            "rounds": {
                "type": "integer",
                "description": "Number of MoA rounds (default: 1). Multi-round feeds output back.",
            },
            "provider": {
                "type": "string",
                "description": "Provider override.",
            },
            "base_url": {
                "type": "string",
                "description": "Base URL override.",
            },
            "api_key": {
                "type": "string",
                "description": "API key override.",
            },
        },
        "required": ["prompt"],
    },
}


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

from tools.registry import registry  # noqa: E402

registry.register(
    name="mixture_of_agents",
    toolset="llm",
    schema=MIXTURE_OF_AGENTS_SCHEMA,
    handler=_handle_mixture_of_agents,
    description="Route problems through multiple models collaboratively.",
    emoji="🧠",
)
