#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if ! command -v pyinstaller >/dev/null 2>&1; then
  echo "[ERROR] pyinstaller not found. Install with: pip install '.[build]'"
  exit 1
fi

echo "[INFO] Building standalone executable..."
pyinstaller \
  --clean \
  --onefile \
  --name wg-ocd \
  --paths src \
  app/main.py

echo "[INFO] Build complete: $ROOT_DIR/dist/wg-ocd"
