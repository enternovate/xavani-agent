#!/usr/bin/env bash
# Xavani Agent — Installer
# Usage: curl -fsSL https://raw.githubusercontent.com/enternovate/xavani-agent/main/install.sh | bash
set -e

BOLD='\033[1m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}${BOLD}"
cat << "LOGO"
                          ╔══════════════════════════════╗
                          ║   XAVANI AGENT              ║
                          ║   by Enternovate             ║
                          ╚══════════════════════════════╝
LOGO
echo -e "${NC}"

echo -e "${CYAN}Installing Xavani Agent — the open-source AI agent gateway...${NC}"
echo ""

# ── Detect OS ──────────────────────────────────────────────────────

OS="$(uname -s)"
case "$OS" in
  Linux*|Darwin*)
    echo -e "  ${GREEN}✓${NC} OS: $OS"
    ;;
  *)
    echo -e "  ${YELLOW}⚠${NC} OS: $OS — attempting POSIX compatibility"
    ;;
esac

# ── Paths ──────────────────────────────────────────────────────────

XAVANI_HOME="${XAVANI_HOME:-$HOME/.xavani}"
REPO_DIR="$XAVANI_HOME/xavani-agent"
VENV_DIR="$REPO_DIR/venv"

# ── Install uv ─────────────────────────────────────────────────────

UV_CMD=""
if command -v uv &> /dev/null; then
    UV_CMD="uv"
elif [ -x "$HOME/.local/bin/uv" ]; then
    UV_CMD="$HOME/.local/bin/uv"
elif [ -x "$HOME/.cargo/bin/uv" ]; then
    UV_CMD="$HOME/.cargo/bin/uv"
fi

if [ -n "$UV_CMD" ]; then
    UV_VERSION=$($UV_CMD --version 2>/dev/null)
    echo -e "  ${GREEN}✓${NC} uv found ($UV_VERSION)"
else
    echo -e "  ${CYAN}→${NC} Installing uv..."
    _uv_installer="$(mktemp 2>/dev/null || echo "/tmp/xavani-uv-installer.$$.sh")"
    if curl -LsSf https://astral.sh/uv/install.sh -o "$_uv_installer" 2>/dev/null; then
        sh "$_uv_installer" 2>/dev/null
        rm -f "$_uv_installer"
        if [ -x "$HOME/.local/bin/uv" ]; then
            UV_CMD="$HOME/.local/bin/uv"
        elif [ -x "$HOME/.cargo/bin/uv" ]; then
            UV_CMD="$HOME/.cargo/bin/uv"
        fi
    fi
    if [ -z "$UV_CMD" ]; then
        echo -e "  ${RED}✗${NC} Could not install uv. Install manually: https://docs.astral.sh/uv/"
        exit 1
    fi
    echo -e "  ${GREEN}✓${NC} uv installed"
fi

# ── Check / install Python 3.11+ ──────────────────────────────────

echo -e "  ${CYAN}→${NC} Checking Python 3.11+..."

PYTHON_VERSION="3.11"
if $UV_CMD python find "$PYTHON_VERSION" &> /dev/null; then
    PYTHON_PATH=$($UV_CMD python find "$PYTHON_VERSION")
    PYTHON_FOUND_VERSION=$($PYTHON_PATH --version 2>/dev/null)
    echo -e "  ${GREEN}✓${NC} $PYTHON_FOUND_VERSION found"
else
    echo -e "  ${CYAN}→${NC} Installing Python $PYTHON_VERSION via uv..."
    $UV_CMD python install "$PYTHON_VERSION"
    PYTHON_PATH=$($UV_CMD python find "$PYTHON_VERSION")
    PYTHON_FOUND_VERSION=$($PYTHON_PATH --version 2>/dev/null)
    echo -e "  ${GREEN}✓${NC} $PYTHON_FOUND_VERSION installed"
fi

# ── Check git ──────────────────────────────────────────────────────

if ! command -v git &>/dev/null; then
    echo -e "  ${RED}✗${NC} git is required. Install it from https://git-scm.com"
    exit 1
fi

# ── Clone or update ────────────────────────────────────────────────

if [ -d "$REPO_DIR/.git" ]; then
    echo -e "  ${CYAN}→${NC} Updating existing installation..."
    cd "$REPO_DIR"
    git pull --ff-only 2>/dev/null || git pull 2>/dev/null || true
else
    echo -e "  ${CYAN}→${NC} Cloning Xavani Agent..."
    mkdir -p "$XAVANI_HOME"
    git clone --depth 1 https://github.com/enternovate/xavani-agent.git "$REPO_DIR"
    cd "$REPO_DIR"
fi

# ── Virtual environment ────────────────────────────────────────────

echo -e "  ${CYAN}→${NC} Setting up virtual environment..."

if [ -d "$VENV_DIR" ]; then
    rm -rf "$VENV_DIR"
fi

$UV_CMD venv "$VENV_DIR" --python "$PYTHON_VERSION"
echo -e "  ${GREEN}✓${NC} venv created"

# ── Install dependencies ──────────────────────────────────────────

echo -e "  ${CYAN}→${NC} Installing dependencies (this may take a minute)..."

if [ -f "uv.lock" ]; then
    if UV_PROJECT_ENVIRONMENT="$VENV_DIR" $UV_CMD sync --extra all --locked 2>/dev/null; then
        echo -e "  ${GREEN}✓${NC} Dependencies installed (hash-verified)"
    else
        $UV_CMD pip install --python "$VENV_DIR/bin/python" -e ".[all]" 2>/dev/null || \
        $UV_CMD pip install --python "$VENV_DIR/bin/python" -e "." 2>/dev/null || \
        $VENV_DIR/bin/python -m pip install -e "."
        echo -e "  ${GREEN}✓${NC} Dependencies installed"
    fi
else
    $UV_CMD pip install --python "$VENV_DIR/bin/python" -e ".[all]" 2>/dev/null || \
    $UV_CMD pip install --python "$VENV_DIR/bin/python" -e "." 2>/dev/null || \
    $VENV_DIR/bin/python -m pip install -e "."
    echo -e "  ${GREEN}✓${NC} Dependencies installed"
fi

# ── Create wrapper script ─────────────────────────────────────────

echo -e "  ${CYAN}→${NC} Setting up xavani command..."

WRAPPER_DIR="$HOME/.local/bin"
mkdir -p "$WRAPPER_DIR"

# Use the venv's installed entry point (same pattern as hermes)
XAVANI_BIN="$VENV_DIR/bin/xavani"
if [ -x "$XAVANI_BIN" ]; then
    ln -sf "$XAVANI_BIN" "$WRAPPER_DIR/xavani"
else
    # Fallback: create a wrapper that uses venv python
    cat > "$WRAPPER_DIR/xavani" << WRAPPER
#!/usr/bin/env bash
exec $VENV_DIR/bin/python -c "from xavani import main; main()" -- "\$@"
WRAPPER
    chmod +x "$WRAPPER_DIR/xavani"
fi

# Also create xavani-agent symlink
ln -sf "$WRAPPER_DIR/xavani" "$WRAPPER_DIR/xavani-agent" 2>/dev/null || true

echo -e "  ${GREEN}✓${NC} Linked xavani → $WRAPPER_DIR/xavani"

# ── PATH setup ─────────────────────────────────────────────────────

SHELL_CONFIG=""
if [ -n "${ZSH_VERSION:-}" ] || [[ "$SHELL" == *"zsh"* ]]; then
    SHELL_CONFIG="$HOME/.zshrc"
elif [ -n "${BASH_VERSION:-}" ] || [[ "$SHELL" == *"bash"* ]]; then
    SHELL_CONFIG="$HOME/.bashrc"
    [ ! -f "$SHELL_CONFIG" ] && SHELL_CONFIG="$HOME/.bash_profile"
else
    if [ -f "$HOME/.zshrc" ]; then
        SHELL_CONFIG="$HOME/.zshrc"
    elif [ -f "$HOME/.bashrc" ]; then
        SHELL_CONFIG="$HOME/.bashrc"
    elif [ -f "$HOME/.bash_profile" ]; then
        SHELL_CONFIG="$HOME/.bash_profile"
    fi
fi

if [ -n "$SHELL_CONFIG" ]; then
    touch "$SHELL_CONFIG" 2>/dev/null || true
    if ! echo "$PATH" | tr ':' '\n' | grep -q "^$HOME/.local/bin$"; then
        if ! grep -q '\.local/bin' "$SHELL_CONFIG" 2>/dev/null; then
            echo "" >> "$SHELL_CONFIG"
            echo "# Xavani Agent — ensure ~/.local/bin is on PATH" >> "$SHELL_CONFIG"
            echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$SHELL_CONFIG"
            echo -e "  ${GREEN}✓${NC} Added ~/.local/bin to PATH in $SHELL_CONFIG"
        else
            echo -e "  ${GREEN}✓${NC} ~/.local/bin already in $SHELL_CONFIG"
        fi
    else
        echo -e "  ${GREEN}✓${NC} ~/.local/bin already on PATH"
    fi
fi

# ── Create Xavani home directories ─────────────────────────────────

mkdir -p "$XAVANI_HOME"/{logs,skills,policies,installed,data,sessions}
touch "$XAVANI_HOME/.env" 2>/dev/null || true
chmod 600 "$XAVANI_HOME/.env" 2>/dev/null || true

# ── Sync bundled skills ───────────────────────────────────────────

echo -e "  ${CYAN}→${NC} Syncing bundled skills..."
XAVANI_SKILLS_DIR="$XAVANI_HOME/skills"
mkdir -p "$XAVANI_SKILLS_DIR"
if "$VENV_DIR/bin/python" "$REPO_DIR/tools/skills_sync.py" 2>/dev/null; then
    echo -e "  ${GREEN}✓${NC} Skills synced"
else
    if [ -d "$REPO_DIR/skills" ]; then
        cp -rn "$REPO_DIR/skills/"* "$XAVANI_SKILLS_DIR/" 2>/dev/null || true
        echo -e "  ${GREEN}✓${NC} Skills copied"
    fi
fi

# ── Done ───────────────────────────────────────────────────────────

echo ""
echo -e "${BLUE}${BOLD}Installation complete!${NC}"
echo ""
echo "  Commands:"
echo "    xavani              Start interactive mode"
echo "    xavani setup        Run setup wizard"
echo "    xavani --message 'Hello'  Single query mode"
echo "    xavani --version    Show version"
echo ""
echo "  Locations:"
echo "    Config:   $XAVANI_HOME/"
echo "    Repo:     $REPO_DIR/"
echo "    Logs:     $XAVANI_HOME/logs/"
echo "    Skills:   $XAVANI_HOME/skills/"
echo ""

if [ -n "$SHELL_CONFIG" ]; then
    echo "  Run: source $SHELL_CONFIG"
    echo "  Then: xavani setup"
fi

echo ""
echo -e "${CYAN}Buffalo out. ⚡${NC}"
