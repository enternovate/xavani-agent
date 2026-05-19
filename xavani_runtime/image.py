# Copyright (c) 2025-2026 Enternovate. All rights reserved.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Portable Agent Image format — Phase 6.

Defines the ``AgentImage`` dataclass which represents a portable, declarative
agent definition. An agent image captures everything needed to instantiate
an agent: model config, skills, toolsets, memory, policies, environment,
and system prompt.

Agent images are serialized to/from ``.agent.toml`` files and can be
stored in a local registry for reuse.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass
class ModelConfig:
    """Configuration for the agent's language model.

    Attributes:
        provider: The provider name (e.g. ``anthropic``, ``openai``, ``openrouter``).
        model: The model identifier (e.g. ``claude-sonnet-4-6``, ``gpt-4o``).
        parameters: Optional model parameters (temperature, max_tokens, etc.).
    """

    provider: str = "anthropic"
    model: str = "claude-sonnet-4-6"
    parameters: Dict[str, Any] = field(default_factory=lambda: {
        "temperature": 0.7,
        "max_tokens": 4096,
    })

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModelConfig":
        return cls(
            provider=data.get("provider", "anthropic"),
            model=data.get("model", "claude-sonnet-4-6"),
            parameters=data.get("parameters", {}),
        )


@dataclass
class SkillsConfig:
    """Configuration for the agent's enabled skills.

    Attributes:
        enabled: List of skill identifiers to enable.
    """

    enabled: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {"enabled": list(self.enabled)}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SkillsConfig":
        return cls(enabled=data.get("enabled", []))


@dataclass
class ToolsetsConfig:
    """Configuration for the agent's enabled tool categories.

    Attributes:
        enabled: List of tool category names (e.g. ``file``, ``terminal``, ``web``).
    """

    enabled: List[str] = field(default_factory=lambda: ["file", "terminal"])

    def to_dict(self) -> Dict[str, Any]:
        return {"enabled": list(self.enabled)}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ToolsetsConfig":
        return cls(enabled=data.get("enabled", []))


@dataclass
class MemoryConfig:
    """Configuration for the agent's memory system.

    Attributes:
        type: Memory type (``episodic``, ``procedural``, ``semantic``, ``none``).
        ttl_days: Number of days before memories are auto-archived.
        max_episodes: Maximum number of episodes to retain per session.
    """

    type: str = "episodic"
    ttl_days: int = 30
    max_episodes: int = 500

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "ttl_days": self.ttl_days,
            "max_episodes": self.max_episodes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryConfig":
        return cls(
            type=data.get("type", "episodic"),
            ttl_days=data.get("ttl_days", 30),
            max_episodes=data.get("max_episodes", 500),
        )


@dataclass
class PolicyConfig:
    """Security and governance policies for the agent.

    Attributes:
        rate_limit: Rate limit string (e.g. ``30/min``, ``100/hour``).
        allowed_tools: List of allowed tool names (empty = all allowed).
        denied_tools: List of explicitly denied tool names.
        audit: Whether to audit all tool calls.
        max_concurrent: Maximum concurrent tool executions.
    """

    rate_limit: str = "30/min"
    allowed_tools: List[str] = field(default_factory=list)
    denied_tools: List[str] = field(default_factory=list)
    audit: bool = True
    max_concurrent: int = 5

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rate_limit": self.rate_limit,
            "allowed_tools": list(self.allowed_tools),
            "denied_tools": list(self.denied_tools),
            "audit": self.audit,
            "max_concurrent": self.max_concurrent,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PolicyConfig":
        return cls(
            rate_limit=data.get("rate_limit", "30/min"),
            allowed_tools=data.get("allowed_tools", []),
            denied_tools=data.get("denied_tools", []),
            audit=data.get("audit", True),
            max_concurrent=data.get("max_concurrent", 5),
        )


@dataclass
class EnvironmentConfig:
    """Environment variables for the agent.

    Attributes:
        vars: Mapping of environment variable names to their default values.
    """

    vars: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, str]:
        return dict(self.vars)

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> "EnvironmentConfig":
        return cls(vars=dict(data))


@dataclass
class SystemPromptConfig:
    """Custom personality and instructions for the agent.

    Attributes:
        content: The system prompt text.
        variables: Optional template variables for prompt customization.
    """

    content: str = "You are a helpful AI assistant."
    variables: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "variables": dict(self.variables),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SystemPromptConfig":
        return cls(
            content=data.get("content", "You are a helpful AI assistant."),
            variables=data.get("variables", {}),
        )


# ---------------------------------------------------------------------------
# AgentImage
# ---------------------------------------------------------------------------


@dataclass
class AgentImage:
    """Portable agent definition — a complete, declarative agent specification.

    An AgentImage captures everything needed to instantiate and run an agent:

    - **Identity**: name, version, description
    - **Model**: which provider and model to use
    - **Skills**: which skills are enabled
    - **Toolsets**: which tool categories are available
    - **Memory**: memory configuration (type, TTL, limits)
    - **Policies**: security rules (rate limits, allowed/denied tools, audit)
    - **Environment**: env vars with defaults
    - **System Prompt**: custom personality and instructions

    Images serialize to/from ``.agent.toml`` files.

    Usage::
        image = AgentImage(
            name="code-reviewer",
            version="1.0.0",
            description="Automated code review agent",
            model=ModelConfig(provider="anthropic", model="claude-sonnet-4-6"),
            skills=SkillsConfig(enabled=["github-code-review", "github-pr-workflow"]),
            toolsets=ToolsetsConfig(enabled=["file", "terminal", "web"]),
            memory=MemoryConfig(type="episodic", ttl_days=30),
            policies=PolicyConfig(
                rate_limit="30/min",
                allowed_tools=["read_file", "search_files", "patch"],
            ),
            environment=EnvironmentConfig(vars={"LOG_LEVEL": "info"}),
            system_prompt=SystemPromptConfig(
                content="You are a code review agent. Be thorough but constructive."
            ),
        )
    """

    # Identity
    name: str = "default-agent"
    version: str = "1.0.0"
    description: str = "A Xavani agent"

    # Configuration
    model: ModelConfig = field(default_factory=ModelConfig)
    skills: SkillsConfig = field(default_factory=SkillsConfig)
    toolsets: ToolsetsConfig = field(default_factory=ToolsetsConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    policies: PolicyConfig = field(default_factory=PolicyConfig)
    environment: EnvironmentConfig = field(default_factory=EnvironmentConfig)

    # System prompt
    system_prompt: SystemPromptConfig = field(default_factory=SystemPromptConfig)

    # Metadata
    image_hash: str = ""

    # ── Serialization ────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the agent image to a nested dict.

        Returns:
            Dict suitable for TOML serialization.
        """
        return {
            "agent": {
                "name": self.name,
                "version": self.version,
                "description": self.description,
            },
            "model": self.model.to_dict(),
            "skills": self.skills.to_dict(),
            "toolsets": self.toolsets.to_dict(),
            "memory": self.memory.to_dict(),
            "policies": self.policies.to_dict(),
            "environment": self.environment.to_dict(),
            "system_prompt": self.system_prompt.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentImage":
        """Create an AgentImage from a nested dict (as parsed from TOML).

        Args:
            data: Dict with keys matching ``.agent.toml`` structure.

        Returns:
            An AgentImage instance.
        """
        agent = data.get("agent", {})
        return cls(
            name=agent.get("name", "default-agent"),
            version=agent.get("version", "1.0.0"),
            description=agent.get("description", "A Xavani agent"),
            model=ModelConfig.from_dict(data.get("model", {})),
            skills=SkillsConfig.from_dict(data.get("skills", {})),
            toolsets=ToolsetsConfig.from_dict(data.get("toolsets", {})),
            memory=MemoryConfig.from_dict(data.get("memory", {})),
            policies=PolicyConfig.from_dict(data.get("policies", {})),
            environment=EnvironmentConfig.from_dict(data.get("environment", {})),
            system_prompt=SystemPromptConfig.from_dict(data.get("system_prompt", {})),
        )

    def to_toml_string(self) -> str:
        """Serialize the agent image to a TOML-formatted string.

        Returns:
            TOML string suitable for writing to a ``.agent.toml`` file.
        """
        lines: List[str] = []
        d = self.to_dict()

        # Agent section
        lines.append("[agent]")
        lines.append(f"name = \"{self._escape_toml(self.name)}\"")
        lines.append(f"version = \"{self._escape_toml(self.version)}\"")
        lines.append(f"description = \"{self._escape_toml(self.description)}\"")
        lines.append("")

        # Model section
        lines.append("[model]")
        lines.append(f"provider = \"{self._escape_toml(self.model.provider)}\"")
        lines.append(f"model = \"{self._escape_toml(self.model.model)}\"")
        if self.model.parameters:
            lines.append(f"parameters = {self._toml_inline_table(self.model.parameters)}")
        lines.append("")

        # Skills section
        lines.append("[skills]")
        lines.append(f"enabled = {self._toml_array(self.skills.enabled)}")
        lines.append("")

        # Toolsets section
        lines.append("[toolsets]")
        lines.append(f"enabled = {self._toml_array(self.toolsets.enabled)}")
        lines.append("")

        # Memory section
        lines.append("[memory]")
        lines.append(f"type = \"{self._escape_toml(self.memory.type)}\"")
        lines.append(f"ttl_days = {self.memory.ttl_days}")
        lines.append("")

        # Policies section
        lines.append("[policies]")
        lines.append(f"rate_limit = \"{self._escape_toml(self.policies.rate_limit)}\"")
        if self.policies.allowed_tools:
            lines.append(f"allowed_tools = {self._toml_array(self.policies.allowed_tools)}")
        if self.policies.denied_tools:
            lines.append(f"denied_tools = {self._toml_array(self.policies.denied_tools)}")
        lines.append(f"audit = {'true' if self.policies.audit else 'false'}")
        lines.append("")

        # Environment section (inline table)
        lines.append("[environment]")
        for key, value in self.environment.vars.items():
            lines.append(f"{key} = \"{self._escape_toml(value)}\"")
        lines.append("")

        # System prompt section
        lines.append("[system_prompt]")
        # Use TOML literal multiline string for the content
        lines.append("content = \"\"\"")
        lines.append(self.system_prompt.content)
        lines.append("\"\"\"")
        if self.system_prompt.variables:
            for key, value in self.system_prompt.variables.items():
                lines.append(f"{key} = \"{self._escape_toml(value)}\"")

        return "\n".join(lines)

    @staticmethod
    def _escape_toml(value: str) -> str:
        """Escape special characters for TOML basic strings."""
        return (
            value.replace("\\", "\\\\")
            .replace("\"", "\\\"")
            .replace("\n", "\\n")
            .replace("\t", "\\t")
        )

    @staticmethod
    def _toml_array(items: List[str]) -> str:
        """Format a list of strings as a TOML inline array."""
        escaped = [f"\"{AgentImage._escape_toml(i)}\"" for i in items]
        return "[" + ", ".join(escaped) + "]"

    @staticmethod
    def _toml_inline_table(data: Dict[str, Any]) -> str:
        """Format a dict as a TOML inline table."""
        items = []
        for key, value in data.items():
            if isinstance(value, str):
                items.append(f"{key} = \"{AgentImage._escape_toml(value)}\"")
            elif isinstance(value, bool):
                items.append(f"{key} = {'true' if value else 'false'}")
            else:
                items.append(f"{key} = {value}")
        return "{" + ", ".join(items) + "}"

    # ── Utility ──────────────────────────────────────────────────────

    @property
    def full_name(self) -> str:
        """Return the full agent identifier: ``name@version``."""
        return f"{self.name}@{self.version}"

    def __str__(self) -> str:
        return f"AgentImage({self.full_name}: {self.description[:50]})"

    def __repr__(self) -> str:
        return f"AgentImage(name={self.name!r}, version={self.version!r})"
