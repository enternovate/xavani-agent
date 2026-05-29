# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Procedural Memory — Phase 4 of Xavani Agent.

Learns from repeated patterns by recording task outcomes, identifying
optimal approaches, and building confidence scores over time.

The procedural memory system:
- Records task outcomes with parameters and approaches
- Retrieves the best-known approach for a given task type
- Learns from success (strengthens an approach) and failure (weakens it)
- Identifies patterns by clustering similar successful approaches
- Provides confidence scores for how well the system knows a task type

All data stored in SQLite under ``~/.xavani/data/memory/``.
"""

from __future__ import annotations

import json
import logging
import math
import os
import sqlite3
import threading
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

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
PROCEDURAL_DB_PATH = MEMORY_DIR / "procedural.db"

# Confidence thresholds
HIGH_CONFIDENCE_EXAMPLES = 10
MEDIUM_CONFIDENCE_EXAMPLES = 5

# Approach weights
SUCCESS_WEIGHT = 1.0
FAILURE_PENALTY = 0.5
LEARNING_RATE = 0.3

# Pattern clustering
SIMILARITY_THRESHOLD = 0.6  # Cosine similarity threshold for clustering


# ---------------------------------------------------------------------------
# ProceduralMemory
# ---------------------------------------------------------------------------


class ProceduralMemory:
    """Learns from repeated task outcomes to optimize future behavior.

    Records every task attempt with its parameters, approach, and result.
    Over time, it builds a knowledge base of which approaches work best
    for each task type, with confidence scores, optimization hints, and
    pattern discovery.

    Thread-safe: uses thread-local SQLite connections with WAL mode.
    Survives restarts: all data persisted to ``~/.xavani/data/memory/procedural.db``.
    """

    def __init__(self, db_path: Path = PROCEDURAL_DB_PATH):
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
        return self._local.conn

    def _init_db(self) -> None:
        """Create tables and indexes if they do not exist."""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = self._get_conn()

        # Task outcomes table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS task_outcomes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                outcome_id TEXT UNIQUE NOT NULL,
                task_type TEXT NOT NULL,
                parameters TEXT NOT NULL,
                approach TEXT NOT NULL,
                result TEXT,
                success INTEGER NOT NULL DEFAULT 1,
                duration_ms REAL,
                confidence REAL DEFAULT 1.0,
                feedback TEXT,
                timestamp TEXT NOT NULL,
                agent_id TEXT DEFAULT 'default',
                metadata TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            )
            """
        )

        # Index for fast task_type lookups
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_task_outcomes_type
            ON task_outcomes(task_type)
            """
        )

        # Index for success filtering
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_task_outcomes_success
            ON task_outcomes(task_type, success)
            """
        )

        # Index for timestamp queries
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_task_outcomes_timestamp
            ON task_outcomes(timestamp)
            """
        )

        # Compiled approaches table (reusable patterns)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS compiled_approaches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_id TEXT UNIQUE NOT NULL,
                task_type TEXT NOT NULL,
                approach TEXT NOT NULL,
                success_count INTEGER DEFAULT 0,
                total_count INTEGER DEFAULT 0,
                success_rate REAL DEFAULT 0.0,
                confidence REAL DEFAULT 0.0,
                example_parameters TEXT,
                tags TEXT,
                last_used TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            )
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_compiled_approaches_type
            ON compiled_approaches(task_type)
            """
        )

        # Approach weights table (for learn_from_success/failure)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS approach_weights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_type TEXT NOT NULL,
                approach TEXT NOT NULL,
                weight REAL DEFAULT 1.0,
                success_count INTEGER DEFAULT 0,
                failure_count INTEGER DEFAULT 0,
                last_updated TEXT,
                UNIQUE(task_type, approach)
            )
            """
        )

        conn.commit()

    # ── Recording Outcomes ───────────────────────────────────────────

    def record_outcome(
        self,
        task_type: str,
        parameters: Dict[str, Any],
        result: Any,
        success: bool,
        *,
        approach: Optional[str] = None,
        duration_ms: Optional[float] = None,
        confidence: float = 1.0,
        feedback: Optional[str] = None,
        agent_id: str = "default",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Record the outcome of a task execution.

        Args:
            task_type: Category of task (e.g. "file_search", "code_review",
                "database_query").
            parameters: The parameters/arguments used for this task.
            result: The result of the execution (string or dict).
            success: Whether the task completed successfully.
            approach: Description of the approach taken (auto-generated
                from parameters if not provided).
            duration_ms: How long the task took in milliseconds.
            confidence: How confident the system was about this approach.
            feedback: Any additional feedback about the outcome.
            agent_id: Which agent executed the task.
            metadata: Arbitrary metadata dict.

        Returns:
            The generated outcome ID.
        """
        outcome_id = f"out_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        conn = self._get_conn()

        # Auto-generate an approach string if not provided
        if approach is None:
            approach = self._generate_approach(task_type, parameters)

        conn.execute(
            """
            INSERT INTO task_outcomes
                (outcome_id, task_type, parameters, approach, result,
                 success, duration_ms, confidence, feedback, timestamp,
                 agent_id, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                outcome_id,
                task_type,
                json.dumps(parameters, default=str),
                approach,
                json.dumps(result, default=str) if not isinstance(result, str) else result,
                1 if success else 0,
                duration_ms,
                min(1.0, max(0.0, confidence)),
                feedback,
                now,
                agent_id,
                json.dumps(metadata, default=str) if metadata else None,
            ),
        )

        conn.commit()

        # Update approach weights
        self._update_approach_weight(task_type, approach, success)

        # If successful, update the compiled approach
        if success:
            self._update_compiled_approach(task_type, approach, parameters)

        logger.debug(
            "Recorded outcome for %s: success=%s (outcome_id=%s)",
            task_type, success, outcome_id,
        )
        return outcome_id

    def _generate_approach(
        self,
        task_type: str,
        parameters: Dict[str, Any],
    ) -> str:
        """Generate a canonical approach string from task parameters.

        Uses the parameter keys sorted alphabetically as a signature
        of the approach, making it possible to group similar calls.
        """
        param_keys = sorted(parameters.keys())
        # Include non-default or distinguishing parameter values
        sig_parts = [task_type]
        for key in param_keys[:5]:  # Limit to first 5 keys for signature
            val = parameters[key]
            if isinstance(val, str):
                sig_parts.append(f"{key}={val[:50]}")
            elif isinstance(val, (int, float, bool)):
                sig_parts.append(f"{key}={val}")

        return "::".join(sig_parts)

    # ── Retrieving Best Approaches ───────────────────────────────────

    def get_best_approach(
        self,
        task_type: str,
        parameters: Optional[Dict[str, Any]] = None,
        *,
        min_success_rate: float = 0.5,
        min_examples: int = 1,
    ) -> Dict[str, Any]:
        """Retrieve the most successful approach for a given task type.

        Uses weighted scoring to find the approach with the best track
        record, considering success rate, number of attempts, and
        recency.

        Args:
            task_type: The task type to look up.
            parameters: Optional parameters to match against stored
                approaches (uses best match if provided).
            min_success_rate: Minimum success rate (0.0 to 1.0).
            min_examples: Minimum number of examples required.

        Returns:
            Dict with:
            - ``approach``: The best approach description.
            - ``success_rate``: Its historical success rate.
            - ``total_attempts``: How many times it was tried.
            - ``confidence``: System confidence level.
            - ``example_parameters``: Sample parameters that worked.
            - ``found``: Whether a matching approach was found.

            If no approach meets the criteria, returns ``found=False``.
        """
        conn = self._get_conn()

        # Try compiled approaches first (higher-level patterns)
        rows = conn.execute(
            """
            SELECT * FROM compiled_approaches
            WHERE task_type = ?
              AND success_rate >= ?
              AND total_count >= ?
            ORDER BY (success_rate * total_count * confidence) DESC
            LIMIT 5
            """,
            (task_type, min_success_rate, min_examples),
        ).fetchall()

        if rows:
            best = dict(rows[0])
            best["found"] = True
            best["source"] = "compiled"
            return {
                "approach": best["approach"],
                "success_rate": best["success_rate"],
                "total_attempts": best["total_count"],
                "confidence": best["confidence"],
                "example_parameters": self._safe_json_loads(best.get("example_parameters")),
                "tags": self._safe_json_loads(best.get("tags")),
                "pattern_id": best["pattern_id"],
                "found": True,
                "source": "compiled",
            }

        # Fall back to raw outcomes
        rows = conn.execute(
            """
            SELECT approach,
                   COUNT(*) as total_count,
                   SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success_count,
                   AVG(CASE WHEN success = 1 THEN 1.0 ELSE 0.0 END) as success_rate
            FROM task_outcomes
            WHERE task_type = ?
            GROUP BY approach
            HAVING success_rate >= ? AND total_count >= ?
            ORDER BY (success_rate * total_count) DESC
            LIMIT 1
            """,
            (task_type, min_success_rate, min_examples),
        ).fetchone()

        if rows:
            return {
                "approach": rows["approach"],
                "success_rate": rows["success_rate"],
                "total_attempts": rows["total_count"],
                "confidence": self._compute_confidence(rows["total_count"]),
                "example_parameters": self._get_example_parameters(
                    task_type, rows["approach"]
                ),
                "found": True,
                "source": "raw",
            }

        # If parameters provided, try fuzzy matching
        if parameters:
            param_json = json.dumps(parameters, default=str)
            rows = conn.execute(
                """
                SELECT approach,
                       COUNT(*) as total_count,
                       SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success_count,
                       AVG(CASE WHEN success = 1 THEN 1.0 ELSE 0.0 END) as success_rate
                FROM task_outcomes
                WHERE task_type = ?
                  AND parameters LIKE ?
                GROUP BY approach
                HAVING success_rate >= ?
                ORDER BY (success_rate * total_count) DESC
                LIMIT 1
                """,
                (
                    task_type,
                    f"%{self._param_fragment(parameters)}%",
                    min_success_rate,
                ),
            ).fetchone()

            if rows:
                return {
                    "approach": rows["approach"],
                    "success_rate": rows["success_rate"],
                    "total_attempts": rows["total_count"],
                    "confidence": self._compute_confidence(rows["total_count"]),
                    "found": True,
                    "source": "parameter_match",
                }

        return {
            "found": False,
            "approach": None,
            "success_rate": 0.0,
            "total_attempts": 0,
            "confidence": 0.0,
        }

    def get_all_approaches(
        self,
        task_type: str,
        *,
        min_examples: int = 1,
        sort_by: str = "success_rate",
    ) -> List[Dict[str, Any]]:
        """Get all approaches for a task type with their statistics.

        Args:
            task_type: The task type to query.
            min_examples: Minimum number of examples for an approach to be included.
            sort_by: Sort field (``success_rate``, ``total_count``, or ``confidence``).

        Returns:
            List of approach summary dicts.
        """
        conn = self._get_conn()

        sort_map = {
            "success_rate": "success_rate DESC",
            "total_count": "total_count DESC",
            "confidence": "confidence DESC",
        }
        order = sort_map.get(sort_by, "success_rate DESC")

        rows = conn.execute(
            f"""
            SELECT approach,
                   COUNT(*) as total_count,
                   SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success_count,
                   AVG(CASE WHEN success = 1 THEN 1.0 ELSE 0.0 END) as success_rate,
                   MAX(timestamp) as last_used
            FROM task_outcomes
            WHERE task_type = ?
            GROUP BY approach
            HAVING total_count >= ?
            ORDER BY {order}
            """,
            (task_type, min_examples),
        ).fetchall()

        results = []
        for row in rows:
            d = dict(row)
            d["confidence"] = self._compute_confidence(d["total_count"])
            results.append(d)

        return results

    # ── Optimization Hints ───────────────────────────────────────────

    def get_optimization_hints(
        self,
        *,
        min_attempts: int = 3,
    ) -> List[Dict[str, Any]]:
        """Returns patterns that suggest better approaches.

        Identifies task types where:
        - Success rate is below 50% (needs improvement)
        - A different approach has significantly better outcomes
        - The system has low confidence (few examples)
        - Duration is high relative to other approaches

        Args:
            min_attempts: Minimum total attempts to consider.

        Returns:
            List of hint dicts with task_type, current approach,
            recommended approach, reason, and potential improvement.
        """
        conn = self._get_conn()

        hints: List[Dict[str, Any]] = []

        # 1. Low success rate tasks
        rows = conn.execute(
            """
            SELECT task_type,
                   COUNT(*) as total_count,
                   SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success_count,
                   AVG(CASE WHEN success = 1 THEN 1.0 ELSE 0.0 END) as success_rate
            FROM task_outcomes
            GROUP BY task_type
            HAVING total_count >= ? AND success_rate < 0.5
            ORDER BY success_rate ASC
            """,
            (min_attempts,),
        ).fetchall()

        for row in rows:
            hints.append({
                "task_type": row["task_type"],
                "current_success_rate": round(row["success_rate"], 2),
                "total_attempts": row["total_count"],
                "type": "low_success_rate",
                "reason": f"Success rate is only {row['success_rate']:.0%} "
                         f"across {row['total_count']} attempts",
                "suggestion": "Consider trying a different approach for this task type",
            })

        # 2. Approach disparity — one approach much better than others
        types = conn.execute(
            """
            SELECT DISTINCT task_type FROM task_outcomes
            """
        ).fetchall()

        for t in types:
            tt = t["task_type"]
            approach_stats = conn.execute(
                """
                SELECT approach,
                       COUNT(*) as total_count,
                       SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success_count,
                       AVG(CASE WHEN success = 1 THEN 1.0 ELSE 0.0 END) as success_rate
                FROM task_outcomes
                WHERE task_type = ?
                GROUP BY approach
                HAVING total_count >= ?
                """,
                (tt, min_attempts),
            ).fetchall()

            if len(approach_stats) >= 2:
                sorted_stats = sorted(
                    approach_stats, key=lambda r: r["success_rate"], reverse=True
                )
                best = sorted_stats[0]
                worst = sorted_stats[-1]

                if best["success_rate"] - worst["success_rate"] > 0.3:
                    hints.append({
                        "task_type": tt,
                        "best_approach": best["approach"],
                        "best_success_rate": round(best["success_rate"], 2),
                        "worst_approach": worst["approach"],
                        "worst_success_rate": round(worst["success_rate"], 2),
                        "type": "approach_disparity",
                        "reason": f"Approach '{best['approach'][:40]}...' "
                                 f"({best['success_rate']:.0%}) significantly "
                                 f"outperforms '{worst['approach'][:40]}...' "
                                 f"({worst['success_rate']:.0%})",
                        "suggestion": f"Use the '{best['approach'][:40]}...' approach",
                    })

        # 3. Low confidence (few examples) — needs more exploration
        rows3 = conn.execute(
            """
            SELECT task_type, COUNT(*) as total_count
            FROM task_outcomes
            GROUP BY task_type
            HAVING total_count < ?
            ORDER BY total_count ASC
            """,
            (HIGH_CONFIDENCE_EXAMPLES,),
        ).fetchall()

        for row in rows3[:5]:  # Limit to top 5
            hints.append({
                "task_type": row["task_type"],
                "total_attempts": row["total_count"],
                "type": "low_confidence",
                "reason": f"Only {row['total_count']} examples — "
                         f"need {HIGH_CONFIDENCE_EXAMPLES} for high confidence",
                "suggestion": "Gather more examples to improve confidence",
            })

        return hints

    # ── Confidence Scoring ───────────────────────────────────────────

    def confidence_score(self, task_type: str) -> Dict[str, Any]:
        """How confident the system is about handling a given task type.

        Confidence is based on:
        - Number of examples (>10 = high, >5 = medium, else low)
        - Success rate (higher = more confident)
        - Consistency across approaches (consistent = more confident)

        Args:
            task_type: The task type to evaluate.

        Returns:
            Dict with ``level`` (high/medium/low), ``score`` (0.0-1.0),
            ``total_examples``, ``success_rate``, and ``explanation``.
        """
        conn = self._get_conn()

        row = conn.execute(
            """
            SELECT COUNT(*) as total_count,
                   SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success_count,
                   AVG(CASE WHEN success = 1 THEN 1.0 ELSE 0.0 END) as success_rate
            FROM task_outcomes
            WHERE task_type = ?
            """,
            (task_type,),
        ).fetchone()

        if row is None or row["total_count"] == 0:
            return {
                "level": "none",
                "score": 0.0,
                "total_examples": 0,
                "success_rate": 0.0,
                "explanation": f"No examples recorded for '{task_type}'",
            }

        total = row["total_count"]
        success_rate = row["success_rate"] or 0.0

        # Compute confidence score
        example_factor = min(1.0, total / HIGH_CONFIDENCE_EXAMPLES)
        success_factor = success_rate
        consistency_factor = self._compute_consistency(task_type)

        score = example_factor * 0.4 + success_factor * 0.4 + consistency_factor * 0.2

        if total >= HIGH_CONFIDENCE_EXAMPLES and score >= 0.7:
            level = "high"
            explanation = f"High confidence ({total} examples, {success_rate:.0%} success rate)"
        elif total >= MEDIUM_CONFIDENCE_EXAMPLES and score >= 0.4:
            level = "medium"
            explanation = f"Medium confidence ({total} examples, {success_rate:.0%} success rate)"
        else:
            level = "low"
            explanation = f"Low confidence ({total} examples, {success_rate:.0%} success rate)"

        return {
            "level": level,
            "score": round(score, 3),
            "total_examples": total,
            "success_rate": round(success_rate, 3),
            "explanation": explanation,
            "breakdown": {
                "example_factor": round(example_factor, 3),
                "success_factor": round(success_factor, 3),
                "consistency_factor": round(consistency_factor, 3),
            },
        }

    def _compute_confidence(self, total_examples: int) -> float:
        """Compute a confidence score from the number of examples."""
        if total_examples >= HIGH_CONFIDENCE_EXAMPLES:
            return 1.0
        elif total_examples >= MEDIUM_CONFIDENCE_EXAMPLES:
            return 0.6
        elif total_examples >= 2:
            return 0.3
        return 0.1

    def _compute_consistency(self, task_type: str) -> float:
        """Compute how consistent the outcomes are for a task type."""
        conn = self._get_conn()

        rows = conn.execute(
            """
            SELECT approach,
                   COUNT(*) as total_count,
                   SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success_count
            FROM task_outcomes
            WHERE task_type = ?
            GROUP BY approach
            """,
            (task_type,),
        ).fetchall()

        if len(rows) <= 1:
            return 1.0  # Single approach = perfectly consistent

        # Compute variance in success rates
        rates = []
        for r in rows:
            if r["total_count"] > 0:
                rates.append(r["success_count"] / r["total_count"])

        if not rates:
            return 0.0

        mean = sum(rates) / len(rates)
        variance = sum((r - mean) ** 2 for r in rates) / len(rates)

        # Low variance = high consistency
        consistency = max(0.0, 1.0 - math.sqrt(variance))
        return consistency

    # ── Learning from Feedback ───────────────────────────────────────

    def learn_from_success(
        self,
        task_type: str,
        approach: str,
        *,
        weight: float = SUCCESS_WEIGHT,
    ) -> Dict[str, Any]:
        """Strengthen an approach based on a successful outcome.

        Increases the weight of the approach and updates the compiled
        pattern for this task type.

        Args:
            task_type: The task type.
            approach: The approach that succeeded.
            weight: How much to strengthen (default 1.0).

        Returns:
            Updated approach weight info.
        """
        conn = self._get_conn()
        now = datetime.now(timezone.utc).isoformat()

        conn.execute(
            """
            INSERT INTO approach_weights (task_type, approach, weight,
                success_count, failure_count, last_updated)
            VALUES (?, ?, ?, 1, 0, ?)
            ON CONFLICT(task_type, approach) DO UPDATE SET
                weight = MIN(10.0, weight + ?),
                success_count = success_count + 1,
                last_updated = ?
            """,
            (task_type, approach, 1.0 + weight, now, weight, now),
        )

        conn.commit()

        # Fetch updated weight
        row = conn.execute(
            """
            SELECT * FROM approach_weights
            WHERE task_type = ? AND approach = ?
            """,
            (task_type, approach),
        ).fetchone()

        return dict(row) if row else {"task_type": task_type, "approach": approach, "weight": 1.0}

    def learn_from_failure(
        self,
        task_type: str,
        approach: str,
        *,
        penalty: float = FAILURE_PENALTY,
    ) -> Dict[str, Any]:
        """Weaken an approach based on a failed outcome.

        Decreases the weight of the approach, making it less likely to
        be recommended in the future.

        Args:
            task_type: The task type.
            approach: The approach that failed.
            penalty: How much to weaken (default 0.5).

        Returns:
            Updated approach weight info.
        """
        conn = self._get_conn()
        now = datetime.now(timezone.utc).isoformat()

        conn.execute(
            """
            INSERT INTO approach_weights (task_type, approach, weight,
                success_count, failure_count, last_updated)
            VALUES (?, ?, ?, 0, 1, ?)
            ON CONFLICT(task_type, approach) DO UPDATE SET
                weight = MAX(0.1, weight - ?),
                failure_count = failure_count + 1,
                last_updated = ?
            """,
            (task_type, approach, 1.0 - penalty, now, penalty, now),
        )

        conn.commit()

        # Fetch updated weight
        row = conn.execute(
            """
            SELECT * FROM approach_weights
            WHERE task_type = ? AND approach = ?
            """,
            (task_type, approach),
        ).fetchone()

        return dict(row) if row else {"task_type": task_type, "approach": approach, "weight": 0.5}

    # ── Pattern Identification ───────────────────────────────────────

    def identify_patterns(
        self,
        *,
        min_examples: int = 3,
        min_similarity: float = SIMILARITY_THRESHOLD,
    ) -> List[Dict[str, Any]]:
        """Cluster similar successful approaches into reusable patterns.

        Identifies groups of approaches that follow the same underlying
        pattern and compiles them into reusable, generalizable strategies.

        Args:
            min_examples: Minimum examples to form a pattern.
            min_similarity: Minimum similarity score for clustering.

        Returns:
            List of identified pattern dicts with:
            - ``task_type``: The task type
            - ``pattern_approach``: The generalized approach description
            - ``example_count``: Number of examples in this pattern
            - ``success_rate``: Success rate across examples
            - ``variants``: Different approach variants clustered
            - ``confidence``: Pattern confidence score
        """
        conn = self._get_conn()

        # Get all task types with enough examples
        rows = conn.execute(
            """
            SELECT task_type,
                   COUNT(*) as total_count,
                   SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success_count
            FROM task_outcomes
            GROUP BY task_type
            HAVING total_count >= ?
            """,
            (min_examples,),
        ).fetchall()

        patterns: List[Dict[str, Any]] = []

        for row in rows:
            task_type = row["task_type"]
            total_count = row["total_count"]
            success_count = row["success_count"]

            # Get approaches for this task type
            app_rows = conn.execute(
                """
                SELECT approach,
                       COUNT(*) as total_count,
                       SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success_count
                FROM task_outcomes
                WHERE task_type = ?
                GROUP BY approach
                ORDER BY total_count DESC
                """,
                (task_type,),
            ).fetchall()

            if len(app_rows) < 2:
                continue  # Need at least 2 approaches to find patterns

            # Cluster by approach similarity
            clusters = self._cluster_approaches(
                [(r["approach"], r["total_count"], r["success_count"]) for r in app_rows],
                min_similarity,
            )

            for cluster in clusters:
                if cluster["count"] < min_examples:
                    continue

                pattern_approach = self._generalize_approach(
                    cluster["approaches"]
                )

                patterns.append({
                    "task_type": task_type,
                    "pattern_approach": pattern_approach,
                    "example_count": cluster["count"],
                    "success_rate": round(cluster["success_rate"], 3),
                    "variants": cluster["approaches"],
                    "confidence": round(
                        self._compute_confidence(cluster["count"]), 3
                    ),
                })

        # Save identified patterns to compiled_approaches table
        for pattern in patterns:
            self._save_pattern(pattern)

        return patterns

    def _cluster_approaches(
        self,
        approaches: List[Tuple[str, int, int]],
        min_similarity: float,
    ) -> List[Dict[str, Any]]:
        """Cluster approaches by textual and structural similarity.

        Simple clustering using shared tokens and structural features.
        """
        if not approaches:
            return []

        clusters: List[Dict[str, Any]] = []
        used: Set[int] = set()

        for i, (approach_i, count_i, success_i) in enumerate(approaches):
            if i in used:
                continue

            cluster_approaches = [approach_i]
            cluster_count = count_i
            cluster_success = success_i
            used.add(i)

            for j, (approach_j, count_j, success_j) in enumerate(approaches):
                if j in used:
                    continue

                similarity = self._approach_similarity(
                    approach_i, approach_j
                )
                if similarity >= min_similarity:
                    cluster_approaches.append(approach_j)
                    cluster_count += count_j
                    cluster_success += success_j
                    used.add(j)

            clusters.append({
                "approaches": cluster_approaches,
                "count": cluster_count,
                "success_rate": cluster_success / cluster_count if cluster_count > 0 else 0.0,
            })

        return clusters

    def _approach_similarity(self, a: str, b: str) -> float:
        """Compute similarity between two approach strings.

        Uses Jaccard similarity on token sets plus structure matching.
        """
        # Token-based Jaccard similarity
        tokens_a = set(a.lower().replace("::", " ").replace("=", " ").split())
        tokens_b = set(b.lower().replace("::", " ").replace("=", " ").split())

        if not tokens_a or not tokens_b:
            return 0.0

        intersection = tokens_a & tokens_b
        union = tokens_a | tokens_b
        jaccard = len(intersection) / len(union) if union else 0.0

        # Structural similarity (same key-value structure)
        parts_a = a.split("::")
        parts_b = b.split("::")

        structure_score = 0.0
        if parts_a and parts_b:
            # First parts should match (task type)
            if parts_a[0] == parts_b[0]:
                structure_score += 0.3
            # Same number of parts = similar structure
            if len(parts_a) == len(parts_b):
                structure_score += 0.2

        return min(1.0, jaccard * 0.7 + structure_score * 0.3)

    def _generalize_approach(self, approaches: List[str]) -> str:
        """Generalize multiple approach variants into a single pattern.

        Extracts the common parts and replaces varying parts with
        placeholders.
        """
        if not approaches:
            return ""
        if len(approaches) == 1:
            return approaches[0] + " (generalized)"

        # Tokenize all approaches
        token_sets = [
            set(a.lower().replace("::", " ").split())
            for a in approaches
        ]

        # Find common tokens
        common = token_sets[0]
        for ts in token_sets[1:]:
            common &= ts

        common_str = " ".join(sorted(common)) if common else approaches[0]
        return f"{common_str} (pattern from {len(approaches)} variants)"

    def _save_pattern(self, pattern: Dict[str, Any]) -> None:
        """Save or update a compiled pattern in the database."""
        conn = self._get_conn()
        pattern_id = f"pat_{uuid.uuid4().hex[:12]}"

        conn.execute(
            """
            INSERT OR REPLACE INTO compiled_approaches
                (pattern_id, task_type, approach, success_count, total_count,
                 success_rate, confidence, example_parameters, tags, last_used)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                pattern_id,
                pattern["task_type"],
                pattern["pattern_approach"],
                int(pattern["success_rate"] * pattern["example_count"]),
                pattern["example_count"],
                pattern["success_rate"],
                pattern["confidence"],
                json.dumps(pattern.get("variants", [])[:3]),
                json.dumps(["learned", "pattern"]),
                datetime.now(timezone.utc).isoformat(),
            ),
        )

        conn.commit()

    # ── Internal Helpers ─────────────────────────────────────────────

    def _update_approach_weight(
        self,
        task_type: str,
        approach: str,
        success: bool,
    ) -> None:
        """Update the weight for a (task_type, approach) pair."""
        conn = self._get_conn()
        now = datetime.now(timezone.utc).isoformat()

        if success:
            conn.execute(
                """
                INSERT INTO approach_weights (task_type, approach, weight,
                    success_count, failure_count, last_updated)
                VALUES (?, ?, ?, 1, 0, ?)
                ON CONFLICT(task_type, approach) DO UPDATE SET
                    weight = MIN(10.0, weight + ?),
                    success_count = success_count + 1,
                    last_updated = ?
                """,
                (task_type, approach, 1.0, now, LEARNING_RATE, now),
            )
        else:
            conn.execute(
                """
                INSERT INTO approach_weights (task_type, approach, weight,
                    success_count, failure_count, last_updated)
                VALUES (?, ?, ?, 0, 1, ?)
                ON CONFLICT(task_type, approach) DO UPDATE SET
                    weight = MAX(0.1, weight - ? * 0.5),
                    failure_count = failure_count + 1,
                    last_updated = ?
                """,
                (task_type, approach, 1.0, now, LEARNING_RATE, now),
            )

        conn.commit()

    def _update_compiled_approach(
        self,
        task_type: str,
        approach: str,
        parameters: Dict[str, Any],
    ) -> None:
        """Update or create a compiled approach entry."""
        conn = self._get_conn()

        existing = conn.execute(
            """
            SELECT * FROM compiled_approaches
            WHERE task_type = ? AND approach = ?
            """,
            (task_type, approach),
        ).fetchone()

        now = datetime.now(timezone.utc).isoformat()

        if existing:
            new_total = existing["total_count"] + 1
            new_success = existing["success_count"] + 1
            success_rate = new_success / new_total
            confidence = self._compute_confidence(new_total)

            conn.execute(
                """
                UPDATE compiled_approaches SET
                    success_count = ?,
                    total_count = ?,
                    success_rate = ?,
                    confidence = ?,
                    last_used = ?
                WHERE id = ?
                """,
                (new_success, new_total, success_rate, confidence, now, existing["id"]),
            )
        else:
            pattern_id = f"pat_{uuid.uuid4().hex[:12]}"
            conn.execute(
                """
                INSERT INTO compiled_approaches
                    (pattern_id, task_type, approach, success_count, total_count,
                     success_rate, confidence, example_parameters, last_used)
                VALUES (?, ?, ?, 1, 1, 1.0, 0.3, ?, ?)
                """,
                (
                    pattern_id,
                    task_type,
                    approach,
                    json.dumps(parameters, default=str),
                    now,
                ),
            )

        conn.commit()

    def _get_example_parameters(
        self,
        task_type: str,
        approach: str,
    ) -> Optional[Dict[str, Any]]:
        """Get example parameters for a specific approach."""
        conn = self._get_conn()

        row = conn.execute(
            """
            SELECT parameters FROM task_outcomes
            WHERE task_type = ? AND approach = ? AND success = 1
            ORDER BY timestamp DESC LIMIT 1
            """,
            (task_type, approach),
        ).fetchone()

        if row:
            return self._safe_json_loads(row["parameters"])
        return None

    @staticmethod
    def _param_fragment(parameters: Dict[str, Any]) -> str:
        """Create a search fragment from parameters."""
        # Use first significant string value
        for key, val in parameters.items():
            if isinstance(val, str) and len(val) > 3:
                return val[:50]
        return ""

    @staticmethod
    def _safe_json_loads(value: Any) -> Any:
        """Safely load JSON, returning None on failure."""
        if value is None:
            return None
        if isinstance(value, (dict, list)):
            return value
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError, ValueError):
            return value

    # ── Maintenance ──────────────────────────────────────────────────

    def stats(self) -> Dict[str, Any]:
        """Get statistics about the procedural memory store.

        Returns:
            Dict with ``total_outcomes``, ``task_types``, ``approaches``,
            ``patterns``, ``success_rate``, ``by_type``.
        """
        conn = self._get_conn()

        total = conn.execute(
            "SELECT COUNT(*) as c FROM task_outcomes"
        ).fetchone()["c"]

        task_types_count = conn.execute(
            "SELECT COUNT(DISTINCT task_type) as c FROM task_outcomes"
        ).fetchone()["c"]

        approach_count = conn.execute(
            "SELECT COUNT(DISTINCT approach) as c FROM task_outcomes"
        ).fetchone()["c"]

        pattern_count = conn.execute(
            "SELECT COUNT(*) as c FROM compiled_approaches"
        ).fetchone()["c"]

        success_row = conn.execute(
            """
            SELECT AVG(CASE WHEN success = 1 THEN 1.0 ELSE 0.0 END) as rate
            FROM task_outcomes
            """
        ).fetchone()
        success_rate = success_row["rate"] if success_row else 0.0

        # Per-type breakdown (top 10 by count)
        by_type_rows = conn.execute(
            """
            SELECT task_type,
                   COUNT(*) as count,
                   AVG(CASE WHEN success = 1 THEN 1.0 ELSE 0.0 END) as success_rate
            FROM task_outcomes
            GROUP BY task_type
            ORDER BY count DESC
            LIMIT 10
            """
        ).fetchall()

        return {
            "total_outcomes": total,
            "unique_task_types": task_types_count,
            "unique_approaches": approach_count,
            "compiled_patterns": pattern_count,
            "overall_success_rate": round(success_rate, 3) if success_rate else 0.0,
            "top_types": [
                {"task_type": r["task_type"], "count": r["count"],
                 "success_rate": round(r["success_rate"], 3)}
                for r in by_type_rows
            ],
        }

    def clear_task_type(self, task_type: str) -> int:
        """Remove all records for a specific task type.

        Args:
            task_type: The task type to clear.

        Returns:
            Number of records removed.
        """
        conn = self._get_conn()
        count = conn.execute(
            "DELETE FROM task_outcomes WHERE task_type = ?",
            (task_type,),
        ).rowcount
        conn.execute(
            "DELETE FROM approach_weights WHERE task_type = ?",
            (task_type,),
        )
        conn.execute(
            "DELETE FROM compiled_approaches WHERE task_type = ?",
            (task_type,),
        )
        conn.commit()
        return count

    def clear_all(self) -> int:
        """Clear all procedural memory.

        Returns:
            Number of outcomes removed.
        """
        conn = self._get_conn()
        count = conn.execute(
            "SELECT COUNT(*) as c FROM task_outcomes"
        ).fetchone()["c"]
        conn.execute("DELETE FROM task_outcomes")
        conn.execute("DELETE FROM approach_weights")
        conn.execute("DELETE FROM compiled_approaches")
        conn.commit()
        logger.warning("Cleared all %d procedural memory records", count)
        return count
