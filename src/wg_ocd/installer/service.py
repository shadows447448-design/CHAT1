"""Install and uninstall workflows."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class InstallerService:
    """Encapsulates install/uninstall workflows."""

    def install(self) -> None:
        logger.info("Starting WireGuard installation workflow...")
        logger.info("[stub] Install dependencies")
        logger.info("[stub] Generate server configuration")
        logger.info("[stub] Enable and start wg service")
        logger.info("Installation workflow completed.")

    def uninstall(self) -> None:
        logger.info("Starting uninstall workflow...")
        logger.info("[stub] Stop wg service")
        logger.info("[stub] Remove firewall rules")
        logger.info("[stub] Remove configuration files")
        logger.info("Uninstall workflow completed.")
