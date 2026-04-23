#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN_SRC="$ROOT_DIR/dist/wg-ocd"
BIN_DST="/usr/local/bin/wg-ocd"

if [[ ! -f "$BIN_SRC" ]]; then
  echo "[ERROR] Executable not found at $BIN_SRC"
  echo "[HINT] Run ./scripts/build_exe.sh first"
  exit 1
fi

if [[ "$EUID" -ne 0 ]]; then
  echo "[ERROR] Please run as root: sudo ./scripts/install_exe.sh"
  exit 1
fi

install -m 0755 "$BIN_SRC" "$BIN_DST"

echo "[INFO] Installed executable to $BIN_DST"
echo "[INFO] Try: wg-ocd --help"
