#!/usr/bin/env bash
# One-shot install: dedicated venv + symlinks so `taskbot` / `taskbot-gui` work
# without touching Homebrew's Python (PEP 668). Tested on macOS and Linux.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_URL="${TASKBOT_REPO:-https://github.com/aliasgar4558/task-tracking-bot.git}"
DEST="${TASKBOT_HOME:-${XDG_DATA_HOME:-$HOME/.local/share}/taskbot}"
VENV="$DEST/venv"
BIN="${TASKBOT_BIN:-$HOME/.local/bin}"

usage() {
  echo "Usage: $0 [--local]"
  echo "  --local    Install editable from this repo (needs pyproject.toml next to this script)."
  echo "Env: TASKBOT_HOME, TASKBOT_BIN, TASKBOT_REPO (git HTTPS URL)"
  exit "${1:-0}"
}

LOCAL=0
case "${1:-}" in
  --help|-h) usage ;;
  --local) LOCAL=1 ;;
  "") ;;
  *) echo "Unknown option: $1" >&2; usage 2 ;;
esac

command -v python3 >/dev/null || {
  echo "taskbot install: python3 not found. Install Python 3.10+ first." >&2
  exit 1
}

mkdir -p "$DEST" "$BIN"

python3 -m venv "$VENV"
"$VENV/bin/python" -m pip install -q --upgrade pip

if [[ "$LOCAL" == "1" ]]; then
  if [[ ! -f "$SCRIPT_DIR/pyproject.toml" ]]; then
    echo "taskbot install: --local requires pyproject.toml in $SCRIPT_DIR" >&2
    exit 1
  fi
  "$VENV/bin/pip" install -q -e "$SCRIPT_DIR"
else
  command -v git >/dev/null || {
    echo "taskbot install: git not found (needed for pip install from GitHub)." >&2
    exit 1
  }
  "$VENV/bin/pip" install -q "git+${REPO_URL}"
fi

ln -sf "$VENV/bin/taskbot" "$BIN/taskbot"
ln -sf "$VENV/bin/taskbot-gui" "$BIN/taskbot-gui"

echo "TaskBot installed."
echo "  Virtualenv: $VENV"
echo "  Commands:   $BIN/taskbot and $BIN/taskbot-gui"
if [[ ":$PATH:" != *":$BIN:"* ]]; then
  echo
  echo "Add this line to ~/.zshrc or ~/.bashrc, then open a new terminal:"
  echo "  export PATH=\"$BIN:\$PATH\""
fi
