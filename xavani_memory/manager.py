# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Memory Manager — Phase 4 of Xavani Agent.

Orchestrates episodic and procedural memory into a unified system that:

- Remembers everything: user input → thought → action → result → outcome
- Provides recall context to the agent prompt automatically
- Auto-archives old episodes to compressed storage
- Cross-session persistence: everything survives restarts
- Deduplicates overlapping memories

The MemoryManager is the main entry point for all memory operations.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .episodic import EpisodicMemory
from .procedural import ProceduralMemory

logger = logging.getLogger(__name__)
try:
    from xavani_cli.safe_logging import SafeLogFilter
    SafeLogFilter.install()
except Exception:
    pass

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

XAVANI_HOME = Path(os.environ.get("XAVANI_HOME", "~/.xavani")).expanduser()
MEMORY_DIR = XAVANI_HOME / "data" / "memory"

# Auto-archive threshold (days)
DEFAULT_ARCHIVE_DAYS = 90

# Max context episodes to include in agent prompt
MAX_CONTEXT_EPISODES = 10

# Max procedural hints to include in agent prompt
MAX_PROCEDURAL_HINTS = 5

# Automatic recall trigger: include context when this many new episodes
# have been added since last recall
RECALL_TRIGGER_INTERVAL = 5

# Background maintenance interval (seconds)
MAINTENANCE_INTERVAL = 3600  # 1 hour

# Episode columns included in full-text / substring search.
SEARCH_FIELDS = (
    "user_input",
    "agent_response",
    "agent_thought",
    "agent_action",
    "outcome",
    "tags",
)


def _fts5_supported() -> bool:
    """True when the bundled sqlite3 was compiled with FTS5 support.

    Module-level so tests can monkeypatch it to exercise the substring
    fallback on FTS5-less builds.
    """
    try:
        conn = sqlite3.connect(":memory:")
        try:
            options = {row[0] for row in conn.execute("PRAGMA compile_options")}
            return "ENABLE_FTS5" in options
        finally:
            conn.close()
    except sqlite3.Error:
        return False


def _fts_escape(query: str) -> str:
    """Render a plain-text query as a literal FTS5 MATCH expression.

    Each whitespace-separated token is double-quoted (embedded quotes
    doubled) so user input is matched literally; tokens OR together and
    bm25 ranks docs matching more terms above partial matches.
    """
    return " OR ".join('"' + token.replace('"', '""') + '"' for token in query.split())


# ---------------------------------------------------------------------------
# MemoryManager
# ---------------------------------------------------------------------------


class MemoryManager:
    """Orchestrates episodic and procedural memory into a unified system.

    Features:
    - Unified ``remember()`` call that stores the full interaction cycle
    - Automatic recall context generation for agent prompts
    - Background auto-archival of old episodes
    - Cross-session persistence (SQLite-backed)
    - Deduplication of similar recent memories
    - Thread-safe operation

    Usage:
        mm = MemoryManager()
        mm.remember(user_input="Hello", agent_response="Hi there!",
                    agent_thought="Greeting the user", outcome="success")

        # Get context for agent prompt
        context = mm.get_recall_context()
    """

    def __init__(
        self,
        memory_dir: Path = MEMORY_DIR,
        archive_days: int = DEFAULT_ARCHIVE_DAYS,
        auto_maintenance: bool = True,
    ):
        self._memory_dir = memory_dir
        self._memory_dir.mkdir(parents=True, exist_ok=True)

        # Initialize sub-memories
        self.episodic = EpisodicMemory(memory_dir / "episodic.db")
        self.procedural = ProceduralMemory(memory_dir / "procedural.db")

        self._archive_days = archive_days
        self._episode_count_since_recall = 0
        self._last_recall_context: Optional[Dict[str, Any]] = None
        self._lock = threading.Lock()

        # Session tracking
        self._current_session_id: Optional[str] = None
        self._current_agent_id: str = "default"
        self._started_at: str = datetime.now(timezone.utc).isoformat()

        # Search backend, resolved lazily on first search() call
        self._search_backend: Optional[str] = None

        # Background maintenance
        self._auto_maintenance = auto_maintenance
        self._maintenance_thread: Optional[threading.Thread] = None
        self._stop_maintenance = threading.Event()
        if auto_maintenance:
            self._start_maintenance()

    # ── Session Management ───────────────────────────────────────────

    @property
    def current_session_id(self) -> str:
        """Get or create the current session ID."""
        if self._current_session_id is None:
            import uuid
            self._current_session_id = f"session_{uuid.uuid4().hex[:12]}"
        return self._current_session_id

    def set_session(self, session_id: str) -> None:
        """Set the current session ID for grouping episodes."""
        self._current_session_id = session_id

    def set_agent(self, agent_id: str) -> None:
        """Set the current agent ID."""
        self._current_agent_id = agent_id

    def new_session(self) -> str:
        """Start a new session, returning the new session ID."""
        import uuid
        self._current_session_id = f"session_{uuid.uuid4().hex[:12]}"
        return self._current_session_id

    # ── Core Memory Operations ───────────────────────────────────────

    def remember(
        self,
        user_input: str,
        agent_response: Optional[str] = None,
        *,
        agent_thought: Optional[str] = None,
        agent_action: Optional[str] = None,
        context_snapshot: Optional[Dict[str, Any]] = None,
        outcome: Optional[str] = None,
        task_type: Optional[str] = None,
        task_parameters: Optional[Dict[str, Any]] = None,
        task_result: Any = None,
        task_success: Optional[bool] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Store a complete interaction cycle in memory.

        This is the single entry point for recording everything the agent
        does. It stores both episodic and procedural memories atomically.

        Args:
            user_input: The user's message or query.
            agent_response: The agent's response text.
            agent_thought: The agent's internal reasoning/thought process.
            agent_action: The action taken (tool call info, etc.).
            context_snapshot: Dict of contextual information.
            outcome: Description of the outcome.
            task_type: If this was a task execution, the task type for
                procedural memory.
            task_parameters: Parameters used for the task.
            task_result: Result of the task execution.
            task_success: Whether the task succeeded.
            tags: Optional list of tags for categorization.
            metadata: Optional metadata dict.

        Returns:
            The episode ID.
        """
        with self._lock:
            # 1. Store episodic memory
            episode_id = self.episodic.store_episode(
                user_input=user_input,
                agent_response=agent_response,
                context_snapshot=context_snapshot,
                outcome=outcome,
                agent_thought=agent_thought,
                agent_action=agent_action,
                session_id=self._current_session_id,
                agent_id=self._current_agent_id,
                tags=tags,
                metadata=metadata,
            )

            # 2. Store procedural memory (if task-related)
            if task_type is not None:
                self.procedural.record_outcome(
                    task_type=task_type,
                    parameters=task_parameters or {},
                    result=task_result or agent_response or "",
                    success=task_success if task_success is not None else True,
                    approach=agent_action,
                    agent_id=self._current_agent_id,
                )

            # 3. Track recall trigger
            self._episode_count_since_recall += 1

            logger.debug(
                "Remembered episode %s (session=%s, agent=%s)",
                episode_id, self._current_session_id, self._current_agent_id,
            )

            # 4. B02: extract durable facts from the user input and
            # persist them (confidence-scored) for future sessions.
            try:
                from xavani_memory.summarizer import extract_facts, store_facts

                facts = extract_facts([{
                    "user_input": user_input or "",
                    "session_id": self._current_session_id,
                }])
                if facts:
                    store_facts(facts)
            except Exception:
                pass

            return episode_id

    def get_episode(self, episode_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a single episode by ID."""
        return self.episodic.get_episode(episode_id)

    # ── Search (S3-5 / E101) ─────────────────────────────────────────

    def search(self, query: str, limit: int = 10) -> List[Tuple[Dict[str, Any], float]]:
        """Search stored memory entries, most relevant first.

        Backend selection: FTS5 full-text MATCH when enabled via
        ``memory.backend: fts5`` in ``~/.xavani/config.yaml`` or the
        ``XAVANI_MEMORY_FTS5=1`` env var AND the bundled sqlite3 supports
        FTS5; otherwise a substring scan. Scores are higher = more
        relevant in both backends. Deterministic tie-break: recency.

        Returns a list of ``(entry_dict, score)`` tuples.
        """
        query = (query or "").strip()
        if not query:
            return []
        if self._resolve_search_backend() == "fts5" and _fts5_supported():
            try:
                return self._search_fts5(query, limit)
            except sqlite3.Error as exc:
                logger.warning(
                    "FTS5 search failed (%s); falling back to substring scan", exc
                )
        return self._search_substring(query, limit)

    def _resolve_search_backend(self) -> str:
        """Pick the search backend: ``fts5`` or ``substring`` (cached)."""
        if self._search_backend is None:
            backend = "fts5" if os.environ.get("XAVANI_MEMORY_FTS5") == "1" else "substring"
            if backend == "substring":
                try:
                    from xavani_cli.config import load_config

                    mem_cfg = (load_config() or {}).get("memory", {}) or {}
                    if mem_cfg.get("backend") == "fts5":
                        backend = "fts5"
                except Exception:
                    pass  # config optional — keep the substring default
            self._search_backend = backend
        return self._search_backend

    def _search_fts5(self, query: str, limit: int) -> List[Tuple[Dict[str, Any], float]]:
        """FTS5 MATCH against the ``episodes_fts`` virtual table.

        bm25 rank is negated so the score is higher = more relevant;
        ties break on recency (timestamp DESC).
        """
        conn = self.episodic._get_conn()
        rows = conn.execute(
            f"""
            SELECT e.*, -bm25(episodes_fts) AS score
            FROM episodes_fts
            JOIN episodes e ON e.id = episodes_fts.rowid
            WHERE episodes_fts MATCH ?
              AND e.archived = 0
            ORDER BY score DESC, e.timestamp DESC
            LIMIT ?
            """,
            (_fts_escape(query), limit),
        ).fetchall()
        return [(self.episodic._row_to_dict(r), float(r["score"])) for r in rows]

    def _search_substring(self, query: str, limit: int) -> List[Tuple[Dict[str, Any], float]]:
        """Substring scan fallback for sqlite builds without FTS5.

        Score = number of searched fields containing the query (higher =
        more relevant); ties break on recency. ``%``/``_`` in the query
        are escaped so they match literally.
        """
        conn = self.episodic._get_conn()
        escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        like = f"%{escaped}%"
        per_field = [
            f"(COALESCE(e.{col}, '') LIKE ? ESCAPE '\\')" for col in SEARCH_FIELDS
        ]
        rows = conn.execute(
            f"""
            SELECT e.*, ({' + '.join(per_field)}) AS score
            FROM episodes e
            WHERE ({' OR '.join(per_field)}) AND e.archived = 0
            ORDER BY score DESC, e.timestamp DESC
            LIMIT ?
            """,
            [like] * len(SEARCH_FIELDS) * 2 + [limit],
        ).fetchall()
        return [(self.episodic._row_to_dict(r), float(r["score"])) for r in rows]

    # ── Recall Context Generation ────────────────────────────────────

    def get_recall_context(
        self,
        *,
        query: Optional[str] = None,
        max_episodes: int = MAX_CONTEXT_EPISODES,
        include_procedural: bool = True,
        include_session_summary: bool = True,
        force: bool = False,
    ) -> Dict[str, Any]:
        """Generate recall context for injection into the agent prompt.

        Automatically gathers:
        - Recent episodes from the current session
        - Similar past episodes (if a query is provided)
        - Best-known approaches for recent task types
        - Optimization hints from procedural memory
        - Session summary statistics

        Args:
            query: Optional search query for similar past episodes.
            max_episodes: Maximum number of recent episodes to include.
            include_procedural: Whether to include procedural memory hints.
            include_session_summary: Whether to include session summary.
            force: Force regeneration even if cache is valid.

        Returns:
            Context dict with sections for prompt injection.
        """
        # Use cache if not forced and not enough new episodes
        if (
            not force
            and self._last_recall_context is not None
            and self._episode_count_since_recall < RECALL_TRIGGER_INTERVAL
        ):
            return self._last_recall_context

        with self._lock:
            context: Dict[str, Any] = {
                "session_id": self._current_session_id,
                "agent_id": self._current_agent_id,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }

            # 1. Recent episodes from current session
            recent = self.episodic.get_recent(
                limit=max_episodes,
                agent_id=self._current_agent_id,
                session_id=self._current_session_id,
            )
            context["recent_episodes"] = recent

            # 2. Similar past episodes (if query provided)
            if query:
                similar = self.episodic.recall_similar(
                    query=query,
                    limit=min(max_episodes, 5),
                    agent_id=self._current_agent_id,
                )
                context["similar_episodes"] = similar
            else:
                context["similar_episodes"] = []

            # 3. Session summary
            if include_session_summary:
                context["session_summary"] = self.episodic.summarize_session(
                    session_id=self._current_session_id,
                    agent_id=self._current_agent_id,
                )

            # 3.5 Durable facts from past sessions (B02) — confidence-
            # filtered so only well-supported facts enter the prompt.
            try:
                from xavani_memory.summarizer import recall_facts

                context["durable_facts"] = recall_facts(
                    session_id=self._current_session_id,
                )
            except Exception:
                context["durable_facts"] = []

            # 4. Procedural memory insights
            if include_procedural:
                context["procedural_hints"] = self._get_procedural_hints()
            else:
                context["procedural_hints"] = []

            # 5. Cross-agent shared context
            shared = self.episodic.get_shared_context(
                agent_id=self._current_agent_id,
                limit=5,
            )
            context["shared_context"] = shared

            # Reset trigger counter and cache
            self._episode_count_since_recall = 0
            self._last_recall_context = context

            return context

    def _get_procedural_hints(self) -> List[Dict[str, Any]]:
        """Get procedural memory hints for the current context.

        Gathers optimization hints and high-confidence approaches.
        """
        hints: List[Dict[str, Any]] = []

        try:
            # Get optimization hints
            opt_hints = self.procedural.get_optimization_hints(
                min_attempts=2,
            )
            hints.extend(opt_hints[:MAX_PROCEDURAL_HINTS])

            # Get recent task types with high confidence
            recent_outcomes = self.episodic.get_recent(
                limit=20, agent_id=self._current_agent_id
            )
            task_types_seen: set = set()

            for ep in recent_outcomes:
                # Check if this episode had a task_type via metadata
                meta = ep.get("metadata")
                if isinstance(meta, dict) and "task_type" in meta:
                    tt = meta["task_type"]
                    if tt not in task_types_seen:
                        task_types_seen.add(tt)
                        confidence = self.procedural.confidence_score(tt)
                        if confidence["level"] in ("high", "medium"):
                            best = self.procedural.get_best_approach(tt)
                            if best.get("found"):
                                hints.append({
                                    "type": "known_approach",
                                    "task_type": tt,
                                    "approach": best["approach"],
                                    "confidence": confidence["level"],
                                    "success_rate": best["success_rate"],
                                })

        except Exception as exc:
            logger.warning("Failed to get procedural hints: %s", exc)

        return hints

    # ── Formatted Context for Agent Prompt ───────────────────────────

    def format_recall_prompt(
        self,
        *,
        query: Optional[str] = None,
        max_episodes: int = MAX_CONTEXT_EPISODES,
    ) -> str:
        """Generate a formatted string for injection into the agent prompt.

        This is the primary method used by the agent loop to inject
        memory context into the system prompt.

        Args:
            query: Optional search query for similar episodes.
            max_episodes: Max recent episodes to include.

        Returns:
            Formatted context string ready for prompt injection.
        """
        context = self.get_recall_context(
            query=query,
            max_episodes=max_episodes,
        )

        parts: List[str] = [
            "=== MEMORY CONTEXT ===",
        ]

        # Session info
        parts.append(f"Session: {context.get('session_id', 'unknown')}")
        parts.append(f"Agent: {context.get('agent_id', 'default')}")

        # Session summary
        summary = context.get("session_summary", {})
        if summary and summary.get("total_episodes", 0) > 0:
            parts.append(
                f"Session: {summary['total_episodes']} episodes, "
                f"{summary['duration_minutes']:.1f} minutes, "
                f"{summary['error_count']} errors"
            )
            if summary.get("key_topics"):
                parts.append(
                    f"Topics: {', '.join(summary['key_topics'][:5])}"
                )

        # Recent episodes
        recent = context.get("recent_episodes", [])
        if recent:
            parts.append(f"\n--- Recent Episodes ({len(recent)}) ---")
            for i, ep in enumerate(recent, 1):
                user_in = ep.get("user_input", "")[:80]
                resp = ep.get("agent_response", "")[:80]
                outcome = ep.get("outcome", "")
                parts.append(
                    f"  [{i}] User: {user_in}"
                )
                if resp:
                    parts.append(f"      Response: {resp}")
                if outcome:
                    parts.append(f"      Outcome: {outcome}")

        # Similar past episodes
        similar = context.get("similar_episodes", [])
        if similar:
            parts.append(f"\n--- Similar Past Episodes ({len(similar)}) ---")
            for i, ep in enumerate(similar, 1):
                score = ep.get("_relevance_score", 0)
                user_in = ep.get("user_input", "")[:80]
                outcome = ep.get("outcome", "")
                parts.append(
                    f"  [{i}] (relevance: {score:.2f}) {user_in}"
                )
                if outcome:
                    parts.append(f"      Outcome: {outcome}")

        # Procedural hints
        hints = context.get("procedural_hints", [])
        if hints:
            parts.append(f"\n--- Procedural Insights ({len(hints)}) ---")
            for hint in hints:
                hint_type = hint.get("type", "info")
                if hint_type == "low_success_rate":
                    parts.append(
                        f"  ⚠ Task '{hint['task_type']}' has low success rate "
                        f"({hint['current_success_rate']:.0%})"
                    )
                elif hint_type == "known_approach":
                    parts.append(
                        f"  ✓ Task '{hint['task_type']}' best approach: "
                        f"{hint['approach'][:60]}"
                    )
                elif hint_type == "low_confidence":
                    parts.append(
                        f"  ? Task '{hint['task_type']}' needs more examples "
                        f"(only {hint['total_attempts']})"
                    )

        # Shared context
        shared = context.get("shared_context", [])
        if shared:
            parts.append(f"\n--- Shared Context ({len(shared)} episodes) ---")
            for ep in shared:
                source = ep.get("_shared_from", "unknown")
                user_in = ep.get("user_input", "")[:60]
                parts.append(f"  [from {source}] {user_in}")

        parts.append("\n=== END MEMORY CONTEXT ===")

        return "\n".join(parts)

    # ── Cross-Agent Sharing ──────────────────────────────────────────

    def share_with(
        self,
        target_agent_id: str,
        episode_ids: Optional[List[str]] = None,
        *,
        recent_count: int = 5,
    ) -> int:
        """Share recent or specified episodes with another agent.

        Args:
            target_agent_id: The agent to share memory with.
            episode_ids: Specific episode IDs to share. If None, shares
                the most recent episodes.
            recent_count: Number of recent episodes to share if
                ``episode_ids`` is not specified.

        Returns:
            Number of episodes shared.
        """
        if episode_ids is None:
            # Share recent episodes
            recent = self.episodic.get_recent(
                limit=recent_count,
                agent_id=self._current_agent_id,
            )
            episode_ids = [ep["episode_id"] for ep in recent]

        return self.episodic.share_context(
            agent_id=self._current_agent_id,
            episode_ids=episode_ids,
            target_agent_id=target_agent_id,
        )

    def get_shared_with_me(self) -> List[Dict[str, Any]]:
        """Get context shared to the current agent."""
        return self.episodic.get_shared_context(
            agent_id=self._current_agent_id,
        )

    # ── Task-specific Memory (Procedural) ────────────────────────────

    def learn_from_task(
        self,
        task_type: str,
        parameters: Dict[str, Any],
        result: Any,
        success: bool,
        *,
        approach: Optional[str] = None,
        duration_ms: Optional[float] = None,
    ) -> str:
        """Record a task outcome and learn from it.

        This is a convenience method that both records the outcome and
        calls learn_from_success/learn_from_failure.

        Args:
            task_type: The type of task executed.
            parameters: The parameters used.
            result: The result of the task.
            success: Whether it succeeded.
            approach: The approach taken (auto-generated if not provided).
            duration_ms: How long it took in milliseconds.

        Returns:
            The outcome ID.
        """
        outcome_id = self.procedural.record_outcome(
            task_type=task_type,
            parameters=parameters,
            result=result,
            success=success,
            approach=approach,
            duration_ms=duration_ms,
            agent_id=self._current_agent_id,
        )

        # Also store in episodic memory
        self.episodic.store_episode(
            user_input=f"[task] {task_type}",
            agent_response=str(result)[:1000] if result else "",
            context_snapshot={"task_type": task_type, "parameters": parameters},
            outcome="success" if success else "failure",
            agent_action=approach,
            session_id=self._current_session_id,
            agent_id=self._current_agent_id,
            tags=["task", task_type],
        )

        # Learn from the outcome
        if success:
            self.procedural.learn_from_success(task_type, approach or task_type)
        else:
            self.procedural.learn_from_failure(task_type, approach or task_type)

        return outcome_id

    def get_best_approach(
        self,
        task_type: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Get the best-known approach for a task type."""
        return self.procedural.get_best_approach(task_type, parameters)

    def get_confidence(self, task_type: str) -> Dict[str, Any]:
        """Get confidence score for a task type."""
        return self.procedural.confidence_score(task_type)

    def identify_patterns(self) -> List[Dict[str, Any]]:
        """Identify reusable patterns from procedural memory."""
        return self.procedural.identify_patterns()

    # ── Maintenance ──────────────────────────────────────────────────

    def archive_old_episodes(self, days: Optional[int] = None) -> int:
        """Archive episodes older than the specified days.

        Args:
            days: Age threshold (defaults to constructor's archive_days).

        Returns:
            Number of episodes archived.
        """
        return self.episodic.forget_older_than(days or self._archive_days)

    def run_maintenance(self) -> Dict[str, Any]:
        """Run all maintenance tasks.

        Performs:
        1. Archive old episodes
        2. Identify new patterns from procedural memory
        3. Clean up resolved shared context
        4. Log memory statistics

        Returns:
            Summary of maintenance actions taken.
        """
        results: Dict[str, Any] = {}

        # 1. Archive old episodes
        archived = self.archive_old_episodes()
        results["episodes_archived"] = archived

        # 2. Identify patterns (if enough data)
        try:
            patterns = self.procedural.identify_patterns(min_examples=3)
            results["patterns_identified"] = len(patterns)
        except Exception as exc:
            logger.warning("Pattern identification failed: %s", exc)
            results["patterns_identified"] = 0

        # 3. Archive stats
        results["archive_stats"] = self.episodic.archive_stats()

        # 4. Procedural stats
        results["procedural_stats"] = self.procedural.stats()

        logger.debug(
            "Maintenance complete: archived %d episodes, identified %d patterns",
            archived, results.get("patterns_identified", 0),
        )

        return results

    def _start_maintenance(self) -> None:
        """Start the background maintenance thread."""
        if self._maintenance_thread is not None:
            return

        def _maintenance_loop():
            logger.debug("Background memory maintenance started")
            while not self._stop_maintenance.is_set():
                try:
                    self.run_maintenance()
                except Exception as exc:
                    logger.error("Background maintenance error: %s", exc)
                self._stop_maintenance.wait(MAINTENANCE_INTERVAL)

        self._maintenance_thread = threading.Thread(
            target=_maintenance_loop,
            name="xavani-memory-maintenance",
            daemon=True,
        )
        self._maintenance_thread.start()

    def stop_maintenance(self) -> None:
        """Stop the background maintenance thread."""
        self._stop_maintenance.set()
        if self._maintenance_thread:
            self._maintenance_thread.join(timeout=5)
            self._maintenance_thread = None

    # ── Conflict Resolution ──────────────────────────────────────────

    def resolve_memory_conflicts(
        self,
        agent_id: Optional[str] = None,
        strategy: str = "newest_wins",
    ) -> Dict[str, Any]:
        """Resolve contradictory memories for an agent.

        Args:
            agent_id: The agent to resolve conflicts for (defaults to
                current agent).
            strategy: Resolution strategy (``newest_wins``,
                ``source_priority``, ``merge``).

        Returns:
            Conflict resolution summary.
        """
        return self.episodic.resolve_conflicts(
            agent_id=agent_id or self._current_agent_id,
            strategy=strategy,
        )

    # ── Episodic Summarization (B05) ─────────────────────────────────

    def summarize_recent_episodes(
        self, days: int = 7, limit: int = 500
    ) -> List[Dict[str, Any]]:
        """Aggregate episodes from the last ``days`` (B05).

        Returns one row per topic (task_type from metadata, else first
        tag, else ``general``): episode count, completion count, and the
        top tags.  Deterministic and offline — no LLM involved.
        """
        from collections import Counter

        from datetime import datetime, timedelta, timezone

        episodes = self.episodic.get_recent(limit=limit, agent_id=self._current_agent_id)
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        per_topic: Dict[str, Dict[str, Any]] = {}
        tag_counter: Counter = Counter()
        for ep in episodes:
            ts = ep.get("timestamp") or ""
            try:
                parsed = datetime.fromisoformat(ts)
            except ValueError:
                continue
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            if parsed < cutoff:
                continue
            metadata = ep.get("metadata") or {}
            if isinstance(metadata, str):
                metadata = {}
            tags = ep.get("tags") or []
            if isinstance(tags, str):
                tags = []
            topic = (
                str(metadata.get("task_type") or "")
                or (str(tags[0]) if tags else "")
                or "general"
            )
            row = per_topic.setdefault(
                topic, {"topic": topic, "count": 0, "completed": 0, "top_tags": []}
            )
            row["count"] += 1
            if ep.get("outcome"):
                row["completed"] += 1
            for tag in tags:
                tag_counter[str(tag)] += 1

        for row in per_topic.values():
            row["top_tags"] = [t for t, _ in tag_counter.most_common(3)]
        return sorted(per_topic.values(), key=lambda r: -r["count"])

    def propose_memory_entries(
        self, summary: List[Dict[str, Any]], max_entries: int = 5
    ) -> List[str]:
        """Render MEMORY.md-style promotion bullets from a summary (B05)."""
        entries: List[str] = []
        for row in summary[:max_entries]:
            line = f"- **{row['topic']}**: {row['count']} recent episode(s)"
            if row["completed"]:
                line += f" ({row['completed']} completed)"
            if row["top_tags"]:
                line += f" — tags: {', '.join(row['top_tags'])}"
            entries.append(line + " — candidate for MEMORY.md")
        return entries

    # ── Daily Learning Digest (G02) ────────────────────────────────

    def build_daily_digest(self, days: int = 1, limit: int = 500) -> str:
        """Render a markdown digest of the last ``days`` of episodes (G02).

        Offline and deterministic — no LLM involved.  Aggregates the
        episode summary and renders MEMORY.md promotion bullets so a
        cron job can turn the episodic store into daily growth.
        Returns an empty string when no episodes fall in the window.
        """
        summary = self.summarize_recent_episodes(days=days, limit=limit)
        if not summary:
            return ""
        total = sum(row["count"] for row in summary)
        completed = sum(row["completed"] for row in summary)
        lines = [
            "# Daily Learning Digest",
            "",
            f"Episodes in the last {days} day(s): **{total}** "
            f"({completed} completed).",
            "",
            "## Topics",
            "",
        ]
        for row in summary:
            tags = f" — tags: {', '.join(row['top_tags'])}" if row["top_tags"] else ""
            lines.append(
                f"- **{row['topic']}**: {row['count']} episode(s)"
                f" ({row['completed']} completed){tags}"
            )
        lines.append("")
        lines.append("## Proposed skill updates")
        lines.append("")
        entries = self.propose_memory_entries(summary)
        lines.extend(entries if entries else ["- (none — no clear promotion candidate)"])
        return "\n".join(lines) + "\n"

    # ── Statistics ───────────────────────────────────────────────────

    def stats(self) -> Dict[str, Any]:
        """Get comprehensive memory statistics.

        Returns:
            Dict with episodic and procedural memory stats.
        """
        return {
            "session": {
                "current_session_id": self._current_session_id,
                "agent_id": self._current_agent_id,
                "started_at": self._started_at,
                "episodes_since_recall": self._episode_count_since_recall,
            },
            "episodic": self.episodic.archive_stats(),
            "procedural": self.procedural.stats(),
            "maintenance": {
                "auto_archive_days": self._archive_days,
                "background_maintenance": self._auto_maintenance,
            },
        }

    def clear_all(self) -> Dict[str, int]:
        """Clear all memory (episodic + procedural).

        Returns:
            Dict with counts of cleared items.
        """
        ep_count = self.episodic.clear_all()
        proc_count = self.procedural.clear_all()
        self._episode_count_since_recall = 0
        self._last_recall_context = None
        logger.warning("Cleared all memory: %d episodes, %d procedural records", ep_count, proc_count)
        return {
            "episodes_cleared": ep_count,
            "procedural_records_cleared": proc_count,
        }

    # ── Context Manager Support ──────────────────────────────────────

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop_maintenance()
