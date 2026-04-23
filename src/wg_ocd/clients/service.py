"""Client manager: add/remove/list/export configs."""

from __future__ import annotations

from pathlib import Path

from wg_ocd.exceptions import ValidationError
from wg_ocd.settings import Settings
from wg_ocd.utils import SystemUtils
from wg_ocd.wireguard.service import WireGuardManager


class ClientManager:
    def __init__(self, settings: Settings, utils: SystemUtils, wg: WireGuardManager) -> None:
        self.settings = settings
        self.utils = utils
        self.wg = wg

    def add_client(self, name: str, dry_run: bool = False) -> Path:
        self._validate_name(name)
        registry = self._registry()
        if name in registry:
            raise ValidationError(f"Client already exists: {name}")

        ip = self._next_client_ip(registry)
        keys = self.wg.generate_client_keys()
        server_public_key = self.wg.load_server_public_key()

        cfg = self.wg.render_client_config(
            client_private_key=keys["private_key"],
            client_address=ip,
            server_public_key=server_public_key,
        )
        client_path = self.settings.clients_dir / f"{name}.conf"
        self.utils.ensure_dirs(self.settings.clients_dir)

        if not dry_run:
            self.utils.backup_file(client_path)
            client_path.write_text(cfg, encoding="utf-8")

            registry[name] = {"ip": ip, "status": "active"}
            self._save_registry(registry)
            self.wg.add_peer(name, keys["public_key"], ip)
            # rewrite server config with peer blocks and reload service
            private_key = self.wg.load_server_private_key()
            self.wg.write_server_config(self.wg.render_server_config(private_key, self.settings.listen_port))
            self.wg.apply_runtime(dry_run=False)
        return client_path

    def remove_client(self, name: str, dry_run: bool = False) -> None:
        registry = self._registry()
        if name not in registry:
            if dry_run:
                return
            raise ValidationError(f"Client does not exist: {name}")

        if not dry_run:
            registry.pop(name)
            self._save_registry(registry)

            client_path = self.settings.clients_dir / f"{name}.conf"
            self.utils.backup_file(client_path)
            client_path.unlink(missing_ok=True)
            self.wg.remove_peer(name)

            private_key = self.wg.load_server_private_key()
            self.wg.write_server_config(self.wg.render_server_config(private_key, self.settings.listen_port))
            self.wg.apply_runtime(dry_run=False)

    def list_clients(self) -> dict[str, dict[str, str]]:
        return self._registry()

    def export_config(self, name: str) -> str:
        client_path = self.settings.clients_dir / f"{name}.conf"
        if not client_path.exists():
            raise ValidationError(f"Client config not found: {name}")
        return client_path.read_text(encoding="utf-8")

    def _registry(self) -> dict[str, dict[str, str]]:
        self.utils.ensure_dirs(self.settings.state_dir)
        return self.utils.read_json(self.settings.registry_file, default={})

    def _save_registry(self, registry: dict[str, dict[str, str]]) -> None:
        self.utils.backup_file(self.settings.registry_file)
        self.utils.write_json(self.settings.registry_file, registry)

    @staticmethod
    def _validate_name(name: str) -> None:
        if not name or not name.replace("-", "").replace("_", "").isalnum():
            raise ValidationError("invalid client name")

    @staticmethod
    def _next_client_ip(registry: dict[str, dict[str, str]]) -> str:
        used = {int(v["ip"].split(".")[-1].split("/")[0]) for v in registry.values()} if registry else set()
        for i in range(2, 255):
            if i not in used:
                return f"10.8.0.{i}/32"
        raise ValidationError("No available client IP")
