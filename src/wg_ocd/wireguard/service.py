"""WireGuard manager: keygen, templating, peer operations."""

from __future__ import annotations

import secrets

from wg_ocd.exceptions import CommandExecutionError, ValidationError
from wg_ocd.settings import Settings
from wg_ocd.utils import SystemUtils


class WireGuardManager:
    def __init__(self, settings: Settings, utils: SystemUtils) -> None:
        self.settings = settings
        self.utils = utils
        self.server_key_meta = self.settings.state_dir / "server_keys.json"

    def generate_server_keys(self) -> dict[str, str]:
        return {"private_key": secrets.token_urlsafe(32), "public_key": secrets.token_urlsafe(32)}

    def generate_client_keys(self) -> dict[str, str]:
        return {"private_key": secrets.token_urlsafe(32), "public_key": secrets.token_urlsafe(32)}

    def save_server_public_key(self, public_key: str) -> None:
        self.utils.write_json(self.server_key_meta, {"public_key": public_key})

    def load_server_public_key(self) -> str:
        return self.utils.read_json(self.server_key_meta, default={}).get("public_key", "REPLACE_SERVER_PUBLIC_KEY")

    def render_server_config(self, private_key: str, port: int) -> str:
        return self.utils.render_template(
            "server.conf.tpl",
            {
                "server_address": self.settings.server_address,
                "listen_port": str(port),
                "private_key": private_key,
                "post_up": "iptables -A FORWARD -i wg0 -j ACCEPT",
                "post_down": "iptables -D FORWARD -i wg0 -j ACCEPT",
            },
        )

    def render_client_config(self, client_private_key: str, client_address: str, server_public_key: str) -> str:
        return self.utils.render_template(
            "client.conf.tpl",
            {
                "client_private_key": client_private_key,
                "client_address": client_address,
                "dns": "1.1.1.1",
                "server_public_key": server_public_key,
                "endpoint": f"vpn.example.com:{self.settings.listen_port}",
                "allowed_ips": "0.0.0.0/0",
            },
        )

    def write_server_config(self, content: str) -> None:
        self.utils.ensure_dirs(self.settings.server_dir)
        self.utils.backup_file(self.settings.server_conf)
        self.settings.server_conf.write_text(content, encoding="utf-8")

    def add_peer(self, name: str, public_key: str, address: str) -> None:
        if not name:
            raise ValidationError("peer name required")
        peers_file = self.settings.state_dir / "peers.json"
        peers = self.utils.read_json(peers_file, default={})
        peers[name] = {"public_key": public_key, "address": address}
        self.utils.write_json(peers_file, peers)

    def remove_peer(self, name: str) -> None:
        peers_file = self.settings.state_dir / "peers.json"
        peers = self.utils.read_json(peers_file, default={})
        peers.pop(name, None)
        self.utils.write_json(peers_file, peers)

    def status(self) -> dict[str, str]:
        try:
            result = self.utils.execute(["wg", "show"], check=False)
            return {
                "service": "running" if result.returncode == 0 else "stopped",
                "interface": self.settings.interface,
                "summary": result.stdout.strip()[:200],
            }
        except CommandExecutionError:
            return {"service": "unknown", "interface": self.settings.interface, "summary": "wg command unavailable"}
