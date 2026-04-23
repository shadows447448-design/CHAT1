"""Backup helpers for safe config mutations."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


class BackupManager:
    """Create timestamped backups before mutating system files."""

    def __init__(self, backup_dir: Path) -> None:
        self.backup_dir = backup_dir
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def backup_file(self, file_path: Path) -> Path | None:
        """Backup file if it exists and return backup path."""
        if not file_path.exists():
            return None

        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        target = self.backup_dir / f"{file_path.name}.{ts}.bak"
        shutil.copy2(file_path, target)
        return target

    def write_manifest(self, manifest_path: Path, created_paths: list[Path]) -> None:
        """Write created path manifest for uninstall rollback."""
        payload = {"created_paths": [str(p) for p in created_paths]}
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
