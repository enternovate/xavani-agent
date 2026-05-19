#!/usr/bin/env bash
# Xavani Agent — Installer
# Built by Enternovate. Open source.
set -e

BOLD='\033[1m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
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

# Detect OS
OS="$(uname -s)"
INSTALL_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/xavani"

case "$OS" in
  Linux*|Darwin*)
    echo "  OS: $OS — ✓ supported"
    ;;
  *)
    echo "  OS: $OS — trying POSIX compatibility"
    ;;
esac

# Check Python
if command -v python3 &>/dev/null; then
    PYTHON="python3"
elif command -v python &>/dev/null; then
    PYTHON="python"
else
    echo "ERROR: Python 3.11+ is required. Install it from https://python.org"
    exit 1
fi

PYVER=$($PYTHON --version 2>&1 | grep -oP '\d+\.\d+')
echo "  Python: $PYTHON $PYVER"

if [ "$(echo "$PYVER < 3.11" | bc -l 2>/dev/null || true)" = "1" ]; then
    echo "  WARNING: Python 3.11+ recommended. You have $PYVER"
fi

# Check git
if ! command -v git &>/dev/null; then
    echo "ERROR: git is required. Install it from https://git-scm.com"
    exit 1
fi

# Clone or update
REPO_DIR="$INSTALL_DIR/repo"
if [ -d "$REPO_DIR/.git" ]; then
    echo "  Updating existing installation..."
    cd "$REPO_DIR"
    git pull --ff-only 2>/dev/null || true
else
    echo "  Cloning Xavani Agent..."
    mkdir -p "$INSTALL_DIR"
    git clone --depth 1 https://github.com/enternovate/xavani-agent.git "$REPO_DIR"
    cd "$REPO_DIR"
fi

# Install
echo "  Installing Python package..."
$PYTHON -m pip install -e "$REPO_DIR" 2>/dev/null || {
    echo "  Trying uv..."
    if command -v uv &>/dev/null; then
        uv pip install -e "$REPO_DIR"
    else
        $PYTHON -m pip install -e "$REPO_DIR" --user
    fi
}

# Create wrapper script
WRAPPER_DIR="$HOME/.local/bin"
mkdir -p "$WRAPPER_DIR"
cat > "$WRAPPER_DIR/xavani" << 'WRAPPER'
#!/usr/bin/env bash
exec python3 -m xavani "$@"
WRAPPER
chmod +x "$WRAPPER_DIR/xavani"

# Create Xavani home
mkdir -p "$HOME/.xavani"/{logs,skills,policies,installed,data}
touch "$HOME/.xavani/.env"

echo ""
echo -e "${BLUE}${BOLD}Installation complete!${NC}"
echo ""
echo "  Run:  xavani"
echo "  Or:   $PYTHON -m xavani"
echo ""
echo "  Config:  $HOME/.xavani/"
echo "  Logs:    $HOME/.xavani/logs/"
echo ""
echo "  Set your API keys in: $HOME/.xavani/.env"
echo ""
echo "  Quick test:  xavani --message 'Hello, who are you?'"
echo ""
echo -e "${CYAN}Buffalo out. ⚡${NC}"
