"""Config templates and rendering helpers."""

from __future__ import annotations

from pathlib import Path
from string import Template

TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "templates"


def render_template(template_name: str, context: dict[str, str]) -> str:
    """Render a config template from disk."""
    template_path = TEMPLATE_DIR / template_name
    content = template_path.read_text(encoding="utf-8")
    return Template(content).safe_substitute(context)
