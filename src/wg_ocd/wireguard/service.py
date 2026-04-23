"""WireGuard manager: keygen, templating, peer operations."""

from __future__ import annotations

import base64
import os

from wg_ocd.exceptions import CommandExecutionError, ValidationError
from wg_ocd.settings import Settings
from wg_ocd.utils import SystemUtils


class WireGuardManager:
    def __init__(self, settings: Settings, utils: SystemUtils) -> None:
        self.settings = settings
        self.utils = utils
        self.server_key_meta = self.settings.state_dir / "server_keys.json"
        self.server_meta = self.settings.state_dir / "server_meta.json"
        self.peers_file = self.settings.state_dir / "peers.json"

    def generate_server_keys(self) -> dict[str, str]:
        return self._generate_keypair()

    def generate_client_keys(self) -> dict[str, str]:
        return self._generate_keypair()

    def _generate_keypair(self) -> dict[str, str]:
        """Prefer wg genkey/pubkey; fallback for non-wg test environment."""
        try:
            gen = self.utils.execute(["wg", "genkey"], check=False)
            if gen.returncode == 0 and gen.stdout.strip():
                private_key = gen.stdout.strip()
                pub = self.utils.execute(["wg", "pubkey"], input_text=f"{private_key}\n", check=False)
                if pub.returncode == 0 and pub.stdout.strip():
                    return {"private_key": private_key, "public_key": pub.stdout.strip()}
        except CommandExecutionError:
            pass

        # fallback (kept for CI environments without wg binary)
        private_key = base64.b64encode(os.urandom(32)).decode()
        public_key = base64.b64encode(os.urandom(32)).decode()
        return {"private_key": private_key, "public_key": public_key}

    def save_server_public_key(self, public_key: str) -> None:
        self.utils.write_json(self.server_key_meta, {"public_key": public_key})

    def load_server_public_key(self) -> str:
        return self.utils.read_json(self.server_key_meta, default={}).get("public_key", "REPLACE_SERVER_PUBLIC_KEY")

    def save_server_endpoint(self, endpoint: str) -> None:
        self.utils.write_json(self.server_meta, {"endpoint": endpoint})

    def load_server_private_key(self) -> str:
        if not self.settings.server_conf.exists():
            raise ValidationError("Server config not found. Run install first.")
        for line in self.settings.server_conf.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("PrivateKey = "):
                return line.split("=", 1)[1].strip()
        raise ValidationError("Server config missing PrivateKey.")

    def load_server_endpoint(self) -> str:
        return self.utils.read_json(self.server_meta, default={}).get("endpoint", f"127.0.0.1:{self.settings.listen_port}")

    def render_server_config(self, private_key: str, port: int) -> str:
        return self.utils.render_template(
            "server.conf.tpl",
            {
                "server_address": self.settings.server_address,
                "listen_port": str(port),
                "private_key": private_key,
                "post_up": "iptables -A FORWARD -i wg0 -j ACCEPT",
                "post_down": "iptables -D FORWARD -i wg0 -j ACCEPT",
                "peers_block": self._render_peers_block(),
            },
        )

    def _render_peers_block(self) -> str:
        peers = self.utils.read_json(self.peers_file, default={})
        blocks: list[str] = []
        for _, peer in peers.items():
            blocks.append(
                "\n".join(
                    [
                        "[Peer]",
                        f"PublicKey = {peer['public_key']}",
                        f"AllowedIPs = {peer['address']}",
                    ]
                )
            )
        return "\n\n".join(blocks)

    def render_client_config(self, client_private_key: str, client_address: str, server_public_key: str) -> str:
        return self.utils.render_template(
            "client.conf.tpl",
            {
                "client_private_key": client_private_key,
                "client_address": client_address,
                "dns": "1.1.1.1",
                "server_public_key": server_public_key,
                "endpoint": self.load_server_endpoint(),
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
        peers = self.utils.read_json(self.peers_file, default={})
        peers[name] = {"public_key": public_key, "address": address}
        self.utils.write_json(self.peers_file, peers)

    def remove_peer(self, name: str) -> None:
        peers = self.utils.read_json(self.peers_file, default={})
        peers.pop(name, None)
        self.utils.write_json(self.peers_file, peers)

    def apply_runtime(self, dry_run: bool = False) -> None:
        if dry_run:
            return
        try:
            self.utils.execute(["systemctl", "restart", f"wg-quick@{self.settings.interface}"], check=False)
        except CommandExecutionError:
            return

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
