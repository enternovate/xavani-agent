# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Deep User Profiling — Phase 7 of Xavani Agent.

The UserProfile class learns the user's personality, communication style,
humor, preferences, and domain expertise from every conversation. It stores
all data in ``~/.xavani/data/user_profile.json`` and provides methods to:

- Analyze each interaction for signals (message length, structure, vocabulary)
- Generate style prompts that tailor the agent's voice
- Recommend skills based on what the user builds
- Track domain expertise (skip the basics for known domains)
- Record favorite project types and pain points
- Export/Import for backup and restore

Usage:
    profile = UserProfile()
    profile.update_from_conversation("user message", "agent response")
    style = profile.get_style_prompt()
    skills = profile.get_skill_suggestions()
"""

from __future__ import annotations

import json
import logging
import os
import re
import threading
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
PROFILE_DIR = XAVANI_HOME / "data"
PROFILE_PATH = PROFILE_DIR / "user_profile.json"

# Default profile (fresh start)
_DEFAULT_PROFILE: Dict[str, Any] = {
    "communication_style": "adaptive",  # terse/verbose/technical/creative/adaptive
    "humor_style": "none",              # dry/witty/sarcastic/absurd/none
    "favorite_builds": [],              # list of project types they enjoy building
    "preferred_example": "adaptive",    # code_first/concepts_first/analogies/adaptive
    "skill_affinities": {},             # skill_name -> usage_count (ranked)
    "knowledge_domains": {},            # domain -> confidence (0.0-1.0)
    "pain_points": [],                  # things they struggle with or dislike
    "tone_preference": "direct",        # formal/casual/motivational/direct
    "timezone": None,                   # detected timezone
    "work_hours": {},                   # hour_of_day -> activity_count
    "session_count": 0,
    "total_messages": 0,
    "first_seen": None,
    "last_seen": None,
    "signals": {                        # raw signal data for learning
        "message_lengths": [],
        "code_block_ratios": [],        # proportion of messages with code
        "question_depths": [],          # 0=no q, 1=simple, 2=deep, 3=expert
        "correction_count": 0,
        "project_mentions": [],
        "skill_command_uses": [],
        "avg_message_length": 0,
        "vocabulary_clues": Counter(),  # key words they use
    },
}

# Signal thresholds
_TERSE_THRESHOLD_WORDS = 20   # messages under this count as terse
_VERBOSE_THRESHOLD_WORDS = 120  # messages over this count as verbose

# Learning rates
_KNOWLEDGE_BOOST = 0.15       # how much each correct answer boosts domain confidence
_KNOWLEDGE_PENALTY = 0.05     # how much a basic question reduces domain confidence


# ---------------------------------------------------------------------------
# UserProfile
# ---------------------------------------------------------------------------


class UserProfile:
    """Deep user profiling that learns from every conversation.

    The profile adapts over time by extracting signals from each interaction:
    message length, code use, question depth, domain references, corrections,
    and project mentions. All learning is ``update_from_conversation()``-driven.

    Thread-safe: uses a reentrant lock for all read/write operations.
    Persisted to ``~/.xavani/data/user_profile.json``.
    """

    def __init__(
        self,
        profile_path: Path = PROFILE_PATH,
        auto_save: bool = True,
    ) -> None:
        """Initialize the user profile, loading existing data if present.

        Args:
            profile_path: Path to the JSON profile file.
            auto_save: Whether to auto-save on every update.
        """
        self._profile_path = profile_path
        self._auto_save = auto_save
        self._lock = threading.RLock()
        self._profile: Dict[str, Any] = {}

        # Ensure directory exists
        self._profile_path.parent.mkdir(parents=True, exist_ok=True)

        # Load existing or create fresh
        self._load()

    # ── Profile Loading/Saving ────────────────────────────────────────

    def _load(self) -> None:
        """Load profile from disk or initialize defaults."""
        if self._profile_path.exists():
            try:
                with open(self._profile_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                # Merge with defaults so new fields are always present
                self._profile = {**_DEFAULT_PROFILE.copy(), **loaded}
                # Deep merge for nested structures
                for key in ("signals",):
                    if key in loaded and isinstance(loaded[key], dict):
                        merged = _DEFAULT_PROFILE.get(key, {}).copy()
                        merged.update(loaded[key])
                        self._profile[key] = merged
                logger.debug("Loaded user profile from %s", self._profile_path)
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Failed to load profile: %s. Using defaults.", exc)
                self._profile = _DEFAULT_PROFILE.copy()
        else:
            self._profile = _DEFAULT_PROFILE.copy()
            logger.debug("Created new user profile at %s", self._profile_path)
            self._save()

    def _save(self) -> None:
        """Save profile to disk."""
        try:
            with open(self._profile_path, "w", encoding="utf-8") as f:
                json.dump(self._profile, f, indent=2, default=str)
            logger.debug("Saved user profile to %s", self._profile_path)
        except OSError as exc:
            logger.warning("Failed to save profile: %s", exc)

    # ── Conversation Learning ─────────────────────────────────────────

    def update_from_conversation(
        self,
        user_message: str,
        agent_message: str,
    ) -> None:
        """Analyze a single user+agent interaction and update the profile.

        Extracts signals from:
        - Message length and structure (terse vs verbose)
        - Questions they ask (depth indicates expertise)
        - Corrections they make (``I don't like X``, ``Actually it's Y``)
        - Projects they describe (trading bot, web scraper, etc.)
        - Code blocks they request or provide
        - Skill commands they run (``/install``, ``/gateway-up``, etc.)
        - Time of day they're working
        - Vocabulary clues (domain-specific jargon)

        Args:
            user_message: The raw user message.
            agent_message: The agent's response to analyze feedback from.
        """
        with self._lock:
            profile = self._profile
            signals = profile["signals"]

            # Update session tracking
            now = datetime.now(timezone.utc)
            now_ts = now.isoformat()
            if profile["first_seen"] is None:
                profile["first_seen"] = now_ts
            profile["last_seen"] = now_ts

            # Track time-of-day activity
            local_hour = now.hour  # best-effort; user can set timezone
            hour_str = f"{local_hour:02d}:00"
            work_hours = profile["work_hours"]
            work_hours[hour_str] = work_hours.get(hour_str, 0) + 1

            # ── Signal 1: Message length ──
            word_count = len(user_message.split())
            signals["message_lengths"].append(word_count)

            # Trim history to keep file small (keep last 200)
            if len(signals["message_lengths"]) > 200:
                signals["message_lengths"] = signals["message_lengths"][-200:]

            # ── Signal 2: Communication style detection ──
            self._detect_communication_style(user_message, word_count)

            # ── Signal 3: Code blocks ──
            has_code = bool(re.search(r"```|`[^`]+`", user_message))
            if has_code:
                signals["code_block_ratios"].append(1.0)
            else:
                signals["code_block_ratios"].append(0.0)
            if len(signals["code_block_ratios"]) > 200:
                signals["code_block_ratios"] = signals["code_block_ratios"][-200:]

            # ── Signal 4: Question depth ──
            depth = self._assess_question_depth(user_message)
            signals["question_depths"].append(depth)
            if len(signals["question_depths"]) > 200:
                signals["question_depths"] = signals["question_depths"][-200:]

            # Update knowledge domains based on question depth
            self._update_knowledge_from_depth(user_message, depth)

            # ── Signal 5: Corrections ──
            if self._is_correction(user_message):
                signals["correction_count"] += 1
                # Extract pain points from corrections
                self._extract_pain_points(user_message)

            # ── Signal 6: Project mentions ──
            projects = self._extract_project_types(user_message)
            for proj in projects:
                signals["project_mentions"].append(proj)
                self._add_to_favorites_if_repeated(proj)

            # ── Signal 7: Skill commands ──
            skills_used = self._extract_skill_commands(user_message)
            for skill_name in skills_used:
                signals["skill_command_uses"].append(skill_name)
                affinities = profile["skill_affinities"]
                affinities[skill_name] = affinities.get(skill_name, 0) + 1

            # ── Signal 8: Vocabulary clues ──
            self._extract_vocabulary(user_message)

            # ── Signal 9: Humor detection ──
            self._detect_humor_style(user_message)

            # ── Signal 10: Tone preference from user feedback ──
            self._detect_tone_preference(user_message, agent_message)

            # Update averages
            total_msgs = profile["total_messages"] + 1
            profile["total_messages"] = total_msgs
            all_lengths = signals["message_lengths"]
            if all_lengths:
                signals["avg_message_length"] = sum(all_lengths) / len(all_lengths)

            # Auto-save
            if self._auto_save:
                self._save()

    def _detect_communication_style(self, message: str, word_count: int) -> None:
        """Update communication style based on message patterns."""
        profile = self._profile
        signals = profile["signals"]

        # Simple heuristic: moving average of word counts
        recent_lengths = signals["message_lengths"][-20:] if len(signals["message_lengths"]) >= 20 else signals["message_lengths"]
        if not recent_lengths:
            return

        avg = sum(recent_lengths) / len(recent_lengths)

        # Check for technical vocabulary
        tech_keywords = {
            "function", "class", "api", "endpoint", "schema", "query",
            "deploy", "docker", "config", "async", "await", "callback",
            "thread", "process", "memory", "latency", "throughput",
            "compile", "build", "test", "debug", "profiling", "benchmark",
            "algorithm", "complexity", "recursion", "iteration",
        }
        has_technical = any(kw in message.lower() for kw in tech_keywords)

        # Check for creative vocabulary
        creative_keywords = {
            "design", "theme", "color", "layout", "font", "style",
            "aesthetic", "beautiful", "clean", "minimal", "modern",
            "animation", "transition", "effect", "gradient", "shadow",
            "creative", "art", "visual", "render", "ui", "ux",
        }
        has_creative = any(kw in message.lower() for kw in creative_keywords)

        if has_technical and avg > 40:
            profile["communication_style"] = "technical"
        elif has_creative and avg > 40:
            profile["communication_style"] = "creative"
        elif avg < _TERSE_THRESHOLD_WORDS:
            # Only switch to terse if it's consistently terse
            terse_count = sum(1 for l in recent_lengths if l < _TERSE_THRESHOLD_WORDS)
            if terse_count > len(recent_lengths) * 0.7:
                profile["communication_style"] = "terse"
        elif avg > _VERBOSE_THRESHOLD_WORDS:
            verbose_count = sum(1 for l in recent_lengths if l > _VERBOSE_THRESHOLD_WORDS)
            if verbose_count > len(recent_lengths) * 0.5:
                profile["communication_style"] = "verbose"
        else:
            profile["communication_style"] = "adaptive"

    def _assess_question_depth(self, message: str) -> int:
        """Assess the depth of questions in a message.

        Returns:
            0 = no question, 1 = simple/basic, 2 = intermediate,
            3 = deep/expert
        """
        msg_lower = message.lower().strip()

        # Check for questions
        if "?" not in msg_lower and "how do" not in msg_lower and "what is" not in msg_lower:
            return 0

        # Deep/expert indicators
        deep_markers = [
            "compare", "contrast", "trade-off", "what are the implications",
            "why does", "how exactly", "under the hood", "internally",
            "architecture", "design pattern", "scalability", "when would you",
            "difference between", "pros and cons", "alternatives",
            "best practice", "optimization", "benchmark", "analyze",
        ]
        if any(marker in msg_lower for marker in deep_markers):
            return 3

        # Intermediate indicators
        inter_markers = [
            "how to", "how can i", "how do i", "how does", "what's the best",
            "what is a", "what are", "can you explain", "example of",
            "show me", "tell me about", "i need to",
        ]
        if any(marker in msg_lower for marker in inter_markers):
            return 2

        # Simple/basic questions
        return 1

    def _is_correction(self, message: str) -> bool:
        """Detect if the user is correcting the agent or expressing dislike."""
        msg_lower = message.lower().strip()
        correction_patterns = [
            r"\bi don't like\b",
            r"\bi hate\b",
            r"\bthat'?s not\b",
            r"\bthat'?s wrong\b",
            r"\bactually\b.*\b(is|it's|that)\b",
            r"\bno[, ]\b",
            r"\binstead\b",
            r"\bnevermind\b",
            r"\bnot what i\b",
            r"\bdifferent\b.*\bplease\b",
            r"\btry again\b",
            r"\bthat'?s incorrect\b",
            r"\byou'?re wrong\b",
            r"\bthat'?s not right\b",
        ]
        return any(re.search(pat, msg_lower) for pat in correction_patterns)

    def _extract_pain_points(self, message: str) -> None:
        """Extract pain points from correction messages."""
        pain_points = self._profile["pain_points"]
        msg_lower = message.lower()

        # Common pain point indicators
        pain_patterns = [
            (r"\bi don't like (.*)", lambda m: m.group(1).strip().rstrip(".!")),
            (r"\bi hate (.*)", lambda m: m.group(1).strip().rstrip(".!")),
            (r"\bnot (.*?)(?:,|\.|$)", lambda m: m.group(1).strip()),
            (r"\btoo (complicated|complex|slow|verbose|vague|simple)(.*)", lambda m: f"too {m.group(1)}"),
        ]

        for pattern, extractor in pain_patterns:
            match = re.search(pattern, msg_lower)
            if match:
                pain = extractor(match)
                if pain and pain not in pain_points:
                    pain_points.append(pain)
                    # Keep list manageable
                    if len(pain_points) > 50:
                        pain_points.pop(0)

    def _extract_project_types(self, message: str) -> List[str]:
        """Extract project types the user is describing or building."""
        msg_lower = message.lower()
        found: List[str] = []

        # Project-type patterns
        project_patterns = [
            (r"(?:build|make|create|write|develop) (?:a|an|my|another) (\w+(?: \w+)?)", lambda m: m.group(1)),
            (r"(?:trading|web|cli|mobile|desktop|api|bot|scraper|crawler) (?:bot|app|tool|service|scraper|crawler|agent)", lambda m: m.group()),
            (r"(\w+(?: \w+)?) (?:bot|agent)", lambda m: f"{m.group(1)} bot"),
            ("trading bot", lambda m: "trading bot"),
            ("web app", lambda m: "web app"),
            ("cli tool", lambda m: "CLI tool"),
            ("API", lambda m: "API"),
            ("microservice", lambda m: "microservices"),
            ("dashboard", lambda m: "dashboard"),
        ]

        # Direct project type mentions
        known_project_types = [
            "trading bot", "web app", "CLI tool", "mobile app", "desktop app",
            "API", "microservice", "dashboard", "game", "scraper", "crawler",
            "automation", "pipeline", "workflow", "integration", "plugin",
            "extension", "library", "framework", "template", "starter",
            "blog", "portfolio", "landing page", "e-commerce", "saas",
        ]

        for ptype in known_project_types:
            if ptype in msg_lower:
                found.append(ptype)

        # Pattern matching for "build a ..."
        for pattern, extractor in project_patterns:
            match = re.search(pattern, msg_lower)
            if match:
                extracted = extractor(match)
                if extracted and extracted not in found:
                    found.append(extracted)

        return found

    def _add_to_favorites_if_repeated(self, project_type: str) -> None:
        """Add a project type to favorites if mentioned repeatedly."""
        signals = self._profile["signals"]
        mentions = signals["project_mentions"]

        # Count how many times this project type has been mentioned
        count = sum(1 for m in mentions if m == project_type)

        # If mentioned 3+ times and not already a favorite, add it
        if count >= 3 and project_type not in self._profile["favorite_builds"]:
            self._profile["favorite_builds"].append(project_type)
            logger.debug("Added favorite build: %s", project_type)

    def _extract_skill_commands(self, message: str) -> List[str]:
        """Extract skill command usage from a message."""
        msg_lower = message.lower()
        found: List[str] = []

        # OAG skill commands
        skill_commands = [
            "/install", "/gateway-up", "/gateway-down", "/gateway-status",
            "/servers", "/config", "/log", "/logs", "/help", "/skills",
            "/profiles", "/memory", "/agent", "/image", "/export", "/import",
        ]

        for cmd in skill_commands:
            if cmd in msg_lower:
                found.append(cmd.lstrip("/"))

        return found

    def _extract_vocabulary(self, message: str) -> None:
        """Extract domain-specific vocabulary clues."""
        signals = self._profile["signals"]
        vocab = signals["vocabulary_clues"]
        msg_lower = message.lower()

        # Domain-specific keyword groups
        domain_keywords: Dict[str, List[str]] = {
            "python": ["python", "pandas", "numpy", "flask", "fastapi", "django",
                       "pytest", "async", "await", "decorator", "generator",
                       "list comprehension", "type hint"],
            "javascript": ["javascript", "node", "react", "vue", "typescript",
                          "npm", "yarn", "webpack", "babel", "es6"],
            "devops": ["docker", "kubernetes", "k8s", "ci/cd", "jenkins",
                      "github actions", "terraform", "ansible", "helm"],
            "ml": ["machine learning", "deep learning", "neural network",
                  "training", "inference", "model", "dataset", "pytorch",
                  "tensorflow", "transformer", "attention", "embedding"],
            "blockchain": ["blockchain", "ethereum", "solana", "smart contract",
                          "solidity", "web3", "defi", "nft", "token"],
            "data": ["data", "analytics", "sql", "database", "etl",
                    "visualization", "pipeline", "query", "schema"],
            "security": ["security", "encryption", "auth", "oauth", "jwt",
                        "vulnerability", "pentest", "xss", "sql injection"],
            "design": ["design", "ui", "ux", "figma", "css", "html",
                      "responsive", "accessibility", "animation"],
        }

        for domain, keywords in domain_keywords.items():
            for kw in keywords:
                if kw in msg_lower:
                    vocab[kw] += 1

    def _detect_humor_style(self, message: str) -> None:
        """Detect the user's humor style from their messages."""
        msg_lower = message.lower()

        # Dry humor: understatement, deadpan, factual absurdity
        dry_indicators = ["technically", "strictly speaking", "in theory",
                         "that's a feature", "as one does"]

        # Witty: wordplay, puns, clever observations
        witty_indicators = ["pun", "wordplay", "ironically",
                           r"\bjoke\b", r"\bfunny\b", "humor"]

        # Sarcastic: obvious reversal, heavy irony markers
        sarcastic_indicators = ["yeah right", "oh great", "just what i needed",
                               "thanks a lot", "sarcasm", "obviously not",
                               "sure thing", "because that worked"]

        # Absurd: surreal, unexpected comparisons
        absurd_indicators = ["llama", "llamas", "unicorn", "quantum",
                            "simulated", "banana", "definitely a human"]

        if any(pat in msg_lower for pat in dry_indicators):
            self._profile["humor_style"] = "dry"
        elif any(pat in msg_lower for pat in witty_indicators):
            self._profile["humor_style"] = "witty"
        elif any(pat in msg_lower for pat in sarcastic_indicators):
            self._profile["humor_style"] = "sarcastic"
        elif any(pat in msg_lower for pat in absurd_indicators):
            self._profile["humor_style"] = "absurd"

    def _detect_tone_preference(self, user_message: str, agent_message: str) -> None:
        """Detect tone preferences from user feedback on agent responses."""
        msg_lower = user_message.lower()
        profile = self._profile

        # Positive tone feedback
        if any(phrase in msg_lower for phrase in [
            "more casual", "chill", "relaxed", "less formal",
            "talk to me like", "be more friendly",
        ]):
            profile["tone_preference"] = "casual"

        elif any(phrase in msg_lower for phrase in [
            "more formal", "professional", "less casual",
            "be more serious", "strictly", "keep it professional",
        ]):
            profile["tone_preference"] = "formal"

        elif any(phrase in msg_lower for phrase in [
            "motivate me", "pump me up", "inspire me", "let's go",
            "get me excited", "hype me", "encourage me",
        ]):
            profile["tone_preference"] = "motivational"

        elif any(phrase in msg_lower for phrase in [
            "just the facts", "get to the point", "be direct",
            "don't elaborate", "short answer", "tl;dr", "brief",
        ]):
            profile["tone_preference"] = "direct"

        # Also check agent message sentiment as implicit signal
        # (if user responds positively to a certain style, reinforce it)
        if "that's perfect" in msg_lower or "exactly what i needed" in msg_lower:
            # User validated the current style — no change needed
            pass

    def _update_knowledge_from_depth(self, message: str, depth: int) -> None:
        """Update domain knowledge based on question depth and vocabulary."""
        profile = self._profile
        knowledge = profile["knowledge_domains"]
        signals = profile["signals"]
        vocab = signals.get("vocabulary_clues", {})

        # Map vocabulary to knowledge domains
        domain_map: Dict[str, List[str]] = {
            "python": ["python", "pandas", "numpy", "flask", "fastapi", "django"],
            "javascript/typescript": ["javascript", "typescript", "react", "node", "npm"],
            "machine learning": ["machine learning", "neural", "pytorch", "tensorflow",
                                 "transformer", "training", "inference", "model"],
            "devops": ["docker", "kubernetes", "ci/cd", "terraform", "ansible", "helm"],
            "blockchain": ["ethereum", "solana", "smart contract", "solidity", "web3"],
            "data engineering": ["sql", "pipeline", "etl", "spark", "data warehouse",
                                 "analytics"],
            "security": ["security", "encryption", "oauth", "vulnerability", "pentest"],
            "web development": ["html", "css", "react", "api", "rest", "graphql",
                                "frontend", "backend"],
        }

        # Detect domain from vocabulary
        detected_domains: Set[str] = set()
        for domain, keywords in domain_map.items():
            for kw in keywords:
                if kw in message.lower():
                    detected_domains.add(domain)
                    # Also count keyword in vocab
                    if isinstance(vocab, Counter):
                        vocab[kw] += 1

        # Update knowledge scores
        for domain in detected_domains:
            current = knowledge.get(domain, 0.0)
            if depth >= 2:
                # Deep question suggests some knowledge
                new_score = min(1.0, current + _KNOWLEDGE_BOOST)
            elif depth == 1:
                # Basic question suggests less knowledge
                new_score = max(0.0, current - _KNOWLEDGE_PENALTY)
            else:
                # No question — could be statement of fact from expert
                new_score = min(1.0, current + _KNOWLEDGE_BOOST * 0.5)
            knowledge[domain] = round(new_score, 2)

        # Clean up stale low-confidence domains
        stale = [d for d, s in knowledge.items() if s < 0.05]
        for d in stale:
            del knowledge[d]

    # ── Profile Queries ──────────────────────────────────────────────

    def get_style_prompt(self) -> List[str]:
        """Generate system prompt snippets that tailor the agent's voice.

        Returns a list of directive strings that can be injected into
        the system prompt to adapt the agent's communication style to
        the user's preferences.

        Returns:
            List of style directive strings.
        """
        with self._lock:
            profile = self._profile
            directives: List[str] = []

            # Communication style
            style = profile.get("communication_style", "adaptive")
            style_map = {
                "terse": "Keep responses brief and to the point.",
                "verbose": "Provide detailed, thorough explanations.",
                "technical": "Use technical language and precise terminology.",
                "creative": "Use expressive, creative language and analogies.",
                "adaptive": "Match the user's communication style naturally.",
            }
            directives.append(style_map.get(style, style_map["adaptive"]))

            # Tone preference
            tone = profile.get("tone_preference", "direct")
            tone_map = {
                "formal": "Maintain a professional, formal tone.",
                "casual": "Use a relaxed, conversational tone.",
                "motivational": "Be encouraging and motivational.",
                "direct": "Be direct and straightforward.",
            }
            directives.append(tone_map.get(tone, tone_map["direct"]))

            # Humor style
            humor = profile.get("humor_style", "none")
            if humor != "none":
                humor_map = {
                    "dry": "Use dry, understated humor when appropriate.",
                    "witty": "Use wordplay and clever observations.",
                    "sarcastic": "Use gentle sarcasm and irony.",
                    "absurd": "Use absurd and surreal humor.",
                }
                directives.append(humor_map.get(humor, ""))

            # Example preference
            example_pref = profile.get("preferred_example", "adaptive")
            if example_pref != "adaptive":
                ex_map = {
                    "code_first": "Show code examples first, then explain.",
                    "concepts_first": "Explain concepts before showing code.",
                    "analogies": "Use analogies to explain complex topics.",
                }
                directives.append(ex_map.get(example_pref, ""))

            # Knowledge domains (skip basics for known domains)
            known_domains = [
                d for d, s in profile.get("knowledge_domains", {}).items()
                if s >= 0.6
            ]
            if known_domains:
                domains_str = ", ".join(sorted(known_domains))
                directives.append(
                    f"User is knowledgeable in: {domains_str}. "
                    "Skip basic explanations in these areas."
                )

            # Pain points (avoid disliked patterns)
            pain_points = profile.get("pain_points", [])
            if pain_points:
                top_pains = pain_points[-3:]  # most recent 3
                for pain in top_pains:
                    directives.append(
                        f"Note: User dislikes '{pain}'. Avoid this pattern."
                    )

            # Filter empty strings
            return [d for d in directives if d]

    def get_skill_suggestions(self) -> List[str]:
        """Recommend skills based on what the user builds.

        Maps favorite project types to relevant skill names from the
        169 built-in skills.

        Returns:
            List of skill names the user might find useful.
        """
        with self._lock:
            profile = self._profile
            favorites = profile.get("favorite_builds", [])

            if not favorites:
                return []

            # Map project types to skill names
            project_to_skills: Dict[str, List[str]] = {
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
                    "memes-template-generator",
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
                "data science": [
                    "jupyter-live-kernel", "chroma", "faiss",
                    "duckduckgo-search", "stocks",
                ],
            }

            suggested: Set[str] = set()
            for fav in favorites:
                for key, skills in project_to_skills.items():
                    if key in fav.lower():
                        suggested.update(skills)

            return sorted(suggested)

    def should_explain(self, concept: str) -> bool:
        """Check if the user needs an explanation for a concept.

        Args:
            concept: The concept or domain to check.

        Returns:
            True if the agent should explain, False if the user already
            knows this domain and a brief mention suffices.
        """
        with self._lock:
            knowledge = self._profile.get("knowledge_domains", {})
            concept_lower = concept.lower()

            # Direct domain match
            for domain, score in knowledge.items():
                if domain.lower() in concept_lower or concept_lower in domain.lower():
                    return score < 0.5

            # Broader category match
            domain_categories: Dict[str, List[str]] = {
                "python": ["python", "list comprehension", "decorator", "generator",
                          "async/await", "type hint", "pydantic"],
                "javascript": ["javascript", "typescript", "promise", "async",
                              "closure", "prototype"],
                "machine learning": ["neural network", "transformer", "attention",
                                    "backpropagation", "loss function", "gradient descent",
                                    "embedding", "tokenization"],
                "devops": ["docker", "kubernetes", "ci/cd", "containerization",
                          "orchestration", "terraform"],
                "web": ["html", "css", "http", "rest", "graphql", "api",
                       "dom", "event loop", "responsive design"],
                "databases": ["sql", "nosql", "index", "query optimization",
                            "normalization", "transaction", "acid"],
                "security": ["authentication", "authorization", "encryption",
                            "hashing", "jwt", "oauth", "cors", "csrf", "xss"],
                "blockchain": ["blockchain", "smart contract", "consensus",
                              "proof of work", "proof of stake", "gas"],
            }

            for category, keywords in domain_categories.items():
                for kw in keywords:
                    if kw in concept_lower or concept_lower in kw:
                        score = knowledge.get(category, 0.0)
                        return score < 0.5

            # Unknown concept — default to explaining
            return True

    def add_favorite_build(self, project_type: str) -> None:
        """Manually add a favorite project type.

        Args:
            project_type: The project type to add (e.g. "trading bot").
        """
        with self._lock:
            if project_type not in self._profile["favorite_builds"]:
                self._profile["favorite_builds"].append(project_type)
                self._save()
                logger.debug("Manually added favorite build: %s", project_type)

    def add_pain_point(self, issue: str) -> None:
        """Manually record something the user dislikes.

        Args:
            issue: Description of the pain point.
        """
        with self._lock:
            if issue not in self._profile["pain_points"]:
                self._profile["pain_points"].append(issue)
                self._save()
                logger.debug("Manually added pain point: %s", issue)

    def set_timezone(self, tz_name: str) -> None:
        """Manually set the user's timezone.

        Args:
            tz_name: IANA timezone name (e.g. "America/New_York").
        """
        with self._lock:
            self._profile["timezone"] = tz_name
            self._save()

    def set_preferred_example(self, style: str) -> None:
        """Manually set the preferred example style.

        Args:
            style: One of 'code_first', 'concepts_first', 'analogies',
                   or 'adaptive'.

        Raises:
            ValueError: If style is not recognized.
        """
        valid_styles = {"code_first", "concepts_first", "analogies", "adaptive"}
        if style not in valid_styles:
            raise ValueError(
                f"Unknown example style '{style}'. "
                f"Valid: {', '.join(sorted(valid_styles))}"
            )
        with self._lock:
            self._profile["preferred_example"] = style
            self._save()

    # ── Profile Properties ───────────────────────────────────────────

    @property
    def communication_style(self) -> str:
        return self._profile.get("communication_style", "adaptive")

    @property
    def humor_style(self) -> str:
        return self._profile.get("humor_style", "none")

    @property
    def favorite_builds(self) -> List[str]:
        return list(self._profile.get("favorite_builds", []))

    @property
    def preferred_example(self) -> str:
        return self._profile.get("preferred_example", "adaptive")

    @property
    def skill_affinities(self) -> Dict[str, int]:
        return dict(self._profile.get("skill_affinities", {}))

    @property
    def knowledge_domains(self) -> Dict[str, float]:
        return dict(self._profile.get("knowledge_domains", {}))

    @property
    def pain_points(self) -> List[str]:
        return list(self._profile.get("pain_points", []))

    @property
    def tone_preference(self) -> str:
        return self._profile.get("tone_preference", "direct")

    @property
    def timezone(self) -> Optional[str]:
        return self._profile.get("timezone")

    @property
    def work_hours(self) -> Dict[str, int]:
        return dict(self._profile.get("work_hours", {}))

    @property
    def total_messages(self) -> int:
        return self._profile.get("total_messages", 0)

    @property
    def session_count(self) -> int:
        return self._profile.get("session_count", 0)

    def increment_session(self) -> None:
        """Increment the session counter (call at session start)."""
        with self._lock:
            self._profile["session_count"] = self._profile.get("session_count", 0) + 1
            self._save()

    # ── Export / Import ──────────────────────────────────────────────

    def export(self, path: Optional[Path] = None) -> Dict[str, Any]:
        """Export the profile as a portable dict.

        Args:
            path: Optional file path to write the profile to. If not
                  provided, returns the dict without writing to disk.

        Returns:
            The complete profile data as a dict.
        """
        with self._lock:
            data = self._to_exportable()

            if path:
                path = Path(path).expanduser()
                path.parent.mkdir(parents=True, exist_ok=True)
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, default=str)
                logger.info("Exported profile to %s", path)

            return data

    def import_profile(self, source: Path | Dict[str, Any]) -> None:
        """Import a profile from a file or dict.

        Args:
            source: A ``Path`` to a JSON file or a dict with profile data.

        Raises:
            ValueError: If the source is invalid or missing required fields.
        """
        with self._lock:
            if isinstance(source, Path):
                src_path = source.expanduser()
                if not src_path.exists():
                    raise FileNotFoundError(f"Profile file not found: {src_path}")
                try:
                    with open(src_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                except (json.JSONDecodeError, OSError) as exc:
                    raise ValueError(f"Failed to load profile from {src_path}: {exc}")
            elif isinstance(source, dict):
                data = source
            else:
                raise ValueError(
                    "Source must be a Path or dict, "
                    f"got {type(source).__name__}"
                )

            # Validate structure
            required_keys = {"communication_style", "favorite_builds", "tone_preference"}
            missing = required_keys - set(data.keys())
            if missing:
                raise ValueError(
                    f"Missing required profile fields: {', '.join(sorted(missing))}"
                )

            # Merge imported data into current profile
            merged = _DEFAULT_PROFILE.copy()
            merged.update(data)

            # Deep merge nested structures
            for nested_key in ("signals", "knowledge_domains", "work_hours"):
                if nested_key in data and isinstance(data[nested_key], dict):
                    current_val = merged.get(nested_key, {})
                    if isinstance(current_val, dict):
                        current_val.update(data[nested_key])
                    else:
                        merged[nested_key] = data[nested_key]
                elif nested_key in _DEFAULT_PROFILE and nested_key not in data:
                    merged[nested_key] = _DEFAULT_PROFILE[nested_key]

            self._profile = merged
            self._save()
            logger.info("Imported profile (%d fields)", len(data))

    def _to_exportable(self) -> Dict[str, Any]:
        """Convert profile to a clean exportable dict (no internal state)."""
        profile = self._profile.copy()
        # Convert Counter to dict for JSON serialization
        signals = profile.get("signals", {})
        if isinstance(signals.get("vocabulary_clues"), Counter):
            signals["vocabulary_clues"] = dict(signals["vocabulary_clues"])
        return profile

    # ── Utility ──────────────────────────────────────────────────────

    def __repr__(self) -> str:
        with self._lock:
            return (
                f"UserProfile("
                f"style={self._profile.get('communication_style', '?')}, "
                f"tone={self._profile.get('tone_preference', '?')}, "
                f"messages={self._profile.get('total_messages', 0)}, "
                f"builds={len(self._profile.get('favorite_builds', []))})"
            )

    def to_dict(self) -> Dict[str, Any]:
        """Return the current profile as a plain dict."""
        with self._lock:
            return self._to_exportable()
