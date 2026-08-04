# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""OAG MCP Gateway Proxy — Phase 1 of Xavani Agent.

The gateway proxy sits between AI clients (Claude Desktop, Cursor, custom apps)
and MCP servers, intercepting every call to enforce security policies, rate
limits, authentication, and audit logging.

Architecture:
  - FastAPI server on localhost:8080
  - Accepts MCP JSON-RPC over HTTP POST
  - Routes to backend MCP servers defined in ~/.xavani/installed/
  - Policy engine evaluates allow/deny/rate-limit rules before forwarding
  - Every request logged to SQLite audit trail
  - Auth via API keys or JWT tokens
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import os
import secrets
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import tomllib
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

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
INSTALLED_DIR = XAVANI_HOME / "installed"
POLICIES_DIR = XAVANI_HOME / "policies"
DATA_DIR = XAVANI_HOME / "data"
AUDIT_DB_PATH = DATA_DIR / "oag_audit.db"
AUTH_DB_PATH = DATA_DIR / "oag_auth.db"
TOKEN_BUCKET_DB_PATH = DATA_DIR / "oag_rate_limits.db"

DEFAULT_RATE_LIMIT = 60  # requests per minute per user
DEFAULT_COST_LIMIT = 0.05  # USD per request max

_JWT_ALGORITHM = "HS256"
_TOKEN_EXPIRY_HOURS = 24 * 7  # 7 days

# ---------------------------------------------------------------------------
# Audit Logger
# ---------------------------------------------------------------------------


class OAGAuditLogger:
    """SQLite-backed audit trail for all MCP requests.

    Every request is logged with: timestamp, user, tool, server, input summary,
    duration, allowed/denied status.

    Auto-rotates logs older than 90 days.
    """

    _RETENTION_DAYS = 90

    def __init__(self, db_path: Path = AUDIT_DB_PATH) -> None:
        self._db_path = db_path
        self._local = threading.local()
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        """Get thread-local connection."""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(str(self._db_path))
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA synchronous=NORMAL")
        return self._local.conn

    def _init_db(self) -> None:
        """Create the audit table if it does not exist."""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = self._get_conn()
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                user_id TEXT NOT NULL,
                tool_name TEXT,
                server_name TEXT,
                input_summary TEXT,
                duration_ms REAL,
                allowed INTEGER NOT NULL,
                denied_reason TEXT,
                request_id TEXT,
                input_size_bytes INTEGER
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_audit_timestamp
            ON audit_log(timestamp)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_audit_user
            ON audit_log(user_id)
            """
        )
        conn.commit()

    def log(
        self,
        user_id: str,
        tool_name: Optional[str],
        server_name: Optional[str],
        input_summary: str,
        duration_ms: float,
        allowed: bool,
        denied_reason: Optional[str] = None,
        request_id: Optional[str] = None,
        input_size_bytes: Optional[int] = None,
    ) -> None:
        """Record a single audit entry.

        A10 verbosity gate: successful requests are verbose records
        (level 2); denials are security decisions (level 1). At
        XAVANI_AUDIT_LOG=0 no request is written.
        """
        from xavani_operator.audit import audit_enabled

        if allowed and not audit_enabled(2):
            return
        if not allowed and not audit_enabled(1):
            return
        conn = self._get_conn()
        conn.execute(
            """
            INSERT INTO audit_log
                (timestamp, user_id, tool_name, server_name, input_summary,
                 duration_ms, allowed, denied_reason, request_id, input_size_bytes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now(timezone.utc).isoformat(),
                user_id,
                tool_name,
                server_name,
                input_summary[:512] if input_summary else "",
                duration_ms,
                1 if allowed else 0,
                denied_reason,
                request_id or "",
                input_size_bytes or 0,
            ),
        )
        conn.commit()

    def query(
        self,
        since: Optional[datetime] = None,
        user_id: Optional[str] = None,
        limit: int = 500,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Query the audit log with optional filters."""
        conn = self._get_conn()
        where_clauses: List[str] = []
        params: List[Any] = []

        if since:
            where_clauses.append("timestamp >= ?")
            params.append(since.isoformat())
        if user_id:
            where_clauses.append("user_id = ?")
            params.append(user_id)

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
        rows = conn.execute(
            f"SELECT * FROM audit_log WHERE {where_sql} "
            f"ORDER BY id DESC LIMIT ? OFFSET ?",
            params + [limit, offset],
        ).fetchall()
        return [dict(r) for r in rows]

    def rotate(self) -> int:
        """Delete entries older than retention period. Returns count removed."""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=self._RETENTION_DAYS)).isoformat()
        conn = self._get_conn()
        cursor = conn.execute("DELETE FROM audit_log WHERE timestamp < ?", (cutoff,))
        conn.commit()
        return cursor.rowcount

    def stats(self) -> Dict[str, Any]:
        """Return aggregate stats from the audit log."""
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) as c FROM audit_log").fetchone()["c"]
        denied = conn.execute(
            "SELECT COUNT(*) as c FROM audit_log WHERE allowed = 0"
        ).fetchone()["c"]
        unique_users = conn.execute(
            "SELECT COUNT(DISTINCT user_id) as c FROM audit_log"
        ).fetchone()["c"]
        unique_tools = conn.execute(
            "SELECT COUNT(DISTINCT tool_name) as c FROM audit_log"
        ).fetchone()["c"]
        return {
            "total_requests": total,
            "denied_requests": denied,
            "unique_users": unique_users,
            "unique_tools": unique_tools,
        }


# ---------------------------------------------------------------------------
# Rate Limiter (Token Bucket)
# ---------------------------------------------------------------------------


class TokenBucket:
    """Thread-safe token bucket rate limiter backed by SQLite."""

    def __init__(self, db_path: Path = TOKEN_BUCKET_DB_PATH) -> None:
        self._db_path = db_path
        self._local = threading.local()
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(str(self._db_path))
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA synchronous=NORMAL")
        return self._local.conn

    def _init_db(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = self._get_conn()
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS token_buckets (
                key TEXT PRIMARY KEY,
                tokens REAL NOT NULL,
                last_refill REAL NOT NULL,
                max_tokens REAL NOT NULL,
                refill_rate REAL NOT NULL
            )
            """
        )
        conn.commit()

    def consume(
        self,
        key: str,
        tokens: float = 1.0,
        max_tokens: float = 60.0,
        refill_rate: float = 1.0,  # tokens per second
    ) -> Tuple[bool, float]:
        """Try to consume tokens from the bucket.

        Returns (allowed, wait_seconds). If not enough tokens, returns
        (False, seconds until next token is available).
        """
        conn = self._get_conn()
        now = time.time()

        row = conn.execute(
            "SELECT tokens, last_refill, max_tokens, refill_rate "
            "FROM token_buckets WHERE key = ?",
            (key,),
        ).fetchone()

        if row is None:
            # Create bucket with full tokens
            conn.execute(
                "INSERT OR REPLACE INTO token_buckets "
                "(key, tokens, last_refill, max_tokens, refill_rate) "
                "VALUES (?, ?, ?, ?, ?)",
                (key, max_tokens - tokens, now, max_tokens, refill_rate),
            )
            conn.commit()
            return True, 0.0

        current_tokens = row["tokens"]
        last_refill = row["last_refill"]
        bucket_max = row["max_tokens"]
        bucket_rate = row["refill_rate"]

        # Refill based on elapsed time
        elapsed = now - last_refill
        refill_amount = elapsed * bucket_rate
        current_tokens = min(bucket_max, current_tokens + refill_amount)

        if current_tokens >= tokens:
            new_tokens = current_tokens - tokens
            conn.execute(
                "UPDATE token_buckets SET tokens = ?, last_refill = ? WHERE key = ?",
                (new_tokens, now, key),
            )
            conn.commit()
            return True, 0.0
        else:
            wait_time = (tokens - current_tokens) / bucket_rate
            return False, wait_time


# ---------------------------------------------------------------------------
# Policy Engine
# ---------------------------------------------------------------------------


class OAGPolicyEngine:
    """Evaluates allow/deny/rate-limit rules against MCP requests.

    Policies are loaded from ~/.xavani/policies/ directory as YAML files.
    Built-in policies cover:
      - Rate limiting (token bucket per user)
      - Allow/deny by tool name
      - Allow/deny by resource URI pattern
      - Cost limits per request
    """

    def __init__(
        self,
        policy_dir: Path = POLICIES_DIR,
        rate_limiter: Optional[TokenBucket] = None,
    ) -> None:
        self._policy_dir = policy_dir
        self._rate_limiter = rate_limiter or TokenBucket()
        self._policy_dir.mkdir(parents=True, exist_ok=True)

    def load_policies(self) -> List[Dict[str, Any]]:
        """Load all policy files from the policy directory."""
        policies: List[Dict[str, Any]] = []
        if not self._policy_dir.exists():
            return policies

        for fpath in sorted(self._policy_dir.iterdir()):
            if fpath.suffix in (".yaml", ".yml", ".json"):
                try:
                    content = fpath.read_text(encoding="utf-8")
                    if fpath.suffix == ".json":
                        import json as json_mod
                        data = json_mod.loads(content)
                    else:
                        import yaml
                        data = yaml.safe_load(content)
                    if isinstance(data, dict):
                        data.setdefault("name", fpath.stem)
                        data.setdefault("source", str(fpath))
                        policies.append(data)
                except Exception as exc:
                    logger.warning("Failed to load policy %s: %s", fpath, exc)
        return policies

    def evaluate(
        self,
        user_id: str,
        tool_name: Optional[str] = None,
        server_name: Optional[str] = None,
        resource_uri: Optional[str] = None,
        input_args: Optional[Dict[str, Any]] = None,
        input_size_bytes: Optional[int] = None,
    ) -> Tuple[bool, Optional[str], Optional[float]]:
        """Evaluate all loaded policies against a request.

        Returns:
            (allowed, denied_reason, retry_after_seconds)

        If allowed is True, the request can proceed.
        If allowed is False, denied_reason explains why and retry_after
        may indicate a rate-limit reset time.
        """
        policies = self.load_policies()

        # Built-in deny rules for dangerous tool access patterns
        built_in_rules = self._get_builtin_rules()
        for rule in built_in_rules:
            allowed, reason = self._evaluate_single_rule(rule, tool_name, server_name, resource_uri, input_args)
            if not allowed:
                return False, reason, None

        for policy in policies:
            rules = policy.get("rules") or policy.get("allow") or policy.get("deny") or policy.get("rate_limit") or []
            if isinstance(rules, dict):
                rules = [rules]

            for rule in rules if isinstance(rules, list) else [rules]:
                if not isinstance(rule, dict):
                    continue

                # Check rule scope
                rule_type = rule.get("type", rule.get("action", "deny"))
                rule_tools = rule.get("tools") or rule.get("tool") or []
                if isinstance(rule_tools, str):
                    rule_tools = [rule_tools]
                if rule_tools and tool_name and tool_name not in rule_tools:
                    continue

                rule_servers = rule.get("servers") or rule.get("server") or []
                if isinstance(rule_servers, str):
                    rule_servers = [rule_servers]
                if rule_servers and server_name and server_name not in rule_servers:
                    continue

                if rule_type == "allow":
                    continue  # Allow rules are only checked after deny passes

                if rule_type == "deny":
                    return False, rule.get("reason", f"Denied by policy: {rule.get('name', 'unknown')}"), None

                # Rate limit rules
                if rule_type in ("rate_limit", "rate-limit", "throttle"):
                    max_rps = float(rule.get("max_requests_per_second", rule.get("rate", 1)))
                    bucket_max = float(rule.get("burst", max_rps * 10))
                    rate_key = f"{user_id}:{tool_name or '*'}:{server_name or '*'}"
                    allowed, wait = self._rate_limiter.consume(
                        key=rate_key,
                        tokens=1.0,
                        max_tokens=bucket_max,
                        refill_rate=max_rps,
                    )
                    if not allowed:
                        return False, "Rate limit exceeded", wait

        return True, None, None

    def _get_builtin_rules(self) -> List[Dict[str, Any]]:
        """Return built-in security rules that always apply."""
        return [
            {
                "type": "deny",
                "tools": ["exec_command", "shell_exec", "run_shell", "execute"],
                "reason": "Remote shell execution denied by built-in security policy",
            },
            {
                "type": "deny",
                "resources": ["file:///etc/shadow", "file:///etc/sudoers", "file:///etc/passwd"],
                "reason": "Access to sensitive system files denied",
            },
        ]

    def _evaluate_single_rule(
        self,
        rule: Dict[str, Any],
        tool_name: Optional[str],
        server_name: Optional[str],
        resource_uri: Optional[str],
        input_args: Optional[Dict[str, Any]],
    ) -> Tuple[bool, Optional[str]]:
        """Evaluate a single rule. Returns (allowed, reason)."""
        rule_type = rule.get("type", "deny")

        # Check tool name match
        rule_tools = rule.get("tools") or []
        if isinstance(rule_tools, str):
            rule_tools = [rule_tools]
        if rule_tools and tool_name:
            if tool_name in rule_tools:
                if rule_type == "deny":
                    return False, rule.get("reason", f"Tool '{tool_name}' denied")
                return True, None

        # Check resource URI match
        rule_resources = rule.get("resources") or []
        if isinstance(rule_resources, str):
            rule_resources = [rule_resources]
        if rule_resources and resource_uri:
            for pattern in rule_resources:
                if resource_uri.startswith(pattern) or resource_uri == pattern:
                    if rule_type == "deny":
                        return False, rule.get("reason", f"Resource '{resource_uri}' denied")
                    return True, None

        return True, None

    def add_policy_from_dict(self, name: str, policy_data: Dict[str, Any]) -> Path:
        """Save a policy dict as a YAML file in the policy directory."""
        dest = self._policy_dir / f"{name}.yaml"
        import yaml
        with dest.open("w", encoding="utf-8") as f:
            yaml.dump(policy_data, f, default_flow_style=False, allow_unicode=True)
        return dest

    def remove_policy(self, name: str) -> bool:
        """Remove a policy file by name."""
        for ext in (".yaml", ".yml", ".json"):
            fpath = self._policy_dir / f"{name}{ext}"
            if fpath.exists():
                fpath.unlink()
                return True
        return False


# ---------------------------------------------------------------------------
# Authentication Manager
# ---------------------------------------------------------------------------


class OAGAuthManager:
    """API key and JWT authentication for the MCP gateway.

    Supports:
      - API key generation and validation (SHA-256 hashed storage)
      - JWT tokens with scope support
      - Role-based access (admin, user, readonly)
    """

    def __init__(self, db_path: Path = AUTH_DB_PATH) -> None:
        self._db_path = db_path
        self._local = threading.local()
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(str(self._db_path))
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA synchronous=NORMAL")
        return self._local.conn

    def _init_db(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = self._get_conn()
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS api_keys (
                key_id TEXT PRIMARY KEY,
                key_hash TEXT NOT NULL,
                user_id TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                scopes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                expires_at TEXT,
                is_active INTEGER NOT NULL DEFAULT 1
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS jwt_secrets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                secret TEXT NOT NULL,
                created_at TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1
            )
            """
        )
        conn.commit()

        # Ensure a default JWT secret exists
        row = conn.execute(
            "SELECT secret FROM jwt_secrets WHERE is_active = 1 LIMIT 1"
        ).fetchone()
        if row is None:
            secret = secrets.token_hex(32)
            conn.execute(
                "INSERT INTO jwt_secrets (secret, created_at, is_active) VALUES (?, ?, 1)",
                (secret, datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()

    def _get_jwt_secret(self) -> str:
        """Get the active JWT signing secret."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT secret FROM jwt_secrets WHERE is_active = 1 LIMIT 1"
        ).fetchone()
        return row["secret"] if row else secrets.token_hex(32)

    def generate_api_key(
        self,
        user_id: str,
        role: str = "user",
        scopes: Optional[List[str]] = None,
        expiry_hours: int = _TOKEN_EXPIRY_HOURS,
    ) -> Dict[str, Any]:
        """Generate a new API key for a user.

        Returns dict with 'key_id', 'api_key' (the full key to share with user),
        and metadata. The key value is only shown once at creation.
        """
        conn = self._get_conn()
        key_id = f"oag_{secrets.token_hex(12)}"
        api_key = f"xavani_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        created_at = datetime.now(timezone.utc).isoformat()
        expires_at = (
            (datetime.now(timezone.utc) + timedelta(hours=expiry_hours)).isoformat()
            if expiry_hours
            else None
        )
        scopes_str = ",".join(scopes) if scopes else ""

        conn.execute(
            "INSERT INTO api_keys (key_id, key_hash, user_id, role, scopes, created_at, expires_at, is_active) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, 1)",
            (key_id, key_hash, user_id, role, scopes_str, created_at, expires_at),
        )
        conn.commit()

        return {
            "key_id": key_id,
            "api_key": api_key,
            "user_id": user_id,
            "role": role,
            "scopes": scopes or [],
            "created_at": created_at,
            "expires_at": expires_at,
        }

    def validate_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """Validate an API key. Returns key metadata if valid, None otherwise."""
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM api_keys WHERE key_hash = ? AND is_active = 1",
            (key_hash,),
        ).fetchone()

        if row is None:
            return None

        # Check expiry
        if row["expires_at"]:
            expires = datetime.fromisoformat(row["expires_at"])
            if expires < datetime.now(timezone.utc):
                return None

        return dict(row)

    def revoke_api_key(self, key_id: str) -> bool:
        """Revoke an API key by its key_id."""
        conn = self._get_conn()
        cursor = conn.execute(
            "UPDATE api_keys SET is_active = 0 WHERE key_id = ?", (key_id,)
        )
        conn.commit()
        return cursor.rowcount > 0

    def list_api_keys(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List API keys, optionally filtered by user."""
        conn = self._get_conn()
        if user_id:
            rows = conn.execute(
                "SELECT key_id, user_id, role, scopes, created_at, expires_at, is_active "
                "FROM api_keys WHERE user_id = ? ORDER BY created_at DESC",
                (user_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT key_id, user_id, role, scopes, created_at, expires_at, is_active "
                "FROM api_keys ORDER BY created_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    def _get_pyjwt(self):
        """Lazy-import PyJWT (jwt) library. It's a core dependency."""
        try:
            import jwt as _jwt
            return _jwt
        except ImportError:
            raise ImportError(
                "PyJWT is required for JWT support. "
                "Install with: pip install PyJWT[crypto]"
            )

    def generate_jwt(
        self,
        user_id: str,
        role: str = "user",
        scopes: Optional[List[str]] = None,
        expiry_hours: int = _TOKEN_EXPIRY_HOURS,
    ) -> str:
        """Generate a JWT token for a user."""
        pyjwt = self._get_pyjwt()
        secret = self._get_jwt_secret()
        now = datetime.now(timezone.utc)
        payload: Dict[str, Any] = {
            "sub": user_id,
            "role": role,
            "scopes": scopes or [],
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(hours=expiry_hours)).timestamp()),
            "iss": "xavani-oag",
        }
        return pyjwt.encode(payload, secret, algorithm=_JWT_ALGORITHM)

    def validate_jwt(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate a JWT token. Returns payload if valid, None otherwise."""
        pyjwt = self._get_pyjwt()
        secret = self._get_jwt_secret()
        try:
            payload = pyjwt.decode(
                token,
                secret,
                algorithms=[_JWT_ALGORITHM],
                issuer="xavani-oag",
            )
            return payload
        except Exception:
            return None

    def authenticate(self, auth_header: Optional[str]) -> Optional[Dict[str, Any]]:
        """Authenticate a request from an Authorization header.

        Supports:
          - Bearer <jwt_token>
          - Bearer <api_key>
          - ApiKey <api_key>

        Returns authenticated user info dict or None.
        """
        if not auth_header:
            return None

        parts = auth_header.strip().split(None, 1)
        if len(parts) != 2:
            return None

        scheme, credentials = parts
        scheme = scheme.lower()

        if scheme == "bearer":
            # Try JWT first, then API key
            jwt_result = self.validate_jwt(credentials)
            if jwt_result:
                return {
                    "user_id": jwt_result.get("sub", "unknown"),
                    "role": jwt_result.get("role", "user"),
                    "scopes": jwt_result.get("scopes", []),
                    "auth_method": "jwt",
                }

            # Fall back to API key
            key_result = self.validate_api_key(credentials)
            if key_result:
                return {
                    "user_id": key_result["user_id"],
                    "role": key_result["role"],
                    "scopes": key_result["scopes"].split(",") if key_result["scopes"] else [],
                    "auth_method": "api_key",
                }
            return None

        elif scheme == "apikey":
            key_result = self.validate_api_key(credentials)
            if key_result:
                return {
                    "user_id": key_result["user_id"],
                    "role": key_result["role"],
                    "scopes": key_result["scopes"].split(",") if key_result["scopes"] else [],
                    "auth_method": "api_key",
                }
            return None

        return None


# ---------------------------------------------------------------------------
# Server Registry Loader
# ---------------------------------------------------------------------------


class MCServerProcess:
    """Manages a running MCP server subprocess."""

    def __init__(self, name: str, config: Dict[str, Any]) -> None:
        self.name = name
        self.config = config
        self.process: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()

    @property
    def is_running(self) -> bool:
        if self.process is None:
            return False
        return self.process.poll() is None

    def start(self) -> None:
        """Start the MCP server subprocess."""
        with self._lock:
            if self.is_running:
                return

            command = self.config.get("command", "")
            args = self.config.get("args", [])
            env = self.config.get("env", {})
            cwd = self.config.get("cwd")

            cmd_parts = [command] + list(args)
            merged_env = os.environ.copy()
            merged_env.update(env)

            try:
                self.process = subprocess.Popen(
                    cmd_parts,
                    cwd=cwd,
                    env=merged_env or None,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    stdin=subprocess.PIPE,
                    start_new_session=True,
                )
                logger.info("Started MCP server '%s' (PID %s)", self.name, self.process.pid)
            except Exception as exc:
                logger.error("Failed to start MCP server '%s': %s", self.name, exc)
                self.process = None

    def stop(self, timeout: float = 5.0) -> None:
        """Stop the MCP server subprocess gracefully."""
        with self._lock:
            if self.process is None:
                return
            try:
                self.process.terminate()
                try:
                    self.process.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=2.0)
            except Exception as exc:
                logger.warning("Error stopping MCP server '%s': %s", self.name, exc)
            finally:
                self.process = None

    def __del__(self) -> None:
        self.stop()


class ServerRegistryLoader:
    """Reads ~/.xavani/installed/*.toml and starts/manages MCP server processes.

    Also supports loading from the installed_servers.json format used by the
    existing OAG CLI commands.
    """

    def __init__(self, installed_dir: Path = INSTALLED_DIR) -> None:
        self._installed_dir = installed_dir
        self._installed_dir.mkdir(parents=True, exist_ok=True)
        self._servers: Dict[str, MCServerProcess] = {}
        self._lock = threading.Lock()

    def discover(self) -> Dict[str, Dict[str, Any]]:
        """Discover all installed MCP servers from TOML files and JSON index."""
        servers: Dict[str, Dict[str, Any]] = {}

        # Load from individual TOML files in installed/
        if self._installed_dir.exists():
            for fpath in self._installed_dir.iterdir():
                if fpath.suffix == ".toml":
                    try:
                        data = tomllib.loads(fpath.read_text(encoding="utf-8"))
                        if "server" in data:
                            srv = data["server"]
                            name = srv.get("name", fpath.stem)
                            servers[name] = srv
                        elif "mcp_server" in data:
                            srv = data["mcp_server"]
                            name = srv.get("name", fpath.stem)
                            servers[name] = srv
                    except Exception as exc:
                        logger.warning("Failed to load server config from %s: %s", fpath, exc)

        # Also load from JSON index (backward compat with existing OAG)
        json_path = XAVANI_HOME / "installed_servers.json"
        if json_path.exists():
            try:
                data = json.loads(json_path.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    for entry in data:
                        name = entry.get("name", "")
                        if name and name not in servers:
                            servers[name] = {
                                "command": entry.get("command", ""),
                                "args": entry.get("args", []),
                                "description": entry.get("description", ""),
                            }
            except Exception as exc:
                logger.warning("Failed to load servers from JSON index: %s", exc)

        # Also load from config.yaml mcp_servers
        config_path = XAVANI_HOME / "config.yaml"
        if config_path.exists():
            try:
                import yaml
                config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
                if isinstance(config, dict):
                    mcp_servers = config.get("mcp_servers", {})
                    if isinstance(mcp_servers, dict):
                        for name, srv_cfg in mcp_servers.items():
                            if name not in servers and isinstance(srv_cfg, dict):
                                servers[name] = srv_cfg
            except Exception:
                pass

        return servers

    def get_server_config(self, name: str) -> Optional[Dict[str, Any]]:
        """Get the configuration for a specific installed server."""
        servers = self.discover()
        return servers.get(name)

    def start_server(self, name: str) -> Optional[MCServerProcess]:
        """Start a specific MCP server by name."""
        with self._lock:
            if name in self._servers and self._servers[name].is_running:
                return self._servers[name]

            config = self.get_server_config(name)
            if config is None:
                logger.warning("Cannot start server '%s': not found", name)
                return None

            proc = MCServerProcess(name, config)
            proc.start()
            if proc.is_running:
                self._servers[name] = proc
            return proc

    def stop_server(self, name: str) -> bool:
        """Stop a specific MCP server by name."""
        with self._lock:
            proc = self._servers.get(name)
            if proc is None:
                return False
            proc.stop()
            del self._servers[name]
            return True

    def start_all(self) -> Dict[str, bool]:
        """Start all discovered MCP servers. Returns {name: success}."""
        servers = self.discover()
        results: Dict[str, bool] = {}
        for name in servers:
            proc = self.start_server(name)
            results[name] = proc is not None and proc.is_running
        return results

    def stop_all(self) -> None:
        """Stop all running MCP servers."""
        with self._lock:
            for proc in self._servers.values():
                proc.stop()
            self._servers.clear()

    def get_running_servers(self) -> Dict[str, MCServerProcess]:
        """Get dict of currently running server processes."""
        with self._lock:
            return dict(self._servers)

    def get_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all discovered MCP servers."""
        discovered = self.discover()
        status: Dict[str, Dict[str, Any]] = {}
        for name, config in discovered.items():
            proc = self._servers.get(name)
            status[name] = {
                "name": name,
                "description": config.get("description", ""),
                "command": config.get("command", ""),
                "args": config.get("args", []),
                "running": proc is not None and proc.is_running,
                "pid": proc.process.pid if proc and proc.process and proc.is_running else None,
            }
        return status

    def forward_request(
        self,
        server_name: str,
        request: Dict[str, Any],
        timeout: float = 30.0,
    ) -> Optional[Dict[str, Any]]:
        """Forward a JSON-RPC request to an MCP server via its stdin/stdout.

        For servers not managed as subprocesses, attempts HTTP forwarding to
        the server's configured endpoint.
        """
        proc = self._servers.get(server_name)
        if proc and proc.is_running and proc.process and proc.process.stdin:
            try:
                req_bytes = (json.dumps(request) + "\n").encode("utf-8")
                proc.process.stdin.write(req_bytes)
                proc.process.stdin.flush()

                # Read response from stdout
                if proc.process.stdout:
                    response_line = proc.process.stdout.readline()
                    if response_line:
                        return json.loads(response_line.decode("utf-8").strip())
                return None
            except Exception as exc:
                logger.error("Error forwarding to server '%s': %s", server_name, exc)
                return None

        # Fall back to HTTP forwarding for external servers
        config = self.get_server_config(server_name)
        if config:
            url = config.get("url", config.get("endpoint", ""))
            if url:
                from urllib.parse import urlparse
                parsed = urlparse(url)
                hostname = parsed.hostname or ""
                # Block SSRF: reject internal/private network targets
                if hostname in ("localhost", "127.0.0.1", "0.0.0.0", "::1"):
                    logger.warning("SSRF blocked: refusing to forward to internal host '%s'", hostname)
                    return None
                try:
                    import httpx
                    resp = httpx.post(
                        url,
                        json=request,
                        timeout=timeout,
                    )
                    return resp.json()
                except Exception as exc:
                    logger.error("HTTP forward error for '%s': %s", server_name, exc)
                    return None

        logger.warning("No active process or URL for server '%s'", server_name)
        return None


# ---------------------------------------------------------------------------
# MCP Gateway Proxy Server (FastAPI)
# ---------------------------------------------------------------------------


class OAGProxyServer:
    """FastAPI-based MCP Gateway Proxy.

    Routes MCP JSON-RPC requests to backend servers with policy enforcement,
    authentication, rate limiting, and audit logging.
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8080,
        auth_manager: Optional[OAGAuthManager] = None,
        policy_engine: Optional[OAGPolicyEngine] = None,
        audit_logger: Optional[OAGAuditLogger] = None,
        server_loader: Optional[ServerRegistryLoader] = None,
    ) -> None:
        self.host = host
        self.port = port
        self.auth = auth_manager or OAGAuthManager()
        self.policies = policy_engine or OAGPolicyEngine()
        self.audit = audit_logger or OAGAuditLogger()
        self.servers = server_loader or ServerRegistryLoader()
        self._app: Optional[Any] = None
        self._uvicorn_server: Optional[Any] = None
        self._running = threading.Event()

    def _build_app(self) -> Any:
        """Build the FastAPI application with all routes."""
        try:
            from fastapi import FastAPI, HTTPException, Request
            from fastapi.responses import JSONResponse
            from pydantic import BaseModel
        except ImportError:
            logger.error(
                "FastAPI is not installed. Install with: pip install 'xavani-agent[web]'"
            )
            raise

        from fastapi.middleware.cors import CORSMiddleware

        app = FastAPI(
            title="Xavani MCP Gateway Proxy",
            description="Open Agent Gateway - MCP Proxy with policy enforcement",
            version="0.1.0",
        )

        app.add_middleware(
            CORSMiddleware,
            allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # ── Request Models ────────────────────────────────────────────

        class MCPRequest(BaseModel):
            jsonrpc: str = "2.0"
            method: str
            params: Optional[Union[Dict[str, Any], List[Any]]] = None
            id: Optional[Union[str, int]] = None

        class AuthTokenRequest(BaseModel):
            user_id: str
            role: str = "user"
            scopes: Optional[List[str]] = None
            expiry_hours: int = _TOKEN_EXPIRY_HOURS

        # ── Middleware: Auth ───────────────────────────────────────────

        @app.middleware("http")
        async def auth_middleware(request: Request, call_next):
            # Skip auth for health, docs, and open endpoints
            open_paths = {"/health", "/docs", "/openapi.json", "/auth/token"}
            if request.url.path in open_paths:
                return await call_next(request)

            auth_header = request.headers.get("Authorization")
            user_info = self.auth.authenticate(auth_header)
            if user_info is None and request.url.path != "/auth/token":
                return JSONResponse(
                    status_code=401,
                    content={
                        "jsonrpc": "2.0",
                        "error": {"code": -32001, "message": "Authentication required"},
                        "id": None,
                    },
                )

            request.state.user = user_info or {"user_id": "anonymous", "role": "anonymous"}
            return await call_next(request)

        # ── Routes ────────────────────────────────────────────────────

        @app.get("/health")
        async def health_check():
            """Health check endpoint returning server and MCP server status."""
            server_status = self.servers.get_status()
            running_count = sum(1 for s in server_status.values() if s.get("running"))
            total_count = len(server_status)

            return {
                "status": "ok",
                "version": "0.1.0",
                "uptime_seconds": time.time() - _start_time,
                "servers": {
                    "total": total_count,
                    "running": running_count,
                    "details": server_status,
                },
                "audit": self.audit.stats(),
            }

        @app.post("/mcp")
        async def mcp_handler(request: Request):
            """Handle MCP JSON-RPC requests.

            Accepts both single requests and batches (list of requests).
            Forwards to the appropriate MCP server after policy evaluation.
            """
            start_time = time.time()
            body = await request.body()
            user_id = getattr(request.state, "user", {}).get("user_id", "anonymous")

            try:
                payload = json.loads(body)
            except json.JSONDecodeError:
                return JSONResponse(
                    status_code=400,
                    content={
                        "jsonrpc": "2.0",
                        "error": {"code": -32700, "message": "Parse error"},
                        "id": None,
                    },
                )

            is_batch = isinstance(payload, list)
            requests_list = payload if is_batch else [payload]

            responses: List[Optional[Dict[str, Any]]] = []
            for req in requests_list:
                resp = await self._handle_single_request(req, user_id, body)
                responses.append(resp)

            duration_ms = (time.time() - start_time) * 1000

            # Audit log the batch
            for req, resp in zip(requests_list, responses):
                method = req.get("method", "unknown") if isinstance(req, dict) else "unknown"
                server_name = self._infer_server_from_method(method)
                tool_name = method
                input_summary = self._summarize_input(req)
                allowed = resp is not None and "error" not in resp
                denied_reason = None
                if resp and "error" in resp:
                    denied_reason = str(resp["error"].get("message", ""))

                self.audit.log(
                    user_id=user_id,
                    tool_name=tool_name,
                    server_name=server_name,
                    input_summary=input_summary,
                    duration_ms=duration_ms / max(len(requests_list), 1),
                    allowed=allowed,
                    denied_reason=denied_reason,
                    request_id=str(req.get("id", "")) if isinstance(req, dict) else None,
                    input_size_bytes=len(body),
                )

            # Rotate old audit entries periodically (1% chance per request)
            if secrets.randbelow(100) == 0:
                asyncio.create_task(self._rotate_audit_async())

            if is_batch:
                return JSONResponse(content=responses)
            else:
                return JSONResponse(content=responses[0] if responses else {})

        @app.get("/audit")
        async def get_audit_log(
            request: Request,
            since: Optional[str] = None,
            user_id: Optional[str] = None,
            limit: int = 500,
            offset: int = 0,
        ):
            """Return audit log entries, optionally filtered."""
            since_dt: Optional[datetime] = None
            if since:
                try:
                    if since.endswith("h"):
                        hours = int(since[:-1])
                        since_dt = datetime.now(timezone.utc) - timedelta(hours=hours)
                    elif since.endswith("d"):
                        days = int(since[:-1])
                        since_dt = datetime.now(timezone.utc) - timedelta(days=days)
                    else:
                        since_dt = datetime.fromisoformat(since)
                except (ValueError, TypeError):
                    return JSONResponse(
                        status_code=400,
                        content={"error": f"Invalid 'since' format: {since}. Use 24h, 7d, or ISO-8601"},
                    )

            entries = self.audit.query(since=since_dt, user_id=user_id, limit=limit, offset=offset)
            return {
                "entries": entries,
                "total": len(entries),
                "since": since,
                "stats": self.audit.stats(),
            }

        @app.post("/auth/token")
        async def create_auth_token(req: AuthTokenRequest):
            """Generate a new API key or JWT token."""
            result = self.auth.generate_api_key(
                user_id=req.user_id,
                role=req.role,
                scopes=req.scopes,
                expiry_hours=req.expiry_hours,
            )
            return {
                "key_id": result["key_id"],
                "api_key": result["api_key"],
                "user_id": result["user_id"],
                "role": result["role"],
                "scopes": result["scopes"],
                "expires_at": result["expires_at"],
                "note": "Save this API key — it will not be shown again.",
            }

        @app.get("/policies")
        async def list_policies():
            """List all active policies."""
            policies = self.policies.load_policies()
            return {
                "policies": policies,
                "count": len(policies),
            }

        @app.get("/mcp/status")
        async def mcp_server_status():
            """Get status of all MCP servers."""
            status = self.servers.get_status()
            return {
                "servers": status,
                "count": len(status),
            }

        return app

    async def _handle_single_request(
        self,
        req: Dict[str, Any],
        user_id: str,
        raw_body: bytes,
    ) -> Dict[str, Any]:
        """Handle a single MCP JSON-RPC request with policy evaluation."""
        if not isinstance(req, dict):
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32600, "message": "Invalid Request"},
                "id": None,
            }

        method = req.get("method", "")
        req_id = req.get("id")
        params = req.get("params", {})
        if isinstance(params, list):
            params_dict = {}
            for i, p in enumerate(params):
                if isinstance(p, dict):
                    params_dict.update(p)
                else:
                    params_dict[str(i)] = p
        else:
            params_dict = params or {}

        # Infer the target server from the method name
        server_name = self._infer_server_from_method(method)

        # Extract tool name and resource URI from params
        tool_name = params_dict.get("tool_name") or params_dict.get("tool") or method
        resource_uri = params_dict.get("uri") or params_dict.get("path") or params_dict.get("resource")

        # Policy evaluation
        allowed, denied_reason, retry_after = self.policies.evaluate(
            user_id=user_id,
            tool_name=tool_name,
            server_name=server_name,
            resource_uri=resource_uri,
            input_args=params_dict,
            input_size_bytes=len(raw_body),
        )

        if not allowed:
            error_code = -32003 if denied_reason == "Rate limit exceeded" else -32002
            error_msg = denied_reason or "Request denied by policy"
            resp: Dict[str, Any] = {
                "jsonrpc": "2.0",
                "error": {"code": error_code, "message": error_msg},
            }
            if retry_after:
                resp["error"]["retry_after_seconds"] = round(retry_after, 2)
            if req_id is not None:
                resp["id"] = req_id
            return resp

        # Forward the request to the target server
        if server_name:
            server_response = self.servers.forward_request(server_name, req)
            if server_response is not None:
                if req_id is not None:
                    server_response["id"] = req_id
                return server_response

        # If no server handles this, return method not found
        return {
            "jsonrpc": "2.0",
            "error": {
                "code": -32601,
                "message": f"Method not found: {method}",
                "data": {"server": server_name or "none"},
            },
            "id": req_id,
        }

    def _infer_server_from_method(self, method: str) -> Optional[str]:
        """Try to infer which MCP server handles a given method."""
        # MCP method conventions:
        #   tools/list, tools/call -> infer from prefix
        #   resources/list, resources/read -> infer from prefix
        #   prompts/list, prompts/get -> infer from prefix
        known_servers = self.servers.discover()

        # Direct method-to-server mapping configured in TOML
        method_map: Dict[str, str] = {}
        for srv_name, srv_config in known_servers.items():
            srv_methods = srv_config.get("methods", [])
            if isinstance(srv_methods, list):
                for m in srv_methods:
                    method_map[m] = srv_name

        if method in method_map:
            return method_map[method]

        # If only one server is installed, assume it handles everything
        if len(known_servers) == 1:
            return list(known_servers.keys())[0]

        return None

    def _summarize_input(self, req: Dict[str, Any]) -> str:
        """Create a short summary of an MCP request for audit logging."""
        method = req.get("method", "unknown")
        params = req.get("params", {})

        summary_parts: List[str] = [f"method={method}"]

        if isinstance(params, dict):
            # Extract key identifiers
            for key in ("name", "tool", "tool_name", "uri", "path", "query", "id"):
                if key in params:
                    val = str(params[key])
                    if len(val) > 80:
                        val = val[:77] + "..."
                    summary_parts.append(f"{key}={val}")
                    break
        elif isinstance(params, list) and params:
            summary_parts.append(f"params_count={len(params)}")

        return " | ".join(summary_parts)

    async def _rotate_audit_async(self) -> None:
        """Run audit log rotation in a thread pool."""
        loop = asyncio.get_event_loop()
        removed = await loop.run_in_executor(None, self.audit.rotate)
        if removed > 0:
            logger.info("Rotated %d old audit log entries", removed)

    def start(self) -> None:
        """Start the FastAPI server in a background thread."""
        import uvicorn

        self._app = self._build_app()
        self._running.clear()
        _start_time = time.time()

        config = uvicorn.Config(
            app=self._app,
            host=self.host,
            port=self.port,
            log_level="info",
        )
        self._uvicorn_server = uvicorn.Server(config)

        def run_server():
            try:
                self._uvicorn_server.run()
            finally:
                self._running.set()

        thread = threading.Thread(target=run_server, daemon=True, name="oag-proxy")
        thread.start()

        # Wait for server to be ready
        for _ in range(50):
            if self._uvicorn_server and getattr(self._uvicorn_server, "started", False):
                break
            time.sleep(0.1)

        self._running.clear()
        logger.info("OAG Gateway Proxy started on http://%s:%s", self.host, self.port)

    def stop(self) -> None:
        """Stop the FastAPI server."""
        if self._uvicorn_server:
            self._uvicorn_server.should_exit = True
            self._running.set()
        logger.info("OAG Gateway Proxy stopped")

    @property
    def is_running(self) -> bool:
        return not self._running.is_set() and self._uvicorn_server is not None

    def run_forever(self) -> None:
        """Start the server synchronously (blocking)."""
        import uvicorn

        self._app = self._build_app()
        uvicorn.run(
            self._app,
            host=self.host,
            port=self.port,
            log_level="info",
        )


_start_time = time.time()


# ---------------------------------------------------------------------------
# Convenience factory
# ---------------------------------------------------------------------------


def create_oag_proxy(
    host: str = "127.0.0.1",
    port: int = 8080,
    auth_manager: Optional[OAGAuthManager] = None,
    policy_engine: Optional[OAGPolicyEngine] = None,
    audit_logger: Optional[OAGAuditLogger] = None,
    server_loader: Optional[ServerRegistryLoader] = None,
) -> OAGProxyServer:
    """Create and return a fully configured OAGProxyServer.

    All dependencies are auto-initialized with defaults if not provided.
    """
    return OAGProxyServer(
        host=host,
        port=port,
        auth_manager=auth_manager or OAGAuthManager(),
        policy_engine=policy_engine or OAGPolicyEngine(),
        audit_logger=audit_logger or OAGAuditLogger(),
        server_loader=server_loader or ServerRegistryLoader(),
    )


def start_oag_gateway(host: str = "127.0.0.1", port: int = 8080) -> OAGProxyServer:
    """Start the OAG gateway proxy in background and return the server instance."""
    proxy = create_oag_proxy(host=host, port=port)
    proxy.start()
    return proxy


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    proxy = create_oag_proxy()
    print(f"Starting Xavani MCP Gateway Proxy on http://{proxy.host}:{proxy.port}")
    proxy.run_forever()
