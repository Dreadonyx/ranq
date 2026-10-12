"""Render a Report to HTML (standalone dashboard), Markdown and JSON."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlsplit

from jinja2 import Environment, PackageLoader, select_autoescape

from ranq.report.builder import Report

_env = Environment(
    loader=PackageLoader("ranq", "report/templates"),
    autoescape=select_autoescape(["html", "j2"]),
    trim_blocks=True,
    lstrip_blocks=True,
)


def _truncate_list(value: list[str], n: int = 25) -> list[str]:
    return value[:n]


def safe_href(url: object) -> str:
    """Only http(s) URLs may become links: crawled values such as sameAs are attacker-controlled
    and a javascript: URL would run in the report when clicked."""
    text = str(url or "").strip()
    return text if urlsplit(text).scheme.lower() in ("http", "https") else "#"


_env.filters["first_n"] = _truncate_list
_env.filters["safe_href"] = safe_href
_env.filters["tojson_pretty"] = lambda v: json.dumps(v, indent=2, ensure_ascii=False, default=str)


def render_json(report: Report) -> str:
    return json.dumps(report.to_dict(), indent=2, ensure_ascii=False, default=str)


def render_markdown(report: Report) -> str:
    md_env = Environment(
        loader=PackageLoader("ranq", "report/templates"),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    md_env.filters["first_n"] = _truncate_list
    md_env.filters["safe_href"] = safe_href
    return md_env.get_template("report.md.j2").render(r=report, d=report.to_dict())


def render_html(report: Report) -> str:
    return _env.get_template("report.html.j2").render(r=report, d=report.to_dict())


def write_reports(report: Report, out_dir: str | Path, formats: list[str]) -> list[Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    written = []
    renderers = {
        "html": ("report.html", render_html),
        "md": ("report.md", render_markdown),
        "json": ("report.json", render_json),
    }
    for fmt in formats:
        name, fn = renderers[fmt]
        path = out / name
        path.write_text(fn(report), encoding="utf-8")
        written.append(path)
    return written
