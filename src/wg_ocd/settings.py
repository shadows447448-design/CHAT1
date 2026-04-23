"""Runtime settings for wg-ocd."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class Settings:
    """Configuration paths and defaults."""

    base_dir: Path = Path("/etc/wg-ocd")
    interface: str = "wg0"
    server_address: str = "10.8.0.1/24"
    listen_port: int = 51820

    @classmethod
    def from_env(cls) -> "Settings":
        base = Path(os.getenv("WG_OCD_BASE_DIR", "/etc/wg-ocd"))
        iface = os.getenv("WG_OCD_INTERFACE", "wg0")
        return cls(base_dir=base, interface=iface)

    @property
    def server_dir(self) -> Path:
        return self.base_dir / "server"

    @property
    def clients_dir(self) -> Path:
        return self.base_dir / "clients"

    @property
    def state_dir(self) -> Path:
        return self.base_dir / "state"

    @property
    def backup_dir(self) -> Path:
        return self.base_dir / "backup"

    @property
    def server_conf(self) -> Path:
        return self.server_dir / f"{self.interface}.conf"

    @property
    def registry_file(self) -> Path:
        return self.state_dir / "clients.json"
