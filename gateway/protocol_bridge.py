# Copyright (c) 2025-2026 Enternovate. All rights reserved.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Protocol Bridge — Phase 3 of Xavani Agent.

Translates between MCP (Model Context Protocol) and A2A (Agent-to-Agent
protocol) so that:

- MCP tools can be called by A2A agents
- A2A agents can be invoked by MCP clients
- OpenAPI endpoints become callable as MCP tools

This module is zero-dependency beyond the standard library and FastAPI
(which is already a dependency of the gateway server).
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import time
import uuid
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import urlparse, urljoin

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

XAVANI_HOME = Path(os.environ.get("XAVANI_HOME", "~/.xavani")).expanduser()
BRIDGE_DATA_DIR = XAVANI_HOME / "data" / "bridge"
BRIDGE_AGENTS_FILE = BRIDGE_DATA_DIR / "registered_agents.json"

A2A_PROTOCOL_VERSION = "1.0"
MCP_PROTOCOL_VERSION = "1.0"

# Default bridge server settings
DEFAULT_BRIDGE_HOST = "127.0.0.1"
DEFAULT_BRIDGE_PORT = 8081

# ---------------------------------------------------------------------------
# Task States (A2A spec)
# ---------------------------------------------------------------------------

class A2ATaskState:
    """Standard A2A task states."""
    SUBMITTED = "submitted"
    WORKING = "working"
    INPUT_REQUIRED = "input-required"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"

# ---------------------------------------------------------------------------
# A2AClient — communicates with A2A agents
# ---------------------------------------------------------------------------

class A2AClient:
    """Client for communicating with A2A (Agent-to-Agent) agents.

    Handles sending tasks, checking status, and cancellation via the
    A2A HTTP API. Supports both streaming and synchronous modes.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: float = 30.0,
        max_retries: int = 3,
    ):
        self._base_url = base_url
        self._timeout = timeout
        self._max_retries = max_retries
        self._session = _SessionManager()

    # ── HTTP request helpers ──────────────────────────────────────────

    async def _request(
        self,
        method: str,
        url: str,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Make an HTTP request with retry logic.

        Uses urllib.request as a fallback; if httpx or aiohttp are
        available, we prefer them for async operation.
        """
        import urllib.request
        import urllib.error

        merged_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": f"Xavani-A2AClient/{A2A_PROTOCOL_VERSION}",
        }
        if headers:
            merged_headers.update(headers)

        last_error: Optional[Exception] = None
        for attempt in range(self._max_retries):
            try:
                if method == "GET":
                    req = urllib.request.Request(
                        url, headers=merged_headers, method="GET"
                    )
                elif method == "POST":
                    data = json.dumps(json_data or {}).encode("utf-8")
                    req = urllib.request.Request(
                        url, data=data, headers=merged_headers, method="POST"
                    )
                elif method == "DELETE":
                    req = urllib.request.Request(
                        url, headers=merged_headers, method="DELETE"
                    )
                elif method == "PUT":
                    data = json.dumps(json_data or {}).encode("utf-8")
                    req = urllib.request.Request(
                        url, data=data, headers=merged_headers, method="PUT"
                    )
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                with urllib.request.urlopen(
                    req, timeout=self._timeout
                ) as resp:
                    body = resp.read().decode("utf-8")
                    return json.loads(body)

            except urllib.error.HTTPError as exc:
                last_error = exc
                if exc.code in (429, 503):
                    # Rate limited or unavailable
                    wait = min(2 ** attempt, 10)
                    await asyncio.sleep(wait)
                    continue
                # Non-retryable HTTP error
                raise
            except (OSError, ConnectionError) as exc:
                last_error = exc
                if attempt < self._max_retries - 1:
                    await asyncio.sleep(min(2 ** attempt, 5))
                    continue
                raise

        raise RuntimeError(
            f"Request failed after {self._max_retries} retries: {last_error}"
        )

    # ── Core A2A operations ───────────────────────────────────────────

    async def send_task(
        self,
        agent_url: str,
        task: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Send a task to an A2A agent.

        Args:
            agent_url: The base URL of the A2A agent (e.g.
                ``http://localhost:8082/a2a``).
            task: A2A task dict with keys like ``message``, ``session_id``,
                ``metadata``. The ``task_id`` is auto-generated if not provided.

        Returns:
            A2A task status response with ``id``, ``status``, ``artifacts``.

        Raises:
            ConnectionError: If the agent is unreachable.
            ValueError: If the response is malformed.
        """
        if "id" not in task:
            task["id"] = _generate_task_id()

        a2a_url = urljoin(agent_url.rstrip("/") + "/", "tasks/send")
        payload = {
            "jsonrpc": "2.0",
            "method": "tasks/send",
            "params": {"task": task},
            "id": str(uuid.uuid4()),
        }

        response = await self._request("POST", a2a_url, json_data=payload)

        # Normalize A2A JSON-RPC response
        if "result" in response:
            return response["result"]
        if "error" in response:
            raise RuntimeError(
                f"A2A agent error: {response['error'].get('message', str(response['error']))}"
            )
        return response

    async def get_task_status(self, task_id: str, agent_url: str) -> Dict[str, Any]:
        """Check the progress/status of a previously submitted task.

        Args:
            task_id: The A2A task ID to query.
            agent_url: The base URL of the A2A agent.

        Returns:
            A2A task status dict.
        """
        a2a_url = urljoin(agent_url.rstrip("/") + "/", f"tasks/{task_id}")
        payload = {
            "jsonrpc": "2.0",
            "method": "tasks/get",
            "params": {"id": task_id},
            "id": str(uuid.uuid4()),
        }

        response = await self._request("POST", a2a_url, json_data=payload)

        if "result" in response:
            return response["result"]
        if "error" in response:
            raise RuntimeError(
                f"A2A status check error: {response['error'].get('message', str(response['error']))}"
            )
        return response

    async def cancel_task(self, task_id: str, agent_url: str) -> Dict[str, Any]:
        """Cancel a running task on an A2A agent.

        Args:
            task_id: The A2A task ID to cancel.
            agent_url: The base URL of the A2A agent.

        Returns:
            Cancellation confirmation dict.
        """
        a2a_url = urljoin(agent_url.rstrip("/") + "/", f"tasks/{task_id}/cancel")
        payload = {
            "jsonrpc": "2.0",
            "method": "tasks/cancel",
            "params": {"id": task_id},
            "id": str(uuid.uuid4()),
        }

        response = await self._request("POST", a2a_url, json_data=payload)

        if "result" in response:
            return response["result"]
        if "error" in response:
            raise RuntimeError(
                f"A2A cancel error: {response['error'].get('message', str(response['error']))}"
            )
        return response

    async def get_agent_card(self, agent_url: str) -> Dict[str, Any]:
        """Retrieve the Agent Card from an A2A agent.

        The Agent Card describes the agent's capabilities, skills, and
        authentication requirements per the A2A specification.

        Args:
            agent_url: The base URL of the A2A agent.

        Returns:
            Agent Card dict with ``name``, ``description``, ``skills``, etc.
        """
        card_url = urljoin(agent_url.rstrip("/") + "/", ".well-known/agent.json")
        payload = {
            "jsonrpc": "2.0",
            "method": "agent/getCard",
            "params": {},
            "id": str(uuid.uuid4()),
        }

        response = await self._request("POST", card_url, json_data=payload)

        if "result" in response:
            return response["result"]
        # Fallback: try direct GET on the well-known URL
        try:
            response = await self._request("GET", card_url)
            return response
        except Exception:
            raise RuntimeError(
                f"Could not retrieve Agent Card from {agent_url}"
            )


# ---------------------------------------------------------------------------
# MCPToolAdapter — wraps an MCP tool as an A2A skill
# ---------------------------------------------------------------------------

class MCPToolAdapter:
    """Converts MCP tools into A2A-format skills and vice versa.

    An MCP tool provides a name, description, and input_schema (JSON Schema).
    An A2A skill describes a capability with a name, description, and
    optional parameters. This adapter bridges the two formats.
    """

    # Mapping from JSON Schema types to A2A parameter types
    _JSON_SCHEMA_TO_A2A_TYPE: Dict[str, str] = {
        "string": "string",
        "number": "number",
        "integer": "integer",
        "boolean": "boolean",
        "array": "array",
        "object": "object",
        "null": "null",
    }

    # Reverse mapping for A2A -> JSON Schema
    _A2A_TYPE_TO_JSON_SCHEMA: Dict[str, str] = {
        "string": "string",
        "number": "number",
        "integer": "integer",
        "boolean": "boolean",
        "array": "array",
        "object": "object",
        "null": "null",
    }

    @staticmethod
    def _get_mcp_tool_definition(tool_name: str, server) -> Optional[Dict[str, Any]]:
        """Extract an MCP tool definition from a server object.

        The ``server`` argument can be:
        - A callable that returns a list of tool dicts with ``name``,
          ``description``, ``inputSchema`` (MCP client server).
        - A dict of ``{tool_name: {description, input_schema, ...}}``.
        - A list of tool dicts.
        """
        if callable(server):
            try:
                tools = server()
                if isinstance(tools, list):
                    for t in tools:
                        if isinstance(t, dict) and t.get("name") == tool_name:
                            return t
            except Exception:
                return None

        if isinstance(server, dict):
            # Dict of tool_name -> tool_def
            if tool_name in server:
                tool = server[tool_name]
                if isinstance(tool, dict):
                    return {
                        "name": tool_name,
                        "description": tool.get("description", ""),
                        "inputSchema": tool.get("inputSchema", tool.get("input_schema", {"type": "object", "properties": {}})),
                    }
            # Dict with a 'tools' key
            tools_list = server.get("tools", server.get("tools_list", []))
            if isinstance(tools_list, list):
                for t in tools_list:
                    if isinstance(t, dict) and t.get("name") == tool_name:
                        return t

        if isinstance(server, list):
            for t in server:
                if isinstance(t, dict) and t.get("name") == tool_name:
                    return t

        return None

    @classmethod
    def to_a2a_skill(
        cls,
        tool_name: str,
        server,
    ) -> Dict[str, Any]:
        """Convert an MCP tool definition to A2A skill card format.

        Args:
            tool_name: Name of the MCP tool to convert.
            server: MCP server object (callable, dict, or list of tool defs).

        Returns:
            A2A skill card dict with ``name``, ``description``, ``parameters``,
            and ``source`` metadata.

        Raises:
            ValueError: If the tool is not found on the server.
        """
        tool_def = cls._get_mcp_tool_definition(tool_name, server)
        if tool_def is None:
            raise ValueError(
                f"Tool '{tool_name}' not found on the provided server"
            )

        name = tool_def.get("name", tool_name)
        description = tool_def.get("description", "")
        input_schema = tool_def.get("inputSchema", tool_def.get("input_schema", {}))

        # Convert JSON Schema properties to A2A parameter list
        parameters: List[Dict[str, Any]] = []
        properties = input_schema.get("properties", {})
        required_fields = input_schema.get("required", [])

        for prop_name, prop_schema in properties.items():
            param: Dict[str, Any] = {
                "name": prop_name,
                "description": prop_schema.get("description", ""),
                "type": cls._JSON_SCHEMA_TO_A2A_TYPE.get(
                    prop_schema.get("type", "string"), "string"
                ),
                "required": prop_name in required_fields,
            }
            # Add default value if present
            if "default" in prop_schema:
                param["default"] = prop_schema["default"]
            # Handle enum constraints
            if "enum" in prop_schema:
                param["enum"] = prop_schema["enum"]
            parameters.append(param)

        return {
            "name": name,
            "description": description,
            "parameters": parameters,
            "source": {
                "type": "mcp",
                "tool_name": name,
                "protocol_version": MCP_PROTOCOL_VERSION,
            },
            "type": "skill",
        }

    @staticmethod
    async def call_as_a2a(
        skill_card: Dict[str, Any],
        params: Dict[str, Any],
        handler: Optional[callable] = None,  # type: ignore[valid-type]
    ) -> Dict[str, Any]:
        """Invoke an MCP tool (wrapped as an A2A skill card) remotely.

        This sends an A2A task with the skill parameters. The A2A agent
        receiving this will route it back to the MCP tool.

        Args:
            skill_card: A2A skill card (produced by ``to_a2a_skill``).
            params: Parameters to pass to the MCP tool.
            handler: Optional callable to handle the execution directly.
                If provided, calls ``handler(skill_name, params)`` instead
                of making a remote A2A call.

        Returns:
            Execution result dict with ``status``, ``output``, and
            ``artifacts``.

        Raises:
            RuntimeError: If execution fails.
        """
        skill_name = skill_card.get("name", "unknown")
        source = skill_card.get("source", {})

        if handler is not None:
            # Direct execution via handler callback
            try:
                if asyncio.iscoroutinefunction(handler):
                    result = await handler(skill_name, params)
                else:
                    result = handler(skill_name, params)
                return {
                    "id": _generate_task_id(),
                    "status": A2ATaskState.COMPLETED,
                    "artifacts": [
                        {
                            "name": "result",
                            "type": "application/json",
                            "content": result if isinstance(result, dict) else {"value": result},
                        }
                    ],
                }
            except Exception as exc:
                return {
                    "id": _generate_task_id(),
                    "status": A2ATaskState.FAILED,
                    "error": {
                        "code": -1,
                        "message": str(exc),
                    },
                }

        # Remote execution — construct A2A task message
        task = {
            "id": _generate_task_id(),
            "message": {
                "role": "user",
                "parts": [
                    {
                        "type": "text",
                        "text": f"Execute skill: {skill_name}",
                    },
                    {
                        "type": "parameters",
                        "parameters": params,
                        "skill": skill_name,
                    },
                ],
            },
            "metadata": {
                "source_type": "mcp-bridge",
                "skill_card_name": skill_name,
            },
        }

        # The caller is responsible for sending this to an A2A agent
        # via A2AClient.send_task(). We return the task payload so the
        # caller can route it appropriately.
        return {
            "task": task,
            "skill_card": skill_card,
            "status": A2ATaskState.SUBMITTED,
            "note": "Use A2AClient.send_task() to dispatch this task to an A2A agent",
        }

    @staticmethod
    def a2a_skill_to_mcp_tool(skill_card: Dict[str, Any]) -> Dict[str, Any]:
        """Convert an A2A skill card back into an MCP tool definition.

        This is the reverse of ``to_a2a_skill()``.

        Args:
            skill_card: A2A skill card dict.

        Returns:
            MCP tool definition dict with ``name``, ``description``,
            ``inputSchema``.
        """
        name = skill_card.get("name", "unknown")
        description = skill_card.get("description", "")
        parameters = skill_card.get("parameters", [])

        properties: Dict[str, Any] = {}
        required: List[str] = []

        for param in parameters:
            prop_name = param.get("name", "param")
            prop_schema: Dict[str, Any] = {
                "type": param.get("type", "string"),
                "description": param.get("description", ""),
            }
            if "default" in param:
                prop_schema["default"] = param["default"]
            if "enum" in param:
                prop_schema["enum"] = param["enum"]
            properties[prop_name] = prop_schema
            if param.get("required", False):
                required.append(prop_name)

        return {
            "name": name,
            "description": description,
            "inputSchema": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        }


# ---------------------------------------------------------------------------
# A2AAgentAdapter — wraps an A2A agent as MCP tools
# ---------------------------------------------------------------------------

class A2AAgentAdapter:
    """Wraps an A2A agent as MCP-callable tools.

    Given an Agent Card (from an A2A agent), this adapter converts each
    skill into an MCP tool definition that can be registered with an MCP
    client. When the MCP tool is invoked, the adapter sends an A2A task
    to the agent and returns the result.
    """

    def __init__(self, agent_url: Optional[str] = None):
        self._agent_url = agent_url
        self._client = A2AClient()
        self._agent_card: Optional[Dict[str, Any]] = None

    async def fetch_agent_card(self, agent_url: Optional[str] = None) -> Dict[str, Any]:
        """Fetch and cache the Agent Card from an A2A agent.

        Args:
            agent_url: Override the agent URL set at construction time.

        Returns:
            The Agent Card dict.
        """
        url = agent_url or self._agent_url
        if not url:
            raise ValueError("No agent URL provided")
        self._agent_card = await self._client.get_agent_card(url)
        self._agent_url = url
        return self._agent_card

    def set_agent_card(self, agent_card: Dict[str, Any]) -> None:
        """Set the Agent Card directly (if already fetched externally)."""
        self._agent_card = agent_card

    def to_mcp_tools(self, agent_card: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Convert A2A agent skills to MCP tool definitions.

        Args:
            agent_card: The Agent Card from the A2A agent. If not provided,
                uses the cached card from a previous ``fetch_agent_card()``.

        Returns:
            A list of MCP tool definition dicts, one per skill.

        Raises:
            ValueError: If no agent card is available.
        """
        card = agent_card or self._agent_card
        if card is None:
            raise ValueError(
                "No Agent Card available. Call fetch_agent_card() or "
                "set_agent_card() first."
            )

        skills = card.get("skills", [])
        if not skills:
            logger.warning("Agent Card has no skills defined")

        mcp_tools: List[Dict[str, Any]] = []
        for skill in skills:
            if isinstance(skill, dict):
                mcp_tool = MCPToolAdapter.a2a_skill_to_mcp_tool(skill)
                # Add agent routing metadata
                mcp_tool["_a2a_agent_url"] = self._agent_url or card.get("url", "")
                mcp_tool["_a2a_skill_name"] = skill.get("name", "")
                mcp_tools.append(mcp_tool)

        return mcp_tools

    async def call_as_mcp(
        self,
        tool_name: str,
        args: Dict[str, Any],
        agent_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Invoke an A2A agent task via MCP tool call semantics.

        This sends an A2A task to the agent with the given tool/args
        and returns the result in MCP-compatible format.

        Args:
            tool_name: The name of the A2A skill (mapped to MCP tool name).
            args: Parameters for the A2A task.
            agent_url: Override the agent URL.

        Returns:
            MCP-compatible result dict with ``content`` list.

        Raises:
            RuntimeError: If the A2A task fails.
            ValueError: If the agent card has not been loaded.
        """
        url = agent_url or self._agent_url
        if not url:
            raise ValueError("No agent URL available")

        # Build an A2A task for this skill
        task = {
            "id": _generate_task_id(),
            "message": {
                "role": "user",
                "parts": [
                    {
                        "type": "text",
                        "text": f"Execute skill: {tool_name}",
                    },
                    {
                        "type": "parameters",
                        "parameters": args,
                        "skill": tool_name,
                    },
                ],
            },
            "metadata": {
                "source_type": "mcp-bridge",
                "a2a_agent_url": url,
                "tool_name": tool_name,
            },
        }

        # Send to A2A agent
        result = await self._client.send_task(url, task)

        # Poll for completion if task is still working
        max_polls = 30
        poll_count = 0
        task_id = result.get("id", task["id"])
        status = result.get("status", A2ATaskState.SUBMITTED)

        while status in (A2ATaskState.SUBMITTED, A2ATaskState.WORKING):
            if poll_count >= max_polls:
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Task {task_id} is still {status}. Use get_task_status() to check later.",
                        }
                    ],
                    "isError": False,
                    "task_id": task_id,
                }
            await asyncio.sleep(0.5)
            status_response = await self._client.get_task_status(task_id, url)
            status = status_response.get("status", A2ATaskState.FAILED)
            result = status_response
            poll_count += 1

        if status == A2ATaskState.FAILED:
            error_info = result.get("error", {})
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"A2A task failed: {error_info.get('message', 'Unknown error')}",
                    }
                ],
                "isError": True,
            }

        if status == A2ATaskState.CANCELED:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"A2A task {task_id} was canceled",
                    }
                ],
                "isError": True,
            }

        # Extract artifacts into MCP content format
        artifacts = result.get("artifacts", [])
        content: List[Dict[str, Any]] = []

        for artifact in artifacts:
            art_type = artifact.get("type", "text")
            art_content = artifact.get("content", "")

            if art_type == "text" or art_type.startswith("text/"):
                content.append({
                    "type": "text",
                    "text": str(art_content) if not isinstance(art_content, str) else art_content,
                })
            elif art_type == "application/json" or art_type.endswith("+json"):
                content.append({
                    "type": "text",
                    "text": json.dumps(art_content, indent=2, default=str),
                })
            else:
                content.append({
                    "type": "text",
                    "text": f"[{art_type}]: {json.dumps(art_content, default=str)}",
                })

        return {
            "content": content,
            "isError": False,
            "task_id": task_id,
        }


# ---------------------------------------------------------------------------
# OpenAPIAdapter — converts OpenAPI specs to MCP tools
# ---------------------------------------------------------------------------

class OpenAPIAdapter:
    """Converts OpenAPI 3.x specifications into MCP tool definitions.

    Each HTTP endpoint in the spec becomes an MCP tool. Path parameters,
    query parameters, request body, and headers are mapped to the tool's
    input schema.

    Supports loading specs from:
    - A URL (e.g. ``https://api.example.com/openapi.json``)
    - A local file path
    - A raw dict
    """

    # HTTP methods that are converted to MCP tools
    _SUPPORTED_METHODS = frozenset({"get", "post", "put", "patch", "delete"})

    def __init__(self, spec_url_or_dict: Optional[Union[str, Dict[str, Any]]] = None):
        self._spec: Optional[Dict[str, Any]] = None
        self._tools_cache: Optional[List[Dict[str, Any]]] = None
        if spec_url_or_dict is not None:
            self._spec = self._resolve_spec(spec_url_or_dict)

    def from_openapi_spec(self, spec_url_or_dict: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Parse an OpenAPI 3.x spec from a URL, file path, or dict.

        Args:
            spec_url_or_dict: Either:
                - A string URL pointing to a JSON/YAML OpenAPI spec
                - A string local file path
                - A dict containing the parsed spec

        Returns:
            The parsed OpenAPI spec dict.

        Raises:
            ValueError: If the spec cannot be loaded or is invalid.
            FileNotFoundError: If a local file path does not exist.
        """
        self._spec = self._resolve_spec(spec_url_or_dict)
        self._tools_cache = None  # Invalidate cache
        self._validate_spec()
        return self._spec

    def _resolve_spec(self, spec_url_or_dict: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Resolve a spec URL/file/dict into a parsed dict."""
        if isinstance(spec_url_or_dict, dict):
            return spec_url_or_dict

        source = str(spec_url_or_dict)

        # Check if it's a local file
        if os.path.exists(source):
            return self._load_spec_file(source)

        # Check if it's a URL
        parsed = urlparse(source)
        if parsed.scheme in ("http", "https"):
            return self._load_spec_url(source)

        # Maybe it's a file that doesn't exist yet — try as path
        if "/" in source or "\\" in source or Path(source).suffix:
            raise FileNotFoundError(f"Spec file not found: {source}")

        raise ValueError(
            f"Cannot resolve spec source: {source}. "
            f"Provide a URL, file path, or parsed dict."
        )

    def _load_spec_file(self, path: str) -> Dict[str, Any]:
        """Load an OpenAPI spec from a local file (JSON or YAML)."""
        p = Path(path)
        raw = p.read_text(encoding="utf-8")

        if p.suffix in (".yaml", ".yml"):
            # Try to import yaml; fallback to JSON
            try:
                import yaml as _yaml
                spec = _yaml.safe_load(raw)
                if isinstance(spec, dict):
                    return spec
            except ImportError:
                pass

        return json.loads(raw)

    def _load_spec_url(self, url: str) -> Dict[str, Any]:
        """Load an OpenAPI spec from a URL."""
        import urllib.request

        req = urllib.request.Request(
            url,
            headers={
                "Accept": "application/json, application/yaml, text/yaml",
                "User-Agent": "Xavani-OpenAPIAdapter/1.0",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            content_type = resp.headers.get("Content-Type", "")

        if "yaml" in content_type or url.endswith((".yaml", ".yml")):
            try:
                import yaml as _yaml
                spec = _yaml.safe_load(raw)
                if isinstance(spec, dict):
                    return spec
            except ImportError:
                pass

        return json.loads(raw)

    def _validate_spec(self) -> None:
        """Validate that the spec has the required OpenAPI structure."""
        if not self._spec:
            raise ValueError("No spec loaded")
        if "openapi" not in self._spec and "swagger" not in self._spec:
            raise ValueError(
                "Not a valid OpenAPI spec: missing 'openapi' or 'swagger' version field"
            )
        if "paths" not in self._spec:
            raise ValueError("Not a valid OpenAPI spec: missing 'paths' field")

    def to_mcp_tools(
        self,
        spec: Optional[Dict[str, Any]] = None,
        *,
        base_url_override: Optional[str] = None,
        include_paths: Optional[List[str]] = None,
        exclude_paths: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Generate MCP tool definitions from the OpenAPI spec.

        Each endpoint becomes an MCP tool with:
        - ``name``: Method + sanitized path (e.g. ``get_users_id``)
        - ``description``: From the operation summary/description
        - ``inputSchema``: Parameters + request body mapped to JSON Schema

        Args:
            spec: The OpenAPI spec dict (uses cached spec if not provided).
            base_url_override: Override the base URL from the spec's
                ``servers`` or ``host`` field.
            include_paths: If set, only generate tools for these path
                patterns (supports ``*`` glob-like matching).
            exclude_paths: If set, exclude tools for these path patterns.

        Returns:
            List of MCP tool definition dicts.
        """
        spec_data = spec or self._spec
        if spec_data is None:
            raise ValueError(
                "No spec available. Call from_openapi_spec() first or pass a spec dict."
            )

        base_url = base_url_override or self._resolve_base_url(spec_data)
        paths = spec_data.get("paths", {})

        tools: List[Dict[str, Any]] = []

        for path, path_item in paths.items():
            if not isinstance(path_item, dict):
                continue

            # Apply path filters
            if include_paths and not self._path_matches_any(path, include_paths):
                continue
            if exclude_paths and self._path_matches_any(path, exclude_paths):
                continue

            # Shared path-level parameters
            path_parameters = path_item.get("parameters", [])

            for method in self._SUPPORTED_METHODS:
                operation = path_item.get(method)
                if not isinstance(operation, dict):
                    continue

                tool = self._operation_to_mcp_tool(
                    method=method,
                    path=path,
                    operation=operation,
                    path_parameters=path_parameters,
                    base_url=base_url,
                )
                tools.append(tool)

        self._tools_cache = tools
        return tools

    def _resolve_base_url(self, spec: Dict[str, Any]) -> str:
        """Extract the base URL from the OpenAPI spec."""
        # OpenAPI 3.x: servers[0].url
        servers = spec.get("servers", [])
        if servers and isinstance(servers, list):
            first = servers[0]
            if isinstance(first, dict):
                url = first.get("url", "")
                if url:
                    return url.rstrip("/") + "/"

        # Swagger 2.0: host + basePath + schemes
        host = spec.get("host", "")
        base_path = spec.get("basePath", "")
        schemes_list = spec.get("schemes", ["https"])
        scheme = schemes_list[0] if schemes_list else "https"
        if host:
            return f"{scheme}://{host}{base_path}/"

        return "http://localhost/"

    def _operation_to_mcp_tool(
        self,
        method: str,
        path: str,
        operation: Dict[str, Any],
        path_parameters: List[Dict[str, Any]],
        base_url: str,
    ) -> Dict[str, Any]:
        """Convert a single OpenAPI operation to an MCP tool definition."""
        # Generate a clean tool name
        operation_id = operation.get("operationId", "")
        if operation_id:
            tool_name = self._sanitize_name(operation_id)
        else:
            tool_name = f"{method}_{self._path_to_name(path)}"

        summary = operation.get("summary", "")
        description = operation.get("description", summary)

        # Collect all parameters (path + operation-level)
        all_params: List[Dict[str, Any]] = list(path_parameters)
        op_params = operation.get("parameters", [])
        if isinstance(op_params, list):
            all_params.extend(op_params)

        # Build JSON Schema input
        properties: Dict[str, Any] = {}
        required_params: List[str] = []

        for param in all_params:
            if not isinstance(param, dict):
                continue
            param_name = param.get("name", "param")
            param_in = param.get("in", "query")
            param_schema = param.get("schema", {})
            if not param_schema:
                # Fallback to inline type
                param_type = param.get("type", "string")
                param_schema = {"type": param_type}

            prop: Dict[str, Any] = {
                "type": param_schema.get("type", "string"),
                "description": param.get("description", ""),
                "x-in": param_in,  # Track where this param goes
            }

            if "default" in param_schema:
                prop["default"] = param_schema["default"]
            if "enum" in param_schema:
                prop["enum"] = param_schema["enum"]
            if param.get("required", False):
                required_params.append(param_name)

            properties[param_name] = prop

        # Handle request body
        request_body = operation.get("requestBody")
        if isinstance(request_body, dict):
            content = request_body.get("content", {})
            content_props: Dict[str, Any] = {}
            for media_type, media_type_obj in content.items():
                if isinstance(media_type_obj, dict):
                    media_schema = media_type_obj.get("schema", {})
                    content_props[media_type] = media_schema

            if content_props:
                properties["request_body"] = {
                    "type": "object",
                    "description": request_body.get("description", "Request body"),
                    "x-in": "body",
                    "x-content-types": list(content_props.keys()),
                    "properties": {},
                }
                # Flatten single-content schemas into request_body properties
                if len(content_props) == 1:
                    single_schema = list(content_props.values())[0]
                    if isinstance(single_schema, dict):
                        properties["request_body"] = {
                            "type": single_schema.get("type", "object"),
                            "description": request_body.get("description", "Request body"),
                            "x-in": "body",
                            "x-content-types": list(content_props.keys()),
                            "properties": single_schema.get("properties", {}),
                        }
                        if single_schema.get("required"):
                            properties["request_body"]["required"] = single_schema["required"]
                else:
                    # Multiple content types — keep as variant
                    properties["request_body"]["x-variants"] = content_props

            if request_body.get("required", False):
                required_params.append("request_body")

        # Build description with URL info
        full_description = (
            f"[{method.upper()}] {base_url}{path.lstrip('/')}\n\n{description}"
        ).strip()

        return {
            "name": tool_name,
            "description": full_description,
            "inputSchema": {
                "type": "object",
                "properties": properties,
                "required": required_params,
            },
            "_openapi": {
                "method": method.upper(),
                "path": path,
                "base_url": base_url,
                "operation_id": operation_id,
            },
        }

    @staticmethod
    def _sanitize_name(name: str) -> str:
        """Sanitize a string for use as an MCP tool name."""
        # Replace non-alphanumeric characters with underscores
        sanitized = ""
        for char in name:
            if char.isalnum() or char == "_":
                sanitized += char
            elif char in (" ", "-", "."):
                sanitized += "_"
        # Remove leading/trailing underscores
        sanitized = sanitized.strip("_")
        # Ensure it starts with a letter
        if sanitized and not sanitized[0].isalpha():
            sanitized = "api_" + sanitized
        return sanitized.lower() if sanitized else "unnamed"

    @staticmethod
    def _path_to_name(path: str) -> str:
        """Convert a URL path like /users/{id} to a name like users_id."""
        parts = path.strip("/").split("/")
        name_parts = []
        for part in parts:
            if part.startswith("{") and part.endswith("}"):
                name_parts.append(part[1:-1])
            else:
                name_parts.append(part)
        return "_".join(name_parts).replace("-", "_").lower()

    @staticmethod
    def _path_matches_any(path: str, patterns: List[str]) -> bool:
        """Check if a path matches any pattern (supports trailing wildcard)."""
        for pattern in patterns:
            if pattern.endswith("*"):
                if path.startswith(pattern.rstrip("*")):
                    return True
            elif path == pattern:
                return True
        return False

    def get_tools(self) -> List[Dict[str, Any]]:
        """Return the last generated tool set, or generate if not cached."""
        if self._tools_cache is not None:
            return self._tools_cache
        if self._spec is not None:
            return self.to_mcp_tools()
        return []

    def make_mcp_call(
        self,
        tool_name: str,
        args: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Prepare an MCP tool call dict for a converted OpenAPI endpoint.

        This returns a dict that can be forwarded to an MCP client or
        used to make the actual HTTP request via :meth:`execute_mcp_call`.

        Args:
            tool_name: The MCP tool name (generated by ``to_mcp_tools()``).
            args: Tool arguments (matching the ``inputSchema``).

        Returns:
            Prepared call dict with ``url``, ``method``, ``headers``,
            ``query_params``, ``body``, ``path_params``.
        """
        tools = self.get_tools()
        tool_def = None
        for t in tools:
            if t["name"] == tool_name:
                tool_def = t
                break

        if tool_def is None:
            raise ValueError(f"Tool '{tool_name}' not found in generated tools")

        openapi_info = tool_def.get("_openapi", {})
        base_url = openapi_info.get("base_url", "")
        api_path = openapi_info.get("path", "")
        http_method = openapi_info.get("method", "GET").lower()

        # Build URL with path parameters
        url = urljoin(base_url, api_path.lstrip("/"))

        # Separate args by location
        path_params: Dict[str, str] = {}
        query_params: Dict[str, str] = {}
        headers: Dict[str, str] = {}
        body: Optional[Dict[str, Any]] = None
        content_type: str = "application/json"

        schema = tool_def.get("inputSchema", {})
        properties = schema.get("properties", {})

        for prop_name, prop_schema in properties.items():
            if prop_name not in args:
                continue

            param_in = prop_schema.get("x-in", "query")
            value = args[prop_name]

            if prop_name == "request_body":
                body = value
                ct_list = prop_schema.get("x-content-types", ["application/json"])
                content_type = ct_list[0] if ct_list else "application/json"
            elif param_in == "path":
                path_params[prop_name] = str(value)
            elif param_in == "header":
                headers[prop_name] = str(value)
            elif param_in == "query":
                query_params[prop_name] = value
            elif param_in == "body":
                body = value
            else:
                query_params[prop_name] = value

        # Substitute path parameters
        for pname, pval in path_params.items():
            url = url.replace(f"{{{pname}}}", pval)

        return {
            "url": url,
            "method": http_method,
            "headers": headers,
            "query_params": query_params,
            "body": body,
            "content_type": content_type,
        }

    async def execute_mcp_call(
        self,
        tool_name: str,
        args: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute an MCP tool call against the real OpenAPI endpoint.

        This makes the actual HTTP request to the converted API endpoint
        and returns the result in MCP-compatible format.

        Args:
            tool_name: The MCP tool name.
            args: Tool arguments.

        Returns:
            MCP tool call result dict.
        """
        call = self.make_mcp_call(tool_name, args)
        return await self._execute_http(call)

    async def _execute_http(self, call: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the HTTP request described by the call dict."""
        import urllib.request
        import urllib.parse

        url = call["url"]
        method = call["method"].upper()
        headers = dict(call.get("headers", {}))
        query_params = call.get("query_params", {})
        body = call.get("body")
        content_type = call.get("content_type", "application/json")

        # Append query params to URL
        if query_params:
            parsed = urlparse(url)
            existing_params = urllib.parse.parse_qs(parsed.query)
            existing_params.update(
                {k: [str(v)] if not isinstance(v, list) else [str(x) for x in v]
                 for k, v in query_params.items()}
            )
            new_query = urllib.parse.urlencode(existing_params, doseq=True)
            url = urlparse(url)._replace(query=new_query).geturl()

        # Build the request
        headers.setdefault("User-Agent", "Xavani-OpenAPIAdapter/1.0")
        headers.setdefault("Accept", "application/json")

        data_bytes: Optional[bytes] = None
        if body is not None:
            if content_type == "application/json":
                data_bytes = json.dumps(body, default=str).encode("utf-8")
                headers["Content-Type"] = "application/json"
            elif content_type == "application/x-www-form-urlencoded":
                if isinstance(body, dict):
                    data_bytes = urllib.parse.urlencode(body).encode("utf-8")
                else:
                    data_bytes = str(body).encode("utf-8")
                headers["Content-Type"] = content_type
            else:
                data_bytes = json.dumps(body, default=str).encode("utf-8")
                headers["Content-Type"] = content_type

        req = urllib.request.Request(
            url,
            data=data_bytes,
            headers=headers,
            method=method,
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                resp_body = resp.read().decode("utf-8")
                status = resp.status

                result_content: Dict[str, Any]
                try:
                    result_content = json.loads(resp_body)
                except (json.JSONDecodeError, ValueError):
                    result_content = {"body": resp_body}

                return {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(
                                {
                                    "status": status,
                                    "data": result_content,
                                },
                                indent=2,
                                default=str,
                            ),
                        }
                    ],
                    "isError": status >= 400,
                    "_http_status": status,
                }

        except Exception as exc:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"HTTP request failed: {exc}",
                    }
                ],
                "isError": True,
            }


# ---------------------------------------------------------------------------
# Agent Registry (Bridge-side)
# ---------------------------------------------------------------------------

class AgentRegistry:
    """Manages registered A2A agents known to the bridge.

    Agents are persisted to a JSON file in ``~/.xavani/data/bridge/``.
    """

    def __init__(self, storage_path: Path = BRIDGE_AGENTS_FILE):
        self._storage_path = storage_path
        self._agents: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        """Load registered agents from disk."""
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        if self._storage_path.exists():
            try:
                raw = self._storage_path.read_text(encoding="utf-8")
                self._agents = json.loads(raw)
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Failed to load agent registry: %s", exc)
                self._agents = {}

    def _save(self) -> None:
        """Save registered agents to disk."""
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._storage_path.with_suffix(".tmp")
        try:
            tmp.write_text(
                json.dumps(self._agents, indent=2, default=str),
                encoding="utf-8",
            )
            tmp.replace(self._storage_path)
        except Exception as exc:
            logger.error("Failed to save agent registry: %s", exc)

    def register(self, agent_id: str, agent_info: Dict[str, Any]) -> Dict[str, Any]:
        """Register or update an A2A agent in the bridge.

        Args:
            agent_id: Unique identifier for the agent.
            agent_info: Agent info dict with at minimum a ``url`` key.
                Also supports ``name``, ``description``, ``skills``, etc.

        Returns:
            The full agent info as stored.
        """
        agent_info["agent_id"] = agent_id
        agent_info.setdefault("registered_at", datetime.now(timezone.utc).isoformat())
        agent_info["updated_at"] = datetime.now(timezone.utc).isoformat()
        agent_info.setdefault("status", "active")
        self._agents[agent_id] = agent_info
        self._save()
        return agent_info

    def unregister(self, agent_id: str) -> bool:
        """Remove an agent from the registry.

        Returns True if the agent was found and removed.
        """
        if agent_id in self._agents:
            del self._agents[agent_id]
            self._save()
            return True
        return False

    def get(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get a registered agent by ID."""
        return self._agents.get(agent_id)

    def list_agents(self) -> List[Dict[str, Any]]:
        """Return all registered agents."""
        return list(self._agents.values())

    def get_by_url(self, url: str) -> Optional[Dict[str, Any]]:
        """Find an agent by its URL."""
        for agent in self._agents.values():
            if agent.get("url") == url:
                return agent
        return None

    def update_status(self, agent_id: str, status: str) -> bool:
        """Update the health status of a registered agent."""
        if agent_id in self._agents:
            self._agents[agent_id]["status"] = status
            self._agents[agent_id]["updated_at"] = datetime.now(timezone.utc).isoformat()
            self._save()
            return True
        return False


# ---------------------------------------------------------------------------
# BridgeServer — FastAPI server for the protocol translation layer
# ---------------------------------------------------------------------------

class BridgeServer:
    """FastAPI server that serves as the MCP ↔ A2A ↔ OpenAPI translation layer.

    Provides REST endpoints for:
    - POST /bridge/mcp-to-a2a — Translate an MCP call into an A2A task
    - POST /bridge/a2a-to-mcp — Translate an A2A request into an MCP call
    - POST /bridge/openapi/convert — Convert an OpenAPI spec to MCP tools
    - GET /bridge/agents — List registered agents
    - GET /bridge/status — Bridge health check

    The server runs as part of the Xavani gateway on a configurable port.
    """

    def __init__(
        self,
        host: str = DEFAULT_BRIDGE_HOST,
        port: int = DEFAULT_BRIDGE_PORT,
        agent_registry: Optional[AgentRegistry] = None,
    ):
        self.host = host
        self.port = port
        self.agent_registry = agent_registry or AgentRegistry()
        self.a2a_client = A2AClient()
        self.openapi_adapter = OpenAPIAdapter()
        self._app: Optional[Any] = None
        self._server: Optional[Any] = None
        self._started_at: Optional[str] = None

    @property
    def app(self):
        """Lazy-build the FastAPI application."""
        if self._app is None:
            self._app = self._build_app()
        return self._app

    def _build_app(self):
        """Construct the FastAPI application with all bridge endpoints."""
        try:
            from fastapi import FastAPI, HTTPException, Request
            from fastapi.responses import JSONResponse
        except ImportError:
            raise ImportError(
                "FastAPI is required for the BridgeServer. "
                "Install with: pip install 'xavani-agent[web]'"
            )

        app = FastAPI(
            title="Xavani Protocol Bridge",
            version="0.1.0",
            description="MCP ↔ A2A ↔ OpenAPI protocol translation layer",
        )

        # ── Middleware: timing + error handling ────────────────────

        @app.middleware("http")
        async def _add_timing_header(request: Request, call_next):
            start = time.time()
            try:
                response = await call_next(request)
                response.headers["X-Bridge-Timing-Ms"] = f"{(time.time() - start) * 1000:.1f}"
                return response
            except Exception as exc:
                logger.exception("Bridge request failed: %s", exc)
                return JSONResponse(
                    status_code=500,
                    content={"error": str(exc), "success": False},
                )

        # ── POST /bridge/mcp-to-a2a ───────────────────────────────

        @app.post("/bridge/mcp-to-a2a")
        async def mcp_to_a2a(request: Request):
            """Translate an MCP tool call into an A2A task.

            Request body:
            ```json
            {
                "tool_name": "my_mcp_tool",
                "arguments": {"key": "value"},
                "agent_url": "http://a2a-agent:8082/a2a",
                "mcp_server": "filesystem"
            }
            ```

            The bridge looks up the MCP tool definition, converts it to
            an A2A skill card, then sends an A2A task to the target agent.
            """
            body = await request.json()
            tool_name = body.get("tool_name", "")
            arguments = body.get("arguments", {})
            agent_url = body.get("agent_url", "")
            mcp_server = body.get("mcp_server", "")

            if not tool_name:
                raise HTTPException(status_code=400, detail="tool_name is required")
            if not agent_url:
                raise HTTPException(status_code=400, detail="agent_url is required")

            # Build A2A task from the MCP call
            skill_card = MCPToolAdapter.to_a2a_skill(tool_name, {})
            # Override name to match the requested tool
            skill_card["name"] = tool_name

            # Send via A2AClient
            task = {
                "id": _generate_task_id(),
                "message": {
                    "role": "user",
                    "parts": [
                        {
                            "type": "text",
                            "text": f"Execute MCP tool: {tool_name}",
                        },
                        {
                            "type": "parameters",
                            "parameters": arguments,
                            "skill": tool_name,
                        },
                    ],
                },
                "metadata": {
                    "source_type": "mcp-bridge",
                    "original_tool_name": tool_name,
                    "mcp_server": mcp_server,
                },
            }

            try:
                result = await self.a2a_client.send_task(agent_url, task)
                return {
                    "success": True,
                    "task_id": result.get("id", task["id"]),
                    "status": result.get("status", "submitted"),
                    "result": result,
                }
            except Exception as exc:
                return {
                    "success": False,
                    "error": str(exc),
                    "task_id": task["id"],
                }

        # ── POST /bridge/a2a-to-mcp ───────────────────────────────

        @app.post("/bridge/a2a-to-mcp")
        async def a2a_to_mcp(request: Request):
            """Translate an A2A request into an MCP tool call.

            Request body:
            ```json
            {
                "agent_card": {"name": "...", "skills": [...]},
                "skill_name": "my_skill",
                "parameters": {"key": "value"},
                "mcp_server_url": "http://localhost:8080/mcp"
            }
            ```

            The bridge converts the A2A skill to an MCP tool definition,
            then either forwards the call to an MCP server or returns
            the tool definition for the caller to invoke.
            """
            body = await request.json()
            agent_card = body.get("agent_card", {})
            skill_name = body.get("skill_name", "")
            parameters = body.get("parameters", {})
            mcp_url = body.get("mcp_server_url", "")

            if not agent_card:
                raise HTTPException(status_code=400, detail="agent_card is required")
            if not skill_name:
                raise HTTPException(status_code=400, detail="skill_name is required")

            # Find the skill in the agent card
            skills = agent_card.get("skills", [])
            skill_card = None
            for s in skills:
                if isinstance(s, dict) and s.get("name") == skill_name:
                    skill_card = s
                    break

            if skill_card is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"Skill '{skill_name}' not found in agent card",
                )

            # Convert to MCP tool
            mcp_tool = MCPToolAdapter.a2a_skill_to_mcp_tool(skill_card)

            result = {
                "success": True,
                "mcp_tool": mcp_tool,
                "converted_parameters": parameters,
            }

            # If an MCP server URL is provided, forward the call
            if mcp_url:
                try:
                    mcp_payload = {
                        "jsonrpc": "2.0",
                        "method": "tools/call",
                        "params": {
                            "name": skill_name,
                            "arguments": parameters,
                        },
                        "id": str(uuid.uuid4()),
                    }
                    mcp_result = await self.a2a_client._request(
                        "POST", mcp_url, json_data=mcp_payload
                    )
                    result["mcp_result"] = mcp_result
                except Exception as exc:
                    result["mcp_error"] = str(exc)
                    result["mcp_forwarded"] = False

            return result

        # ── POST /bridge/openapi/convert ──────────────────────────

        @app.post("/bridge/openapi/convert")
        async def openapi_convert(request: Request):
            """Convert an OpenAPI spec to MCP tool definitions.

            Request body:
            ```json
            {
                "spec_url": "https://api.example.com/openapi.json",
                "spec": {...},  // OR inline spec dict
                "base_url_override": "https://custom.example.com",
                "include_paths": ["/users/*"],
                "exclude_paths": ["/internal/*"]
            }
            ```
            """
            body = await request.json()
            spec_url = body.get("spec_url", "")
            spec_dict = body.get("spec", None)
            base_url_override = body.get("base_url_override")
            include_paths = body.get("include_paths")
            exclude_paths = body.get("exclude_paths")

            adapter = OpenAPIAdapter()

            if spec_url:
                adapter.from_openapi_spec(spec_url)
            elif spec_dict:
                adapter.from_openapi_spec(spec_dict)
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Either 'spec_url' or 'spec' is required",
                )

            tools = adapter.to_mcp_tools(
                base_url_override=base_url_override,
                include_paths=include_paths,
                exclude_paths=exclude_paths,
            )

            spec_info = {}
            if adapter._spec is not None:
                spec_info = {
                    "title": adapter._spec.get("info", {}).get("title", "Unknown"),
                    "version": adapter._spec.get("info", {}).get("version", "Unknown"),
                    "endpoints": len(adapter._spec.get("paths", {})),
                }

            return {
                "success": True,
                "tool_count": len(tools),
                "tools": tools,
                "spec_info": spec_info,
            }

        # ── GET /bridge/agents ────────────────────────────────────

        @app.get("/bridge/agents")
        async def list_agents():
            """List all registered A2A agents known to the bridge."""
            agents = self.agent_registry.list_agents()
            return {
                "success": True,
                "agent_count": len(agents),
                "agents": agents,
            }

        @app.post("/bridge/agents/register")
        async def register_agent(request: Request):
            """Register an A2A agent with the bridge."""
            body = await request.json()
            agent_id = body.get("agent_id", str(uuid.uuid4()))
            agent_info = body.get("info", {})

            if not agent_info.get("url"):
                raise HTTPException(status_code=400, detail="Agent 'url' is required in info")

            registered = self.agent_registry.register(agent_id, agent_info)
            return {"success": True, "agent": registered}

        @app.delete("/bridge/agents/{agent_id}")
        async def unregister_agent(agent_id: str):
            """Remove an agent from the bridge registry."""
            removed = self.agent_registry.unregister(agent_id)
            if not removed:
                raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
            return {"success": True, "message": f"Agent '{agent_id}' unregistered"}

        # ── GET /bridge/status ────────────────────────────────────

        @app.get("/bridge/status")
        async def bridge_status():
            """Bridge health check endpoint."""
            now = datetime.now(timezone.utc).isoformat()
            return {
                "success": True,
                "status": "healthy",
                "started_at": self._started_at or now,
                "now": now,
                "version": "0.1.0",
                "agent_count": len(self.agent_registry.list_agents()),
                "protocols": {
                    "mcp": MCP_PROTOCOL_VERSION,
                    "a2a": A2A_PROTOCOL_VERSION,
                },
                "uptime_seconds": (
                    (datetime.now(timezone.utc) - datetime.fromisoformat(self._started_at)).total_seconds()
                    if self._started_at else 0
                ),
            }

        # ── Health check at root ──────────────────────────────────

        @app.get("/health")
        async def health():
            return {"status": "ok", "service": "xavani-protocol-bridge"}

        return app

    async def start(self):
        """Start the bridge server (asyncio-friendly)."""
        try:
            import uvicorn
        except ImportError:
            raise ImportError(
                "uvicorn is required to run the BridgeServer. "
                "Install with: pip install 'xavani-agent[web]'"
            )

        self._started_at = datetime.now(timezone.utc).isoformat()
        config = uvicorn.Config(
            app=self.app,
            host=self.host,
            port=self.port,
            log_level="info",
        )
        self._server = uvicorn.Server(config)
        logger.info(
            "Bridge server starting on http://%s:%s", self.host, self.port
        )
        await self._server.serve()

    def run_forever(self):
        """Start the bridge server synchronously (blocking)."""
        import uvicorn
        self._started_at = datetime.now(timezone.utc).isoformat()
        logger.info(
            "Bridge server starting on http://%s:%s", self.host, self.port
        )
        uvicorn.run(
            self.app,
            host=self.host,
            port=self.port,
            log_level="info",
        )


# ---------------------------------------------------------------------------
# Internal Helpers
# ---------------------------------------------------------------------------

class _SessionManager:
    """Simple session manager for HTTP connections.

    Provides connection reuse when using httpx/aiohttp, with a
    urllib.request fallback for zero-dependency operation.
    """

    def __init__(self):
        self._session = None


def _generate_task_id() -> str:
    """Generate a unique A2A task ID."""
    return f"task_{uuid.uuid4().hex[:16]}_{int(time.time())}"


# ---------------------------------------------------------------------------
# Module-level convenience factory
# ---------------------------------------------------------------------------

def create_bridge_server(
    host: str = DEFAULT_BRIDGE_HOST,
    port: int = DEFAULT_BRIDGE_PORT,
) -> BridgeServer:
    """Create and return a configured BridgeServer instance.

    This is the main entry point for starting the protocol bridge.
    """
    return BridgeServer(host=host, port=port)
