"""Shell command helpers."""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass

from wg_ocd.exceptions import CommandExecutionError

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class CommandResult:
    """Normalized command execution result."""

    returncode: int
    stdout: str
    stderr: str


class CommandRunner:
    """Encapsulates all system command execution."""

    def run(self, command: list[str], check: bool = True) -> CommandResult:
        logger.debug("Running command: %s", " ".join(command))
        try:
            proc = subprocess.run(command, capture_output=True, text=True)
        except OSError as exc:
            raise CommandExecutionError(f"Command execution failed: {' '.join(command)} | error={exc}") from exc
        result = CommandResult(proc.returncode, proc.stdout, proc.stderr)
        if check and result.returncode != 0:
            raise CommandExecutionError(
                f"Command failed: {' '.join(command)} | rc={result.returncode} | stderr={result.stderr.strip()}"
            )
        return result
