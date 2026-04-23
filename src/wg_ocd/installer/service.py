"""Install and uninstall workflows."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from wg_ocd.config.templates import render_template
from wg_ocd.settings import Settings
from wg_ocd.utils.backup import BackupManager
from wg_ocd.utils.command import CommandRunner

logger = logging.getLogger(__name__)


class InstallerService:
    """Encapsulates install/uninstall workflows."""

    def __init__(self, settings: Settings, command_runner: CommandRunner | None = None) -> None:
        self.settings = settings
        self.command_runner = command_runner or CommandRunner()
        self.backup = BackupManager(self.settings.backup_dir)

    def install(self, dry_run: bool = False) -> list[Path]:
        logger.info("Starting WireGuard installation workflow (dry_run=%s)", dry_run)
        created_paths: list[Path] = []

        for directory in [self.settings.server_dir, self.settings.clients_dir, self.settings.state_dir]:
            if not directory.exists():
                created_paths.append(directory)
            if not dry_run:
                directory.mkdir(parents=True, exist_ok=True)

        if not dry_run:
            self.backup.backup_file(self.settings.server_conf)
            server_content = render_template(
                "server.conf.tpl",
                {
                    "server_address": self.settings.server_address,
                    "listen_port": str(self.settings.listen_port),
                    # Do not log/render external details beyond required file content.
                    "private_key": "REPLACE_SERVER_PRIVATE_KEY",
                    "post_up": "iptables -A FORWARD -i wg0 -j ACCEPT",
                    "post_down": "iptables -D FORWARD -i wg0 -j ACCEPT",
                },
            )
            self.settings.server_conf.write_text(server_content, encoding="utf-8")
            created_paths.append(self.settings.server_conf)

            if not self.settings.registry_file.exists():
                self.settings.registry_file.write_text("{}", encoding="utf-8")
                created_paths.append(self.settings.registry_file)

            self.command_runner.run(["wg", "quick", "down", self.settings.interface], check=False)
            self.command_runner.run(["wg", "quick", "up", self.settings.interface])
            self.command_runner.run(["systemctl", "enable", f"wg-quick@{self.settings.interface}"])
        else:
            logger.info("Dry-run: skipping filesystem and command mutations.")

        manifest = self.settings.state_dir / "install-manifest.json"
        if not dry_run:
            self.backup.write_manifest(manifest, created_paths)

        logger.info("Installation workflow completed.")
        return created_paths

    def uninstall(self, dry_run: bool = False) -> list[Path]:
        logger.info("Starting uninstall workflow (dry_run=%s)", dry_run)
        removed: list[Path] = []
        manifest = self.settings.state_dir / "install-manifest.json"

        if not dry_run:
            self.command_runner.run(["wg", "quick", "down", self.settings.interface], check=False)
            self.command_runner.run(["systemctl", "disable", f"wg-quick@{self.settings.interface}"], check=False)

            if manifest.exists():
                data = json.loads(manifest.read_text(encoding="utf-8"))
                for item in reversed(data.get("created_paths", [])):
                    path = Path(item)
                    if path.is_file() and path.exists():
                        path.unlink()
                        removed.append(path)
                    elif path.is_dir() and path.exists() and not any(path.iterdir()):
                        path.rmdir()
                        removed.append(path)
                manifest.unlink(missing_ok=True)
                removed.append(manifest)
        else:
            logger.info("Dry-run: skipping uninstall mutations.")

        logger.info("Uninstall workflow completed.")
        return removed
