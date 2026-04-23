"""Application orchestration layer."""

from __future__ import annotations

from wg_ocd.clients.service import ClientService
from wg_ocd.firewall.service import FirewallService
from wg_ocd.installer.service import InstallerService
from wg_ocd.settings import Settings
from wg_ocd.wireguard.service import WireGuardService


class Application:
    """Top-level use-case orchestrator for CLI handlers."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings.from_env()
        self.installer = InstallerService(self.settings)
        self.wireguard = WireGuardService(self.settings)
        self.firewall = FirewallService()
        self.clients = ClientService(self.settings)

    def install(self, dry_run: bool = False) -> None:
        self.installer.install(dry_run=dry_run)
        self.firewall.apply_rules(dry_run=dry_run)
        self.wireguard.apply_server_config(dry_run=dry_run)

    def add_client(self, name: str) -> str:
        return str(self.clients.add_client(name))

    def remove_client(self, name: str) -> None:
        self.clients.remove_client(name)

    def status(self) -> dict[str, str]:
        return self.wireguard.get_status()

    def uninstall(self, dry_run: bool = False) -> None:
        self.firewall.remove_rules(dry_run=dry_run)
        self.installer.uninstall(dry_run=dry_run)
