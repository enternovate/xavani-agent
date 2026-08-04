#!/usr/bin/env bash
# Xavani Agent — Installer (delegates to scripts/install.sh)
# Usage: curl -fsSL https://raw.githubusercontent.com/enternovate/xavani-agent/main/install.sh | bash
#
# The full installer lives at scripts/install.sh (uv, Python 3.11+, Node.js
# for browser tools, Termux support, branch pins, skip flags). This root
# wrapper exists so the documented one-liner stays short; it downloads and
# executes the canonical installer from the same commit/tag.
set -e

BOLD='\033[1m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
GREEN='\033[0;32m'
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

# ── Resolve the canonical installer from the same branch/tag ────────

BRANCH="main"
EXTRA_ARGS=()

while [ $# -gt 0 ]; do
  case "$1" in
    --branch)
      BRANCH="$2"
      shift 2
      ;;
    --tag)
      BRANCH="$2"
      shift 2
      ;;
    *)
      EXTRA_ARGS+=("$1")
      shift
      ;;
  esac
done

INSTALLER_URL="https://raw.githubusercontent.com/enternovate/xavani-agent/${BRANCH}/scripts/install.sh"
INSTALLER_TMP="$(mktemp 2>/dev/null || echo "/tmp/xavani-installer.$$.sh")"

echo -e "  ${CYAN}→${NC} Fetching canonical installer (${BRANCH})..."

if ! curl -fsSL "$INSTALLER_URL" -o "$INSTALLER_TMP" 2>/dev/null; then
  echo -e "  ${RED}✗${NC} Could not download installer from $INSTALLER_URL"
  rm -f "$INSTALLER_TMP"
  exit 1
fi

chmod +x "$INSTALLER_TMP"
echo -e "  ${GREEN}✓${NC} Installer ready — executing..."

if [ ${#EXTRA_ARGS[@]} -gt 0 ]; then
  bash "$INSTALLER_TMP" "${EXTRA_ARGS[@]}"
else
  bash "$INSTALLER_TMP"
fi

RC=$?
rm -f "$INSTALLER_TMP"
exit $RC
