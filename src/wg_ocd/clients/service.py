"""Client lifecycle operations."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from wg_ocd.config.templates import render_template
from wg_ocd.exceptions import ValidationError
from wg_ocd.settings import Settings
from wg_ocd.utils.backup import BackupManager

logger = logging.getLogger(__name__)


class ClientService:
    """Manage WireGuard clients."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.backup = BackupManager(self.settings.backup_dir)

    def add_client(self, name: str) -> Path:
        self._validate_name(name)
        self._ensure_dirs()
        registry = self._load_registry()
        if name in registry:
            raise ValidationError(f"Client already exists: {name}")

        ip = self._next_client_ip(registry)
        registry[name] = {"ip": ip, "status": "active"}

        self.backup.backup_file(self.settings.registry_file)
        self.settings.registry_file.write_text(json.dumps(registry, indent=2), encoding="utf-8")

        client_config = render_template(
            "client.conf.tpl",
            {
                "client_private_key": "REPLACE_CLIENT_PRIVATE_KEY",
                "client_address": ip,
                "dns": "1.1.1.1",
                "server_public_key": "REPLACE_SERVER_PUBLIC_KEY",
                "endpoint": "vpn.example.com:51820",
                "allowed_ips": "0.0.0.0/0",
            },
        )
        client_path = self.settings.clients_dir / f"{name}.conf"
        client_path.write_text(client_config, encoding="utf-8")

        logger.info("Client added: %s", name)
        return client_path

    def remove_client(self, name: str) -> None:
        self._validate_name(name)
        registry = self._load_registry()
        if name not in registry:
            raise ValidationError(f"Client does not exist: {name}")

        self.backup.backup_file(self.settings.registry_file)
        registry.pop(name)
        self.settings.registry_file.write_text(json.dumps(registry, indent=2), encoding="utf-8")

        client_path = self.settings.clients_dir / f"{name}.conf"
        if client_path.exists():
            self.backup.backup_file(client_path)
            client_path.unlink()

        logger.info("Client removed: %s", name)

    def list_clients(self) -> dict[str, dict[str, str]]:
        return self._load_registry()

    def _ensure_dirs(self) -> None:
        self.settings.clients_dir.mkdir(parents=True, exist_ok=True)
        self.settings.state_dir.mkdir(parents=True, exist_ok=True)
        if not self.settings.registry_file.exists():
            self.settings.registry_file.write_text("{}", encoding="utf-8")

    def _load_registry(self) -> dict[str, dict[str, str]]:
        self._ensure_dirs()
        return json.loads(self.settings.registry_file.read_text(encoding="utf-8"))

    @staticmethod
    def _validate_name(name: str) -> None:
        if not name or not name.replace("-", "").replace("_", "").isalnum():
            raise ValidationError(
                "Client name must be non-empty and contain only letters, numbers, '-' or '_'."
            )

    @staticmethod
    def _next_client_ip(registry: dict[str, dict[str, str]]) -> str:
        used = {int(info["ip"].split(".")[-1].split("/")[0]) for info in registry.values()} if registry else set()
        for last in range(2, 255):
            if last not in used:
                return f"10.8.0.{last}/32"
        raise ValidationError("No available client IP address")
