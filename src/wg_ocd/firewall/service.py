"""Firewall manager: detect backend, apply/remove NAT and allowlist."""

from __future__ import annotations

import logging

from wg_ocd.utils import SystemUtils

logger = logging.getLogger(__name__)


class FirewallManager:
    def __init__(self, utils: SystemUtils) -> None:
        self.utils = utils

    def detect_backend(self) -> str:
        if self.utils.execute(["which", "nft"], check=False).returncode == 0:
            return "nftables"
        if self.utils.execute(["which", "iptables"], check=False).returncode == 0:
            return "iptables"
        if self.utils.execute(["which", "ufw"], check=False).returncode == 0:
            return "ufw"
        return "unknown"

    def setup_nat(self, dry_run: bool = False) -> None:
        if dry_run:
            logger.info("Dry-run: skip NAT setup")
            return
        self.utils.execute(["sysctl", "-w", "net.ipv4.ip_forward=1"])

    def allow_port(self, port: int, dry_run: bool = False) -> None:
        if dry_run:
            logger.info("Dry-run: skip allow port %s", port)
            return
        if self.detect_backend() == "ufw":
            self.utils.execute(["ufw", "allow", f"{port}/udp"], check=False)

    def teardown(self, port: int, dry_run: bool = False) -> None:
        if dry_run:
            logger.info("Dry-run: skip firewall teardown")
            return
        self.utils.execute(["sysctl", "-w", "net.ipv4.ip_forward=0"], check=False)
        if self.detect_backend() == "ufw":
            self.utils.execute(["ufw", "delete", "allow", f"{port}/udp"], check=False)
