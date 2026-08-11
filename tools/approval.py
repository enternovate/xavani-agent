# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Dangerous command approval -- detection, prompting, and per-session state.

This module is the single source of truth for the dangerous command system:
- Risk tiers (RISK_TIER_SAFE / RISK_TIER_WARN / RISK_TIER_BLOCK,
  classify_command_risk) — the approval model is a three-tier ladder:
    * ``block``  — HARDLINE_PATTERNS: catastrophic commands with no recovery
      path (rm -rf /, mkfs, dd to raw block device, shutdown/reboot, fork
      bomb, kill -1). Unconditionally denied even under --yolo / mode=off.
    * ``warn``   — DANGEROUS_PATTERNS: costly-but-recoverable commands
      (recursive deletes, git force push, curl|sh, sudo -S, ...). Requires
      interactive/gateway approval unless approved or yolo.
    * ``safe``   — matches neither list; runs without approval.
- Pattern detection (DANGEROUS_PATTERNS, detect_dangerous_command)
- Dangerous command CHAIN detection (detect_dangerous_chain) — 2+ dangerous
  commands joined by shell separators (&&, ;, |, ||) flagged as a chain.
- Per-session approval state (thread-safe, keyed by session_key)
- Approval prompting (CLI interactive + gateway async)
- Smart approval via auxiliary LLM (auto-approve low-risk commands)
- Permanent allowlist persistence (config.yaml)

Note: containerized backends (docker, singularity, modal, daytona) bypass
the approval layer entirely — nothing they run can touch the host.
"""

import contextvars
import logging
import os
import re
import sys
import threading
import time
import unicodedata
from typing import Optional
from xavani_cli.config import cfg_get

from utils import env_var_enabled, is_truthy_value

# Hoisted to module top: lazy imports of gateway.session_context inside worker
# threads deadlock on the global import lock when the main thread is mid-import
# of a gateway.* submodule (Python issue #83054-class circular hang).
from gateway.session_context import get_session_env

logger = logging.getLogger(__name__)
try:
    from xavani_cli.safe_logging import SafeLogFilter
    SafeLogFilter.install()
except Exception:
    pass

# Per-thread/per-task gateway session identity.
# Gateway runs agent turns concurrently in executor threads, so reading a
# process-global env var for session identity is racy. Keep env fallback for
# legacy single-threaded callers, but prefer the context-local value when set.
_approval_session_key: contextvars.ContextVar[str] = contextvars.ContextVar(
    "approval_session_key",
    default="",
)

_approval_reason: contextvars.ContextVar[str] = contextvars.ContextVar(
    "approval_reason",
    default="",
)


def _fire_approval_hook(hook_name: str, **kwargs) -> None:
    """Invoke a plugin lifecycle hook for the approval system.

    Lazy-imports the plugin manager to avoid circular imports (approval.py is
    imported very early, long before plugins are discovered). Never raises --
    plugin errors are logged and swallowed.

    Only fires for the two approval-specific hooks in VALID_HOOKS:
    pre_approval_request, post_approval_response.
    """
    try:
        from xavani_cli.plugins import invoke_hook
    except Exception:
        # Plugin system not available in this execution context
        # (e.g. bare tool-only imports, minimal test environments).
        return
    try:
        invoke_hook(hook_name, **kwargs)
    except Exception as exc:
        # invoke_hook() already swallows per-callback errors, so reaching here
        # means the dispatch layer itself failed. Log and move on -- approval
        # flow is safety-critical, plugin observability is not.
        logger.debug("Approval hook %s dispatch failed: %s", hook_name, exc)


def _log_approval_decision(
    decision: str,
    reason: str,
    command: str = "",
    pattern_key: Optional[str] = None,
    description: str = "",
    session_key: str = "",
    extra: Optional[dict] = None,
) -> None:
    """Record an approval decision with its reasoning chain (D09).

    Best-effort: a failing log must never break the approval flow.
    ``decision`` is one of allow/deny/ask/timeout; ``reason`` names the
    decision category (hardline, yolo, smart, user, cron, ...).
    """
    try:
        from xavani_approval_reasoning import record_approval_reasoning

        record_approval_reasoning(
            decision=decision,
            reason=reason,
            command=command,
            pattern_key=pattern_key,
            description=description,
            session_key=session_key or get_current_session_key(),
            extra=extra,
        )
    except Exception:
        pass



def set_current_session_key(session_key: str) -> contextvars.Token[str]:
    """Bind the active approval session key to the current context."""
    return _approval_session_key.set(session_key or "")


def reset_current_session_key(token: contextvars.Token[str]) -> None:
    """Restore the prior approval session key context."""
    _approval_session_key.reset(token)


def get_current_session_key(default: str = "default") -> str:
    """Return the active session key, preferring context-local state.

    Resolution order:
    1. approval-specific contextvars (set by gateway before agent.run)
    2. session_context contextvars (set by _set_session_env)
    3. os.environ fallback (CLI, cron, tests)
    """
    session_key = _approval_session_key.get()
    if session_key:
        return session_key
    return get_session_env("XAVANI_SESSION_KEY", default)


def set_current_approval_reason(reason: str) -> contextvars.Token[str]:
    """Bind the current approval reason to the active context.

    The agent loop sets the model's reasoning for the current turn here so
    every approval prompt in that turn shows the rationale (J232).
    """
    return _approval_reason.set(reason or "")


def reset_current_approval_reason(token: contextvars.Token[str]) -> None:
    """Restore the prior approval reason context."""
    _approval_reason.reset(token)


def get_current_approval_reason() -> str:
    """Return the active approval reason (empty when unset)."""
    return _approval_reason.get()


def _get_session_platform() -> str:
    """Return the current gateway platform from contextvars/env fallback."""
    try:
        return get_session_env("XAVANI_SESSION_PLATFORM", "") or ""
    except Exception:
        return os.getenv("XAVANI_SESSION_PLATFORM", "") or ""


def _is_gateway_approval_context() -> bool:
    """True when this call is inside a gateway/API session.

    Legacy gateway integrations set XAVANI_GATEWAY_SESSION in process env.
    Newer concurrent gateway paths bind XAVANI_SESSION_PLATFORM via
    contextvars so approval mode does not depend on process-global flags.

    Cron jobs are NEVER gateway-approval contexts even when they originate
    from a gateway platform (cron binds XAVANI_SESSION_PLATFORM via
    contextvars for delivery routing). Cron approvals are governed by
    ``approvals.cron_mode`` config, not interactive resolve — letting cron
    fall through to the gateway branch would submit a pending approval
    with no listener and block the job indefinitely.
    """
    if env_var_enabled("XAVANI_CRON_SESSION"):
        return False
    if env_var_enabled("XAVANI_GATEWAY_SESSION"):
        return True
    return bool(_get_session_platform())

# Sensitive write targets that should trigger approval even when referenced
# via shell expansions like $HOME or $XAVANI_HOME.
_SSH_SENSITIVE_PATH = r'(?:~|\$home|\$\{home\})/\.ssh(?:/|$)'
_XAVANI_ENV_PATH = (
    r'(?:~\/\.xavani/|'
    r'(?:\$home|\$\{home\})/\.xavani/|'
    r'(?:\$xavani_home|\$\{xavani_home\})/)'
    r'\.env\b'
)
_PROJECT_ENV_PATH = r'(?:(?:/|\.{1,2}/)?(?:[^\s/"\'`]+/)*\.env(?:\.[^/\s"\'`]+)*)'
_PROJECT_CONFIG_PATH = r'(?:(?:/|\.{1,2}/)?(?:[^\s/"\'`]+/)*config\.yaml)'
_SHELL_RC_FILES = (
    r'(?:~|\$home|\$\{home\})/\.'
    r'(?:bashrc|zshrc|profile|bash_profile|zprofile)\b'
)
_CREDENTIAL_FILES = (
    r'(?:~|\$home|\$\{home\})/\.'
    r'(?:netrc|pgpass|npmrc|pypirc)\b'
)
# macOS: /etc, /var, /tmp, /home are symlinks to /private/{etc,var,tmp,home}.
# A command written to target /private/etc/sudoers works identically to
# /etc/sudoers on macOS but bypasses a plain "/etc/" pattern check. Match
# both forms. Inspired by Claude Code 2.1.113's "dangerous path protection".
_MACOS_PRIVATE_SYSTEM_PATH = r'/private/(?:etc|var|tmp|home)/'
# System-config paths that should trigger approval for any write/edit,
# collapsing /etc, its macOS /private/etc mirror, and /etc/sudoers.d/ into
# one shared fragment so new DANGEROUS_PATTERNS stay consistent.
_SYSTEM_CONFIG_PATH = (
    rf'(?:/etc/|{_MACOS_PRIVATE_SYSTEM_PATH})'
)
_SENSITIVE_WRITE_TARGET = (
    rf'(?:{_SYSTEM_CONFIG_PATH}|/dev/sd|'
    rf'{_SSH_SENSITIVE_PATH}|'
    rf'{_XAVANI_ENV_PATH}|'
    rf'{_SHELL_RC_FILES}|'
    rf'{_CREDENTIAL_FILES})'
)
_PROJECT_SENSITIVE_WRITE_TARGET = rf'(?:{_PROJECT_ENV_PATH}|{_PROJECT_CONFIG_PATH})'
_COMMAND_TAIL = r'(?:\s*(?:&&|\|\||;).*)?$'

# =========================================================================
# Hardline (unconditional) blocklist
# =========================================================================
#
# Commands so catastrophic they should NEVER run via the agent, regardless
# of --yolo, /yolo, approvals.mode=off, or cron approve mode.  This is a
# floor below yolo: opting into yolo is the user trusting the agent with
# their files and services, not trusting it to wipe the disk or power the
# box off.
#
# Hardline only applies to environments that can actually damage the host
# (local, ssh, container-host cron).  Containerized backends (docker,
# singularity, modal, daytona) already bypass the dangerous-command layer
# because nothing they do can touch the host, so we leave that behavior
# alone.
#
# The list is deliberately tiny — only things with no recovery path:
# filesystem destruction rooted at /, raw block device overwrites, kernel
# shutdown/reboot, and denial-of-service commands that take the host down.
# Recoverable-but-costly operations (git reset --hard, rm -rf /tmp/x,
# chmod -R 777, curl|sh) stay in DANGEROUS_PATTERNS where yolo can pass
# them through — that's what yolo is for.
#
# Inspired by Mercury Agent's permission-hardened blocklist
# (https://github.com/cosmicstack-labs/mercury-agent).

# Regex fragment matching the *start* of a command (i.e. positions where
# a shell would begin parsing a new command).  Used by shutdown/reboot
# patterns so they don't fire on "echo reboot" or "grep 'shutdown' log".
# Matches: start of string, after command separators (; && || | newline),
# after subshell openers ( `$(` or backtick ), optionally consuming
# leading wrapper commands (sudo, env VAR=VAL, exec, nohup, setsid).
_CMDPOS = (
    r'(?:^|[;&|\n`]|\$\()'         # start position
    r'\s*'                          # optional whitespace
    r'(?:sudo\s+(?:-[^\s]+\s+)*)?'  # optional sudo with flags
    r'(?:env\s+(?:\w+=\S*\s+)*)?'   # optional env with VAR=VAL pairs
    r'(?:(?:exec|nohup|setsid|time)\s+)*'  # optional wrapper commands
    r'\s*'
)

HARDLINE_PATTERNS = [
    # rm recursive targeting the root filesystem or protected roots
    (r'\brm\s+(-[^\s]*\s+)*(/|/\*|/ \*)(\s|$)', "recursive delete of root filesystem"),
    (r'\brm\s+(-[^\s]*\s+)*(/home|/home/\*|/root|/root/\*|/etc|/etc/\*|/usr|/usr/\*|/var|/var/\*|/bin|/bin/\*|/sbin|/sbin/\*|/boot|/boot/\*|/lib|/lib/\*)(\s|$)', "recursive delete of system directory"),
    (r'\brm\s+(-[^\s]*\s+)*(~|\$HOME)(/?|/\*)?(\s|$)', "recursive delete of home directory"),
    # Filesystem format
    (r'\bmkfs(\.[a-z0-9]+)?\b', "format filesystem (mkfs)"),
    # Raw block device overwrites (dd + redirection)
    (r'\bdd\b[^\n]*\bof=/dev/(sd|nvme|hd|mmcblk|vd|xvd)[a-z0-9]*', "dd to raw block device"),
    (r'>\s*/dev/(sd|nvme|hd|mmcblk|vd|xvd)[a-z0-9]*\b', "redirect to raw block device"),
    # Fork bomb (classic shell form)
    (r':\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:', "fork bomb"),
    # Kill every process on the system
    (r'\bkill\s+(-[^\s]+\s+)*-1\b', "kill all processes"),
    # System shutdown / reboot — anchor to command position (start of line,
    # after a command separator, or after sudo/env wrappers) so we don't
    # false-positive on "echo reboot" or "grep 'shutdown' logs".
    # _CMDPOS matches start-of-command positions.
    (_CMDPOS + r'(shutdown|reboot|halt|poweroff)\b', "system shutdown/reboot"),
    (_CMDPOS + r'init\s+[06]\b', "init 0/6 (shutdown/reboot)"),
    (_CMDPOS + r'systemctl\s+(poweroff|reboot|halt|kexec)\b', "systemctl poweroff/reboot"),
    (_CMDPOS + r'telinit\s+[06]\b', "telinit 0/6 (shutdown/reboot)"),
]

# Pre-compiled variant used by the hot-path matcher. Building these at module
# load eliminates the ~2.6 ms cold-cache re.compile fan-out on the first
# terminal() call per process (12 HARDLINE + 47 DANGEROUS patterns, each
# potentially evicted from Python's 512-entry ``re._cache`` by unrelated
# regex work elsewhere in the agent). DANGEROUS_PATTERNS_COMPILED is built
# at the end of this module after DANGEROUS_PATTERNS is defined.
_RE_FLAGS = re.IGNORECASE | re.DOTALL
HARDLINE_PATTERNS_COMPILED = [
    (re.compile(pattern, _RE_FLAGS), description)
    for pattern, description in HARDLINE_PATTERNS
]


# =========================================================================
# Sudo stdin guard — block password guessing via "sudo -S"
# =========================================================================
# When SUDO_PASSWORD is not configured, any explicit "sudo -S" in the
# command is the LLM piping a guessed password via stdin.  This is a
# brute-force attack vector: the model iterates through candidate
# passwords, inspects sudo's "Sorry, try again" output, and refines.
# Treat this as an unconditional block — there is never a legitimate
# reason for the agent to pipe passwords to sudo -S when no password
# has been configured.
_SUDO_STDIN_RE = re.compile(
    r'(?:^|[;&|`\n]|&&|\|\||\$\()\s*sudo\s+-S\b',
    re.IGNORECASE)


def _check_sudo_stdin_guard(command: str) -> tuple:
    """Detect ``sudo -S`` (stdin password) without configured SUDO_PASSWORD.

    When SUDO_PASSWORD is set, ``_transform_sudo_command`` injects ``-S``
    internally — that path is legitimate and handled elsewhere.  This guard
    only fires when SUDO_PASSWORD is *not* set, meaning the LLM explicitly
    wrote ``sudo -S`` to pipe a guessed password.

    Returns:
        (is_blocked: bool, description: str | None)
    """
    if "SUDO_PASSWORD" in os.environ:
        return (False, None)
    normalized = _normalize_command_for_detection(command).lower()
    if _SUDO_STDIN_RE.search(normalized):
        return (True, "sudo password guessing via stdin (sudo -S)")
    return (False, None)


def detect_hardline_command(command: str) -> tuple:
    """Check if a command matches the unconditional hardline blocklist.

    Returns:
        (is_hardline, description) or (False, None)
    """
    normalized = _normalize_command_for_detection(command).lower()
    for pattern_re, description in HARDLINE_PATTERNS_COMPILED:
        if pattern_re.search(normalized):
            return (True, description)
    return (False, None)


def _hardline_block_result(description: str) -> dict:
    """Build the standard block result for a hardline match."""
    return {
        "approved": False,
        "hardline": True,
        "message": (
            f"BLOCKED (hardline): {description}. "
            "This command is on the unconditional blocklist and cannot "
            "be executed via the agent — not even with --yolo, /yolo, "
            "approvals.mode=off, or cron approve mode. If you genuinely "
            "need to run it, run it yourself in a terminal outside the "
            "agent."
        ),
    }


def _sudo_stdin_block_result(description: str) -> dict:
    """Build the standard block result for sudo stdin guard."""
    return {
        "approved": False,
        "message": (
            f"BLOCKED: {description}. "
            "Do not pipe passwords to 'sudo -S' — this is a brute-force "
            "attack vector. Set SUDO_PASSWORD in your .env file if the "
            "agent needs passwordless sudo, or run the sudo command "
            "manually in your own terminal."
        ),
    }


# =========================================================================
# Dangerous command patterns
# =========================================================================

DANGEROUS_PATTERNS = [
    (r'\brm\s+(-[^\s]*\s+)*/', "delete in root path"),
    (r'\brm\s+-[^\s]*r', "recursive delete"),
    (r'\brm\s+--recursive\b', "recursive delete (long flag)"),
    (r'\bchmod\s+(-[^\s]*\s+)*(777|666|o\+[rwx]*w|a\+[rwx]*w)\b', "world/other-writable permissions"),
    (r'\bchmod\s+--recursive\b.*(777|666|o\+[rwx]*w|a\+[rwx]*w)', "recursive world/other-writable (long flag)"),
    (r'\bchown\s+(-[^\s]*)?R\s+root', "recursive chown to root"),
    (r'\bchown\s+--recursive\b.*root', "recursive chown to root (long flag)"),
    (r'\bmkfs\b', "format filesystem"),
    (r'\bdd\s+.*if=', "disk copy"),
    (r'>\s*/dev/sd', "write to block device"),
    (r'\bDROP\s+(TABLE|DATABASE)\b', "SQL DROP"),
    # Use [^\n]* instead of .* so DOTALL mode does not cause a WHERE clause on the
    # *next* line to satisfy the negative lookahead, silently allowing DELETE without WHERE.
    (r'\bDELETE\s+FROM\b(?![^\n]*\bWHERE\b)', "SQL DELETE without WHERE"),
    (r'\bTRUNCATE\s+(TABLE)?\s*\w', "SQL TRUNCATE"),
    (rf'>\s*{_SYSTEM_CONFIG_PATH}', "overwrite system config"),
    (r'\bsystemctl\s+(-[^\s]+\s+)*(stop|restart|disable|mask)\b', "stop/restart system service"),
    (r'\bkill\s+-9\s+-1\b', "kill all processes"),
    (r'\bpkill\s+-9\b', "force kill processes"),
    # killall with SIGKILL (parallel to pkill -9). Catches -9 / -KILL /
    # -s KILL / -SIGKILL forms, and also `killall -r <regex>` broad sweeps
    # that can wipe out unrelated processes by accident.
    # Inspired by Claude Code 2.1.113 expanded deny rules.
    (r'\bkillall\s+(-[^\s]*\s+)*-(9|KILL|SIGKILL)\b', "force kill processes (killall -KILL)"),
    (r'\bkillall\s+(-[^\s]*\s+)*-s\s+(KILL|SIGKILL|9)\b', "force kill processes (killall -s KILL)"),
    (r'\bkillall\s+(-[^\s]*\s+)*-r\b', "kill processes by regex (killall -r)"),
    (r':\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:', "fork bomb"),
    # Any shell invocation via -c or combined flags like -lc, -ic, etc.
    (r'\b(bash|sh|zsh|ksh)\s+-[^\s]*c(\s+|$)', "shell command via -c/-lc flag"),
    (r'\b(python[23]?|perl|ruby|node)\s+-[ec]\s+', "script execution via -e/-c flag"),
    (r'\b(curl|wget)\b.*\|\s*(ba)?sh\b', "pipe remote content to shell"),
    (r'\b(bash|sh|zsh|ksh)\s+<\s*<?\s*\(\s*(curl|wget)\b', "execute remote script via process substitution"),
    (rf'\btee\b.*["\']?{_SENSITIVE_WRITE_TARGET}', "overwrite system file via tee"),
    (rf'>>?\s*["\']?{_SENSITIVE_WRITE_TARGET}', "overwrite system file via redirection"),
    (rf'\btee\b.*["\']?{_PROJECT_SENSITIVE_WRITE_TARGET}["\']?{_COMMAND_TAIL}', "overwrite project env/config via tee"),
    (rf'>>?\s*["\']?{_PROJECT_SENSITIVE_WRITE_TARGET}["\']?{_COMMAND_TAIL}', "overwrite project env/config via redirection"),
    (r'\bxargs\s+.*\brm\b', "xargs with rm"),
    # find -exec rm / -execdir rm — the -execdir variant (same semantics,
    # runs in the directory of each match) was previously missed. Claude
    # Code 2.1.113 tightened their equivalent find rule to stop auto-
    # approving -exec / -delete flags.
    (r'\bfind\b.*-exec(?:dir)?\s+(/\S*/)?rm\b', "find -exec/-execdir rm"),
    (r'\bfind\b.*-delete\b', "find -delete"),
    # Gateway lifecycle protection: prevent the agent from killing its own
    # gateway process.  These commands trigger a gateway restart/stop that
    # terminates all running agents mid-work.
    (r'\bxavani\s+gateway\s+(stop|restart)\b', "stop/restart xavani gateway (kills running agents)"),
    (r'\bxavani\s+update\b', "xavani update (restarts gateway, kills running agents)"),
    # Gateway protection: never start gateway outside systemd management
    (r'gateway\s+run\b.*(&\s*$|&\s*;|\bdisown\b|\bsetsid\b)', "start gateway outside systemd (use 'systemctl --user restart xavani-gateway')"),
    (r'\bnohup\b.*gateway\s+run\b', "start gateway outside systemd (use 'systemctl --user restart xavani-gateway')"),
    # Self-termination protection: prevent agent from killing its own process
    (r'\b(pkill|killall)\b.*\b(xavani|gateway|cli\.py)\b', "kill xavani/gateway process (self-termination)"),
    # Self-termination via kill + command substitution (pgrep/pidof).
    # The name-based pattern above catches `pkill xavani` but not
    # `kill -9 $(pgrep -f xavani)` because the substitution is opaque
    # to regex at detection time. Catch the structural pattern instead.
    (r'\bkill\b.*\$\(\s*pgrep\b', "kill process via pgrep expansion (self-termination)"),
    (r'\bkill\b.*`\s*pgrep\b', "kill process via backtick pgrep expansion (self-termination)"),
    # File copy/move/edit into sensitive system paths (/etc/ and macOS
    # /private/etc/ mirror).
    (rf'\b(cp|mv|install)\b.*\s{_SYSTEM_CONFIG_PATH}', "copy/move file into system config path"),
    (rf'\b(cp|mv|install)\b.*\s["\']?{_PROJECT_SENSITIVE_WRITE_TARGET}["\']?{_COMMAND_TAIL}', "overwrite project env/config file"),
    (rf'\bsed\s+-[^\s]*i.*\s{_SYSTEM_CONFIG_PATH}', "in-place edit of system config"),
    (rf'\bsed\s+--in-place\b.*\s{_SYSTEM_CONFIG_PATH}', "in-place edit of system config (long flag)"),
    # Script execution via heredoc — bypasses the -e/-c flag patterns above.
    # `python3 << 'EOF'` feeds arbitrary code via stdin without -c/-e flags.
    (r'\b(python[23]?|perl|ruby|node)\s+<<', "script execution via heredoc"),
    # Git destructive operations that can lose uncommitted work or rewrite
    # shared history. Not captured by rm/chmod/etc patterns.
    (r'\bgit\s+reset\s+--hard\b', "git reset --hard (destroys uncommitted changes)"),
    (r'\bgit\s+push\b.*--force\b', "git force push (rewrites remote history)"),
    (r'\bgit\s+push\b.*-f\b', "git force push short flag (rewrites remote history)"),
    (r'\bgit\s+clean\s+-[^\s]*f', "git clean with force (deletes untracked files)"),
    (r'\bgit\s+branch\s+-D\b', "git branch force delete"),
    # Script execution after chmod +x — catches the two-step pattern where
    # a script is first made executable then immediately run. The script
    # content may contain dangerous commands that individual patterns miss.
    (r'\bchmod\s+\+x\b.*[;&|]+\s*\./', "chmod +x followed by immediate execution"),
    # Sudo with stdin / askpass / shell / list-privs flags. An LLM-driven
    # agent has no TTY, so sudo invocations that succeed without human
    # interaction are those reading the password from stdin (-S/--stdin)
    # or via an askpass helper (-A/--askpass). The shell-launch (-s) and
    # list-privileges (-a) flags are also gated since they are
    # privilege-relevant invocations the agent can chain after acquiring
    # the password (e.g. read SUDO_PASSWORD from .env -> sudo -S -s ->
    # root shell). Plain `sudo cmd` (no flag) is TTY-bound and excluded.
    # `_normalize_command_for_detection` lowercases input before pattern
    # matching, so case variants of S/s and A/a collapse — both forms
    # are gated below. Lazy `[^;|&\n]*?` allows flag arguments (e.g.
    # `sudo -u root -S whoami`) without spanning command separators. See
    # #17873 category 4.
    (r'\bsudo\b[^;|&\n]*?\s+(?:-s\b|--stdin\b|-a\b|--askpass\b)',
     "sudo with privilege flag (stdin/askpass/shell/list)"),
    # Combined short-flag form: -nS, -ns, -sa, -las — sudo flags packed
    # into a single -X token. Catches the same threat class.
    (r'\bsudo\b[^;|&\n]*?\s+-[a-z]*[sa][a-z]*\b',
     "sudo with combined-flag privilege escalation"),
]


# Pre-compiled variant (same rationale as HARDLINE_PATTERNS_COMPILED above).
DANGEROUS_PATTERNS_COMPILED = [
    (re.compile(pattern, _RE_FLAGS), description)
    for pattern, description in DANGEROUS_PATTERNS
]


def _legacy_pattern_key(pattern: str) -> str:
    """Reproduce the old regex-derived approval key for backwards compatibility."""
    return pattern.split(r'\b')[1] if r'\b' in pattern else pattern[:20]


_PATTERN_KEY_ALIASES: dict[str, set[str]] = {}
for _pattern, _description in DANGEROUS_PATTERNS:
    _legacy_key = _legacy_pattern_key(_pattern)
    _canonical_key = _description
    _PATTERN_KEY_ALIASES.setdefault(_canonical_key, set()).update({_canonical_key, _legacy_key})
    _PATTERN_KEY_ALIASES.setdefault(_legacy_key, set()).update({_legacy_key, _canonical_key})


def _approval_key_aliases(pattern_key: str) -> set[str]:
    """Return all approval keys that should match this pattern.

    New approvals use the human-readable description string, but older
    command_allowlist entries and session approvals may still contain the
    historical regex-derived key.
    """
    return _PATTERN_KEY_ALIASES.get(pattern_key, {pattern_key})


# =========================================================================
# Detection
# =========================================================================

def _normalize_command_for_detection(command: str) -> str:
    """Normalize a command string before dangerous-pattern matching.

    Strips ANSI escape sequences (full ECMA-48 via tools.ansi_strip),
    null bytes, and normalizes Unicode fullwidth characters so that
    obfuscation techniques cannot bypass the pattern-based detection.
    """
    from tools.ansi_strip import strip_ansi

    # Strip all ANSI escape sequences (CSI, OSC, DCS, 8-bit C1, etc.)
    command = strip_ansi(command)
    # Strip null bytes
    command = command.replace('\x00', '')
    # Normalize Unicode (fullwidth Latin, halfwidth Katakana, etc.)
    command = unicodedata.normalize('NFKC', command)
    return command


def detect_dangerous_command(command: str) -> tuple:
    """Check if a command matches any dangerous patterns.

    Returns:
        (is_dangerous, pattern_key, description) or (False, None, None)
    """
    command_lower = _normalize_command_for_detection(command).lower()
    for pattern_re, description in DANGEROUS_PATTERNS_COMPILED:
        if pattern_re.search(command_lower):
            pattern_key = description
            return (True, pattern_key, description)
    return (False, None, None)


# =========================================================================
# Risk tiers (D01) — safe / warn / block
# =========================================================================
# The approval model is a three-tier ladder:
#   block — HARDLINE_PATTERNS: catastrophic, no recovery path. Unconditionally
#           denied, even under --yolo / approvals.mode=off (see the hardline
#           floor in check_dangerous_command / check_all_command_guards).
#   warn  — DANGEROUS_PATTERNS: recoverable-but-costly; requires approval
#           unless pre-approved or yolo is active.
#   safe  — matches neither list; runs without approval.
RISK_TIER_SAFE = "safe"
RISK_TIER_WARN = "warn"
RISK_TIER_BLOCK = "block"
RISK_TIER_ORDER = (RISK_TIER_SAFE, RISK_TIER_WARN, RISK_TIER_BLOCK)
RISK_TIER_INFO = {
    RISK_TIER_SAFE: "no dangerous patterns; runs without approval",
    RISK_TIER_WARN: "matches DANGEROUS_PATTERNS; requires approval",
    RISK_TIER_BLOCK: "matches HARDLINE_PATTERNS; unconditionally blocked",
}


def classify_command_risk(command: str) -> str:
    """Classify a command into a risk tier: ``safe``, ``warn``, or ``block``.

    ``block`` wins over ``warn``: hardline patterns describe catastrophic
    commands that the approval layer denies unconditionally. Containerized
    backends bypass the approval layer entirely, but this classifier is
    pattern-based and does not know about the execution environment — callers
    that skip containers should skip this check too.

    Returns:
        One of RISK_TIER_SAFE / RISK_TIER_WARN / RISK_TIER_BLOCK.
    """
    normalized = _normalize_command_for_detection(command).lower()
    for pattern_re, _description in HARDLINE_PATTERNS_COMPILED:
        if pattern_re.search(normalized):
            return RISK_TIER_BLOCK
    for pattern_re, _description in DANGEROUS_PATTERNS_COMPILED:
        if pattern_re.search(normalized):
            return RISK_TIER_WARN
    return RISK_TIER_SAFE


# =========================================================================
# Dangerous command CHAINS (D05)
# =========================================================================
# A chain is 2+ dangerous commands joined by shell separators (&&, ;, |, ||,
# newline). Each command individually matches DANGEROUS_PATTERNS, so the
# existing single-command detection already flags them — the chain detector
# makes the *combination* explicit so approvals show the full chain instead
# of only the first matching pattern.

_SEPARATOR_CHARS = ("&&", "||", ";", "|", "\n")


def split_command_segments(command: str) -> list:
    """Best-effort split of a command into segments at shell separators.

    Separators inside single/double quotes are not treated as separators
    (a quoted ``;`` or ``&&`` is data, not a command boundary). This is a
    heuristic, not a full shell tokenizer — it intentionally stays simple.

    Returns:
        List of non-empty stripped segments.
    """
    segments = []
    current = []
    quote = None
    i = 0
    n = len(command)
    while i < n:
        ch = command[i]
        if quote:
            current.append(ch)
            if ch == quote:
                quote = None
            i += 1
            continue
        if ch in ("'", '"'):
            quote = ch
            current.append(ch)
            i += 1
            continue
        two = command[i:i + 2]
        if two in ("&&", "||"):
            segments.append("".join(current))
            current = []
            i += 2
            continue
        if ch in ";|\n":
            segments.append("".join(current))
            current = []
            i += 1
            continue
        current.append(ch)
        i += 1
    segments.append("".join(current))
    return [s.strip() for s in segments if s.strip()]


def detect_dangerous_chain(command: str, min_segments: int = 2) -> tuple:
    """Detect dangerous command CHAINS: ``min_segments`` (default 2) or more
    dangerous commands joined by shell separators (``&&``, ``;``, ``|``,
    ``||``, newline).

    Each segment is run through ``detect_dangerous_command`` independently,
    so ``rm -rf A && rm -rf B`` and ``git reset --hard HEAD && git push
    --force origin main`` are flagged while ``echo hi && rm -rf /tmp/x`` is
    not (only one dangerous segment).

    Returns:
        (is_chain, hits, description) where ``hits`` is a list of
        ``(segment, description)`` pairs for each dangerous segment, or
        (False, [], None) when fewer than ``min_segments`` segments match.
    """
    normalized = _normalize_command_for_detection(command).lower()
    hits = []
    for segment in split_command_segments(normalized):
        is_dangerous, _key, description = detect_dangerous_command(segment)
        if is_dangerous:
            hits.append((segment, description))
    if len(hits) >= min_segments:
        descriptions = [desc for _seg, desc in hits]
        return (
            True,
            hits,
            "dangerous command chain: " + "; ".join(descriptions),
        )
    return (False, [], None)


# =========================================================================
# Per-session approval state (thread-safe)
# =========================================================================

_lock = threading.Lock()
_pending: dict[str, dict] = {}
_session_approved: dict[str, set] = {}
_session_approved_by_user: dict[str, dict] = {}  # session_key -> user_id -> set
_session_yolo: set[str] = set()
_permanent_approved: set = set()


# ── D07: per-user approval scope ────────────────────────────────────
# Shared multi-user sessions (one session_key, many users) must not let
# user A's approval leak to user B. User-scoped approvals are keyed
# (session_key, user_id) and consulted before the session-wide set.


def _user_scope_key(session_key: str, user_id: str) -> str:
    """Compound key binding approval state to one user in a session."""
    return f"{session_key}::{user_id}" if user_id else session_key


def approve_session_for_user(session_key: str, user_id: str, pattern_key: str) -> None:
    """Approve a pattern for one user within a session (D07)."""
    if not user_id:
        approve_session(session_key, pattern_key)
        return
    with _lock:
        _session_approved_by_user.setdefault(session_key, {}).setdefault(user_id, set()).add(pattern_key)


def is_approved_for_user(session_key: str, user_id: str, pattern_key: str) -> bool:
    """True when the pattern is approved for this user in this session.

    Checks the user-scoped set first, then the session-wide set (a
    session-wide approval legitimately covers every user). Never raises.
    """
    try:
        if not user_id:
            return is_approved(session_key, pattern_key)
        with _lock:
            user_set = _session_approved_by_user.get(session_key, {}).get(user_id)
            if user_set and pattern_key in user_set:
                return True
            session_set = _session_approved.get(session_key)
            return bool(session_set and pattern_key in session_set)
    except Exception:
        return False


# =========================================================================
# Blocking gateway approval (mirrors CLI's synchronous input() flow)
# =========================================================================
# Per-session QUEUE of pending approvals.  Multiple threads (parallel
# subagents, execute_code RPC handlers) can block concurrently — each gets
# its own threading.Event.  /approve resolves the oldest, /approve all
# resolves every pending approval in the session.


class _ApprovalEntry:
    """One pending dangerous-command approval inside a gateway session."""
    __slots__ = ("event", "data", "result")

    def __init__(self, data: dict):
        self.event = threading.Event()
        self.data = data          # command, description, pattern_keys, …
        self.result: Optional[str] = None  # "once"|"session"|"always"|"deny"


_gateway_queues: dict[str, list] = {}        # session_key → [_ApprovalEntry, …]
_gateway_notify_cbs: dict[str, object] = {}  # session_key → callable(approval_data)


def register_gateway_notify(session_key: str, cb) -> None:
    """Register a per-session callback for sending approval requests to the user.

    The callback signature is ``cb(approval_data: dict) -> None`` where
    *approval_data* contains ``command``, ``description``, and
    ``pattern_keys``.  The callback bridges sync→async (runs in the agent
    thread, must schedule the actual send on the event loop).
    """
    with _lock:
        _gateway_notify_cbs[session_key] = cb


def unregister_gateway_notify(session_key: str) -> None:
    """Unregister the per-session gateway approval callback.

    Signals ALL blocked threads for this session so they don't hang forever
    (e.g. when the agent run finishes or is interrupted).
    """
    with _lock:
        _gateway_notify_cbs.pop(session_key, None)
        entries = _gateway_queues.pop(session_key, [])
    for entry in entries:
        entry.event.set()


def resolve_gateway_approval(session_key: str, choice: str,
                             resolve_all: bool = False) -> int:
    """Called by the gateway's /approve or /deny handler to unblock
    waiting agent thread(s).

    When *resolve_all* is True every pending approval in the session is
    resolved at once (``/approve all``).  Otherwise only the oldest one
    is resolved (FIFO).

    Returns the number of approvals resolved (0 means nothing was pending).
    """
    with _lock:
        queue = _gateway_queues.get(session_key)
        if not queue:
            return 0
        if resolve_all:
            targets = list(queue)
            queue.clear()
        else:
            targets = [queue.pop(0)]
        if not queue:
            _gateway_queues.pop(session_key, None)

    for entry in targets:
        entry.result = choice
        entry.event.set()
    return len(targets)


def has_blocking_approval(session_key: str) -> bool:
    """Check if a session has one or more blocking gateway approvals waiting."""
    with _lock:
        return bool(_gateway_queues.get(session_key))


def submit_pending(session_key: str, approval: dict):
    """Store a pending approval request for a session."""
    with _lock:
        _pending[session_key] = approval


def approve_session(session_key: str, pattern_key: str):
    """Approve a pattern for this session only."""
    with _lock:
        _session_approved.setdefault(session_key, set()).add(pattern_key)


def enable_session_yolo(session_key: str) -> None:
    """Enable YOLO bypass for a single session key."""
    if not session_key:
        return
    with _lock:
        _session_yolo.add(session_key)


def disable_session_yolo(session_key: str) -> None:
    """Disable YOLO bypass for a single session key."""
    if not session_key:
        return
    with _lock:
        _session_yolo.discard(session_key)


def clear_session(session_key: str) -> None:
    """Remove all approval and yolo state for a given session."""
    if not session_key:
        return
    with _lock:
        _session_approved.pop(session_key, None)
        _session_approved_by_user.pop(session_key, None)  # D07
        _session_yolo.discard(session_key)
        _pending.pop(session_key, None)
        entries = _gateway_queues.pop(session_key, [])
    for entry in entries:
        # Session-boundary cleanup should cancel any blocked approval waits
        # immediately so the old run can unwind instead of idling until timeout.
        entry.result = "deny"
        entry.event.set()


def is_session_yolo_enabled(session_key: str) -> bool:
    """Return True when YOLO bypass is enabled for a specific session."""
    if not session_key:
        return False
    with _lock:
        return session_key in _session_yolo


def is_current_session_yolo_enabled() -> bool:
    """Return True when the active approval session has YOLO bypass enabled."""
    return is_session_yolo_enabled(get_current_session_key(default=""))


def is_approved(session_key: str, pattern_key: str) -> bool:
    """Check if a pattern is approved (session-scoped or permanent).

    Accept both the current canonical key and the legacy regex-derived key so
    existing command_allowlist entries continue to work after key migrations.
    """
    aliases = _approval_key_aliases(pattern_key)
    with _lock:
        if any(alias in _permanent_approved for alias in aliases):
            return True
        session_approvals = _session_approved.get(session_key, set())
        return any(alias in session_approvals for alias in aliases)


def approve_permanent(pattern_key: str):
    """Add a pattern to the permanent allowlist."""
    with _lock:
        _permanent_approved.add(pattern_key)


def load_permanent(patterns: set):
    """Bulk-load permanent allowlist entries from config."""
    with _lock:
        _permanent_approved.update(patterns)



# =========================================================================
# Config persistence for permanent allowlist
# =========================================================================

def load_permanent_allowlist() -> set:
    """Load permanently allowed command patterns from config.

    Also syncs them into the approval module so is_approved() works for
    patterns added via 'always' in a previous session.
    """
    try:
        from xavani_cli.config import load_config
        config = load_config()
        patterns = set(config.get("command_allowlist", []) or [])
        if patterns:
            load_permanent(patterns)
        return patterns
    except Exception as e:
        logger.warning("Failed to load permanent allowlist: %s", e)
        return set()


def save_permanent_allowlist(patterns: set):
    """Save permanently allowed command patterns to config."""
    try:
        from xavani_cli.config import load_config, save_config
        config = load_config()
        config["command_allowlist"] = list(patterns)
        save_config(config)
    except Exception as e:
        logger.warning("Could not save allowlist: %s", e)


# =========================================================================
# Approval prompting + orchestration
# =========================================================================

def prompt_dangerous_approval(command: str, description: str,
                              timeout_seconds: int | None = None,
                              allow_permanent: bool = True,
                              approval_callback=None,
                              reason: str = "") -> str:
    """Prompt the user to approve a dangerous command (CLI only).

    Args:
        allow_permanent: When False, hide the [a]lways option (used when
            tirith warnings are present, since broad permanent allowlisting
            is inappropriate for content-level security findings).
        approval_callback: Optional callback registered by the CLI for
            prompt_toolkit integration. Signature:
            (command, description, *, allow_permanent=True, reason="") -> str.
        reason: The model's stated rationale for the command. When empty,
            falls back to the current context's approval reason (J232).
    """
    if timeout_seconds is None:
        timeout_seconds = _get_approval_timeout()

    if not reason:
        reason = get_current_approval_reason()

    if approval_callback is not None:
        try:
            return approval_callback(command, description,
                                     allow_permanent=allow_permanent,
                                     reason=reason)
        except TypeError:
            # Pre-J232 callbacks accept (command, description, *,
            # allow_permanent=True) only. Retry without the reason kwarg so
            # third-party callbacks never hit the deny-on-exception path.
            return approval_callback(command, description,
                                     allow_permanent=allow_permanent)
        except Exception as e:
            logger.error("Approval callback failed: %s", e, exc_info=True)
            return "deny"

    # Fail-closed guard: if prompt_toolkit owns the terminal (interactive
    # CLI session) and no approval callback is registered on this thread,
    # the input() fallback below would spawn a daemon thread whose read
    # can never see Enter -- the user's keystrokes go to prompt_toolkit,
    # not input(), producing an invisible 60s deadlock (issue #15216).
    # Deny fast and log loudly instead so the caller can surface a real
    # error to the agent. Any thread that needs interactive approval must
    # install a callback via tools.terminal_tool.set_approval_callback()
    # before reaching this point (see delegate_tool.py, run_agent.py
    # _execute_tool_calls_concurrent / _spawn_background_review for the
    # established pattern).
    try:
        from prompt_toolkit.application.current import get_app_or_none
        if get_app_or_none() is not None:
            logger.warning(
                "Dangerous-command approval requested on a thread with no "
                "approval callback while prompt_toolkit is active; denying "
                "to avoid stdin deadlock. command=%r description=%r",
                command, description,
            )
            return "deny"
    except Exception:
        # prompt_toolkit not installed, or detection failed -- fall through
        # to the legacy input() path (safe in non-TUI contexts: scripts,
        # tests, sshd, etc.).
        pass

    os.environ["XAVANI_SPINNER_PAUSE"] = "1"
    try:
        # Resolve the active UI language once per prompt so we don't re-read
        # config/YAML inside the retry loop below.
        from agent.i18n import t
        while True:
            print()
            print(f"  {t('approval.dangerous_header', description=description)}")
            print(f"      {command}")
            if reason:
                print(f"      Reason: {reason}")
            print()
            if allow_permanent:
                print(t("approval.choose_long"))
            else:
                print(t("approval.choose_short"))
            print()
            sys.stdout.flush()

            result = {"choice": ""}

            def get_input():
                try:
                    prompt = t("approval.prompt_long") if allow_permanent else t("approval.prompt_short")
                    result["choice"] = input(prompt).strip().lower()
                except (EOFError, OSError):
                    result["choice"] = ""

            thread = threading.Thread(target=get_input, daemon=True)
            thread.start()
            thread.join(timeout=timeout_seconds)

            if thread.is_alive():
                print("\n" + t("approval.timeout"))
                return "deny"

            choice = result["choice"]
            if choice in {'o', 'once'}:
                print(t("approval.allowed_once"))
                return "once"
            elif choice in {'s', 'session'}:
                print(t("approval.allowed_session"))
                return "session"
            elif choice in {'a', 'always'}:
                if not allow_permanent:
                    print(t("approval.allowed_session"))
                    return "session"
                print(t("approval.allowed_always"))
                return "always"
            else:
                print(t("approval.denied"))
                return "deny"

    except (EOFError, KeyboardInterrupt):
        print("\n" + t("approval.cancelled"))
        return "deny"
    finally:
        if "XAVANI_SPINNER_PAUSE" in os.environ:
            del os.environ["XAVANI_SPINNER_PAUSE"]
        print()
        sys.stdout.flush()


def _normalize_approval_mode(mode) -> str:
    """Normalize approval mode values loaded from YAML/config.

    YAML 1.1 treats bare words like `off` as booleans, so a config entry like
    `approvals:\n  mode: off` is parsed as False unless quoted. Treat that as the
    intended string mode instead of falling back to manual approvals.
    """
    if isinstance(mode, bool):
        return "off" if mode is False else "manual"
    if isinstance(mode, str):
        normalized = mode.strip().lower()
        return normalized or "manual"
    return "manual"


def _get_approval_config() -> dict:
    """Read the approvals config block. Returns a dict with 'mode', 'timeout', etc."""
    try:
        from xavani_cli.config import load_config
        config = load_config()
        return config.get("approvals", {}) or {}
    except Exception as e:
        logger.warning("Failed to load approval config: %s", e)
        return {}


def _get_approval_mode() -> str:
    """Read the approval mode from config. Returns 'manual', 'smart', or 'off'."""
    mode = _get_approval_config().get("mode", "manual")
    return _normalize_approval_mode(mode)


def _get_approval_timeout() -> int:
    """Read the approval timeout from config. Defaults to 60 seconds."""
    try:
        return int(_get_approval_config().get("timeout", 60))
    except (ValueError, TypeError):
        return 60


def _get_cron_approval_mode() -> str:
    """Read the cron approval mode from config. Returns 'deny' or 'approve'."""
    try:
        from xavani_cli.config import load_config
        config = load_config()
        mode = str(cfg_get(config, "approvals", "cron_mode", default="deny")).lower().strip()
        if mode in {"approve", "off", "allow", "yes"}:
            return "approve"
        return "deny"
    except Exception:
        return "deny"


def _smart_approve(command: str, description: str) -> str:
    """Use the auxiliary LLM to assess risk and decide approval.

    Returns 'approve' if the LLM determines the command is safe,
    'deny' if genuinely dangerous, or 'escalate' if uncertain.

    Inspired by OpenAI Codex's Smart Approvals guardian subagent
    (openai/codex#13860).
    """
    try:
        from agent.auxiliary_client import call_llm

        prompt = f"""You are a security reviewer for an AI coding agent. A terminal command was flagged by pattern matching as potentially dangerous.

Command: {command}
Flagged reason: {description}

Assess the ACTUAL risk of this command. Many flagged commands are false positives — for example, `python -c "print('hello')"` is flagged as "script execution via -c flag" but is completely harmless.

Rules:
- APPROVE if the command is clearly safe (benign script execution, safe file operations, development tools, package installs, git operations, etc.)
- DENY if the command could genuinely damage the system (recursive delete of important paths, overwriting system files, fork bombs, wiping disks, dropping databases, etc.)
- ESCALATE if you're uncertain

Respond with exactly one word: APPROVE, DENY, or ESCALATE"""

        response = call_llm(
            task="approval",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=16,
        )

        answer = (response.choices[0].message.content or "").strip().upper()

        if "APPROVE" in answer:
            return "approve"
        elif "DENY" in answer:
            return "deny"
        else:
            return "escalate"

    except Exception as e:
        logger.debug("Smart approvals: LLM call failed (%s), escalating", e)
        return "escalate"


def check_dangerous_command(command: str, env_type: str,
                            approval_callback=None) -> dict:
    """Check if a command is dangerous and handle approval.

    This is the main entry point called by terminal_tool before executing
    any command. It orchestrates detection, session checks, and prompting.

    Args:
        command: The shell command to check.
        env_type: Terminal backend type ('local', 'ssh', 'docker', etc.).
        approval_callback: Optional CLI callback for interactive prompts.

    Returns:
        {"approved": True/False, "message": str or None, ...}
    """
    if env_type in {"docker", "singularity", "modal", "daytona", "vercel_sandbox"}:
        return {"approved": True, "message": None}

    # Hardline floor: commands with no recovery path (rm -rf /, mkfs, dd
    # to raw device, shutdown/reboot, fork bomb, kill -1) are blocked
    # unconditionally, BEFORE the yolo bypass.  Opting into yolo is
    # trusting the agent with your files and services, not trusting it
    # to wipe the disk or power the box off.
    is_hardline, hardline_desc = detect_hardline_command(command)
    if is_hardline:
        logger.warning("Hardline block: %s (command: %s)", hardline_desc, command[:200])
        _log_approval_decision(
            "deny", "hardline", command=command, description=hardline_desc,
        )
        return _hardline_block_result(hardline_desc)

    # --yolo: bypass all approval prompts. Gateway /yolo is session-scoped;
    # CLI --yolo remains process-scoped via the env var for local use.
    if is_truthy_value(os.getenv("XAVANI_YOLO_MODE")) or is_current_session_yolo_enabled():
        _log_approval_decision("allow", "yolo", command=command)
        return {"approved": True, "message": None}

    is_dangerous, pattern_key, description = detect_dangerous_command(command)
    if not is_dangerous:
        return {"approved": True, "message": None}

    # D05 — dangerous command CHAIN (2+ dangerous commands joined by
    # &&, ;, |, ||). The command is already flagged by the single-command
    # detection above; surface the full chain in the approval description
    # so the user sees every dangerous stage, not just the first match.
    is_chain, _chain_hits, chain_description = detect_dangerous_chain(command)
    if is_chain:
        description = chain_description

    session_key = get_current_session_key()
    # D08: after N privileged (sudo) approvals, require re-verification —
    # a session must not run forever with unlimited privilege.
    try:
        from tools.privilege_recheck import check_privilege_recheck

        _recheck_due = bool(re.search(r"\bsudo\b", command)) and check_privilege_recheck(session_key)
    except Exception:
        _recheck_due = False
    # D03: a session risk budget bounds how many dangerous commands may
    # auto-pass via allowlist/session approval. Exhausted budget means
    # even approved patterns must ask again.
    try:
        from tools.risk_budget import risk_budget_for

        _budget = risk_budget_for(session_key)
        _budget_exhausted = _budget.exhausted()
    except Exception:
        _budget = None
        _budget_exhausted = False
    if is_approved(session_key, pattern_key) and not _budget_exhausted and not _recheck_due:
        _log_approval_decision(
            "allow", "allowlist", command=command, pattern_key=pattern_key,
            description=description, session_key=session_key,
        )
        # D08: an allowlist-approved sudo still accumulates toward the
        # privilege re-check (no explicit user verification happened).
        try:
            if re.search(r"\bsudo\b", command):
                from tools.privilege_recheck import mark_privileged_action

                mark_privileged_action(session_key)
        except Exception:
            pass
        return {"approved": True, "message": None}

    is_cli = env_var_enabled("XAVANI_INTERACTIVE")
    is_gateway = _is_gateway_approval_context()

    if not is_cli and not is_gateway:
        # Cron sessions: respect cron_mode config
        if env_var_enabled("XAVANI_CRON_SESSION"):
            if _get_cron_approval_mode() == "deny":
                _log_approval_decision(
                    "deny", "cron_mode", command=command,
                    pattern_key=pattern_key, description=description,
                )
                return {
                    "approved": False,
                    "message": (
                        f"BLOCKED: Command flagged as dangerous ({description}) "
                        "but cron jobs run without a user present to approve it. "
                        "Find an alternative approach that avoids this command. "
                        "To allow dangerous commands in cron jobs, set "
                        "approvals.cron_mode: approve in config.yaml."
                    ),
                }
        return {"approved": True, "message": None}

    if is_gateway or env_var_enabled("XAVANI_EXEC_ASK"):
        submit_pending(session_key, {
            "command": command,
            "pattern_key": pattern_key,
            "description": description,
        })
        return {
            "approved": False,
            "pattern_key": pattern_key,
            "status": "approval_required",
            "command": command,
            "description": description,
            "message": (
                f"⚠️ This command is potentially dangerous ({description}). "
                f"Asking the user for approval.\n\n**Command:**\n```\n{command}\n```"
            ),
        }

    choice = prompt_dangerous_approval(command, description,
                                       approval_callback=approval_callback)

    if choice == "deny":
        _log_approval_decision(
            "deny", "user", command=command, pattern_key=pattern_key,
            description=description, session_key=session_key,
        )
        return {
            "approved": False,
            "message": f"BLOCKED: User denied this potentially dangerous command (matched '{description}' pattern). Do NOT retry this command - the user has explicitly rejected it.",
            "pattern_key": pattern_key,
            "description": description,
        }

    if choice == "session":
        approve_session(session_key, pattern_key)
    elif choice == "always":
        approve_session(session_key, pattern_key)
        approve_permanent(pattern_key)
        save_permanent_allowlist(_permanent_approved)

    # D03: an approved dangerous command costs the session risk budget.
    if _budget is not None:
        try:
            from tools.risk_budget import TIER_COSTS

            _budget.spend(TIER_COSTS.get("high", 40.0))
        except Exception:
            pass

    # D08: a sudo command approval counts toward the privilege re-check.
    try:
        if re.search(r"\bsudo\b", command):
            from tools.privilege_recheck import (
                confirm_privilege_recheck,
                mark_privileged_action,
            )

            mark_privileged_action(session_key)
            confirm_privilege_recheck(session_key)  # user just verified
    except Exception:
        pass

    _log_approval_decision(
        "allow", "user", command=command, pattern_key=pattern_key,
        description=description, session_key=session_key,
        extra={"choice": choice or "once"},
    )
    return {"approved": True, "message": None}


# =========================================================================
# Combined pre-exec guard (tirith + dangerous command detection)
# =========================================================================

def _format_tirith_description(tirith_result: dict) -> str:
    """Build a human-readable description from tirith findings.

    Includes severity, title, and description for each finding so users
    can make an informed approval decision.
    """
    findings = tirith_result.get("findings") or []
    if not findings:
        summary = tirith_result.get("summary") or "security issue detected"
        return f"Security scan: {summary}"

    parts = []
    for f in findings:
        severity = f.get("severity", "")
        title = f.get("title", "")
        desc = f.get("description", "")
        if title and desc:
            parts.append(f"[{severity}] {title}: {desc}" if severity else f"{title}: {desc}")
        elif title:
            parts.append(f"[{severity}] {title}" if severity else title)
    if not parts:
        summary = tirith_result.get("summary") or "security issue detected"
        return f"Security scan: {summary}"

    return "Security scan — " + "; ".join(parts)


def check_all_command_guards(command: str, env_type: str,
                             approval_callback=None) -> dict:
    """Run all pre-exec security checks and return a single approval decision.

    Gathers findings from tirith and dangerous-command detection, then
    presents them as a single combined approval request. This prevents
    a gateway force=True replay from bypassing one check when only the
    other was shown to the user.
    """
    # Skip containers for both checks
    if env_type in {"docker", "singularity", "modal", "daytona", "vercel_sandbox"}:
        return {"approved": True, "message": None}

    # Hardline floor: unconditional block for catastrophic commands
    # (rm -rf /, mkfs, dd to raw device, shutdown/reboot, fork bomb,
    # kill -1). Applies BEFORE yolo / mode=off / cron approve-mode so
    # no session-level setting can bypass it.
    is_hardline, hardline_desc = detect_hardline_command(command)
    if is_hardline:
        logger.warning("Hardline block: %s (command: %s)", hardline_desc, command[:200])
        _log_approval_decision(
            "deny", "hardline", command=command, description=hardline_desc,
        )
        return _hardline_block_result(hardline_desc)

    # == Sudo stdin guard ==
    # Like the hardline floor above, this is unconditional: there is never a
    # legitimate reason for the agent to pipe passwords to sudo -S when no
    # SUDO_PASSWORD has been configured.  This must fire BEFORE the yolo
    # check so even yolo/smart approval/mode=off cannot bypass it.
    is_sudo_guess, sudo_guess_desc = _check_sudo_stdin_guard(command)
    if is_sudo_guess:
        logger.warning("Sudo stdin guard block: %s (command: %s)",
                       sudo_guess_desc, command[:200])
        _log_approval_decision(
            "deny", "sudo_stdin", command=command, description=sudo_guess_desc,
        )
        return _sudo_stdin_block_result(sudo_guess_desc)

    # --yolo or approvals.mode=off: bypass all approval prompts.
    # Gateway /yolo is session-scoped; CLI --yolo remains process-scoped.
    approval_mode = _get_approval_mode()
    if is_truthy_value(os.getenv("XAVANI_YOLO_MODE")) or is_current_session_yolo_enabled() or approval_mode == "off":
        _log_approval_decision(
            "allow", "yolo", command=command,
            extra={"approval_mode": approval_mode},
        )
        return {"approved": True, "message": None}

    is_cli = env_var_enabled("XAVANI_INTERACTIVE")
    is_gateway = _is_gateway_approval_context()
    is_ask = env_var_enabled("XAVANI_EXEC_ASK")

    # Preserve the existing non-interactive behavior: outside CLI/gateway/ask
    # flows, we do not block on approvals and we skip external guard work.
    if not is_cli and not is_gateway and not is_ask:
        # Cron sessions: respect cron_mode config
        if env_var_enabled("XAVANI_CRON_SESSION"):
            if _get_cron_approval_mode() == "deny":
                # Run detection to get a description for the block message
                is_dangerous, _pk, description = detect_dangerous_command(command)
                if is_dangerous:
                    _log_approval_decision(
                        "deny", "cron_mode", command=command,
                        pattern_key=_pk, description=description,
                    )
                    return {
                        "approved": False,
                        "message": (
                            f"BLOCKED: Command flagged as dangerous ({description}) "
                            "but cron jobs run without a user present to approve it. "
                            "Find an alternative approach that avoids this command. "
                            "To allow dangerous commands in cron jobs, set "
                            "approvals.cron_mode: approve in config.yaml."
                        ),
                    }
        return {"approved": True, "message": None}

    # --- Phase 1: Gather findings from both checks ---

    # Tirith check — wrapper guarantees no raise for expected failures.
    # Only catch ImportError (module not installed).
    tirith_result = {"action": "allow", "findings": [], "summary": ""}
    try:
        from tools.tirith_security import check_command_security
        tirith_result = check_command_security(command)
    except ImportError:
        pass  # tirith module not installed — allow

    # Dangerous command check (detection only, no approval)
    is_dangerous, pattern_key, description = detect_dangerous_command(command)

    # D05 — dangerous command CHAIN: 2+ dangerous commands joined by
    # &&, ;, |, ||. Surface the full chain in the combined description so
    # the user sees every dangerous stage of the command.
    is_chain, _chain_hits, chain_description = detect_dangerous_chain(command)
    if is_chain:
        description = chain_description

    # --- Phase 2: Decide ---

    # Collect warnings that need approval
    warnings = []  # list of (pattern_key, description, is_tirith)

    session_key = get_current_session_key()

    # Tirith block/warn → approvable warning with rich findings.
    # Previously, tirith "block" was a hard block with no approval prompt.
    # Now both block and warn go through the approval flow so users can
    # inspect the explanation and approve if they understand the risk.
    if tirith_result["action"] in {"block", "warn"}:
        findings = tirith_result.get("findings") or []
        rule_id = findings[0].get("rule_id", "unknown") if findings else "unknown"
        tirith_key = f"tirith:{rule_id}"
        tirith_desc = _format_tirith_description(tirith_result)
        if not is_approved(session_key, tirith_key):
            warnings.append((tirith_key, tirith_desc, True))

    if is_dangerous:
        if not is_approved(session_key, pattern_key):
            warnings.append((pattern_key, description, False))

    # Nothing to warn about
    if not warnings:
        return {"approved": True, "message": None}
    # --- Phase 2.5: Smart approval (auxiliary LLM risk assessment) ---
    # When approvals.mode=smart, ask the aux LLM before prompting the user.
    # Inspired by OpenAI Codex's Smart Approvals guardian subagent
    # (openai/codex#13860).
    if approval_mode == "smart":
        combined_desc_for_llm = "; ".join(desc for _, desc, _ in warnings)
        verdict = _smart_approve(command, combined_desc_for_llm)
        if verdict == "approve":
            # Auto-approve and grant session-level approval for these patterns
            for key, _, _ in warnings:
                approve_session(session_key, key)
            logger.debug("Smart approval: auto-approved '%s' (%s)",
                         command[:60], combined_desc_for_llm)
            _log_approval_decision(
                "allow", "smart", command=command, description=combined_desc_for_llm,
                session_key=session_key, extra={"verdict": "approve"},
            )
            return {"approved": True, "message": None,
                    "smart_approved": True,
                    "description": combined_desc_for_llm}
        elif verdict == "deny":
            combined_desc_for_llm = "; ".join(desc for _, desc, _ in warnings)
            _log_approval_decision(
                "deny", "smart", command=command, description=combined_desc_for_llm,
                session_key=session_key, extra={"verdict": "deny"},
            )
            return {
                "approved": False,
                "message": f"BLOCKED by smart approval: {combined_desc_for_llm}. "
                           "The command was assessed as genuinely dangerous. Do NOT retry.",
                "smart_denied": True,
            }
        # verdict == "escalate" → fall through to manual prompt

    # --- Phase 3: Approval ---

    # Combine descriptions for a single approval prompt
    combined_desc = "; ".join(desc for _, desc, _ in warnings)
    primary_key = warnings[0][0]
    all_keys = [key for key, _, _ in warnings]
    has_tirith = any(is_t for _, _, is_t in warnings)

    # Gateway/async approval — block the agent thread until the user
    # responds with /approve or /deny, mirroring the CLI's synchronous
    # input() flow.  The agent never sees "approval_required"; it either
    # gets the command output (approved) or a definitive "BLOCKED" message.
    if is_gateway or is_ask:
        notify_cb = None
        with _lock:
            notify_cb = _gateway_notify_cbs.get(session_key)

        if notify_cb is not None:
            # --- Blocking gateway approval (queue-based) ---
            # Each call gets its own _ApprovalEntry so parallel subagents
            # and execute_code threads can block concurrently.
            approval_data = {
                "command": command,
                "pattern_key": primary_key,
                "pattern_keys": all_keys,
                "description": combined_desc,
            }
            entry = _ApprovalEntry(approval_data)
            with _lock:
                _gateway_queues.setdefault(session_key, []).append(entry)

            # Notify plugins that an approval is being requested. Fires before
            # the gateway notify callback so observers (e.g. macOS notifier
            # plugins, audit logs, Slack alerts) get the event in real time.
            _fire_approval_hook(
                "pre_approval_request",
                command=command,
                description=combined_desc,
                pattern_key=primary_key,
                pattern_keys=list(all_keys),
                session_key=session_key,
                surface="gateway",
            )

            # Notify the user (bridges sync agent thread → async gateway)
            try:
                notify_cb(approval_data)
            except Exception as exc:
                logger.warning("Gateway approval notify failed: %s", exc)
                with _lock:
                    queue = _gateway_queues.get(session_key, [])
                    if entry in queue:
                        queue.remove(entry)
                    if not queue:
                        _gateway_queues.pop(session_key, None)
                return {
                    "approved": False,
                    "message": "BLOCKED: Failed to send approval request to user. Do NOT retry.",
                    "pattern_key": primary_key,
                    "description": combined_desc,
                }

            # Block until the user responds or timeout (default 5 min).
            # Poll in short slices so we can fire activity heartbeats every
            # ~10s to the agent's inactivity tracker.  Without this, the
            # blocking event.wait() never touches activity, and the
            # gateway's inactivity watchdog (agent.gateway_timeout, default
            # 1800s) kills the agent while the user is still responding to
            # the approval prompt.  Mirrors the _wait_for_process() cadence
            # in tools/environments/base.py.
            timeout = _get_approval_config().get("gateway_timeout", 300)
            try:
                timeout = int(timeout)
            except (ValueError, TypeError):
                timeout = 300

            try:
                from tools.environments.base import touch_activity_if_due
            except Exception:  # pragma: no cover
                touch_activity_if_due = None

            _now = time.monotonic()
            _deadline = _now + max(timeout, 0)
            _activity_state = {"last_touch": _now, "start": _now}
            resolved = False
            while True:
                _remaining = _deadline - time.monotonic()
                if _remaining <= 0:
                    break
                # 1s poll slice — the event is set immediately when the
                # user responds, so slice length only controls heartbeat
                # cadence, not user-visible responsiveness.
                if entry.event.wait(timeout=min(1.0, _remaining)):
                    resolved = True
                    break
                if touch_activity_if_due is not None:
                    touch_activity_if_due(
                        _activity_state, "waiting for user approval"
                    )

            # Clean up this entry from the queue
            with _lock:
                queue = _gateway_queues.get(session_key, [])
                if entry in queue:
                    queue.remove(entry)
                if not queue:
                    _gateway_queues.pop(session_key, None)

            choice = entry.result
            # Normalize outcome for the post hook. Unresolved (timeout) and
            # None both mean the user never responded; report that explicitly
            # so plugins can distinguish timeout from explicit deny.
            _outcome = (
                "timeout" if not resolved
                else (choice if choice else "timeout")
            )
            _fire_approval_hook(
                "post_approval_response",
                command=command,
                description=combined_desc,
                pattern_key=primary_key,
                pattern_keys=list(all_keys),
                session_key=session_key,
                surface="gateway",
                choice=_outcome,
            )

            if not resolved or choice is None or choice == "deny":
                reason = "timed out" if not resolved else "denied by user"
                _log_approval_decision(
                    "timeout" if not resolved else "deny",
                    "user", command=command, pattern_key=primary_key,
                    description=combined_desc, session_key=session_key,
                    extra={"surface": "gateway"},
                )
                return {
                    "approved": False,
                    "message": f"BLOCKED: Command {reason}. Do NOT retry this command.",
                    "pattern_key": primary_key,
                    "description": combined_desc,
                }

            # User approved — persist based on scope (same logic as CLI)
            for key, _, is_tirith in warnings:
                if choice == "session" or (choice == "always" and is_tirith):
                    approve_session(session_key, key)
                elif choice == "always":
                    approve_session(session_key, key)
                    approve_permanent(key)
                    save_permanent_allowlist(_permanent_approved)
                # choice == "once": no persistence — command allowed this
                # single time only, matching the CLI's behavior.

            _log_approval_decision(
                "allow", "user", command=command, pattern_key=primary_key,
                description=combined_desc, session_key=session_key,
                extra={"surface": "gateway", "choice": choice},
            )
            return {"approved": True, "message": None,
                    "user_approved": True, "description": combined_desc}

        # Fallback: no gateway callback registered (e.g. cron, batch).
        # Return approval_required for backward compat.
        submit_pending(session_key, {
            "command": command,
            "pattern_key": primary_key,
            "pattern_keys": all_keys,
            "description": combined_desc,
        })
        return {
            "approved": False,
            "pattern_key": primary_key,
            "status": "pending_approval",
            "approval_pending": True,
            "command": command,
            "description": combined_desc,
            "message": (
                f"⚠️ {combined_desc}. Asking the user for approval.\n\n**Command:**\n```\n{command}\n```"
            ),
        }

    # CLI interactive: single combined prompt
    # Hide [a]lways when any tirith warning is present
    _fire_approval_hook(
        "pre_approval_request",
        command=command,
        description=combined_desc,
        pattern_key=primary_key,
        pattern_keys=list(all_keys),
        session_key=session_key,
        surface="cli",
    )
    choice = prompt_dangerous_approval(command, combined_desc,
                                       allow_permanent=not has_tirith,
                                       approval_callback=approval_callback)
    _fire_approval_hook(
        "post_approval_response",
        command=command,
        description=combined_desc,
        pattern_key=primary_key,
        pattern_keys=list(all_keys),
        session_key=session_key,
        surface="cli",
        choice=choice,
    )

    # G04: when a risky command gets approved, attach the proactive
    # disclosure (risks + rollback) so the caller can surface it to the
    # user before execution. Advisory only — never blocks.
    try:
        from xavani_cli.proactive_disclosure import disclosure_for

        _disclosure = disclosure_for(command)
        if _disclosure:
            _log_approval_decision(
                "allow", "disclosure", command=command,
                description="; ".join(_disclosure["risks"]),
                session_key=session_key,
            )
    except Exception:
        _disclosure = None

    if choice == "deny":
        _log_approval_decision(
            "deny", "user", command=command, pattern_key=primary_key,
            description=combined_desc, session_key=session_key,
            extra={"surface": "cli"},
        )
        return {
            "approved": False,
            "message": "BLOCKED: User denied. Do NOT retry.",
            "pattern_key": primary_key,
            "description": combined_desc,
        }

    # Persist approval for each warning individually
    for key, _, is_tirith in warnings:
        if choice == "session" or (choice == "always" and is_tirith):
            # tirith: session only (no permanent broad allowlisting)
            approve_session(session_key, key)
        elif choice == "always":
            # dangerous patterns: permanent allowed
            approve_session(session_key, key)
            approve_permanent(key)
            save_permanent_allowlist(_permanent_approved)

    _log_approval_decision(
        "allow", "user", command=command, pattern_key=primary_key,
        description=combined_desc, session_key=session_key,
        extra={"surface": "cli", "choice": choice},
    )
    result = {"approved": True, "message": None,
              "user_approved": True, "description": combined_desc}
    # G04: surface the proactive disclosure on approved risky commands.
    if _disclosure:
        try:
            from xavani_cli.proactive_disclosure import format_disclosure
            result["disclosure"] = format_disclosure(_disclosure)
        except Exception:
            pass
    return result


# Load permanent allowlist from config on module import
load_permanent_allowlist()
