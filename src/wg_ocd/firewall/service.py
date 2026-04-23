"""Firewall abstraction for nftables/iptables integration."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class FirewallService:
    """Handles firewall rule setup and teardown."""

    def apply_rules(self) -> None:
        logger.info("[stub] Applying firewall/NAT rules")

    def remove_rules(self) -> None:
        logger.info("[stub] Removing firewall/NAT rules")
