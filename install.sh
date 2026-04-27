#!/usr/bin/env bash
# Thin wrapper around install.py (for clones only). Prefer: python3 install.py
set -euo pipefail
DIR="$(CDPATH= cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
exec python3 "$DIR/install.py" "$@"
