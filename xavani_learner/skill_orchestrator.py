# Copyright (c) 2025-2026 Enternovate. All rights reserved.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Skill Orchestrator — Phase 7 of Xavani Agent.

The SkillOrchestrator provides intelligent skill matching from the 169
built-in skills. It scans user messages for keywords matching skill
descriptions, ranks skills by relevance, loads skill context, and
suggests skills the user hasn't tried but would benefit from.

Key capabilities:
- **load_relevant_skills(message)**: Scans user message, finds matching skills.
- **get_skill_context(skill_names)**: Loads skill content for the agent.
- **rank_skills_by_relevance(message, limit)**: Returns most relevant skills.
- **get_user_skill_affinities()**: Returns skills the user tends to use.
- **suggest_skill(message)**: Recommends a skill the user hasn't tried yet.

Skills are loaded from ``oag_skills/MANIFEST.json`` using keyword + category
matching against skill descriptions.

Usage:
    orch = SkillOrchestrator()
    skills = orch.rank_skills_by_relevance("build a trading bot")
    context = orch.get_skill_context(["stocks", "hyperliquid"])
    suggestion = orch.suggest_skill("I want to make a website")
"""

from __future__ import annotations

import json
import logging
import os
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

XAVANI_HOME = Path(os.environ.get("XAVANI_HOME", "~/.xavani")).expanduser()

# Auto-detect manifest path: first check relative to repo, then ~/.xavani
_REPO_MANIFEST = (
    Path(__file__).resolve().parent.parent / "oag_skills" / "MANIFEST.json"
)
_XAVANI_MANIFEST = XAVANI_HOME / "skills" / "MANIFEST.json"
_OAG_MANIFEST = Path(os.environ.get(
    "XAVANI_SKILLS_MANIFEST",
    str(_REPO_MANIFEST if _REPO_MANIFEST.exists() else _XAVANI_MANIFEST),
))

# Stop words for similarity scoring
_STOP_WORDS: set = {
    "a", "an", "the", "in", "on", "at", "to", "for", "of", "with",
    "and", "or", "but", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "shall", "can",
    "use", "using", "used", "via", "by", "as", "from", "this",
    "that", "these", "those", "it", "its", "you", "your", "they",
    "them", "their", "we", "our", "i", "me", "my", "not", "no",
    "just", "like", "get", "got", "make", "made", "want", "need",
    "also", "very", "really", "quite", "some", "any", "all", "each",
    "every", "both", "few", "more", "most", "other", "such", "only",
    "own", "same", "so", "than", "too", "very", "just", "about",
    "above", "after", "again", "against", "below", "between",
    "during", "without", "throughout", "because", "before",
}

# Weight boost categories (skills in these categories get a priority boost
# for "build" type intent messages)
_BUILD_CATEGORIES: set = {
    "web-development", "software-development", "creative", "mlops",
    "blockchain", "productivity", "gaming",
}


# ---------------------------------------------------------------------------
# SkillOrchestrator
# ---------------------------------------------------------------------------


class SkillOrchestrator:
    """Intelligent skill matcher against the 169 built-in skills.

    Provides ranking, loading, context fetching, and suggestion for skills
    based on user messages and their learning profile.

    Thread-safe: read-only after construction; manifest is loaded once and
    cached. Uses no locks (immutable skill index after init).
    """

    def __init__(
        self,
        manifest_path: Optional[Path] = None,
        profile=None,  # Optional UserProfile — avoid circular import at class level
    ) -> None:
        """Initialize the skill orchestrator.

        Args:
            manifest_path: Path to the ``MANIFEST.json`` file. Auto-detected
                           if not provided.
            profile: An optional ``UserProfile`` instance for personalizing
                     skill suggestions.
        """
        self._manifest_path = manifest_path or _OAG_MANIFEST
        self._profile = profile

        # Cached skill index
        self._skills: List[Dict[str, Any]] = []
        self._skills_by_name: Dict[str, Dict[str, Any]] = {}
        self._skills_by_category: Dict[str, List[Dict[str, Any]]] = {}
        self._keyword_index: Dict[str, List[Tuple[str, float]]] = {}
        self._loaded = False

        # Build index on construction
        self._load_and_index()

    # ── Indexing ─────────────────────────────────────────────────────

    def _load_and_index(self) -> None:
        """Load the manifest and build all search indexes."""
        try:
            if self._manifest_path.exists():
                with open(self._manifest_path, "r", encoding="utf-8") as f:
                    manifest = json.load(f)
            else:
                logger.warning("Skill manifest not found at %s", self._manifest_path)
                manifest = {"skills": []}
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to load skill manifest: %s", exc)
            manifest = {"skills": []}

        self._skills = manifest.get("skills", [])
        self._build_indexes()
        self._loaded = True

        logger.debug(
            "Indexed %d skills from %s",
            len(self._skills),
            self._manifest_path,
        )

    def _build_indexes(self) -> None:
        """Build search indexes from the loaded skill list."""
        by_name: Dict[str, Dict[str, Any]] = {}
        by_category: Dict[str, List[Dict[str, Any]]] = {}
        kw_index: Dict[str, List[Tuple[str, float]]] = defaultdict(list)

        for skill in self._skills:
            name = skill.get("name", "")
            description = skill.get("description", "")
            category = skill.get("category", "")

            by_name[name] = skill

            # Category index
            if category:
                if category not in by_category:
                    by_category[category] = []
                by_category[category].append(skill)

            # Keyword index — extract significant words from name and description
            self._index_keywords(kw_index, name, name_weight=3.0)
            self._index_keywords(kw_index, description, name_weight=1.0)

        self._skills_by_name = by_name
        self._skills_by_category = dict(by_category)
        self._keyword_index = dict(kw_index)

    def _index_keywords(
        self,
        index: Dict[str, List[Tuple[str, float]]],
        text: str,
        name_weight: float = 1.0,
    ) -> None:
        """Add significant words from text to the keyword index."""
        text_lower = text.lower()
        words = re.findall(r"[a-z][a-z0-9]+(?:[-_][a-z0-9]+)*", text_lower)
        for word in words:
            if word not in _STOP_WORDS and len(word) > 2:
                # Don't add duplicate entries for same skill name
                existing = [s for s, _ in index.get(word, [])]
                # We can't easily check without storing skill name; just append
                pass

        # Simpler approach: just track word -> skill_name with weight
        for skill in self._skills:
            skill_name = skill.get("name", "")
            desc = skill.get("description", "")
            cat = skill.get("category", "")

            combined = f"{skill_name} {desc} {cat}".lower()
            words = set(re.findall(r"[a-z][a-z0-9]+(?:[-_][a-z0-9]+)*", combined))
            for w in words:
                if w not in _STOP_WORDS and len(w) > 2:
                    # Weight: 3 for name match, 2 for category, 1 for description
                    weight = 1.0
                    if w in skill_name.lower():
                        weight = 3.0
                    elif w in cat.lower():
                        weight = 2.0
                    index[w].append((skill_name, weight))

    # ── Core Query Methods ───────────────────────────────────────────

    def load_relevant_skills(self, message: str) -> List[Dict[str, Any]]:
        """Find all skills relevant to a user message.

        Scans the message against the keyword index and returns all
        matched skills with their metadata.

        Args:
            message: The user message to match against.

        Returns:
            List of skill dicts with name, description, category, and
            a ``_relevance_score`` field.
        """
        if not self._loaded or not self._skills:
            return []

        msg_lower = message.lower()
        msg_words = set(
            w for w in re.findall(r"[a-z][a-z0-9]+(?:[-_][a-z0-9]+)*", msg_lower)
            if w not in _STOP_WORDS and len(w) > 2
        )

        # Score each skill
        scored: Dict[str, float] = {}
        for skill in self._skills:
            name = skill.get("name", "")
            score = self._score_skill(message, name, skill.get("description", ""),
                                      skill.get("category", ""))
            if score > 0:
                scored[name] = score

        # Build result list
        results: List[Dict[str, Any]] = []
        for name, score in sorted(scored.items(), key=lambda x: x[1], reverse=True):
            skill = self._skills_by_name.get(name)
            if skill:
                result = dict(skill)
                result["_relevance_score"] = round(score, 2)
                results.append(result)

        return results

    def get_skill_context(self, skill_names: List[str]) -> Dict[str, Any]:
        """Load metadata and context for specific skills.

        Looks up each skill by name and returns its full metadata.

        Args:
            skill_names: List of skill names to look up.

        Returns:
            Dict mapping skill name -> skill metadata dict.
            Skills not found are omitted from the result.
        """
        result: Dict[str, Any] = {}
        for name in skill_names:
            skill = self._skills_by_name.get(name)
            if skill:
                result[name] = {
                    "name": skill.get("name"),
                    "description": skill.get("description"),
                    "category": skill.get("category"),
                    "path": self._get_skill_path(name),
                }
        return result

    def rank_skills_by_relevance(
        self,
        message: str,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Return the most relevant skills for a user message.

        Args:
            message: The user message to match against.
            limit: Maximum number of skills to return (default 5).

        Returns:
            List of top-N skill dicts with ``_relevance_score``, sorted by
            relevance descending.
        """
        all_skills = self.load_relevant_skills(message)
        return all_skills[:limit]

    # ── User Affinities ─────────────────────────────────────────────

    def get_user_skill_affinities(self) -> List[Dict[str, Any]]:
        """Return skills the user tends to use, ordered by affinity.

        If a ``UserProfile`` was provided at construction, returns skills
        the user has used the most. Otherwise returns an empty list.

        Returns:
            List of skill dicts with usage count metadata.
        """
        if not self._profile:
            return []

        try:
            affinities = self._profile.skill_affinities
        except Exception as exc:
            logger.warning("Failed to get skill affinities: %s", exc)
            return []

        results: List[Dict[str, Any]] = []
        for skill_name, count in sorted(
            affinities.items(), key=lambda x: x[1], reverse=True
        ):
            skill = self._skills_by_name.get(skill_name)
            if skill:
                result = dict(skill)
                result["_usage_count"] = count
                results.append(result)

        return results

    # ── Skill Suggestions ────────────────────────────────────────────

    def suggest_skill(self, message: str) -> Optional[Dict[str, Any]]:
        """Recommend a skill the user hasn't tried but would benefit from.

        Analyzes the message to determine what the user wants to do,
        then finds a relevant skill they haven't used yet.

        Args:
            message: The user message context.

        Returns:
            A single skill dict with an explanation, or ``None`` if no
            good suggestion can be made.
        """
        if not self._loaded or not self._skills:
            return None

        # Get already-used skills
        used_skills: Set[str] = set()
        if self._profile:
            try:
                used_skills = set(self._profile.skill_affinities.keys())
            except Exception:
                pass

        # Score all skills the user hasn't used
        candidates: List[Tuple[str, float]] = []
        for skill in self._skills:
            name = skill.get("name", "")
            if name in used_skills:
                continue

            desc = skill.get("description", "")
            category = skill.get("category", "")
            score = self._score_skill(message, name, desc, category)

            if score > 0:
                candidates.append((name, score))

        if not candidates:
            return None

        # Sort by relevance and pick the best
        candidates.sort(key=lambda x: x[1], reverse=True)
        best_name = candidates[0][0]
        best_score = candidates[0][1]

        # Only suggest if relevance is meaningful
        if best_score < 3:
            return None

        best_skill = self._skills_by_name.get(best_name)
        if not best_skill:
            return None

        result = dict(best_skill)
        result["_relevance_score"] = best_score
        result["_reason"] = self._generate_suggestion_reason(
            best_skill, message
        )
        return result

    def _generate_suggestion_reason(
        self,
        skill: Dict[str, Any],
        message: str,
    ) -> str:
        """Generate a human-readable reason for suggesting a skill."""
        name = skill.get("name", "")
        description = skill.get("description", "")
        category = skill.get("category", "")

        # Truncate description for readability
        if len(description) > 80:
            desc_short = description[:77] + "..."
        else:
            desc_short = description

        return (
            f"Based on your request, I think you'd benefit from the "
            f"**{name}** skill ({category}): {desc_short}"
        )

    # ── Skill Matching Helpers ───────────────────────────────────────

    def match_skills_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Get all skills in a given category.

        Args:
            category: The skill category to filter by.

        Returns:
            List of skill dicts in that category.
        """
        return list(self._skills_by_category.get(category, []))

    def get_all_categories(self) -> List[str]:
        """Get a sorted list of all skill categories."""
        return sorted(self._skills_by_category.keys())

    def get_category_counts(self) -> Dict[str, int]:
        """Get the number of skills in each category."""
        return {
            cat: len(skills)
            for cat, skills in self._skills_by_category.items()
        }

    def search_skills(self, query: str) -> List[Dict[str, Any]]:
        """Free-text search across all skills.

        Args:
            query: Search query string.

        Returns:
            List of matching skill dicts with ``_relevance_score``.
        """
        return self.load_relevant_skills(query)

    def _score_skill(
        self,
        message: str,
        skill_name: str,
        description: str,
        category: str,
    ) -> float:
        """Compute a relevance score for a skill against a message.

        Scoring factors:
        - Exact name match: +15
        - Name substring match in message: +10
        - Message substring in name: +6
        - Name component match (e.g. "docker" → "docker-management"): +4
        - Category match: +5
        - Bigram overlap (semantically richer): +3 per matching bigram
        - Description trigram overlap: +2 per matching trigram
        - Description keyword overlap: +1 per keyword (capped)
        - Build-intent boost for build categories: +4
        - Project-type boost for known projects: +8

        Returns:
            Float score (higher = more relevant).
        """
        score: float = 0.0
        msg_lower = message.lower().strip()
        name_lower = skill_name.lower()
        desc_lower = description.lower()
        cat_lower = category.lower()

        msg_words = [w for w in msg_lower.split()
                     if w not in _STOP_WORDS and len(w) > 2]

        # 1. Name matching (exact or direct)
        if name_lower == msg_lower:
            score += 15.0
        elif name_lower in msg_lower:
            score += 10.0
        elif any(name_lower.startswith(w) or w.startswith(name_lower)
                 for w in msg_words if len(w) > 4):
            score += 6.0

        # Check name components (e.g. "docker" matches "docker-management")
        name_parts = [p for p in name_lower.replace("-", " ").split()
                      if p not in _STOP_WORDS and len(p) > 2]
        for part in name_parts:
            if part in msg_words:
                score += 4.0

        # 2. Category matching
        cat_parts = [p for p in cat_lower.replace("-", " ").split()
                     if p not in _STOP_WORDS and len(p) > 2]
        for cp in cat_parts:
            if cp in msg_words:
                score += 5.0

        # 3. Bigram overlap (two-word phrases — semantically richer)
        desc_bigrams = self._word_bigrams(desc_lower)
        msg_bigrams = self._word_bigrams(msg_lower)
        bigram_overlap = desc_bigrams & msg_bigrams
        score += len(bigram_overlap) * 3.0

        # 4. Description trigram overlap
        desc_trigrams = self._word_trigrams(desc_lower)
        msg_trigrams = self._word_trigrams(msg_lower)
        trigram_overlap = desc_trigrams & msg_trigrams
        score += len(trigram_overlap) * 2.0

        # 5. Description keyword overlap (capped to avoid noise)
        desc_words = set(
            w.strip(".,;:!?()[]{}'\"") for w in desc_lower.split()
            if w.strip(".,;:!?()[]{}'\"") not in _STOP_WORDS
            and len(w.strip(".,;:!?()[]{}'\"")) > 3  # Min 4 chars to avoid noise
        )
        msg_word_set = set(msg_words)
        overlap = desc_words & msg_word_set
        score += min(len(overlap) * 1.0, 5.0)  # Cap at 5

        # 6. Build-intent boost
        build_intent = any(w in msg_lower for w in
                          ["build", "make", "create", "write", "develop", "implement"])
        if build_intent and category in _BUILD_CATEGORIES:
            score += 4.0

        # 7. Project-type boost (explicit mappings)
        project_match = self._detect_project_type(message)
        if project_match:
            name_lower_flat = name_lower.replace("-", " ")
            if project_match in name_lower_flat or project_match in desc_lower:
                score += 8.0
            # Also check if project keywords appear in description
            project_keywords = project_match.split()
            if any(kw in desc_lower for kw in project_keywords if len(kw) > 3):
                score += 4.0

        return score

    @staticmethod
    def _word_bigrams(text: str) -> Set[str]:
        """Generate word-level bigrams from text."""
        words = re.findall(r"[a-z][a-z0-9'-]+", text.lower())
        return {" ".join(words[i:i + 2]) for i in range(len(words) - 1)}

    @staticmethod
    def _word_trigrams(text: str) -> Set[str]:
        """Generate word-level trigrams from text."""
        words = re.findall(r"[a-z][a-z0-9'-]+", text.lower())
        return {" ".join(words[i:i + 3]) for i in range(len(words) - 2)}

    @staticmethod
    def _detect_project_type(message: str) -> Optional[str]:
        """Detect the type of project being described."""
        msg_lower = message.lower()
        patterns = [
            (r"\btrading\b.*\bbot\b", "trading bot"),
            (r"\bweb\b.*\b(?:app|site|application)\b", "web app"),
            (r"\bcli\b.*\b(?:tool|app)\b", "CLI tool"),
            (r"\bdashboard\b", "dashboard"),
            (r"\bapi\b.*\b(?:server|service|endpoint)\b", "API"),
            (r"\bscraper\b|\bcrawler\b", "scraper"),
            (r"\b(mobile|ios|android)\b.*\bapp\b", "mobile app"),
            (r"\bgame\b", "game"),
            (r"\bbot\b", "bot"),
            (r"\bmachine learning\b|\bml\b.*\bmodel\b", "machine learning"),
            (r"\bdata\b.*\b(?:pipeline|pipeline)\b", "pipeline"),
            (r"\b(?:docker|container)\b", "docker"),
            (r"\bgit\b|\bgithub\b", "github"),
        ]
        for pattern, ptype in patterns:
            if re.search(pattern, msg_lower):
                return ptype
        return None

    # ── Utility ──────────────────────────────────────────────────────

    def _get_skill_path(self, skill_name: str) -> Optional[str]:
        """Resolve the filesystem path to a skill's directory.

        Returns the path to the skill's ``SKILL.md`` file if it exists,
        or ``None`` if the skill's directory cannot be found.
        """
        # Skills are stored under oag_skills/<category>/<skill-name>/
        skill = self._skills_by_name.get(skill_name)
        if not skill:
            return None

        category = skill.get("category", "")
        # Determine base path
        manifest_dir = self._manifest_path.parent  # oag_skills/
        skill_dir = manifest_dir / category / skill_name

        if skill_dir.exists() and (skill_dir / "SKILL.md").exists():
            return str(skill_dir / "SKILL.md")

        return None

    def count_skills(self) -> int:
        """Return the total number of loaded skills."""
        return len(self._skills)

    def skill_exists(self, name: str) -> bool:
        """Check if a skill exists by name."""
        return name in self._skills_by_name

    def get_skill(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a single skill's metadata by name.

        Args:
            name: The skill name.

        Returns:
            Skill dict or ``None`` if not found.
        """
        skill = self._skills_by_name.get(name)
        if skill:
            return dict(skill)
        return None

    # ── Serialization ───────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        """Export the orchestrator's state as a dict (for diagnostics)."""
        return {
            "total_skills": len(self._skills),
            "categories": self.get_all_categories(),
            "category_counts": self.get_category_counts(),
            "manifest_path": str(self._manifest_path),
            "loaded": self._loaded,
        }

    def __repr__(self) -> str:
        return (
            f"SkillOrchestrator("
            f"skills={len(self._skills)}, "
            f"categories={len(self._skills_by_category)})"
        )
