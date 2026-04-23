"""Application orchestration layer."""

from __future__ import annotations

from wg_ocd.clients.service import ClientService
from wg_ocd.firewall.service import FirewallService
from wg_ocd.installer.service import InstallerService
from wg_ocd.wireguard.service import WireGuardService


class Application:
    """Top-level use-case orchestrator for CLI handlers."""

    def __init__(self) -> None:
        self.installer = InstallerService()
        self.wireguard = WireGuardService()
        self.firewall = FirewallService()
        self.clients = ClientService()

    def install(self) -> None:
        self.installer.install()
        self.firewall.apply_rules()
        self.wireguard.apply_server_config()

    def add_client(self, name: str) -> None:
        self.clients.add_client(name)

    def remove_client(self, name: str) -> None:
        self.clients.remove_client(name)

    def status(self) -> dict[str, str]:
        return self.wireguard.get_status()

    def uninstall(self) -> None:
        self.installer.uninstall()
        self.firewall.remove_rules()
