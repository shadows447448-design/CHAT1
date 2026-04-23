import json
from pathlib import Path

import pytest

from wg_ocd.clients.service import ClientService
from wg_ocd.exceptions import ValidationError
from wg_ocd.settings import Settings


def make_settings(tmp_path: Path) -> Settings:
    return Settings(base_dir=tmp_path / "wg-ocd-test")


def test_add_client_creates_config_and_registry(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    svc = ClientService(settings)

    client_path = svc.add_client("alice")

    assert client_path.exists()
    registry = json.loads(settings.registry_file.read_text(encoding="utf-8"))
    assert "alice" in registry
    assert registry["alice"]["status"] == "active"


def test_remove_client_deletes_registry_and_config(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    svc = ClientService(settings)
    client_path = svc.add_client("alice")

    svc.remove_client("alice")

    assert not client_path.exists()
    registry = json.loads(settings.registry_file.read_text(encoding="utf-8"))
    assert "alice" not in registry


def test_add_client_duplicate_raises(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    svc = ClientService(settings)
    svc.add_client("alice")

    with pytest.raises(ValidationError):
        svc.add_client("alice")
