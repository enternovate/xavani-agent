---
name: weng-guidelines
description: Lilian Weng's principles for building LLM-powered systems — decomposition-first, tool-augmented reasoning, hallucination-aware, evaluation-obsessed.
domain: ai-engineering
mandatory: true
priority: 90
version: 1.0
sources:
  - "LLM Powered Autonomous Agents (lilianweng.github.io, 2023)"
  - "Extrinsic Hallucinations in LLMs (2024)"
  - "Prompt Engineering Guide (lilianweng.github.io)"
  - "GANs and Diffusion Models (lilianweng.github.io)"
---

# Lilian Weng — Operating Guidelines

> "The best way to reduce hallucination is to give the model fewer opportunities to hallucinate — constrain the task, provide retrieval, verify the output."

## Core Principles (always-on)

1. **Decompose before you solve.** Complex tasks fail as single prompts. Break them into planning, retrieval, execution, and verification stages. Each stage should have a measurable output.

2. **Tool use beats prompt engineering.** If a model needs to do math, call a calculator. If it needs current data, call a search engine. Do not ask a language model to pretend it has capabilities it does not have.

3. **Hallucination is a feature of the architecture, not a bug to be ignored.** LLMs generate plausible text, not verified facts. Every factual claim needs a retrieval source or a verification step. Design the pipeline so hallucinations are caught, not hoped away.

4. **Retrieval-augmented generation is the default.** Whenever the task involves knowledge beyond the model's training cutoff, use retrieval. Do not trust the model's parametric memory for facts.

5. **Evaluate with real queries, not synthetic ones.** The test set should reflect what users actually ask. If your eval set is 100 carefully crafted examples and production is 10,000 messy ones, you are evaluating the wrong thing.

6. **Observability is not optional.** In an agentic system, you must see the chain of thought, the tool calls, the intermediate results. If you cannot trace a bad answer back to its source, you cannot fix the system.

## Heuristics for the agent

- Before deploying an LLM pipeline, **run 50+ real user queries** through it and categorise failure modes.
- If a chain-of-thought prompt exceeds 3 tool calls, **add a verification step** at the end.
- When a model confidently states something, **check whether the retrieval context actually supports it**.
- If an agent loop exceeds 5 iterations without converging, **stop and decompose the task further**.
- When building RAG, **test with adversarial queries** — ones designed to trick the retriever.

## Anti-patterns to reject

- "The prompt handles it" — if the prompt is 200 lines of edge-case handling, the architecture is wrong.
- "The model knows this" — parametric memory is unreliable; verify with retrieval.
- "We'll add guardrails later" — guardrails are not an afterthought; they are a core component.
- "It works on my test set" — your test set is not production traffic; diversify.

## When to invoke

- Designing an LLM pipeline, agent, or RAG system.
- Evaluating model outputs for factual accuracy.
- When you notice an agent stuck in a loop or producing repetitive outputs.
