#!/bin/bash
# Xavani → Xavani comprehensive rename script
# Run from repo root. Handles files, directories, and content.
# 
# IMPORTANT: This script handles the RENAME in phases:
# Phase 1: Content replacements (sed) on all files BEFORE renaming files
# Phase 2: File/directory renames (git mv)
# Phase 3: Cleanup

set -e
cd "$(git rev-parse --show-toplevel)"

echo "=== Phase 0: Stash any uncommitted changes ==="
git stash -u -m "Pre-rename stash" 2>/dev/null || true
git stash pop 2>/dev/null || true

echo "=== Phase 1: Content replacements ==="

# 1a. Python imports: xavani_cli → xavani_cli
# 1b. Python imports: xavani_state → xavani_state  
# 1c. Python imports: xavani_logging → xavani_logging
# 1d. Python imports: xavani_constants → xavani_constants
# 1e. Python imports: xavani_bootstrap → xavani_bootstrap
# 1f. Python imports: xavani_time → xavani_time
# 1g. Python imports: xavani_tools_mcp_server → xavani_tools_mcp_server

# Find all text files (exclude .git, node_modules, __pycache__, binary)
EXCLUDE="-not -path './.git/*' -not -path '*/node_modules/*' -not -path '*/__pycache__/*' -not -path '*/.next/*' -not -path '*/dist/*' -not -path '*/build/*' -not -path '*.pyc' -not -path '*.pyo' -not -path '*.so' -not -path '*.png' -not -path '*.jpg' -not -path '*.jpeg' -not -path '*.gif' -not -path '*.ico' -not -path '*.woff*' -not -path '*.ttf' -not -path '*.eot' -not -path '*.pdf' -not -path '*.woff' -not -name '*.lock' -not -name 'package-lock.json' -not -name 'yarn.lock' -not -name 'pnpm-lock.yaml'"

# Helper: sed in-place with both GNU and BSD compatibility
do_replace() {
    local pattern="$1"
    local replacement="$2"
    local desc="$3"
    echo "  Replacing: $desc"
    find . $EXCLUDE -type f \( -name '*.py' -o -name '*.md' -o -name '*.yml' -o -name '*.yaml' -o -name '*.json' -o -name '*.toml' -o -name '*.cfg' -o -name '*.ini' -o -name '*.sh' -o -name '*.bash' -o -name '*.txt' -o -name '*.tsx' -o -name '*.ts' -o -name '*.js' -o -name '*.jsx' -o -name '*.html' -o -name '*.css' -o -name '*.scss' -o -name '*.rb' -o -name '*.nix' -o -name '*.service' -o -name '*.rst' -o -name '*.mjs' -o -name '*.d.ts' \) -exec sed -i '' "s/${pattern}/${replacement}/g" {} + 2>/dev/null || \
    find . $EXCLUDE -type f \( -name '*.py' -o -name '*.md' -o -name '*.yml' -o -name '*.yaml' -o -name '*.json' -o -name '*.toml' -o -name '*.cfg' -o -name '*.ini' -o -name '*.sh' -o -name '*.bash' -o -name '*.txt' -o -name '*.tsx' -o -name '*.ts' -o -name '*.js' -o -name '*.jsx' -o -name '*.html' -o -name '*.css' -o -name '*.scss' -o -name '*.rb' -o -name '*.nix' -o -name '*.service' -o -name '*.rst' -o -name '*.mjs' -o -name '*.d.ts' \) -exec sed -i "s/${pattern}/${replacement}/g" {} + 2>/dev/null || true
}

# ---- Specific replacements (order matters: longest/most-specific first) ----

# Python module references (import paths) - MUST come before generic replacements
do_replace "from xavani_state import" "from xavani_state import" "import: xavani_state → xavani_state"
do_replace "import xavani_state" "import xavani_state" "import: xavani_state → xavani_state"
do_replace "from xavani_logging import" "from xavani_logging import" "import: xavani_logging → xavani_logging"
do_replace "import xavani_logging" "import xavani_logging" "import: xavani_logging → xavani_logging"
do_replace "from xavani_constants import" "from xavani_constants import" "import: xavani_constants → xavani_constants"
do_replace "import xavani_constants" "import xavani_constants" "import: xavani_constants → xavani_constants"
do_replace "from xavani_bootstrap import" "from xavani_bootstrap import" "import: xavani_bootstrap → xavani_bootstrap"
do_replace "import xavani_bootstrap" "import xavani_bootstrap" "import: xavani_bootstrap → xavani_bootstrap"
do_replace "from xavani_time import" "from xavani_time import" "import: xavani_time → xavani_time"
do_replace "import xavani_time" "import xavani_time" "import: xavani_time → xavani_time"
do_replace "from xavani_cli" "from xavani_cli" "import: xavani_cli → xavani_cli"
do_replace "import xavani_cli" "import xavani_cli" "import: xavani_cli → xavani_cli"
do_replace "xavani_tools_mcp_server" "xavani_tools_mcp_server" "module: xavani_tools_mcp_server → xavani_tools_mcp_server"

# CLI command references
do_replace "xavani profile" "xavani profile" "cli: xavani profile → xavani profile"
do_replace "xavani config" "xavani config" "cli: xavani config → xavani config"
do_replace "xavani setup" "xavani setup" "cli: xavani setup → xavani setup"
do_replace "xavani doctor" "xavani doctor" "cli: xavani doctor → xavani doctor"
do_replace "xavani run" "xavani run" "cli: xavani run → xavani run"
do_replace "xavani models" "xavani models" "cli: xavani models → xavani models"
do_replace "xavani skills" "xavani skills" "cli: xavani skills → xavani skills"
do_replace "xavani dump" "xavani dump" "cli: xavani dump → xavani dump"
do_replace "xavani status" "xavani status" "cli: xavani status → xavani status"
do_replace "xavani gateway" "xavani gateway" "cli: xavani gateway → xavani gateway"

# Environment variables - specific patterns first
do_replace "XAVANI_REDACT_SECRETS" "XAVANI_REDACT_SECRETS" "env: XAVANI_REDACT_SECRETS → XAVANI_REDACT_SECRETS"
do_replace "XAVANI_HOME" "XAVANI_HOME" "env: XAVANI_HOME → XAVANI_HOME"

# Now the generic XAVANI_ env var prefix
do_replace "XAVANI_" "XAVANI_" "env: XAVANI_ → XAVANI_ (generic)"

# Home directory references - be careful with .xavani path
do_replace "/.xavani" "/.xavani" "path: /.xavani → /.xavani"
do_replace "~/.xavani" "~/.xavani" "path: ~/.xavani → ~/.xavani"
do_replace ".xavani/logs" ".xavani/logs" "path: .xavani/logs → .xavani/logs"
do_replace ".xavani/config" ".xavani/config" "path: .xavani/config → .xavani/config"
do_replace ".xavani/.env" ".xavani/.env" "path: .xavani/.env → .xavani/.env"
do_replace ".xavani/sessions" ".xavani/sessions" "path: .xavani/sessions → .xavani/sessions"
do_replace ".xavani/profiles" ".xavani/profiles" "path: .xavani/profiles → .xavani/profiles"
do_replace '"xavani"' '"xavani"' 'string: "xavani" → "xavani"'
do_replace "'xavani'" "'xavani'" "string: 'xavani' → 'xavani'"

# Binary/executable names
do_replace "xavani-agent" "xavani-agent" "binary: xavani-agent → xavani-agent"
do_replace "xavani_agent" "xavani_agent" "underscore: xavani_agent → xavani_agent"

# Logo/brand references
do_replace "Xavani Agent" "Xavani Agent" "brand: Xavani Agent → Xavani Agent"

# Documentation references (case-sensitive)
do_replace "Xavani Agent" "Xavani Agent" "title: Xavani Agent → Xavani Agent"

# Package names in setup.py/pyproject.toml
do_replace "xavani-agent" "xavani-agent" "pkg: xavani-agent → xavani-agent"

echo ""
echo "=== Phase 1 Complete: Content replacements done ==="
echo ""
echo "=== Phase 2: File and directory renames ==="

# Rename files (most important ones first)
git mv xavani_bootstrap.py xavani_bootstrap.py 2>/dev/null || echo "  xavani_bootstrap.py already renamed or missing"
git mv xavani_constants.py xavani_constants.py 2>/dev/null || echo "  xavani_constants.py already renamed or missing"
git mv xavani_logging.py xavani_logging.py 2>/dev/null || echo "  xavani_logging.py already renamed or missing"
git mv xavani_state.py xavani_state.py 2>/dev/null || echo "  xavani_state.py already renamed or missing"
git mv xavani_time.py xavani_time.py 2>/dev/null || echo "  xavani_time.py already renamed or missing"
git mv xavani xavani 2>/dev/null || echo "  xavani binary already renamed or missing"

# Rename directories
git mv xavani_cli xavani_cli 2>/dev/null || echo "  xavani_cli/ already renamed or missing"
git mv tests/xavani_cli tests/xavani_cli 2>/dev/null || echo "  tests/xavani_cli/ already renamed or missing"
git mv tests/xavani_state tests/xavani_state 2>/dev/null || echo "  tests/xavani_state/ already renamed or missing"
git mv agent/transports/xavani_tools_mcp_server.py agent/transports/xavani_tools_mcp_server.py 2>/dev/null || echo "  xavani_tools_mcp_server.py already renamed"
git mv tests/agent/transports/test_xavani_tools_mcp_server.py tests/agent/transports/test_xavani_tools_mcp_server.py 2>/dev/null || echo "  test already renamed"

# Rename test files
git mv tests/test_xavani_bootstrap.py tests/test_xavani_bootstrap.py 2>/dev/null || echo "  test_xavani_bootstrap.py already renamed"
git mv tests/test_xavani_constants.py tests/test_xavani_constants.py 2>/dev/null || echo "  test_xavani_constants.py already renamed"
git mv tests/test_xavani_home_profile_warning.py tests/test_xavani_home_profile_warning.py 2>/dev/null || echo "  test_xavani_home_profile_warning.py already renamed"
git mv tests/test_xavani_logging.py tests/test_xavani_logging.py 2>/dev/null || echo "  test_xavani_logging.py already renamed"
git mv tests/test_xavani_state.py tests/test_xavani_state.py 2>/dev/null || echo "  test_xavani_state.py already renamed"
git mv tests/test_xavani_state_wal_fallback.py tests/test_xavani_state_wal_fallback.py 2>/dev/null || echo "  test already renamed"
git mv tests/xavani_cli/test_setup_xavani_script.py tests/xavani_cli/test_setup_xavani_script.py 2>/dev/null || echo "  test_setup already renamed"
git mv tests/xavani_cli/test_nous_xavani_non_agentic.py tests/xavani_cli/test_nous_xavani_non_agentic.py 2>/dev/null || echo "  test_nous already renamed"

# Skill directories
git mv oag_skills/autonomous-ai-agents/xavani-agent oag_skills/autonomous-ai-agents/xavani-agent 2>/dev/null || echo "  oag xavani-agent skill dir already renamed"
git mv skills/autonomous-ai-agents/xavani-agent skills/autonomous-ai-agents/xavani-agent 2>/dev/null || echo "  skills xavani-agent dir already renamed"
git mv oag_skills/software-development/debugging-xavani-tui-commands oag_skills/software-development/debugging-xavani-tui-commands 2>/dev/null || echo "  oag debugging dir already renamed"
git mv skills/software-development/debugging-xavani-tui-commands skills/software-development/debugging-xavani-tui-commands 2>/dev/null || echo "  skills debugging dir already renamed"
git mv oag_skills/software-development/xavani-agent-skill-authoring oag_skills/software-development/xavani-agent-skill-authoring 2>/dev/null || echo "  oag authoring dir already renamed"
git mv skills/software-development/xavani-agent-skill-authoring skills/software-development/xavani-agent-skill-authoring 2>/dev/null || echo "  skills authoring dir already renamed"
git mv plugins/xavani-achievements plugins/xavani-achievements 2>/dev/null || echo "  plugins xavani-achievements already renamed"
git mv .github/actions/xavani-smoke-test .github/actions/xavani-smoke-test 2>/dev/null || echo "  github action dir already renamed"

# Scripts
git mv scripts/xavani-gateway scripts/xavani-gateway 2>/dev/null || echo "  xavani-gateway script already renamed"
git mv setup-xavani.sh setup-xavani.sh 2>/dev/null || echo "  setup-xavani.sh already renamed"
git mv packaging/homebrew/xavani-agent.rb packaging/homebrew/xavani-agent.rb 2>/dev/null || echo "  homebrew formula already renamed"
git mv plugins/kanban/systemd/xavani-kanban-dispatcher.service plugins/kanban/systemd/xavani-kanban-dispatcher.service 2>/dev/null || echo "  systemd service already renamed"
git mv nix/xavani-agent.nix nix/xavani-agent.nix 2>/dev/null || echo "  nix package already renamed"

# UI/TUI
git mv ui-tui/packages/xavani-ink ui-tui/packages/xavani-ink 2>/dev/null || echo "  xavani-ink package already renamed"
git mv ui-tui/src/types/xavani-ink.d.ts ui-tui/src/types/xavani-ink.d.ts 2>/dev/null || echo "  xavani-ink types already renamed"

# Website docs
git mv website/docs/guides/build-a-xavani-plugin.md website/docs/guides/build-a-xavani-plugin.md 2>/dev/null || echo "  build plugin doc already renamed"
git mv website/docs/guides/use-mcp-with-xavani.md website/docs/guides/use-mcp-with-xavani.md 2>/dev/null || echo "  mcp doc already renamed"
git mv website/docs/guides/use-soul-with-xavani.md website/docs/guides/use-soul-with-xavani.md 2>/dev/null || echo "  soul doc already renamed"
git mv website/docs/guides/use-voice-mode-with-xavani.md website/docs/guides/use-voice-mode-with-xavani.md 2>/dev/null || echo "  voice doc already renamed"
git mv website/static/img/xavani-agent-banner.png website/static/img/xavani-agent-banner.png 2>/dev/null || echo "  banner img already renamed"

# Migration scripts
git mv oag_skills/migration/openclaw-migration/scripts/openclaw_to_xavani.py oag_skills/migration/openclaw-migration/scripts/openclaw_to_xavani.py 2>/dev/null || echo "  openclaw migration already renamed"
git mv optional-skills/migration/openclaw-migration/scripts/openclaw_to_xavani.py optional-skills/migration/openclaw-migration/scripts/openclaw_to_xavani.py 2>/dev/null || echo "  openclaw migration (optional) already renamed"

# Skill scripts with xavani in name
git mv skills/productivity/google-workspace/scripts/_xavani_home.py skills/productivity/google-workspace/scripts/_xavani_home.py 2>/dev/null || echo "  _xavani_home.py already renamed"
git mv oag_skills/productivity/google-workspace/scripts/_xavani_home.py oag_skills/productivity/google-workspace/scripts/_xavani_home.py 2>/dev/null || echo "  oag _xavani_home.py already renamed"

echo ""
echo "=== Phase 2 Complete: File and directory renames done ==="

echo "=== Phase 3: Cleanup ==="

# Remove all RELEASE_*.md files except the initial one (v0.2.0 is the oldest/initial)
for f in RELEASE_v0.3.0.md RELEASE_v0.4.0.md RELEASE_v0.5.0.md RELEASE_v0.6.0.md RELEASE_v0.7.0.md RELEASE_v0.8.0.md RELEASE_v0.9.0.md RELEASE_v0.10.0.md RELEASE_v0.11.0.md RELEASE_v0.12.0.md RELEASE_v0.13.0.md RELEASE_v0.14.0.md; do
    git rm "$f" 2>/dev/null || echo "  $f already removed or missing"
done

# Remove the migrate_from_xavani script (no longer needed after rename)
git rm scripts/migrate_from_xavani.py 2>/dev/null || echo "  migrate_from_xavani.py already removed"

# Remove xavani-already-has-routines.md (stale doc)
git rm xavani-already-has-routines.md 2>/dev/null || echo "  xavani-already-has-routines.md already removed"

# Remove docs/xavani-kanban-v1-spec.pdf  
git rm docs/xavani-kanban-v1-spec.pdf 2>/dev/null || echo "  kanban spec pdf already removed"

echo ""
echo "=== Rename complete! ==="
echo "Run 'git diff --stat' to see all changes."
echo "Then run 'find . -name '*xavani*' -not -path './.git/*'' to check for remaining references."