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
        self.utils.execute(["sysctl", "-w", "net.ipv4.ip_forward=1"], check=False)
        backend = self.detect_backend()
        if backend == "nftables":
            self.utils.execute(["bash", "-lc", "nft add table ip wgocd"], check=False)
            self.utils.execute(
                ["bash", "-lc", "nft 'add chain ip wgocd postrouting { type nat hook postrouting priority 100; }'"],
                check=False,
            )
            self.utils.execute(["bash", "-lc", "nft add rule ip wgocd postrouting masquerade"], check=False)
        elif backend == "iptables":
            self.utils.execute(["iptables", "-t", "nat", "-A", "POSTROUTING", "-j", "MASQUERADE"], check=False)

    def allow_port(self, port: int, dry_run: bool = False) -> None:
        if dry_run:
            logger.info("Dry-run: skip allow port %s", port)
            return
        backend = self.detect_backend()
        if backend == "ufw":
            self.utils.execute(["ufw", "allow", f"{port}/udp"], check=False)
        elif backend == "iptables":
            self.utils.execute(["iptables", "-A", "INPUT", "-p", "udp", "--dport", str(port), "-j", "ACCEPT"], check=False)
        elif backend == "nftables":
            self.utils.execute(["bash", "-lc", f"nft add rule inet filter input udp dport {port} accept"], check=False)

    def teardown(self, port: int, dry_run: bool = False) -> None:
        if dry_run:
            logger.info("Dry-run: skip firewall teardown")
            return
        self.utils.execute(["sysctl", "-w", "net.ipv4.ip_forward=0"], check=False)
        backend = self.detect_backend()
        if backend == "ufw":
            self.utils.execute(["ufw", "delete", "allow", f"{port}/udp"], check=False)
        elif backend == "iptables":
            self.utils.execute(["iptables", "-D", "INPUT", "-p", "udp", "--dport", str(port), "-j", "ACCEPT"], check=False)
            self.utils.execute(["iptables", "-t", "nat", "-D", "POSTROUTING", "-j", "MASQUERADE"], check=False)
        elif backend == "nftables":
            self.utils.execute(["bash", "-lc", "nft delete table ip wgocd"], check=False)
