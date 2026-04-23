"""Installer manager: root/distro checks, packages, kernel, systemd."""

from __future__ import annotations

import os
from pathlib import Path

from wg_ocd.exceptions import ValidationError
from wg_ocd.firewall.service import FirewallManager
from wg_ocd.settings import Settings
from wg_ocd.utils import SystemUtils
from wg_ocd.wireguard.service import WireGuardManager


class InstallerManager:
    def __init__(self, settings: Settings, utils: SystemUtils, wg: WireGuardManager, fw: FirewallManager) -> None:
        self.settings = settings
        self.utils = utils
        self.wg = wg
        self.fw = fw

    def check_root(self) -> None:
        if hasattr(os, "geteuid") and os.geteuid() != 0:
            raise ValidationError("Root privileges required")

    def check_distribution(self) -> str:
        info = Path("/etc/os-release")
        if not info.exists():
            return "unknown"
        text = info.read_text(encoding="utf-8").lower()
        if "ubuntu" in text:
            return "ubuntu"
        if "debian" in text:
            return "debian"
        return "other"

    def install_packages(self, dry_run: bool = False) -> None:
        if dry_run:
            return
        distro = self.check_distribution()
        if distro in {"ubuntu", "debian"}:
            self.utils.execute(["apt-get", "update"], check=False)
            self.utils.execute(["apt-get", "install", "-y", "wireguard", "wireguard-tools"], check=False)

    def enable_kernel_forward(self, dry_run: bool = False) -> None:
        self.fw.setup_nat(dry_run=dry_run)

    def configure_systemd(self, dry_run: bool = False) -> None:
        if dry_run:
            return
        self.utils.execute(["systemctl", "enable", f"wg-quick@{self.settings.interface}"], check=False)

    def install(self, dry_run: bool = False) -> None:
        self.utils.ensure_dirs(self.settings.server_dir, self.settings.clients_dir, self.settings.state_dir)
        if not dry_run:
            self.check_root()
        self.install_packages(dry_run=dry_run)

        server_keys = self.wg.generate_server_keys()
        server_cfg = self.wg.render_server_config(server_keys["private_key"], self.settings.listen_port)
        if not dry_run:
            self.wg.write_server_config(server_cfg)

        self.enable_kernel_forward(dry_run=dry_run)
        self.fw.allow_port(self.settings.listen_port, dry_run=dry_run)
        self.configure_systemd(dry_run=dry_run)

        manifest = self.settings.state_dir / "install-manifest.json"
        if not dry_run:
            self.utils.write_json(
                manifest,
                {
                    "created_paths": [
                        str(self.settings.server_conf),
                        str(self.settings.registry_file),
                        str(self.settings.clients_dir),
                    ]
                },
            )
            if not self.settings.registry_file.exists():
                self.utils.write_json(self.settings.registry_file, {})

    def uninstall(self, dry_run: bool = False) -> None:
        self.fw.teardown(self.settings.listen_port, dry_run=dry_run)
        if dry_run:
            return
        self.utils.execute(["systemctl", "disable", f"wg-quick@{self.settings.interface}"], check=False)
        manifest = self.settings.state_dir / "install-manifest.json"
        data = self.utils.read_json(manifest, default={})
        for path_str in reversed(data.get("created_paths", [])):
            p = Path(path_str)
            if p.is_file():
                p.unlink(missing_ok=True)
            elif p.is_dir() and p.exists() and not any(p.iterdir()):
                p.rmdir()
        manifest.unlink(missing_ok=True)
