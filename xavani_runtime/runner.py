# Copyright (c) 2025-2026 Enternovate. All rights reserved.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Agent lifecycle runner — Phase 6.

AgentRunner manages the full lifecycle of portable agents defined by
AgentImages. Supports start, stop, restart, listing, and log retrieval.

Each agent runs in its own isolated context with separate conversation
history and resource limits.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from rich.console import Console
from rich.table import Table
from rich.text import Text

from .image import AgentImage
from .loader import ImageLoader

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

XAVANI_HOME = Path(os.environ.get("XAVANI_HOME", "~/.xavani")).expanduser()
AGENT_RUN_DIR = XAVANI_HOME / "runs"
AGENT_LOG_DIR = XAVANI_HOME / "logs" / "agents"

# Default resource limits
DEFAULT_MAX_TOKENS_PER_SESSION = 128_000
DEFAULT_MAX_TOOL_CALLS = 500
DEFAULT_MAX_DURATION_SECONDS = 3600  # 1 hour


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class AgentState(str, Enum):
    """Enumeration of agent lifecycle states."""

    STARTING = "starting"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"

    def __str__(self) -> str:
        return self.value


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class AgentInstance:
    """A running instance of an agent.

    Tracks the agent's identity, state, resource usage, and metadata
    for the duration of a session.
    """

    agent_id: str
    image: AgentImage
    session_id: str
    state: AgentState = AgentState.STARTING
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    stopped_at: Optional[str] = None
    last_activity: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # Resource tracking
    tokens_used: int = 0
    tool_calls_made: int = 0
    llm_calls_made: int = 0
    errors_encountered: int = 0

    # Resource limits (from policy or defaults)
    max_tokens_per_session: int = DEFAULT_MAX_TOKENS_PER_SESSION
    max_tool_calls: int = DEFAULT_MAX_TOOL_CALLS
    max_duration_seconds: int = DEFAULT_MAX_DURATION_SECONDS

    # Context
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Internal
    _lock: threading.RLock = field(default_factory=threading.RLock)

    @property
    def is_alive(self) -> bool:
        """Check if the agent is in an active state."""
        return self.state in (AgentState.READY, AgentState.RUNNING, AgentState.PAUSED)

    @property
    def uptime_seconds(self) -> float:
        """Return the number of seconds since the agent started."""
        try:
            start = datetime.fromisoformat(self.started_at)
            now = datetime.now(timezone.utc)
            if self.stopped_at:
                end = datetime.fromisoformat(self.stopped_at)
                return (end - start).total_seconds()
            return (now - start).total_seconds()
        except (ValueError, TypeError):
            return 0.0

    @property
    def is_at_limit(self) -> bool:
        """Check if the agent has exceeded any resource limit."""
        limits: List[str] = []
        if self.tokens_used >= self.max_tokens_per_session:
            limits.append(f"token limit ({self.tokens_used}/{self.max_tokens_per_session})")
        if self.tool_calls_made >= self.max_tool_calls:
            limits.append(f"tool call limit ({self.tool_calls_made}/{self.max_tool_calls})")
        if self.uptime_seconds >= self.max_duration_seconds:
            limits.append(f"duration limit ({self.uptime_seconds:.0f}/{self.max_duration_seconds}s)")
        return len(limits) > 0

    @property
    def limit_description(self) -> str:
        """Return a human-readable description of which limits are approached."""
        desc: List[str] = []
        ratio = self.tokens_used / self.max_tokens_per_session
        if ratio > 0.8:
            desc.append(f"tokens: {self.tokens_used}/{self.max_tokens_per_session}")
        ratio = self.tool_calls_made / self.max_tool_calls
        if ratio > 0.8:
            desc.append(f"tool calls: {self.tool_calls_made}/{self.max_tool_calls}")
        ratio = self.uptime_seconds / self.max_duration_seconds
        if ratio > 0.8:
            desc.append(f"duration: {self.uptime_seconds:.0f}/{self.max_duration_seconds}s")
        return "; ".join(desc) if desc else "within limits"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a JSON-compatible dict."""
        return {
            "agent_id": self.agent_id,
            "name": self.image.name,
            "version": self.image.version,
            "session_id": self.session_id,
            "state": self.state.value,
            "started_at": self.started_at,
            "stopped_at": self.stopped_at or "",
            "last_activity": self.last_activity,
            "tokens_used": self.tokens_used,
            "tool_calls_made": self.tool_calls_made,
            "llm_calls_made": self.llm_calls_made,
            "errors_encountered": self.errors_encountered,
            "uptime_seconds": self.uptime_seconds,
            "at_limit": self.is_at_limit,
            "limit_description": self.limit_description,
            "model": f"{self.image.model.provider}/{self.image.model.model}",
            "description": self.image.description,
        }


# ---------------------------------------------------------------------------
# AgentRunner
# ---------------------------------------------------------------------------


def is_process_alive(pid: int) -> bool:
    """Cross-platform process existence check using psutil.

    Args:
        pid: Process ID to check.

    Returns:
        True if the process exists and is running.
    """
    import psutil
    try:
        proc = psutil.Process(pid)
        return proc.is_running()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False


class AgentRunner:
    """Manages the full lifecycle of portable agents.

    Agents are started from AgentImage definitions and run in isolated
    contexts with independent conversation histories and resource limits.

    Lifecycle::
        start → starting → ready → running → paused → stopped
                                         ↓
                                      [reaches limit] → stopped

    Usage::
        runner = AgentRunner()
        instance = runner.start(image, session_id="my-session")
        # ... agent runs ...
        runner.stop(instance.agent_id)
        runner.list()
    """

    def __init__(self, loader: Optional[ImageLoader] = None) -> None:
        self._loader = loader or ImageLoader()
        self._agents: Dict[str, AgentInstance] = {}
        self._agent_logs: Dict[str, List[Dict[str, Any]]] = {}
        self._lock = threading.RLock()
        self._console = Console()

        # Ensure log directory exists
        AGENT_LOG_DIR.mkdir(parents=True, exist_ok=True)

        # Background thread for limit checking
        self._stop_monitor = threading.Event()
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="agent-limit-monitor",
        )
        self._monitor_thread.start()

    # ── Lifecycle: Start ─────────────────────────────────────────────

    def start(
        self,
        image: AgentImage,
        session_id: Optional[str] = None,
        *,
        max_tokens: Optional[int] = None,
        max_tool_calls: Optional[int] = None,
        max_duration: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AgentInstance:
        """Launch a new agent from its image definition.

        Creates an isolated agent instance with its own conversation
        history and resource tracking.

        Args:
            image: The AgentImage defining the agent.
            session_id: Optional session identifier. Auto-generated if omitted.
            max_tokens: Override max tokens per session.
            max_tool_calls: Override max tool calls.
            max_duration: Override max duration in seconds.
            metadata: Optional metadata for the instance.

        Returns:
            The created AgentInstance (in READY state).

        Raises:
            ValueError: If the agent image is invalid.
        """
        # Validate the image
        errors = self._loader.validate(image)
        if errors:
            error_msg = "\n".join(f"  - {e}" for e in errors)
            raise ValueError(f"Cannot start agent with invalid image:\n{error_msg}")

        agent_id = f"agent_{uuid.uuid4().hex[:12]}"
        session = session_id or f"session_{uuid.uuid4().hex[:12]}"

        instance = AgentInstance(
            agent_id=agent_id,
            image=image,
            session_id=session,
            metadata=metadata or {},
        )

        # Apply resource limits (image policy → parameter override → default)
        instance.max_tokens_per_session = (
            max_tokens
            or image.model.parameters.get("max_tokens", DEFAULT_MAX_TOKENS_PER_SESSION)
        )
        instance.max_tool_calls = max_tool_calls or DEFAULT_MAX_TOOL_CALLS
        instance.max_duration_seconds = max_duration or DEFAULT_MAX_DURATION_SECONDS

        with self._lock:
            self._agents[agent_id] = instance
            self._agent_logs[agent_id] = []

        # Transition to READY
        self._transition(instance, AgentState.READY)

        self._log(instance, "info", f"Agent started: {image.full_name}")
        logger.info(
            "Started agent '%s' (id=%s, session=%s)",
            image.name, agent_id, session,
        )

        return instance

    # ── Lifecycle: Stop ──────────────────────────────────────────────

    def stop(self, agent_id: str) -> bool:
        """Gracefully stop a running agent.

        Transitions the agent through STOPPING → STOPPED states.

        Args:
            agent_id: The agent identifier.

        Returns:
            True if successfully stopped, False if not found.
        """
        with self._lock:
            instance = self._agents.get(agent_id)
            if instance is None:
                self._console.print(f"[red]Agent '{agent_id}' not found.[/red]")
                return False

            if instance.state in (AgentState.STOPPED, AgentState.STOPPING):
                self._console.print(
                    f"[yellow]Agent '{instance.image.name}' "
                    f"is already {instance.state.value}.[/yellow]"
                )
                return False

            self._transition(instance, AgentState.STOPPING)
            self._log(instance, "info", "Agent stopping...")

        # Simulate graceful shutdown work
        time.sleep(0.1)

        with self._lock:
            self._transition(instance, AgentState.STOPPED, stopped=True)
            self._log(instance, "info", "Agent stopped")

        logger.info("Stopped agent '%s' (id=%s)", instance.image.name, agent_id)
        return True

    def stop_all(self) -> int:
        """Stop all running agents.

        Returns:
            Number of agents stopped.
        """
        with self._lock:
            agent_ids = list(self._agents.keys())

        count = 0
        for agent_id in agent_ids:
            if self.stop(agent_id):
                count += 1
        return count

    # ── Lifecycle: Restart ───────────────────────────────────────────

    def restart(self, agent_id: str) -> Optional[AgentInstance]:
        """Restart a stopped agent.

        Creates a new instance with the same image but a fresh session.

        Args:
            agent_id: The agent identifier to restart.

        Returns:
            New AgentInstance if restarted, None if not found or still running.
        """
        with self._lock:
            old_instance = self._agents.get(agent_id)
            if old_instance is None:
                self._console.print(f"[red]Agent '{agent_id}' not found.[/red]")
                return None

            if old_instance.is_alive:
                self._console.print(
                    f"[yellow]Agent '{old_instance.image.name}' is still "
                    f"running. Stop it first.[/yellow]"
                )
                return None

            image = old_instance.image
            metadata = old_instance.metadata

            # Remove old instance
            self._agents.pop(agent_id, None)
            self._agent_logs.pop(agent_id, None)

        # Start new instance with same image and metadata
        return self.start(
            image,
            metadata=metadata,
        )

    # ── Lifecycle: Pause / Resume ────────────────────────────────────

    def set_running(self, agent_id: str) -> bool:
        """Transition an agent from READY to RUNNING state.

        Called by the agent execution loop when it begins processing.

        Args:
            agent_id: The agent identifier.

        Returns:
            True if transitioned, False if not found or not in READY state.
        """
        with self._lock:
            instance = self._agents.get(agent_id)
            if instance is None:
                return False

            if instance.state != AgentState.READY:
                self._console.print(
                    f"[yellow]Agent '{instance.image.name}' is "
                    f"{instance.state.value}; can only set running from READY.[/yellow]"
                )
                return False

            self._transition(instance, AgentState.RUNNING)
            self._log(instance, "info", "Agent is now running")
            return True

    def pause(self, agent_id: str) -> bool:
        """Pause a running agent.

        Args:
            agent_id: The agent identifier.

        Returns:
            True if paused, False if not found or not in a pausable state.
        """
        with self._lock:
            instance = self._agents.get(agent_id)
            if instance is None:
                return False

            if instance.state != AgentState.RUNNING:
                self._console.print(
                    f"[yellow]Agent '{instance.image.name}' is "
                    f"{instance.state.value}; can only pause RUNNING agents.[/yellow]"
                )
                return False

            self._transition(instance, AgentState.PAUSED)
            self._log(instance, "info", "Agent paused")
            return True

    def resume(self, agent_id: str) -> bool:
        """Resume a paused agent.

        Args:
            agent_id: The agent identifier.

        Returns:
            True if resumed, False if not found or not paused.
        """
        with self._lock:
            instance = self._agents.get(agent_id)
            if instance is None:
                return False

            if instance.state != AgentState.PAUSED:
                self._console.print(
                    f"[yellow]Agent '{instance.image.name}' is "
                    f"{instance.state.value}; can only resume PAUSED agents.[/yellow]"
                )
                return False

            self._transition(instance, AgentState.RUNNING)
            self._log(instance, "info", "Agent resumed")
            return True

    # ── Resource Tracking ────────────────────────────────────────────

    def record_tool_call(self, agent_id: str) -> bool:
        """Record a tool call for an agent, checking limits.

        Args:
            agent_id: The agent identifier.

        Returns:
            True if within limits, False if limit exceeded.
        """
        with self._lock:
            instance = self._agents.get(agent_id)
            if instance is None:
                return False

            instance.tool_calls_made += 1
            instance.last_activity = datetime.now(timezone.utc).isoformat()

            if instance.tool_calls_made >= instance.max_tool_calls:
                self._log(instance, "warn", f"Tool call limit reached ({instance.tool_calls_made})")
                return False
            return True

    def record_tokens(self, agent_id: str, tokens: int) -> bool:
        """Record token usage for an agent, checking limits.

        Args:
            agent_id: The agent identifier.
            tokens: Number of tokens used.

        Returns:
            True if within limits, False if limit exceeded.
        """
        with self._lock:
            instance = self._agents.get(agent_id)
            if instance is None:
                return False

            instance.tokens_used += tokens
            instance.last_activity = datetime.now(timezone.utc).isoformat()

            if instance.tokens_used >= instance.max_tokens_per_session:
                self._log(instance, "warn", f"Token limit reached ({instance.tokens_used})")
                return False
            return True

    def record_error(self, agent_id: str) -> None:
        """Record an error encountered by an agent."""
        with self._lock:
            instance = self._agents.get(agent_id)
            if instance is None:
                return
            instance.errors_encountered += 1
            instance.last_activity = datetime.now(timezone.utc).isoformat()

    def record_llm_call(self, agent_id: str) -> None:
        """Record an LLM call made by an agent."""
        with self._lock:
            instance = self._agents.get(agent_id)
            if instance is None:
                return
            instance.llm_calls_made += 1
            instance.last_activity = datetime.now(timezone.utc).isoformat()

    # ── Conversation History ─────────────────────────────────────────

    def add_message(
        self,
        agent_id: str,
        role: str,
        content: str,
        *,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Add a message to an agent's conversation history.

        Args:
            agent_id: The agent identifier.
            role: Message role (``user``, ``assistant``, ``system``, ``tool``).
            content: Message content.
            metadata: Optional message metadata.

        Returns:
            True if added, False if agent not found.
        """
        with self._lock:
            instance = self._agents.get(agent_id)
            if instance is None:
                return False

            message = {
                "role": role,
                "content": content,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            if metadata:
                message["metadata"] = metadata

            instance.conversation_history.append(message)
            instance.last_activity = datetime.now(timezone.utc).isoformat()
            return True

    def get_conversation(self, agent_id: str) -> List[Dict[str, Any]]:
        """Get the conversation history for an agent.

        Args:
            agent_id: The agent identifier.

        Returns:
            List of message dicts, or empty list if not found.
        """
        with self._lock:
            instance = self._agents.get(agent_id)
            if instance is None:
                return []
            return list(instance.conversation_history)

    # ── Listing ──────────────────────────────────────────────────────

    def list(self, state: Optional[AgentState] = None) -> List[Dict[str, Any]]:
        """List agents and their status.

        Displays a Rich table with agent ID, name, state, uptime,
        and resource usage.

        Args:
            state: Optional filter by agent state.

        Returns:
            List of agent instance dicts.
        """
        with self._lock:
            instances = list(self._agents.values())

        if state:
            instances = [i for i in instances if i.state == state]

        if not instances:
            self._console.print(
                "[yellow]No agents"
                + (f" in state '{state.value}'" if state else "")
                + ".[/yellow]"
            )
            return []

        table = Table(
            title=f"Agent Runtimes ({len(instances)})",
            title_style="bold",
            header_style="bold cyan",
            border_style="blue",
        )

        table.add_column("ID", width=18, style="dim")
        table.add_column("Name", width=18)
        table.add_column("State", width=10)
        table.add_column("Uptime", justify="right", width=8)
        table.add_column("Tokens", justify="right", width=10)
        table.add_column("Tool Calls", justify="right", width=10)
        table.add_column("Model", width=24)
        table.add_column("Limits", width=20)

        for instance in sorted(instances, key=lambda i: i.started_at, reverse=True):
            state_style = {
                AgentState.RUNNING: "green",
                AgentState.READY: "cyan",
                AgentState.PAUSED: "yellow",
                AgentState.STOPPING: "red",
                AgentState.STOPPED: "dim",
                AgentState.ERROR: "red bold",
                AgentState.STARTING: "cyan",
            }.get(instance.state, "white")

            uptime = f"{instance.uptime_seconds:.0f}s" if instance.is_alive else "-"
            tokens = f"{instance.tokens_used}/{instance.max_tokens_per_session}"
            tool_calls = f"{instance.tool_calls_made}/{instance.max_tool_calls}"
            model = f"{instance.image.model.provider}/{instance.image.model.model}"

            limit_text = instance.limit_description
            if instance.is_at_limit:
                limit_text = Text(limit_text, style="red bold")

            table.add_row(
                instance.agent_id[:16],
                instance.image.name,
                Text(instance.state.value, style=state_style),
                uptime,
                tokens,
                tool_calls,
                model,
                limit_text,
            )

        self._console.print("")
        self._console.print(table)
        self._console.print("")

        return [i.to_dict() for i in instances]

    def get(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed info about a specific agent.

        Args:
            agent_id: The agent identifier.

        Returns:
            Agent instance dict, or None if not found.
        """
        with self._lock:
            instance = self._agents.get(agent_id)
            if instance is None:
                return None
            return instance.to_dict()

    # ── Logs ─────────────────────────────────────────────────────────

    def get_logs(
        self,
        agent_id: str,
        limit: int = 50,
        level: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Return recent agent logs.

        Args:
            agent_id: The agent identifier.
            limit: Maximum number of log entries.
            level: Optional filter by log level (info, warn, error, debug).

        Returns:
            List of log entry dicts.
        """
        with self._lock:
            logs = self._agent_logs.get(agent_id, [])

        if level:
            logs = [e for e in logs if e.get("level") == level]

        return logs[-limit:]

    def clear_logs(self, agent_id: str) -> int:
        """Clear all logs for an agent.

        Args:
            agent_id: The agent identifier.

        Returns:
            Number of log entries cleared.
        """
        with self._lock:
            logs = self._agent_logs.get(agent_id, [])
            count = len(logs)
            self._agent_logs[agent_id] = []
            return count

    # ── Internal Methods ─────────────────────────────────────────────

    def _transition(
        self,
        instance: AgentInstance,
        new_state: AgentState,
        *,
        stopped: bool = False,
    ) -> None:
        """Transition an agent to a new state.

        Args:
            instance: The agent instance to transition.
            new_state: The target state.
            stopped: If True, set the stopped_at timestamp.
        """
        instance.state = new_state
        instance.last_activity = datetime.now(timezone.utc).isoformat()
        if stopped:
            instance.stopped_at = datetime.now(timezone.utc).isoformat()

    def _log(
        self,
        instance: AgentInstance,
        level: str,
        message: str,
        *,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Add a log entry for an agent instance.

        Args:
            instance: The agent instance.
            level: Log level (info, warn, error, debug).
            message: Log message.
            extra: Optional extra data.
        """
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "agent_id": instance.agent_id,
            "agent_name": instance.image.name,
            "message": message,
        }
        if extra:
            entry["extra"] = extra

        with self._lock:
            logs = self._agent_logs.setdefault(instance.agent_id, [])
            logs.append(entry)

            # Also persist to agent log file
            log_file = AGENT_LOG_DIR / f"{instance.agent_id}.jsonl"
            try:
                with open(log_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(entry, default=str) + "\n")
            except OSError:
                pass

        # Also log via Python logging
        log_method = getattr(logger, level, logger.info)
        log_method("[%s] %s", instance.agent_id[:8], message)

    def _monitor_loop(self) -> None:
        """Background thread that checks agents for resource limit violations.

        Agents that exceed their limits are automatically stopped.
        """
        while not self._stop_monitor.is_set():
            try:
                with self._lock:
                    to_stop: List[str] = []
                    for agent_id, instance in self._agents.items():
                        if instance.is_alive and instance.is_at_limit:
                            to_stop.append(agent_id)

                for agent_id in to_stop:
                    with self._lock:
                        instance = self._agents.get(agent_id)
                        if instance and instance.is_alive and instance.is_at_limit:
                            self._log(
                                instance,
                                "warn",
                                f"Resource limit reached: {instance.limit_description}",
                            )
                            self._transition(instance, AgentState.STOPPING)

                    time.sleep(0.05)
                    with self._lock:
                        instance = self._agents.get(agent_id)
                        if instance and instance.state == AgentState.STOPPING:
                            self._transition(instance, AgentState.STOPPED, stopped=True)
                            self._log(instance, "info", "Agent stopped (limit reached)")

            except Exception as exc:
                logger.debug("Monitor loop error: %s", exc)

            # Check every 5 seconds
            self._stop_monitor.wait(timeout=5.0)

    def cleanup(self) -> None:
        """Clean up all agent runtimes.

        Stops the monitor thread and all running agents.
        """
        self._stop_monitor.set()
        self.stop_all()

        with self._lock:
            self._agents.clear()
            self._agent_logs.clear()

    def __del__(self) -> None:
        """Ensure cleanup on destruction."""
        try:
            self.cleanup()
        except Exception:
            pass
