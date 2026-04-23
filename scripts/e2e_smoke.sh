#!/usr/bin/env bash
set -euo pipefail

# Run on a real target server with sudo privileges.
: "${WG_OCD_BASE_DIR:=/etc/wg-ocd}"

python -m app.main install
python -m app.main add-client --name smoke-client
python -m app.main status

echo "[INFO] 请在客户端导入配置后，回到服务端执行: wg show"

grep -q "smoke-client" "$WG_OCD_BASE_DIR/state/peers.json"
python -m app.main remove-client --name smoke-client
python -m app.main uninstall

echo "[OK] E2E smoke completed"
