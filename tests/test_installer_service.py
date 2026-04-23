from pathlib import Path

from wg_ocd.firewall import FirewallManager
from wg_ocd.installer import InstallerManager
from wg_ocd.settings import Settings
from wg_ocd.utils import SystemUtils
from wg_ocd.wireguard import WireGuardManager


class FakeUtils(SystemUtils):
    def __init__(self, template_dir: Path, backup_dir: Path) -> None:
        super().__init__(template_dir, backup_dir)
        self.commands: list[list[str]] = []

    def execute(self, command: list[str], check: bool = True, input_text: str | None = None):  # type: ignore[override]
        self.commands.append(command)
        from wg_ocd.utils import CommandResult

        return CommandResult(returncode=0, stdout="ok", stderr="")


def test_install_and_uninstall_dry_run(tmp_path: Path) -> None:
    settings = Settings(base_dir=tmp_path / "wg")
    template_dir = Path(__file__).resolve().parents[1] / "src" / "wg_ocd" / "templates"
    utils = FakeUtils(template_dir=template_dir, backup_dir=settings.backup_dir)
    wg = WireGuardManager(settings, utils)
    fw = FirewallManager(utils)
    installer = InstallerManager(settings, utils, wg, fw)

    installer.install(dry_run=True)
    installer.uninstall(dry_run=True)

    assert settings.server_conf.exists() is False
    assert utils.commands == []
