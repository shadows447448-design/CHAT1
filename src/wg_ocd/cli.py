"""Compatibility CLI entrypoint to reuse app.main parser."""

from __future__ import annotations

from app.main import run


def main(argv: list[str] | None = None) -> int:
    return run(argv)


if __name__ == "__main__":
    raise SystemExit(main())
