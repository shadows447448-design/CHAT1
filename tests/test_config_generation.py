from pathlib import Path

from wg_ocd.settings import Settings
from wg_ocd.utils import SystemUtils
from wg_ocd.wireguard import WireGuardManager


def test_render_server_and_client_templates(tmp_path: Path) -> None:
    settings = Settings(base_dir=tmp_path / "wg")
    template_dir = Path(__file__).resolve().parents[1] / "src" / "wg_ocd" / "templates"
    utils = SystemUtils(template_dir=template_dir, backup_dir=settings.backup_dir)
    wg = WireGuardManager(settings, utils)

    server = wg.render_server_config("server-private", 51820)
    client = wg.render_client_config("client-private", "10.8.0.2/32", "server-public")

    assert "PrivateKey = server-private" in server
    assert "ListenPort = 51820" in server
    assert "PrivateKey = client-private" in client
    assert "PublicKey = server-public" in client
