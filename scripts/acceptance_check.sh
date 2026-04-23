#!/usr/bin/env bash
set -euo pipefail

: "${WG_OCD_BASE_DIR:=/etc/wg-ocd}"
: "${WG_IFACE:=wg0}"

echo "[1/4] 检查安装产物..."
[[ -f "$WG_OCD_BASE_DIR/server/$WG_IFACE.conf" ]]
[[ -f "$WG_OCD_BASE_DIR/state/server_keys.json" ]]
[[ -f "$WG_OCD_BASE_DIR/state/server_meta.json" ]]
echo "  OK"

echo "[2/4] 检查客户端握手前置..."
[[ -f "$WG_OCD_BASE_DIR/state/peers.json" ]] || echo "  WARN: peers.json 不存在（可能尚未加客户端）"
echo "  OK"

echo "[3/4] 检查开机自启..."
if systemctl is-enabled "wg-quick@$WG_IFACE" >/dev/null 2>&1; then
  echo "  enabled"
else
  echo "  disabled"
  exit 1
fi

echo "[4/4] 检查服务状态..."
systemctl status "wg-quick@$WG_IFACE" --no-pager >/dev/null 2>&1 && echo "  active" || (echo "  inactive" && exit 1)

echo "[DONE] 验收基础项通过"
