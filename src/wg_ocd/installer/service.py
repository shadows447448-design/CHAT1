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

    def detect_package_manager(self) -> str:
        for pm in ["apt-get", "dnf", "yum", "pacman"]:
            if self.utils.execute(["which", pm], check=False).returncode == 0:
                return pm
        return "unknown"

    def detect_endpoint(self) -> str:
        pub = self.utils.execute(["bash", "-lc", "curl -4s ifconfig.me"], check=False)
        host = pub.stdout.strip()
        if not host:
            ipr = self.utils.execute(["bash", "-lc", "hostname -I | awk '{print $1}'"], check=False)
            host = ipr.stdout.strip() or "127.0.0.1"
        return f"{host}:{self.settings.listen_port}"

    def install_packages(self, dry_run: bool = False) -> None:
        if dry_run:
            return

        pm = self.detect_package_manager()
        if pm == "apt-get":
            self.utils.execute(["apt-get", "update"], check=True)
            self.utils.execute(["apt-get", "install", "-y", "wireguard", "wireguard-tools", "curl"], check=True)
        elif pm == "dnf":
            self.utils.execute(["dnf", "install", "-y", "wireguard-tools", "curl"], check=True)
        elif pm == "yum":
            self.utils.execute(["yum", "install", "-y", "wireguard-tools", "curl"], check=True)
        elif pm == "pacman":
            self.utils.execute(["pacman", "-Sy", "--noconfirm", "wireguard-tools", "curl"], check=True)
        else:
            raise ValidationError("Unsupported package manager; install wireguard-tools and curl manually")

    def configure_systemd(self, dry_run: bool = False) -> None:
        if dry_run:
            return
        self.utils.execute(["systemctl", "enable", f"wg-quick@{self.settings.interface}"], check=True)
        self.utils.execute(["systemctl", "restart", f"wg-quick@{self.settings.interface}"], check=True)

    def install(self, dry_run: bool = False) -> None:
        self.utils.ensure_dirs(self.settings.server_dir, self.settings.clients_dir, self.settings.state_dir)
        if not dry_run:
            self.check_root()
        self.install_packages(dry_run=dry_run)

        if not dry_run:
            server_keys = self.wg.generate_server_keys()
            server_cfg = self.wg.render_server_config(server_keys["private_key"], self.settings.listen_port)
            self.wg.write_server_config(server_cfg)
            self.wg.save_server_public_key(server_keys["public_key"])
            self.wg.save_server_endpoint(self.detect_endpoint())

        self.fw.setup_nat(dry_run=dry_run)
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
                        str(self.settings.state_dir / "peers.json"),
                        str(self.settings.state_dir / "server_keys.json"),
                        str(self.settings.state_dir / "server_meta.json"),
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
        self.utils.execute(["systemctl", "stop", f"wg-quick@{self.settings.interface}"], check=False)

        manifest = self.settings.state_dir / "install-manifest.json"
        data = self.utils.read_json(manifest, default={})
        for path_str in reversed(data.get("created_paths", [])):
            p = Path(path_str)
            if p.is_file():
                p.unlink(missing_ok=True)

        for d in [self.settings.clients_dir, self.settings.server_dir, self.settings.state_dir]:
            if d.exists() and not any(d.iterdir()):
                d.rmdir()
        manifest.unlink(missing_ok=True)
