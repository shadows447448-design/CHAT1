from pathlib import Path

from wg_ocd.config.templates import render_template


def test_server_config_uses_template_values(tmp_path: Path) -> None:
    text = render_template(
        "server.conf.tpl",
        {
            "server_address": "10.8.0.1/24",
            "listen_port": "51820",
            "private_key": "SAMPLE",
            "post_up": "up",
            "post_down": "down",
        },
    )

    assert "Address = 10.8.0.1/24" in text
    assert "ListenPort = 51820" in text
    assert "PrivateKey = SAMPLE" in text
