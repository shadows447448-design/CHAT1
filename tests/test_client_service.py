from pathlib import Path

import pytest

from wg_ocd.clients import ClientManager
from wg_ocd.settings import Settings
from wg_ocd.utils import SystemUtils
from wg_ocd.wireguard import WireGuardManager


@pytest.fixture
def client_manager(tmp_path: Path) -> ClientManager:
    settings = Settings(base_dir=tmp_path / "wg")
    template_dir = Path(__file__).resolve().parents[1] / "src" / "wg_ocd" / "templates"
    utils = SystemUtils(template_dir=template_dir, backup_dir=settings.backup_dir)
    wg = WireGuardManager(settings, utils)
    settings.server_dir.mkdir(parents=True, exist_ok=True)
    settings.server_conf.write_text("[Interface]\nPrivateKey = test-private\n", encoding="utf-8")
    wg.save_server_public_key("test-public")
    wg.save_server_endpoint("127.0.0.1:51820")
    return ClientManager(settings, utils, wg)


def test_add_and_list_client(client_manager: ClientManager) -> None:
    path = client_manager.add_client("alice")
    assert path.exists()
    data = client_manager.list_clients()
    assert "alice" in data


def test_remove_client(client_manager: ClientManager) -> None:
    client_manager.add_client("alice")
    client_manager.remove_client("alice")
    assert "alice" not in client_manager.list_clients()


def test_export_config(client_manager: ClientManager) -> None:
    client_manager.add_client("alice")
    text = client_manager.export_config("alice")
    assert "[Peer]" in text


def test_duplicate_client_raises(client_manager: ClientManager) -> None:
    client_manager.add_client("alice")
    with pytest.raises(Exception):
        client_manager.add_client("alice")
