"""CLI entrypoint for wg-ocd."""

from __future__ import annotations

import argparse
import json
import logging
import sys

from wg_ocd.app import Application
from wg_ocd.exceptions import WGOCDError
from wg_ocd.utils.logging_utils import configure_logging

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="wg-ocd",
        description="One-click WireGuard VPN deployment tool",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("install", help="Install and initialize WireGuard server")

    add_client_parser = subparsers.add_parser("add-client", help="Add a WireGuard client")
    add_client_parser.add_argument("name", help="Client name")

    remove_client_parser = subparsers.add_parser("remove-client", help="Remove a WireGuard client")
    remove_client_parser.add_argument("name", help="Client name")

    subparsers.add_parser("status", help="Show current WireGuard service status")
    subparsers.add_parser("uninstall", help="Uninstall WireGuard configuration managed by wg-ocd")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    configure_logging(verbose=args.verbose)

    app = Application()

    try:
        if args.command == "install":
            app.install()
            logger.info("Install completed")
        elif args.command == "add-client":
            app.add_client(args.name)
            logger.info("Client added: %s", args.name)
        elif args.command == "remove-client":
            app.remove_client(args.name)
            logger.info("Client removed: %s", args.name)
        elif args.command == "status":
            status = app.status()
            print(json.dumps(status, ensure_ascii=False, indent=2))
        elif args.command == "uninstall":
            app.uninstall()
            logger.info("Uninstall completed")
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


if __name__ == "__main__":
    sys.exit(main())
