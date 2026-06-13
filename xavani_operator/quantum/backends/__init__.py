# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Quantum backends — classical default + optional real QPUs (v1.0.0 ①).

A *backend* solves a :class:`~xavani_operator.quantum.qubo.QUBO`. The always-on
``inspired`` backend (classical, pure Python) is the default. Real quantum
backends (Qiskit Aer simulator, IBM Quantum, AWS Braket, D-Wave) are **optional**:
each lives in its own lazily-imported module and is only selected when both its
SDK *and* its credentials are present — exactly the same auto-detect pattern the
agent already uses for model-provider API keys. If nothing real is available, the
classical backend is returned. No heavy dependency is ever forced (R10-friendly).

``select_backend()`` is deterministic given the environment.
"""

from __future__ import annotations

import os

from xavani_operator.quantum.backends.inspired import InspiredBackend

# provider name -> the env var whose presence signals "credentials available".
_QUANTUM_CREDS: dict[str, str] = {
    "ibm": "IBM_QUANTUM_TOKEN",
    "dwave": "DWAVE_API_TOKEN",
    "braket": "AMAZON_BRAKET_ENABLED",  # plus the usual AWS_* credentials
}

# provider name -> the backend module to import lazily if creds are present.
_PROVIDER_MODULE: dict[str, str] = {
    "ibm": "ibm_quantum",
    "dwave": "dwave",
    "braket": "braket",
    "aer": "qiskit_aer",
}


def available_quantum_providers(env: dict | None = None) -> list[str]:
    """Providers whose credentials are present in ``env`` (defaults to os.environ)."""
    e = env if env is not None else os.environ
    return [name for name, var in _QUANTUM_CREDS.items() if e.get(var)]


def _try_load(provider: str):
    """Import a real backend module if it exists and is importable, else None."""
    mod_name = _PROVIDER_MODULE.get(provider)
    if not mod_name:
        return None
    try:
        import importlib

        mod = importlib.import_module(f"xavani_operator.quantum.backends.{mod_name}")
    except Exception:  # pragma: no cover - SDK/module absent → classical fallback
        return None
    factory = getattr(mod, "backend", None)
    return factory() if callable(factory) else None


def select_backend(env: dict | None = None):
    """Return the best AVAILABLE backend; the classical ``inspired`` one otherwise.

    Deterministic given ``env``. Mirrors the model-provider key auto-detect: a real
    QPU is used only when its credentials *and* its (optional) SDK module are both
    present; otherwise we fall back to the always-on classical solver.
    """
    for provider in available_quantum_providers(env):
        backend = _try_load(provider)
        if backend is not None:
            return backend
    return InspiredBackend()
