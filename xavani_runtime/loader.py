# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Agent Image loader — Phase 6.

ImageLoader handles loading, validating, and exporting agent images
from ``.agent.toml`` files and a local image registry.

Images are stored under ``~/.xavani/agent-images/``.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from rich.console import Console
from rich.table import Table
from rich.text import Text

from .image import AgentImage

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
AGENT_IMAGES_DIR = XAVANI_HOME / "agent-images"
REGISTRY_INDEX = AGENT_IMAGES_DIR / "index.json"

# Valid tool categories
_VALID_TOOLSETS: set = {
    "file", "terminal", "web", "network", "database",
    "search", "memory", "notebook", "image", "audio",
    "video", "social", "email", "calendar", "mcp",
}

# Valid memory types
_VALID_MEMORY_TYPES: set = {"episodic", "procedural", "semantic", "none"}

# Valid provider names
_VALID_PROVIDERS: set = {
    "anthropic", "openai", "openrouter", "google", "aws-bedrock",
    "azure", "together", "groq", "mistral", "deepseek", "custom",
}

# Maximum TTL days
_MAX_TTL_DAYS = 3650  # 10 years

# Maximum description length
_MAX_DESCRIPTION_LENGTH = 500

# Maximum system prompt length
_MAX_SYSTEM_PROMPT_LENGTH = 100_000


# ---------------------------------------------------------------------------
# ImageLoader
# ---------------------------------------------------------------------------


class ImageLoader:
    """Loads, validates, exports, and manages agent images.

    Agent images are portable definitions stored in ``.agent.toml`` files.
    The loader manages a local registry of available images under
    ``~/.xavani/agent-images/``.

    Usage::
        loader = ImageLoader()

        # Load from file
        image = loader.load_from_file("path/to/agent.agent.toml")

        # Load from registry
        image = loader.load_from_registry("code-reviewer")

        # Validate
        errors = loader.validate(image)

        # Export
        loader.export(image, "path/to/output.agent.toml")

        # List available
        loader.list_available()
    """

    def __init__(self, images_dir: Optional[Path] = None) -> None:
        self._images_dir = images_dir or AGENT_IMAGES_DIR
        self._registry_index = self._images_dir / "index.json"
        self._console = Console()

        # Ensure directories exist
        self._images_dir.mkdir(parents=True, exist_ok=True)

        # Initialize registry index if missing
        if not self._registry_index.exists():
            self._save_index({"images": {}, "updated_at": datetime.now(timezone.utc).isoformat()})

    # ── Load Methods ─────────────────────────────────────────────────

    def load_from_file(self, path: str) -> AgentImage:
        """Load an agent image from a ``.agent.toml`` file.

        Args:
            path: Path to the ``.agent.toml`` file.

        Returns:
            An AgentImage instance.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the file is not valid TOML or missing required fields.
        """
        file_path = Path(path).expanduser().resolve()

        if not file_path.exists():
            raise FileNotFoundError(f"Agent image file not found: {file_path}")

        if file_path.suffix not in (".toml", ".agent.toml"):
            logger.warning("File does not have .toml extension: %s", file_path)

        try:
            with open(file_path, "rb") as f:
                raw = f.read()
        except OSError as exc:
            raise ValueError(f"Failed to read image file: {exc}") from exc

        # Parse TOML using tomllib (Python 3.11+ standard library)
        try:
            import tomllib
            data = tomllib.loads(raw.decode("utf-8"))
        except (ValueError, KeyError, SyntaxError, ImportError) as exc:
            try:
                import tomli
                data = tomli.loads(raw.decode("utf-8"))
            except ImportError:
                raise ValueError(
                    "Cannot parse TOML. Python 3.11+ has tomllib built-in; "
                    "on older Python install tomli (`pip install tomli`)."
                ) from exc
            except Exception as inner:
                raise ValueError(f"Failed to parse TOML file: {inner}") from exc
        except Exception as exc:
            raise ValueError(f"Failed to parse TOML file: {exc}") from exc

        # Validate structure
        if "agent" not in data:
            raise ValueError("Missing [agent] section in image file")

        image = AgentImage.from_dict(data)

        # Compute hash from raw content
        image.image_hash = hashlib.sha256(raw).hexdigest()[:16]

        return image

    def load_from_registry(self, name: str) -> AgentImage:
        """Load an agent image from the local registry by name.

        Args:
            name: Agent image name (e.g. ``code-reviewer``).

        Returns:
            An AgentImage instance.

        Raises:
            ValueError: If the image is not found in the registry.
        """
        index = self._load_index()
        images = index.get("images", {})

        if name not in images:
            raise ValueError(
                f"Agent image '{name}' not found in registry. "
                f"Available: {', '.join(sorted(images.keys())) or '(none)'}"
            )

        entry = images[name]
        file_path = entry.get("path")

        if not file_path or not Path(file_path).exists():
            # Try relative path
            alt_path = self._images_dir / f"{name}.agent.toml"
            if alt_path.exists():
                file_path = str(alt_path)
            else:
                raise ValueError(
                    f"Image file for '{name}' not found at registered path. "
                    f"Try re-importing the image."
                )

        return self.load_from_file(file_path)

    # ── Validation ───────────────────────────────────────────────────

    def validate(self, image: AgentImage) -> List[str]:
        """Validate all fields and dependencies of an agent image.

        Checks:
        - Required fields are present and non-empty
        - Model provider is known
        - Toolsets are valid categories
        - Memory type is valid
        - Policy values are reasonable
        - Version string is semver-like

        Args:
            image: The AgentImage to validate.

        Returns:
            List of validation error messages. Empty list = valid.
        """
        errors: List[str] = []

        # ── Agent identity ──
        if not image.name or not image.name.strip():
            errors.append("Agent name is required")
        elif not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$", image.name):
            errors.append(
                f"Agent name '{image.name}' must start with a letter or digit "
                f"and contain only letters, digits, dots, hyphens, and underscores"
            )

        if not image.version or not image.version.strip():
            errors.append("Agent version is required")
        elif not re.match(r"^\d+\.\d+\.\d+", image.version):
            errors.append(
                f"Agent version '{image.version}' should follow semver "
                f"(e.g. 1.0.0)"
            )

        if not image.description:
            errors.append("Agent description is required")
        elif len(image.description) > _MAX_DESCRIPTION_LENGTH:
            errors.append(
                f"Description too long ({len(image.description)} > "
                f"{_MAX_DESCRIPTION_LENGTH} chars)"
            )

        # ── Model ──
        if not image.model.provider:
            errors.append("Model provider is required")
        elif image.model.provider not in _VALID_PROVIDERS:
            errors.append(
                f"Unknown model provider '{image.model.provider}'. "
                f"Valid: {', '.join(sorted(_VALID_PROVIDERS))}"
            )

        if not image.model.model:
            errors.append("Model name is required")

        params = image.model.parameters
        if not isinstance(params, dict):
            errors.append("Model parameters must be a dict")
        else:
            temp = params.get("temperature")
            if temp is not None and not isinstance(temp, (int, float)):
                errors.append("Model temperature must be a number")
            max_tokens = params.get("max_tokens")
            if max_tokens is not None and not isinstance(max_tokens, int):
                errors.append("Model max_tokens must be an integer")

        # ── Skills ──
        if not isinstance(image.skills.enabled, list):
            errors.append("Skills must be a list")

        # ── Toolsets ──
        if not isinstance(image.toolsets.enabled, list):
            errors.append("Toolsets must be a list")
        else:
            for toolset in image.toolsets.enabled:
                if toolset not in _VALID_TOOLSETS:
                    errors.append(
                        f"Unknown toolset '{toolset}'. "
                        f"Valid: {', '.join(sorted(_VALID_TOOLSETS))}"
                    )

        # ── Memory ──
        if image.memory.type not in _VALID_MEMORY_TYPES:
            errors.append(
                f"Unknown memory type '{image.memory.type}'. "
                f"Valid: {', '.join(sorted(_VALID_MEMORY_TYPES))}"
            )

        if image.memory.ttl_days < 0:
            errors.append("Memory TTL days cannot be negative")
        elif image.memory.ttl_days > _MAX_TTL_DAYS:
            errors.append(
                f"Memory TTL days ({image.memory.ttl_days}) exceeds maximum "
                f"({_MAX_TTL_DAYS})"
            )

        if image.memory.max_episodes < 1:
            errors.append("Memory max_episodes must be at least 1")

        # ── Policies ──
        rate = image.policies.rate_limit
        if rate and not re.match(r"^\d+/(min|hour|day|sec)$", rate):
            errors.append(
                f"Invalid rate limit format '{rate}'. "
                f"Expected format: N/min, N/hour, N/day, N/sec"
            )

        if image.policies.max_concurrent < 1:
            errors.append("Policy max_concurrent must be at least 1")

        # ── Environment ──
        if not isinstance(image.environment.vars, dict):
            errors.append("Environment must be a dict")

        # ── System prompt ──
        if not image.system_prompt.content:
            errors.append("System prompt content is required")
        elif len(image.system_prompt.content) > _MAX_SYSTEM_PROMPT_LENGTH:
            errors.append(
                f"System prompt too long ({len(image.system_prompt.content)} > "
                f"{_MAX_SYSTEM_PROMPT_LENGTH} chars)"
            )

        return errors

    # ── Export ───────────────────────────────────────────────────────

    def export(self, image: AgentImage, path: str) -> str:
        """Export an agent image to a ``.agent.toml`` file.

        Validates the image before exporting. If validation fails,
        errors are printed but the file is still written.

        Args:
            image: The AgentImage to export.
            path: Output file path.

        Returns:
            The absolute path to the written file as a string.

        Raises:
            ValueError: If the path is not writable.
        """
        file_path = Path(path).expanduser().resolve()

        # Ensure parent directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Validate before export
        errors = self.validate(image)
        if errors:
            self._console.print("[yellow]Validation warnings for exported image:[/yellow]")
            for err in errors:
                self._console.print(f"  [yellow]- {err}[/yellow]")

        # Generate TOML
        toml_content = image.to_toml_string()

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(toml_content)
                f.write("\n")
        except OSError as exc:
            raise ValueError(f"Failed to write image file: {exc}") from exc

        logger.info("Exported agent image to %s", file_path)
        return str(file_path)

    # ── Registry Management ──────────────────────────────────────────

    def register(self, image: AgentImage, source_path: Optional[str] = None) -> str:
        """Register an agent image in the local registry.

        Copies the image file to the registry directory and indexes it.

        Args:
            image: The AgentImage to register.
            source_path: Optional source file path. If provided, the file is
                copied to the registry. If None, an ``.agent.toml`` file is
                generated in the registry directory.

        Returns:
            The registered image name as a string.
        """
        # Validate first
        errors = self.validate(image)
        if errors:
            error_msg = "\n".join(f"  - {e}" for e in errors)
            raise ValueError(f"Cannot register invalid image:\n{error_msg}")

        target_path = self._images_dir / f"{image.name}.agent.toml"

        if source_path:
            src = Path(source_path).expanduser().resolve()
            if src.exists():
                shutil.copy2(src, target_path)
            else:
                raise FileNotFoundError(f"Source file not found: {source_path}")
        else:
            self.export(image, str(target_path))

        # Update registry index
        index = self._load_index()
        images = index.get("images", {})

        images[image.name] = {
            "version": image.version,
            "description": image.description,
            "path": str(target_path),
            "provider": image.model.provider,
            "model": image.model.model,
            "registered_at": datetime.now(timezone.utc).isoformat(),
        }

        index["images"] = images
        index["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._save_index(index)

        logger.info("Registered agent image '%s' v%s", image.name, image.version)
        return image.name

    def unregister(self, name: str) -> bool:
        """Remove an agent image from the registry.

        Args:
            name: Agent image name to remove.

        Returns:
            True if removed, False if not found.
        """
        index = self._load_index()
        images = index.get("images", {})

        if name not in images:
            return False

        entry = images.pop(name)
        index["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._save_index(index)

        # Remove the file
        file_path = entry.get("path")
        if file_path and Path(file_path).exists():
            Path(file_path).unlink()
        else:
            alt = self._images_dir / f"{name}.agent.toml"
            if alt.exists():
                alt.unlink()

        logger.info("Unregistered agent image '%s'", name)
        return True

    def list_available(self) -> List[Dict[str, Any]]:
        """List all available agent images in the registry.

        Displays a Rich table with name, version, description, model info.

        Returns:
            List of image metadata dicts.
        """
        index = self._load_index()
        images = index.get("images", {})

        if not images:
            self._console.print("[yellow]No agent images registered.[/yellow]")
            self._console.print(
                "Register an image with: loader.register(image) or "
                "loader.load_from_file(path)"
            )
            return []

        table = Table(
            title=f"Available Agent Images ({len(images)})",
            title_style="bold",
            header_style="bold cyan",
            border_style="blue",
        )

        table.add_column("Name", style="green", width=20)
        table.add_column("Version", width=10)
        table.add_column("Model", width=24)
        table.add_column("Description", width=50)
        table.add_column("Registered", width=20)

        sorted_names = sorted(images.keys())
        result: List[Dict[str, Any]] = []

        for name in sorted_names:
            entry = images[name]
            model_str = f"{entry.get('provider', '?')}/{entry.get('model', '?')}"
            registered = entry.get("registered_at", "")[:19] if entry.get("registered_at") else "-"

            table.add_row(
                name,
                entry.get("version", "?"),
                model_str,
                (entry.get("description", "") or "")[:60],
                registered,
            )
            result.append(entry)

        self._console.print("")
        self._console.print(table)
        self._console.print("")
        return result

    def find(self, name: str) -> Optional[Dict[str, Any]]:
        """Find an image in the registry by name (fuzzy match).

        Args:
            name: Image name to search for (partial match allowed).

        Returns:
            Image metadata dict if found, None otherwise.
        """
        index = self._load_index()
        images = index.get("images", {})

        # Exact match first
        if name in images:
            return images[name]

        # Partial match
        name_lower = name.lower()
        for img_name, entry in images.items():
            if name_lower in img_name.lower():
                return entry

        return None

    # ── Internal Registry Persistence ────────────────────────────────

    def _load_index(self) -> Dict[str, Any]:
        """Load the registry index from disk."""
        try:
            if self._registry_index.exists():
                with open(self._registry_index, "r", encoding="utf-8") as f:
                    return json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Failed to load registry index: %s", exc)

        return {"images": {}, "updated_at": datetime.now(timezone.utc).isoformat()}

    def _save_index(self, index: Dict[str, Any]) -> None:
        """Save the registry index to disk."""
        try:
            self._registry_index.parent.mkdir(parents=True, exist_ok=True)
            with open(self._registry_index, "w", encoding="utf-8") as f:
                json.dump(index, f, indent=2, default=str)
        except OSError as exc:
            logger.error("Failed to save registry index: %s", exc)

    # ── Utility ──────────────────────────────────────────────────────

    def get_image_path(self, name: str) -> Optional[Path]:
        """Get the filesystem path of a registered agent image.

        Args:
            name: Image name.

        Returns:
            Path if found, None otherwise.
        """
        index = self._load_index()
        entry = index.get("images", {}).get(name)
        if entry:
            p = entry.get("path")
            if p:
                return Path(p)
            alt = self._images_dir / f"{name}.agent.toml"
            if alt.exists():
                return alt
        return None
