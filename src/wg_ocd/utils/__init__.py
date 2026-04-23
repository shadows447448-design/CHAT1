"""Shared utilities: command execution, backup, template, logging, path helpers."""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from string import Template

from wg_ocd.exceptions import CommandExecutionError

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


class SystemUtils:
    """Centralized utility layer required by the MVP split."""

    def __init__(self, template_dir: Path, backup_dir: Path) -> None:
        self.template_dir = template_dir
        self.backup_dir = backup_dir
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def execute(self, command: list[str], check: bool = True, input_text: str | None = None) -> CommandResult:
        logger.debug("Running command: %s", " ".join(command))
        try:
            proc = subprocess.run(command, input=input_text, capture_output=True, text=True)
        except OSError as exc:
            raise CommandExecutionError(f"Command execution failed: {' '.join(command)} | error={exc}") from exc
        result = CommandResult(proc.returncode, proc.stdout, proc.stderr)
        if check and result.returncode != 0:
            raise CommandExecutionError(
                f"Command failed: {' '.join(command)} | rc={result.returncode} | stderr={result.stderr.strip()}"
            )
        return result

    def backup_file(self, file_path: Path) -> Path | None:
        if not file_path.exists():
            return None
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        target = self.backup_dir / f"{file_path.name}.{ts}.bak"
        shutil.copy2(file_path, target)
        return target

    def render_template(self, template_name: str, context: dict[str, str]) -> str:
        content = (self.template_dir / template_name).read_text(encoding="utf-8")
        return Template(content).safe_substitute(context)

    @staticmethod
    def ensure_dirs(*dirs: Path) -> None:
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def write_json(path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    @staticmethod
    def read_json(path: Path, default: dict | None = None) -> dict:
        if not path.exists():
            return default or {}
        return json.loads(path.read_text(encoding="utf-8"))


__all__ = ["SystemUtils", "CommandResult"]
