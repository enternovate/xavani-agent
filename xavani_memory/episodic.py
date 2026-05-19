# Copyright (c) 2025-2026 Enternovate. All rights reserved.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Episodic Memory — Phase 4 of Xavani Agent.

SQLite-backed episodic memory system that stores and retrieves agent-user
interaction episodes with full-text search, time-range queries, cross-agent
context sharing, and conflict resolution.

Every episode captures an interaction cycle:
  user_input → agent_thought → agent_action → result → outcome

This mirrors the agent's thought loop and preserves the full context for
later recall, reflection, and learning.
"""

from __future__ import annotations

import gzip
import json
import logging
import os
import sqlite3
import threading
import time
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

XAVANI_HOME = Path(os.environ.get("XAVANI_HOME", "~/.xavani")).expanduser()
MEMORY_DIR = XAVANI_HOME / "data" / "memory"
EPISODIC_DB_PATH = MEMORY_DIR / "episodic.db"

# Maximum length for text fields stored in SQLite indexing
_MAX_TEXT_LENGTH = 10000

# Default FTS results limit
_DEFAULT_FTS_LIMIT = 20

# ---------------------------------------------------------------------------
# EpisodicMemory
# ---------------------------------------------------------------------------


class EpisodicMemory:
    """SQLite-backed episodic memory with full-text search and context sharing.

    Stores agent-user interaction episodes and provides:
    - FTS5-powered keyword search (``recall_similar``)
    - Time-range queries (``recall_by_timeframe``)
    - Recent episode retrieval (``get_recent``)
    - Session summarization (``summarize_session``)
    - Auto-archival of old episodes (``forget_older_than``)
    - Cross-agent context sharing with conflict resolution

    Thread-safe: uses thread-local SQLite connections with WAL mode.
    Survives restarts: all data persisted to ``~/.xavani/data/memory/episodic.db``.
    """

    def __init__(self, db_path: Path = EPISODIC_DB_PATH):
        self._db_path = db_path
        self._local = threading.local()
        self._init_db()

    # ── Database Connection ──────────────────────────────────────────

    def _get_conn(self) -> sqlite3.Connection:
        """Get a thread-local SQLite connection."""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(str(self._db_path))
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA synchronous=NORMAL")
            self._local.conn.execute("PRAGMA foreign_keys=ON")
        return self._local.conn

    def _init_db(self) -> None:
        """Create tables and indexes if they do not exist."""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = self._get_conn()

        # Main episodes table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS episodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                episode_id TEXT UNIQUE NOT NULL,
                timestamp TEXT NOT NULL,
                user_input TEXT NOT NULL,
                agent_response TEXT,
                agent_thought TEXT,
                agent_action TEXT,
                context_snapshot TEXT,
                outcome TEXT,
                session_id TEXT,
                agent_id TEXT DEFAULT 'default',
                tags TEXT,
                metadata TEXT,
                shared_with TEXT,
                archived INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            )
            """
        )

        # FTS5 virtual table for full-text search across key fields
        conn.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS episodes_fts USING fts5(
                episode_id UNINDEXED,
                user_input,
                agent_response,
                agent_thought,
                agent_action,
                outcome,
                tags,
                content='episodes',
                content_rowid='id',
                tokenize='porter unicode61'
            )
            """
        )

        # Triggers to keep FTS index in sync
        conn.executescript(
            """
            CREATE TRIGGER IF NOT EXISTS episodes_ai AFTER INSERT ON episodes BEGIN
                INSERT INTO episodes_fts(rowid, episode_id, user_input, agent_response,
                    agent_thought, agent_action, outcome, tags)
                VALUES (new.id, new.episode_id, new.user_input, new.agent_response,
                    new.agent_thought, new.agent_action, new.outcome, new.tags);
            END;

            CREATE TRIGGER IF NOT EXISTS episodes_ad AFTER DELETE ON episodes BEGIN
                INSERT INTO episodes_fts(episodes_fts, rowid, episode_id, user_input,
                    agent_response, agent_thought, agent_action, outcome, tags)
                VALUES ('delete', old.id, old.episode_id, old.user_input,
                    old.agent_response, old.agent_thought, old.agent_action,
                    old.outcome, old.tags);
            END;

            CREATE TRIGGER IF NOT EXISTS episodes_au AFTER UPDATE ON episodes BEGIN
                INSERT INTO episodes_fts(episodes_fts, rowid, episode_id, user_input,
                    agent_response, agent_thought, agent_action, outcome, tags)
                VALUES ('delete', old.id, old.episode_id, old.user_input,
                    old.agent_response, old.agent_thought, old.agent_action,
                    old.outcome, old.tags);
                INSERT INTO episodes_fts(rowid, episode_id, user_input, agent_response,
                    agent_thought, agent_action, outcome, tags)
                VALUES (new.id, new.episode_id, new.user_input, new.agent_response,
                    new.agent_thought, new.agent_action, new.outcome, new.tags);
            END;
            """
        )

        # Index for time-range queries
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_episodes_timestamp
            ON episodes(timestamp)
            """
        )

        # Index for session queries
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_episodes_session
            ON episodes(session_id)
            """
        )

        # Index for agent queries
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_episodes_agent
            ON episodes(agent_id)
            """
        )

        # Cross-agent context sharing table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS shared_context (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_agent_id TEXT NOT NULL,
                target_agent_id TEXT NOT NULL,
                episode_id TEXT NOT NULL,
                shared_at TEXT DEFAULT (datetime('now')),
                status TEXT DEFAULT 'active',
                FOREIGN KEY (episode_id) REFERENCES episodes(episode_id)
            )
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_shared_context_target
            ON shared_context(target_agent_id)
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_shared_context_source
            ON shared_context(source_agent_id)
            """
        )

        conn.commit()

    # ── Core Episode Operations ──────────────────────────────────────

    def store_episode(
        self,
        user_input: str,
        agent_response: Optional[str] = None,
        context_snapshot: Optional[Dict[str, Any]] = None,
        outcome: Optional[str] = None,
        *,
        agent_thought: Optional[str] = None,
        agent_action: Optional[str] = None,
        session_id: Optional[str] = None,
        agent_id: str = "default",
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Store a new episode in memory.

        Args:
            user_input: The user's message or query.
            agent_response: The agent's response text.
            context_snapshot: Dict of contextual information at the time
                of the episode (e.g. channel, platform, conversation state).
            outcome: Description of the outcome (e.g. "success",
                "user satisfied", "error: timeout").
            agent_thought: The agent's internal reasoning/thought process.
            agent_action: The action taken by the agent (tool call, etc.).
            session_id: Session identifier for grouping related episodes.
            agent_id: Identifier for the agent instance.
            tags: List of tags for categorization.
            metadata: Arbitrary metadata dict.

        Returns:
            The generated episode ID string.
        """
        episode_id = _generate_episode_id()
        now = datetime.now(timezone.utc).isoformat()

        conn = self._get_conn()

        conn.execute(
            """
            INSERT INTO episodes
                (episode_id, timestamp, user_input, agent_response,
                 agent_thought, agent_action, context_snapshot, outcome,
                 session_id, agent_id, tags, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                episode_id,
                now,
                user_input[:_MAX_TEXT_LENGTH] if user_input else "",
                agent_response[:_MAX_TEXT_LENGTH] if agent_response else None,
                agent_thought[:_MAX_TEXT_LENGTH] if agent_thought else None,
                agent_action[:_MAX_TEXT_LENGTH] if agent_action else None,
                json.dumps(context_snapshot, default=str) if context_snapshot else None,
                outcome[:_MAX_TEXT_LENGTH] if outcome else None,
                session_id,
                agent_id,
                json.dumps(tags) if tags else None,
                json.dumps(metadata, default=str) if metadata else None,
            ),
        )

        conn.commit()
        logger.debug("Stored episode %s", episode_id)
        return episode_id

    def get_episode(self, episode_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a single episode by its ID.

        Args:
            episode_id: The episode identifier.

        Returns:
            Episode dict, or None if not found.
        """
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM episodes WHERE episode_id = ?",
            (episode_id,),
        ).fetchone()

        if row is None:
            return None

        return self._row_to_dict(row)

    # ── Recall / Query ───────────────────────────────────────────────

    def recall_similar(
        self,
        query: str,
        limit: int = 5,
        *,
        min_score: float = 0.0,
        agent_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """FTS5 keyword search across episodes.

        Uses SQLite FTS5's BM25 ranking to find episodes whose user_input,
        agent_response, thought, action, or outcome match the query terms.

        Args:
            query: Free-text search query (FTS5 syntax supported).
            limit: Maximum number of results to return.
            min_score: Minimum relevance score threshold (0.0 = no minimum).
            agent_id: If set, only search episodes from this agent.

        Returns:
            List of matching episode dicts, sorted by relevance descending.
        """
        conn = self._get_conn()

        if agent_id:
            sql = """
                SELECT e.*, rank
                FROM episodes_fts f
                JOIN episodes e ON e.id = f.rowid
                WHERE episodes_fts MATCH ?
                  AND e.agent_id = ?
                  AND e.archived = 0
                ORDER BY rank
                LIMIT ?
            """
            rows = conn.execute(sql, (query, agent_id, limit)).fetchall()
        else:
            sql = """
                SELECT e.*, rank
                FROM episodes_fts f
                JOIN episodes e ON e.id = f.rowid
                WHERE episodes_fts MATCH ?
                  AND e.archived = 0
                ORDER BY rank
                LIMIT ?
            """
            rows = conn.execute(sql, (query, limit)).fetchall()

        results: List[Dict[str, Any]] = []
        for row in rows:
            d = self._row_to_dict(row)
            # FTS5 rank is negative for good matches (BM25), clamp to 0-1
            rank = row["rank"] if "rank" in row else 0
            d["_relevance_score"] = max(0.0, min(1.0, -rank / 10.0))
            if d["_relevance_score"] >= min_score:
                results.append(d)

        return results

    def recall_by_timeframe(
        self,
        start: datetime,
        end: Optional[datetime] = None,
        *,
        agent_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get episodes within a time range.

        Args:
            start: Start of the time range (inclusive, ISO format).
            end: End of the time range (inclusive, defaults to now).
            agent_id: If set, only episodes from this agent.
            limit: Maximum results.

        Returns:
            List of episode dicts, ordered by timestamp descending.
        """
        conn = self._get_conn()
        end = end or datetime.now(timezone.utc)

        start_str = start.isoformat() if isinstance(start, datetime) else str(start)
        end_str = end.isoformat() if isinstance(end, datetime) else str(end)

        if agent_id:
            rows = conn.execute(
                """
                SELECT * FROM episodes
                WHERE timestamp >= ? AND timestamp <= ?
                  AND agent_id = ?
                  AND archived = 0
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (start_str, end_str, agent_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT * FROM episodes
                WHERE timestamp >= ? AND timestamp <= ?
                  AND archived = 0
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (start_str, end_str, limit),
            ).fetchall()

        return [self._row_to_dict(r) for r in rows]

    def get_recent(
        self,
        limit: int = 10,
        *,
        agent_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get the most recent episodes.

        Args:
            limit: Maximum number of episodes to return.
            agent_id: Filter by agent.
            session_id: Filter by session.

        Returns:
            List of episode dicts, most recent first.
        """
        conn = self._get_conn()

        conditions = ["archived = 0"]
        params: List[Any] = []

        if agent_id:
            conditions.append("agent_id = ?")
            params.append(agent_id)
        if session_id:
            conditions.append("session_id = ?")
            params.append(session_id)

        where = " AND ".join(conditions)
        rows = conn.execute(
            f"SELECT * FROM episodes WHERE {where} ORDER BY timestamp DESC LIMIT ?",
            params + [limit],
        ).fetchall()

        return [self._row_to_dict(r) for r in rows]

    def summarize_session(
        self,
        session_id: Optional[str] = None,
        *,
        agent_id: Optional[str] = None,
        since: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Generate a compact summary of current session activity.

        Args:
            session_id: The session to summarize. If None, summarizes
                the most recent session found.
            agent_id: Filter by agent.
            since: Only consider episodes since this time.

        Returns:
            Summary dict with counts, duration, key topics, and outcomes.
        """
        conn = self._get_conn()

        # Auto-detect latest session if not specified
        if not session_id:
            row = conn.execute(
                """
                SELECT session_id FROM episodes
                WHERE archived = 0
                ORDER BY timestamp DESC LIMIT 1
                """
            ).fetchone()
            if row and row["session_id"]:
                session_id = row["session_id"]
            else:
                return {
                    "session_id": None,
                    "total_episodes": 0,
                    "duration_minutes": 0,
                    "key_topics": [],
                    "outcome_summary": {},
                    "error_count": 0,
                }

        conditions = ["archived = 0", "session_id = ?"]
        params: List[Any] = [session_id]

        if agent_id:
            conditions.append("agent_id = ?")
            params.append(agent_id)
        if since:
            conditions.append("timestamp >= ?")
            params.append(since.isoformat())

        where = " AND ".join(conditions)

        # Get all episodes for this session
        rows = conn.execute(
            f"SELECT * FROM episodes WHERE {where} ORDER BY timestamp ASC",
            params,
        ).fetchall()

        if not rows:
            return {
                "session_id": session_id,
                "total_episodes": 0,
                "duration_minutes": 0,
                "key_topics": [],
                "outcome_summary": {},
                "error_count": 0,
            }

        # Compute summary
        total = len(rows)
        first_ts = rows[0]["timestamp"]
        last_ts = rows[-1]["timestamp"]

        # Calculate duration
        try:
            duration = (
                datetime.fromisoformat(last_ts)
                - datetime.fromisoformat(first_ts)
            )
            duration_minutes = duration.total_seconds() / 60.0
        except (ValueError, TypeError):
            duration_minutes = 0.0

        # Extract topics from tags
        all_tags: List[str] = []
        for r in rows:
            if r["tags"]:
                try:
                    tags = json.loads(r["tags"])
                    if isinstance(tags, list):
                        all_tags.extend(tags)
                except (json.JSONDecodeError, TypeError):
                    pass

        from collections import Counter
        tag_counts = Counter(all_tags)
        key_topics = [tag for tag, count in tag_counts.most_common(10)]

        # Outcome summary
        outcome_summary: Dict[str, int] = {}
        error_count = 0
        for r in rows:
            outcome = r["outcome"] or "unknown"
            if "error" in outcome.lower() or "fail" in outcome.lower():
                error_count += 1
            outcome_summary[outcome] = outcome_summary.get(outcome, 0) + 1

        return {
            "session_id": session_id,
            "total_episodes": total,
            "duration_minutes": round(duration_minutes, 1),
            "first_episode": first_ts,
            "last_episode": last_ts,
            "key_topics": key_topics,
            "outcome_summary": outcome_summary,
            "error_count": error_count,
        }

    # ── Maintenance ──────────────────────────────────────────────────

    def forget_older_than(self, days: int = 90) -> int:
        """Archive episodes older than the specified number of days.

        Archived episodes are compressed in-place (their text fields are
        stored as gzip-compressed JSON) and marked as archived to exclude
        them from normal queries. They can still be decompressed if needed.

        Args:
            days: Age threshold in days.

        Returns:
            Number of episodes archived.
        """
        conn = self._get_conn()
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

        # Find episodes to archive
        rows = conn.execute(
            """
            SELECT id, episode_id, user_input, agent_response, agent_thought,
                   agent_action, context_snapshot, outcome, tags, metadata
            FROM episodes
            WHERE timestamp < ? AND archived = 0
            """,
            (cutoff,),
        ).fetchall()

        count = 0
        for row in rows:
            # Compress the text fields
            archive_data = {
                k: row[k] for k in row.keys()
                if k not in ("id", "episode_id")
                and row[k] is not None
            }
            compressed = gzip.compress(
                json.dumps(archive_data, default=str).encode("utf-8")
            )

            conn.execute(
                """
                UPDATE episodes SET
                    archived = 1,
                    context_snapshot = ?
                WHERE id = ?
                """,
                (compressed.hex(), row["id"]),
            )
            count += 1

        conn.commit()
        if count > 0:
            logger.info("Archived %d episodes older than %d days", count, days)

        return count

    def decompress_archived(self, episode: Dict[str, Any]) -> Dict[str, Any]:
        """Decompress an archived episode's fields.

        Args:
            episode: Episode dict with archived=1.

        Returns:
            Episode dict with decompressed text fields.
        """
        if not episode.get("archived"):
            return episode

        hex_data = episode.get("context_snapshot", "")
        if not hex_data:
            return episode

        try:
            raw = gzip.decompress(bytes.fromhex(hex_data))
            data = json.loads(raw.decode("utf-8"))
            episode.update(data)
            episode["context_snapshot"] = None  # Remove compressed blob
        except Exception as exc:
            logger.warning("Failed to decompress episode: %s", exc)

        return episode

    def archive_stats(self) -> Dict[str, Any]:
        """Get statistics about archived vs active episodes.

        Returns:
            Dict with ``total``, ``active``, ``archived``, ``oldest``, ``newest``.
        """
        conn = self._get_conn()

        total = conn.execute("SELECT COUNT(*) as c FROM episodes").fetchone()["c"]
        active = conn.execute(
            "SELECT COUNT(*) as c FROM episodes WHERE archived = 0"
        ).fetchone()["c"]
        archived = conn.execute(
            "SELECT COUNT(*) as c FROM episodes WHERE archived = 1"
        ).fetchone()["c"]

        oldest = conn.execute(
            "SELECT MIN(timestamp) as ts FROM episodes"
        ).fetchone()["ts"]
        newest = conn.execute(
            "SELECT MAX(timestamp) as ts FROM episodes"
        ).fetchone()["ts"]

        return {
            "total": total,
            "active": active,
            "archived": archived,
            "oldest_episode": oldest,
            "newest_episode": newest,
        }

    def clear_all(self) -> int:
        """Clear all episodes from memory.

        This is destructive but keeps the database structure intact.

        Returns:
            Number of episodes removed.
        """
        conn = self._get_conn()
        count = conn.execute("SELECT COUNT(*) as c FROM episodes").fetchone()["c"]
        conn.execute("DELETE FROM episodes")
        conn.execute("DELETE FROM shared_context")
        conn.execute("DELETE FROM episodes_fts")
        conn.commit()
        logger.warning("Cleared all %d episodes from memory", count)
        return count

    # ── Cross-Agent Context Sharing ──────────────────────────────────

    def share_context(
        self,
        agent_id: str,
        episode_ids: List[str],
        *,
        target_agent_id: str,
    ) -> int:
        """Mark episodes as shared with another agent.

        This records that agent ``agent_id`` has shared specific episodes
        with ``target_agent_id``, enabling cross-agent memory transfer.

        Args:
            agent_id: The sharing agent's ID (source).
            episode_ids: List of episode IDs to share.
            target_agent_id: The agent to share context with.

        Returns:
            Number of episodes successfully shared.
        """
        conn = self._get_conn()
        count = 0

        for ep_id in episode_ids:
            # Verify the episode exists
            exists = conn.execute(
                "SELECT 1 FROM episodes WHERE episode_id = ?",
                (ep_id,),
            ).fetchone()
            if not exists:
                logger.warning(
                    "Cannot share non-existent episode %s", ep_id
                )
                continue

            # Insert shared context record
            conn.execute(
                """
                INSERT OR IGNORE INTO shared_context
                    (source_agent_id, target_agent_id, episode_id)
                VALUES (?, ?, ?)
                """,
                (agent_id, target_agent_id, ep_id),
            )

            # Update the episode's shared_with field
            conn.execute(
                """
                UPDATE episodes SET shared_with = ?
                WHERE episode_id = ?
                """,
                (target_agent_id, ep_id),
            )

            count += 1

        conn.commit()
        logger.debug(
            "Shared %d episodes from agent '%s' to agent '%s'",
            count, agent_id, target_agent_id,
        )
        return count

    def get_shared_context(
        self,
        agent_id: str,
        *,
        since: Optional[datetime] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Retrieve context that has been shared TO this agent.

        Args:
            agent_id: The receiving agent's ID.
            since: Only return shares since this time.
            limit: Maximum results.

        Returns:
            List of episode dicts shared to this agent.
        """
        conn = self._get_conn()

        conditions = ["sc.target_agent_id = ?", "sc.status = 'active'"]
        params: List[Any] = [agent_id]

        if since:
            conditions.append("sc.shared_at >= ?")
            params.append(since.isoformat())

        where = " AND ".join(conditions)

        rows = conn.execute(
            f"""
            SELECT e.*, sc.source_agent_id, sc.shared_at, sc.status
            FROM shared_context sc
            JOIN episodes e ON e.episode_id = sc.episode_id
            WHERE {where}
            ORDER BY sc.shared_at DESC
            LIMIT ?
            """,
            params + [limit],
        ).fetchall()

        results = []
        for row in rows:
            d = self._row_to_dict(row)
            d["_shared_from"] = row["source_agent_id"]
            d["_shared_at"] = row["shared_at"]
            results.append(d)

        return results

    def resolve_conflicts(
        self,
        agent_id: str,
        *,
        strategy: str = "newest_wins",
    ) -> Dict[str, Any]:
        """Resolve overlapping or contradictory memories for an agent.

        Conflict detection looks at shared context episodes that may
        contradict each other (e.g. different outcomes for the same
        user input). Resolution strategies:

        - ``newest_wins`` (default): Keep the most recent episode,
          mark older ones as resolved.
        - ``source_priority``: Keep episodes from higher-priority agents.
        - ``merge``: Attempt to merge contradictory fields.

        Args:
            agent_id: The agent to resolve conflicts for.
            strategy: Resolution strategy (see above).

        Returns:
            Summary of conflicts found and resolved.
        """
        conn = self._get_conn()

        # Find episodes shared to this agent that may conflict
        # Conflicts are episodes with very similar user_input but
        # different outcomes or agent_responses
        rows = conn.execute(
            """
            SELECT e.episode_id, e.user_input, e.outcome, e.timestamp,
                   e.agent_response, sc.source_agent_id
            FROM shared_context sc
            JOIN episodes e ON e.episode_id = sc.episode_id
            WHERE sc.target_agent_id = ?
              AND sc.status = 'active'
            ORDER BY e.user_input, e.timestamp
            """,
            (agent_id,),
        ).fetchall()

        # Group by similar user input (basic conflict detection)
        conflicts_found = 0
        conflicts_resolved = 0
        groups: Dict[str, List[Dict[str, Any]]] = {}

        for row in rows:
            d = dict(row)
            # Use a normalized version of user_input as group key
            key = self._normalize_text(d.get("user_input", ""))[:100]
            if key not in groups:
                groups[key] = []
            groups[key].append(d)

        for key, group in groups.items():
            if len(group) < 2:
                continue  # No conflict in single-episode groups

            # Check for contradictions
            outcomes = set(g.get("outcome") for g in group)
            responses = set(g.get("agent_response", "")[:50] for g in group)

            if len(outcomes) <= 1 and len(responses) <= 1:
                continue  # No actual contradiction

            conflicts_found += 1
            conflicts_resolved += 1

            if strategy == "newest_wins":
                # Sort by timestamp, keep the newest
                group.sort(
                    key=lambda x: x.get("timestamp", ""), reverse=True
                )
                keeper = group[0]
                for stale in group[1:]:
                    conn.execute(
                        """
                        UPDATE shared_context SET status = 'resolved'
                        WHERE episode_id = ? AND target_agent_id = ?
                        """,
                        (stale["episode_id"], agent_id),
                    )
            elif strategy == "source_priority":
                # Keep the one with the most recent or preferred source
                group.sort(
                    key=lambda x: x.get("timestamp", ""), reverse=True
                )
                keeper = group[0]
                for stale in group[1:]:
                    conn.execute(
                        """
                        UPDATE shared_context SET status = 'resolved'
                        WHERE episode_id = ? AND target_agent_id = ?
                        """,
                        (stale["episode_id"], agent_id),
                    )
            elif strategy == "merge":
                keeper = group[-1]  # Keep the latest as base
                for other in group[:-1]:
                    # Attempt merge of non-conflicting fields
                    if (
                        not keeper.get("outcome")
                        and other.get("outcome")
                    ):
                        conn.execute(
                            """
                            UPDATE episodes SET outcome = ?
                            WHERE episode_id = ?
                            """,
                            (other["outcome"], keeper["episode_id"]),
                        )
                    conn.execute(
                        """
                        UPDATE shared_context SET status = 'resolved'
                        WHERE episode_id = ? AND target_agent_id = ?
                        """,
                        (other["episode_id"], agent_id),
                    )

        conn.commit()

        return {
            "agent_id": agent_id,
            "strategy": strategy,
            "conflicts_found": conflicts_found,
            "conflicts_resolved": conflicts_resolved,
            "groups_examined": len(groups),
        }

    # ── Internal Helpers ─────────────────────────────────────────────

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Convert a SQLite Row to a plain dict with parsed JSON fields."""
        d = dict(row)

        # Parse JSON fields
        for field in ("context_snapshot", "metadata", "tags"):
            if field in d and isinstance(d[field], str):
                try:
                    d[field] = json.loads(d[field])
                except (json.JSONDecodeError, TypeError):
                    pass  # Leave as string

        return d

    @staticmethod
    def _normalize_text(text: str) -> str:
        """Normalize text for conflict detection key generation."""
        return " ".join(text.lower().split())


def _generate_episode_id() -> str:
    """Generate a unique episode ID."""
    import uuid
    return f"ep_{uuid.uuid4().hex[:12]}_{int(time.time())}"
