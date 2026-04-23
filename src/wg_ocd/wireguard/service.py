"""WireGuard-specific operations."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class WireGuardService:
    """Handles WireGuard interface and config-level operations."""

    def apply_server_config(self) -> None:
        logger.info("[stub] Applying WireGuard server config")

    def get_status(self) -> dict[str, str]:
        logger.info("[stub] Reading WireGuard status")
        return {
            "service": "unknown",
            "interface": "wg0",
            "handshakes": "0",
        }
