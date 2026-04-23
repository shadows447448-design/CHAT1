"""Firewall abstraction for nftables/iptables integration."""

from __future__ import annotations

import logging

from wg_ocd.utils.command import CommandRunner

logger = logging.getLogger(__name__)


class FirewallService:
    """Handles firewall rule setup and teardown."""

    def __init__(self, command_runner: CommandRunner | None = None) -> None:
        self.command_runner = command_runner or CommandRunner()

    def apply_rules(self, dry_run: bool = False) -> None:
        if dry_run:
            logger.info("Dry-run: skip firewall rule apply")
            return
        self.command_runner.run(["sysctl", "-w", "net.ipv4.ip_forward=1"])

    def remove_rules(self, dry_run: bool = False) -> None:
        if dry_run:
            logger.info("Dry-run: skip firewall rule removal")
            return
        self.command_runner.run(["sysctl", "-w", "net.ipv4.ip_forward=0"], check=False)
