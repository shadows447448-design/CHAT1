"""CLI MVP entrypoint.

Usage examples:
  python -m app.main install
  python -m app.main add-client --name alice
  python -m app.main remove-client --name alice
  python -m app.main status
  python -m app.main uninstall
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

# Allow `python -m app.main ...` to import the src-layout package without install.
ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from wg_ocd.app import Application
from wg_ocd.exceptions import WGOCDError
from wg_ocd.utils.logging_utils import configure_logging

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.main",
        description="WireGuard one-click deploy CLI MVP",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("install", help="完成完整部署")

    add_client_parser = subparsers.add_parser("add-client", help="新建客户端配置")
    add_client_parser.add_argument("--name", required=True, help="Client name")

    remove_client_parser = subparsers.add_parser("remove-client", help="删除客户端")
    remove_client_parser.add_argument("--name", required=True, help="Client name")

    subparsers.add_parser("status", help="查看服务状态和配置摘要")
    subparsers.add_parser("uninstall", help="移除服务和规则")

    return parser


def run(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    configure_logging(args.verbose)

    app = Application()

    try:
        if args.command == "install":
            app.install()
            logger.info("Install completed.")
        elif args.command == "add-client":
            app.add_client(args.name)
            logger.info("Client added: %s", args.name)
        elif args.command == "remove-client":
            app.remove_client(args.name)
            logger.info("Client removed: %s", args.name)
        elif args.command == "status":
            payload = {
                "service_status": app.status(),
                "config_summary": {
                    "interface": "wg0",
                    "managed_by": "wg-ocd",
                    "mode": "mvp-stub",
                },
            }
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        elif args.command == "uninstall":
            app.uninstall()
            logger.info("Uninstall completed.")
        else:
            parser.error("Unknown command")
            return 2

        return 0
    except WGOCDError as exc:
        logger.error("Operation failed: %s", exc)
        return 1
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected error: %s", exc)
        return 1


def main() -> None:
    """Console-script friendly wrapper."""
    raise SystemExit(run())


if __name__ == "__main__":
    main()
