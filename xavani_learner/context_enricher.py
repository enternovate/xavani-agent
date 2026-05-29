# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Context Enricher — Phase 7 of Xavani Agent.

The ContextEnricher is the reiteration layer between user and agent.
It intercepts EVERY user message before it reaches the LLM and performs
a six-step pipeline:

1. RECEIVE: Gets the raw user message.
2. ANALYZE: Checks the user profile for relevant context (style, knowledge,
   pain points, time-of-day preferences).
3. ENRICH: Rewrites the message to include implicit context the agent needs
   (e.g. "User already knows Python — skip basics").
4. CHECK_SKILLS: Scans the message for keywords that match any of the 169
   skills, loads relevant skill context.
5. REITERATE: Paraphrases what the user wants back to them to confirm
   understanding.
6. FORWARD: Sends the enriched message to the agent with attached context.

Usage:
    enricher = ContextEnricher()
    enriched = enricher.process("build me a trading bot")
    print(enriched["message"])       # the enriched user message
    print(enriched["reiteration"])   # "Let me make sure I understand..."
    print(enriched["skills"])        # matched skill names
    print(enriched["context"])       # style + knowledge context for agent
"""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from .user_profile import UserProfile

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
MANIFEST_PATH = Path(os.environ.get(
    "XAVANI_SKILLS_MANIFEST",
    str(XAVANI_HOME.parent / "xavani-agent" / "oag_skills" / "MANIFEST.json"),
))

# If running from the repo, also try relative path
_REPO_MANIFEST = (
    Path(__file__).resolve().parent.parent / "oag_skills" / "MANIFEST.json"
)
if _REPO_MANIFEST.exists():
    MANIFEST_PATH = _REPO_MANIFEST

# Maximum length of the reiteration summary
_MAX_REITERATION_LENGTH = 200

# Skill detection threshold (how many keyword matches needed)
_SKILL_MATCH_THRESHOLD = 1

# Stop words for skill matching
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


_PROJECT_TO_SKILLS: Dict[str, List[str]] = {
    "trading bot": [
        "stocks", "hyperliquid", "solana", "evm",
        "duckduckgo-search", "docker-management",
    ],
    "web app": [
        "page-agent", "sketch", "popular-web-designs",
        "architecture-diagram", "claude-design",
        "fastmcp", "rest-graphql-debug",
    ],
    "CLI tool": [
        "plan", "test-driven-development", "spike",
        "writing-plans",
    ],
    "API": [
        "rest-graphql-debug", "fastmcp", "native-mcp",
        "requesting-code-review",
    ],
    "microservices": [
        "docker-management", "fastmcp", "native-mcp",
        "rest-graphql-debug", "watchers",
    ],
    "dashboard": [
        "sketch", "popular-web-designs", "architecture-diagram",
        "claude-design",
    ],
    "game": [
        "excalidraw", "p5js", "pixel-art",
        "meme-generation",
    ],
    "scraper": [
        "duckduckgo-search", "scrapling", "domain-intel",
    ],
    "automation": [
        "watchers", "webhook-subscriptions", "blogwatcher",
        "docker-management",
    ],
    "pipeline": [
        "docker-management", "watchers",
        "kanban-orchestrator", "plan",
    ],
    "bot": [
        "docker-management", "watchers",
        "duckduckgo-search",
    ],
    "machine learning": [
        "peft-fine-tuning", "unsloth", "axolotl",
        "fine-tuning-with-trl", "serving-llms-vllm",
        "huggingface-hub", "stable-diffusion-image-generation",
        "dspy", "instructor", "chroma", "faiss",
    ],
    "docker": [
        "docker-management",
    ],
    "github": [
        "github-auth", "github-issues", "github-pr-workflow",
        "github-code-review", "github-repo-management",
        "codebase-inspection",
    ],
}


class ContextEnricher:
    """Intercepts user messages and enriches them with profile context.

    The enricher runs a six-step pipeline on every user message:

    1. **RECEIVE** — Raw user message capture.
    2. **ANALYZE** — Profile lookups for style, knowledge, pain points.
    3. **ENRICH** — Implicit context injection (e.g. ``[user knows Python]``).
    4. **CHECK_SKILLS** — Keyword matching against 169 built-in skills.
    5. **REITERATE** — Confirmation of understanding back to user.
    6. **FORWARD** — Enriched message + context dict prepared for agent.

    All user profile updates also flow through here, so the enricher ensures
    ``UserProfile.update_from_conversation()`` is called for every interaction.

    Usage:
        enricher = ContextEnricher()
        result = enricher.process("build a trading bot with backtesting")

        # The enriched message can be fed directly to the LLM
        agent_message = my_llm(result["enriched_message"])

        # After getting the response, complete the cycle
        enricher.complete_cycle(response_text="...")
    """

    def __init__(
        self,
        profile: Optional[UserProfile] = None,
        manifest_path: Optional[Path] = None,
        enable_reiteration: bool = True,
        enable_enrichment: bool = True,
        enable_skill_detection: bool = True,
    ) -> None:
        """Initialize the context enricher.

        Args:
            profile: A ``UserProfile`` instance. Creates a new one if not
                     provided.
            manifest_path: Path to the skills ``MANIFEST.json``. Auto-detected
                           if not provided.
            enable_reiteration: Whether to generate reiteration messages.
            enable_enrichment: Whether to enrich messages with profile context.
            enable_skill_detection: Whether to detect skill keywords.
        """
        self._profile = profile or UserProfile()
        self._manifest_path = manifest_path or MANIFEST_PATH
        self._enable_reiteration = enable_reiteration
        self._enable_enrichment = enable_enrichment
        self._enable_skill_detection = enable_skill_detection

        # Cache the skill manifest
        self._manifest: Optional[Dict[str, Any]] = None
        self._skill_index: Optional[Dict[str, Dict[str, Any]]] = None

        # Last processed data (for cycle completion)
        self._last_user_message: Optional[str] = None
        self._last_agent_response: Optional[str] = None

        # Increment session on first use
        self._session_incremented = False

    # ── Main Pipeline ────────────────────────────────────────────────

    def process(self, user_message: str) -> Dict[str, Any]:
        """Run the full enrichment pipeline on a user message.

        Args:
            user_message: The raw user input string.

        Returns:
            A dict with keys:
            - ``original_message``: The raw user input.
            - ``enriched_message``: Message with implicit context injected.
            - ``reiteration``: Validation prompt for the user (or empty).
            - ``skilled``: List of matched skill names.
            - ``context``: Dict of profile context for the agent.
            - ``knowledge_context``: Domains the user knows (skip basics).
        """
        raw = user_message.strip()
        self._last_user_message = raw

        # ── Step 1: RECEIVE — just capturing raw (done) ─────────────

        # ── Step 2: ANALYZE — profile lookups ───────────────────────
        if not self._session_incremented:
            self._profile.increment_session()
            self._session_incremented = True

        context = self._build_profile_context(raw)

        # ── Step 3: ENRICH — inject implicit context ────────────────
        enriched = raw
        enrichment_parts: List[str] = []

        if self._enable_enrichment:
            enrichment_parts = self._build_enrichment(context, raw)

            if enrichment_parts:
                enriched = self._inject_context(raw, enrichment_parts)

        # ── Step 4: CHECK_SKILLS — keyword matching ────────────────
        matched_skills: List[str] = []
        if self._enable_skill_detection:
            matched_skills = self._detect_skills(raw)

        # ── Step 5: REITERATE — confirm understanding ──────────────
        reiteration = ""
        if self._enable_reiteration:
            reiteration = self.reiterate(raw)

        # ── Step 6: FORWARD — assemble result ──────────────────────
        result: Dict[str, Any] = {
            "original_message": raw,
            "enriched_message": enriched,
            "reiteration": reiteration,
            "matched_skills": matched_skills,
            "context": context,
            "knowledge_context": {
                "known_domains": [
                    d for d, s in context.get("knowledge_domains", {}).items()
                    if s >= 0.6
                ],
                "unknown_domains": [
                    d for d, s in context.get("knowledge_domains", {}).items()
                    if s < 0.3
                ],
            },
        }

        logger.debug(
            "Enriched message: style=%s, skills=%s, reiteration=%s",
            context.get("style", "?"),
            len(matched_skills),
            bool(reiteration),
        )

        return result

    def complete_cycle(self, agent_response_text: str) -> None:
        """Complete the processing cycle by recording the agent's response.

        This must be called after forwarding the enriched message to the
        LLM and receiving a response. It updates the user profile with
        the full interaction.

        Args:
            agent_response_text: The agent's response text.
        """
        if self._last_user_message is not None:
            self._profile.update_from_conversation(
                self._last_user_message,
                agent_response_text,
            )
            self._last_agent_response = agent_response_text
            logger.debug("Completed learning cycle for user message")

    # ── Step 2: Profile Context ──────────────────────────────────────

    def _build_profile_context(self, message: str) -> Dict[str, Any]:
        """Extract relevant profile context for the current message."""
        profile = self._profile
        now = datetime.now(timezone.utc)

        return {
            "style": profile.communication_style,
            "tone": profile.tone_preference,
            "humor": profile.humor_style,
            "knowledge_domains": profile.knowledge_domains,
            "favorite_builds": profile.favorite_builds,
            "pain_points": profile.pain_points[:5],
            "skill_affinities": dict(
                sorted(
                    profile.skill_affinities.items(),
                    key=lambda x: x[1],
                    reverse=True,
                )[:10]
            ),
            "hour": now.hour,
        }

    # ── Step 3: Enrichment ───────────────────────────────────────────

    def _build_enrichment(
        self,
        context: Dict[str, Any],
        message: str,
    ) -> List[str]:
        """Build enrichment markers from profile context."""
        parts: List[str] = []

        # Style context
        style = context.get("style", "adaptive")
        if style != "adaptive":
            parts.append(f"[user prefers {style} communication]")

        # Tone
        tone = context.get("tone", "direct")
        if tone != "direct":
            parts.append(f"[user prefers {tone} tone]")

        # Known domains — skip basics
        known = [
            d for d, s in context.get("knowledge_domains", {}).items()
            if s >= 0.6
        ]
        if known:
            parts.append(
                f"[user knows: {', '.join(known)} — skip basic explanations]"
            )

        # Pain points — avoid
        pains = context.get("pain_points", [])
        if pains and self._message_touches_pain_points(message, pains):
            parts.append(
                f"[user dislikes: {', '.join(pains[-3:])} — avoid this pattern]"
            )

        # Skill affinities
        affinities = context.get("skill_affinities", {})
        if affinities:
            top_skills = list(affinities.keys())[:5]
            parts.append(
                f"[user's frequently used skills: {', '.join(top_skills)}]"
            )

        # Time-of-day context
        hour = context.get("hour", 12)
        if hour < 6:
            parts.append("[user is active in early morning hours]")
        elif hour >= 22:
            parts.append("[user is active late at night]")

        return parts

    def _message_touches_pain_points(
        self,
        message: str,
        pain_points: List[str],
    ) -> bool:
        """Check if a message relates to any known pain points."""
        msg_lower = message.lower()
        for pain in pain_points:
            pain_lower = pain.lower()
            # Check if any significant word from the pain point appears
            pain_words = set(pain_lower.split())
            # Skip short/stop words
            significant = {w for w in pain_words if len(w) > 3}
            if significant and any(w in msg_lower for w in significant):
                return True
        return False

    def _inject_context(
        self,
        message: str,
        enrichment_parts: List[str],
    ) -> str:
        """Inject enrichment markers into the message.

        Adds context as a structured prefix so the LLM can see it but it
        doesn't disrupt the natural flow of the message.
        """
        prefix = " | ".join(enrichment_parts)
        return f"{prefix}\n\n{message}"

    # ── Step 4: Skill Detection ──────────────────────────────────────

    def _detect_skills(self, message: str) -> List[str]:
        """Scan the message for keywords matching any of the 169 skills.

        Uses a hybrid approach:
        1. First checks explicit project-to-skill mappings from UserProfile.
        2. Then augments with keyword-based matching from the SkillOrchestrator.

        Returns:
            List of matched skill names, ordered by relevance, unique.
        """
        if self._manifest is None:
            self._load_manifest()

        if not self._manifest:
            return []

        msg_lower = message.lower()
        seen: Set[str] = set()
        matched: List[Tuple[str, int]] = []  # (skill_name, priority)

        # ── Phase 1: Explicit project-to-skill mappings ──────────
        # These come from UserProfile.get_skill_suggestions() which
        # has expert-curated mappings between project types and skills.
        # We also check the static _PROJECT_TO_SKILLS mapping directly
        # so even brand-new project types get correct suggestions.
        project_matches = self._detect_project_types(message)

        # Check direct project-to-skill mappings (always available)
        for proj_type in project_matches:
            direct_skills = _PROJECT_TO_SKILLS.get(proj_type, [])
            for skill_name in direct_skills:
                if skill_name not in seen:
                    seen.add(skill_name)
                    matched.append((skill_name, 4))  # Highest priority

        # Also check profile-based suggestions (requires learned favorites)
        if project_matches and self._profile:
            explicit_suggestions = self._profile.get_skill_suggestions()
            if explicit_suggestions:
                for skill_name in explicit_suggestions:
                    if skill_name not in seen:
                        seen.add(skill_name)
                        matched.append((skill_name, 3))  # High priority

        # ── Phase 2: Project-type keyword boost ────────────────
        # Boost skills whose descriptions mention the project type.
        for project_type in project_matches:
            proj_keywords = set(project_type.lower().split())
            for skill in self._manifest.get("skills", []):
                name = skill.get("name", "")
                desc = skill.get("description", "").lower()
                if name in seen:
                    continue
                # Check if any project keyword appears in description
                if any(kw in desc for kw in proj_keywords if len(kw) > 3):
                    seen.add(name)
                    matched.append((name, 2))

        # ── Phase 3: Keyword-based matching ─────────────────────
        for skill in self._manifest.get("skills", []):
            name = skill.get("name", "")
            if name in seen:
                continue
            description = skill.get("description", "")
            category = skill.get("category", "")
            score = self._score_skill_light(msg_lower, name, description, category)
            if score > 0:
                seen.add(name)
                matched.append((name, 1))  # Normal priority

        # Sort: first by priority (higher first), then by name
        matched.sort(key=lambda x: (-x[1], x[0]))
        return [name for name, _priority in matched[:15]]

    def _score_skill_light(
        self,
        msg_lower: str,
        skill_name: str,
        description: str,
        category: str,
    ) -> int:
        """Lightweight keyword scoring for a skill against a message.

        Returns a simple integer score (0 = no match, higher = better).
        """
        score = 0
        name_lower = skill_name.lower()
        desc_lower = description.lower()

        # Direct name mention in message
        name_variants = {name_lower, name_lower.replace("-", " ")}
        for variant in name_variants:
            if variant in msg_lower:
                return 5  # Strong match — return immediately

        # Name component match
        name_parts = [p for p in name_lower.replace("-", " ").split()
                      if p not in _STOP_WORDS and len(p) > 3]
        msg_words = set(msg_lower.split())
        for part in name_parts:
            if part in msg_words:
                score += 2

        # Description bigram overlap
        desc_words = set(
            w.strip(".,;:!?()[]{}'\"") for w in desc_lower.split()
            if w.strip(".,;:!?()[]{}'\"") not in _STOP_WORDS
            and len(w.strip(".,;:!?()[]{}'\"")) > 3
        )
        overlap = desc_words & msg_words
        score += min(len(overlap), 3)

        return score

    @staticmethod
    def _detect_project_types(message: str) -> List[str]:
        """Detect project types mentioned in a message."""
        msg_lower = message.lower()
        found: List[str] = []
        patterns = [
            (r"\btrading\b.*\bbot\b", "trading bot"),
            (r"\bweb\b.*\b(?:app|site|application)\b", "web app"),
            (r"\bcli\b", "CLI tool"),
            (r"\bdashboard\b", "dashboard"),
            (r"\bscraper\b|\bcrawler\b", "scraper"),
            (r"\bbot\b", "bot"),
            (r"\bmachine learning\b|\bml\b", "machine learning"),
            (r"\bapi\b", "API"),
            (r"\bdocker\b", "docker"),
            (r"\bgit\b|\bgithub\b", "github"),
        ]
        for pattern, ptype in patterns:
            if re.search(pattern, msg_lower):
                found.append(ptype)
        return found

    def _load_manifest(self) -> None:
        """Load the skill manifest from disk."""
        import json

        manifest_path = self._manifest_path
        self._manifest = {"skills": []}
        try:
            if manifest_path.exists():
                with open(manifest_path, "r", encoding="utf-8") as f:
                    self._manifest = json.load(f)
                logger.debug(
                    "Loaded skill manifest with %d skills",
                    len(self._manifest.get("skills", [])),
                )
            else:
                logger.warning("Skill manifest not found at %s", manifest_path)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to load skill manifest: %s", exc)

    # ── Step 5: Reiteration ──────────────────────────────────────────

    def reiterate(self, user_message: str) -> str:
        """Generate a condensed reiteration/confirmation of understanding.

        Analyzes the user message and produces a short paraphrase that
        confirms what the agent thinks the user wants. This is shown to
        the user before the full agent response.

        Returns an empty string if the message doesn't need reiteration
        (e.g. very short messages or greetings).

        Args:
            user_message: The user's raw message.

        Returns:
            A short reiteration string, or empty if not needed.
        """
        message = user_message.strip()

        # Don't reiterate very short messages or greetings
        if len(message.split()) <= 2:
            return ""

        greetings = {"hi", "hello", "hey", "yo", "sup", "ok", "okay", "thanks",
                     "thank you", "bye", "goodbye", "good morning", "good evening"}
        if message.lower().strip() in greetings:
            return ""

        # Extract the core intent
        intent = self._extract_intent(message)
        project = self._extract_project_type(message)
        knowledge_level = self._extract_knowledge_level(message)

        # Build reiteration
        parts: List[str] = ["Let me make sure I understand:"]

        if intent:
            parts.append(f"you want to {intent}")

        if project:
            parts.append(f"specifically a {project}")

        reiteration = " ".join(parts)

        if len(reiteration) > _MAX_REITERATION_LENGTH:
            reiteration = reiteration[:_MAX_REITERATION_LENGTH - 3] + "..."

        # Add confirmation prompt
        return f"{reiteration} Is that right?"

    def _extract_intent(self, message: str) -> Optional[str]:
        """Extract what the user actually wants to do.

        Returns a concise action phrase or ``None``.
        """
        msg_lower = message.lower()

        # Action patterns
        patterns = [
            (r"(?:i want|i'd like|i need|help me) (?:to )?(.+)", lambda m: m.group(1).strip()),
            (r"(?:can you|could you|could you please) (.+)", lambda m: m.group(1).strip()),
            (r"(?:build|make|create|write|develop|implement|deploy) (.+)", lambda m: f"build {m.group(1).strip()}"),
            (r"(?:explain|tell me about|describe|what is|how does) (.+)", lambda m: f"learn about {m.group(1).strip()}"),
            (r"(?:fix|debug|help with|troubleshoot) (.+)", lambda m: f"fix {m.group(1).strip()}"),
            (r"(?:find|search|look up|show me|get me) (.+)", lambda m: f"find {m.group(1).strip()}"),
            (r"(?:install|set up|configure) (.+)", lambda m: f"set up {m.group(1).strip()}"),
            (r"(?:convert|translate|transform) (.+)", lambda m: f"convert {m.group(1).strip()}"),
        ]

        for pattern, extractor in patterns:
            match = re.search(pattern, msg_lower)
            if match:
                intent = extractor(match)
                # Trim trailing punctuation and common fillers
                intent = intent.rstrip(".,!?:;")
                if len(intent) > 5 and len(intent) < 100:
                    return intent

        return None

    def _extract_project_type(self, message: str) -> Optional[str]:
        """Detect if the user is describing something to build.

        Returns a project type string or ``None``.
        """
        msg_lower = message.lower()

        project_types = {
            "trading bot": r"\btrading\b.*\bbot\b",
            "web app": r"\bweb\b.*\bapp\b",
            "CLI tool": r"\bcli\b",
            "API": r"\bapi\b",
            "dashboard": r"\bdashboard\b",
            "scraper": r"\bscraper\b|\bcrawler\b",
            "mobile app": r"\bmobile\b.*\bapp\b",
            "game": r"\bgame\b",
            "bot": r"\bbot\b",
        }

        for ptype, pattern in project_types.items():
            if re.search(pattern, msg_lower):
                return ptype

        return None

    def _extract_knowledge_level(self, message: str) -> str:
        """Assess if the user is a beginner or expert for this message.

        Returns one of: ``"beginner"``, ``"intermediate"``, ``"expert"``.
        """
        msg_lower = message.lower()

        # Expert indicators
        expert_markers = [
            "optimize", "profile", "benchmark", "trade-off",
            "scalability", "architecture", "design pattern",
            "under the hood", "internals", "compared to",
            "alternative to", "vs ", " versus ",
        ]
        if any(m in msg_lower for m in expert_markers):
            return "expert"

        # Beginner indicators
        beginner_markers = [
            "what is", "how to", "beginner", "simple", "basic",
            "start with", "getting started", "new to", "never used",
            "explain like", "dumb it down", "noob", "novice",
            "first time", "tutorial", "example for",
        ]
        if any(m in msg_lower for m in beginner_markers):
            return "beginner"

        # Intermediate (default when no strong signal)
        return "intermediate"

    # ── Profile Access ───────────────────────────────────────────────

    @property
    def profile(self) -> UserProfile:
        """Access the underlying user profile."""
        return self._profile
