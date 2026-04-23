"""Application orchestration layer."""

from __future__ import annotations

from pathlib import Path

from wg_ocd.clients import ClientManager
from wg_ocd.firewall import FirewallManager
from wg_ocd.installer import InstallerManager
from wg_ocd.settings import Settings
from wg_ocd.utils import SystemUtils
from wg_ocd.wireguard import WireGuardManager


class Application:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings.from_env()
        template_dir = Path(__file__).resolve().parent / "templates"
        self.utils = SystemUtils(template_dir=template_dir, backup_dir=self.settings.backup_dir)
        self.wg = WireGuardManager(self.settings, self.utils)
        self.firewall = FirewallManager(self.utils)
        self.installer = InstallerManager(self.settings, self.utils, self.wg, self.firewall)
        self.clients = ClientManager(self.settings, self.utils, self.wg)

    def install(self, dry_run: bool = False) -> None:
        self.installer.install(dry_run=dry_run)

    def add_client(self, name: str, dry_run: bool = False) -> str:
        return str(self.clients.add_client(name, dry_run=dry_run))

    def remove_client(self, name: str, dry_run: bool = False) -> None:
        self.clients.remove_client(name, dry_run=dry_run)

    def status(self) -> dict[str, str]:
        return self.wg.status()

    def uninstall(self, dry_run: bool = False) -> None:
        self.installer.uninstall(dry_run=dry_run)
