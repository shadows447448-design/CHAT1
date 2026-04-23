"""WireGuard-specific operations."""

from __future__ import annotations

import logging

from wg_ocd.exceptions import CommandExecutionError
from wg_ocd.settings import Settings
from wg_ocd.utils.command import CommandRunner

logger = logging.getLogger(__name__)


class WireGuardService:
    """Handles WireGuard interface and config-level operations."""

    def __init__(self, settings: Settings, command_runner: CommandRunner | None = None) -> None:
        self.settings = settings
        self.command_runner = command_runner or CommandRunner()

    def apply_server_config(self, dry_run: bool = False) -> None:
        if dry_run:
            logger.info("Dry-run: skip apply server config")
            return
        self.command_runner.run(["wg", "syncconf", self.settings.interface, str(self.settings.server_conf)])

    def get_status(self) -> dict[str, str]:
        try:
            result = self.command_runner.run(["wg", "show"], check=False)
            return {
                "service": "running" if result.returncode == 0 else "stopped",
                "interface": self.settings.interface,
                "summary": result.stdout.strip()[:200],
            }
        except CommandExecutionError:
            return {
                "service": "unknown",
                "interface": self.settings.interface,
                "summary": "wg command unavailable",
            }
