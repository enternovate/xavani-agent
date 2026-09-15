#!/usr/bin/env bash

# Set up an isolated evaluation home for the reliability task corpus (task 25).
# Usage: bash scripts/task_bench/eval_home/setup_eval_home.sh <home-dir>
#
# The script copies the active Xavani config and credentials into the target
# home and installs the bench-capture plugin. It never prints secret values.

set -euo pipefail

HOME_DIR="${1:?usage: setup_eval_home.sh <home-dir>}"
SOURCE_HOME="${XAVANI_SOURCE_HOME:-$HOME/.xavani}"
RIG_DIR="$(cd "$(dirname "$0")" && pwd)"

mkdir -p "$HOME_DIR/plugins/bench-capture"
cp "$SOURCE_HOME/config.yaml" "$HOME_DIR/config.yaml"
if [ -f "$SOURCE_HOME/auth.json" ]; then
  cp "$SOURCE_HOME/auth.json" "$HOME_DIR/auth.json"
fi
cp "$RIG_DIR/bench-capture/plugin.yaml" "$HOME_DIR/plugins/bench-capture/plugin.yaml"
cp "$RIG_DIR/bench-capture/__init__.py" "$HOME_DIR/plugins/bench-capture/__init__.py"

python3 - "$HOME_DIR/config.yaml" <<'PY'
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
if "bench-capture" not in text:
    text += "\nplugins:\n  enabled:\n    - bench-capture\n"
    path.write_text(text, encoding="utf-8")
PY

echo "evaluation home ready: $HOME_DIR"
