"""Shell command helpers."""

from __future__ import annotations

import logging
import subprocess

from wg_ocd.exceptions import CommandExecutionError

logger = logging.getLogger(__name__)


def run_command(command: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """Execute a shell command and return the completed process."""
    logger.debug("Running command: %s", " ".join(command))
    result = subprocess.run(command, capture_output=True, text=True)
    if check and result.returncode != 0:
        raise CommandExecutionError(
            f"Command failed: {' '.join(command)} | rc={result.returncode} | stderr={result.stderr.strip()}"
        )
    return result
