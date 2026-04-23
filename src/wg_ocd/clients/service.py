"""Client lifecycle operations."""

from __future__ import annotations

import logging

from wg_ocd.exceptions import ValidationError

logger = logging.getLogger(__name__)


class ClientService:
    """Manage WireGuard clients."""

    def add_client(self, name: str) -> None:
        self._validate_name(name)
        logger.info("[stub] Adding client: %s", name)

    def remove_client(self, name: str) -> None:
        self._validate_name(name)
        logger.info("[stub] Removing client: %s", name)

    @staticmethod
    def _validate_name(name: str) -> None:
        if not name or not name.replace("-", "").replace("_", "").isalnum():
            raise ValidationError(
                "Client name must be non-empty and contain only letters, numbers, '-' or '_'."
            )
