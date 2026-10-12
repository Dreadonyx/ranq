"""`seoforge fix`: generate ready-to-paste files, and optionally apply some of them to a local
site directory - only after showing a diff and getting confirmation for each file."""

from __future__ import annotations

import difflib
import json
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from seoforge.checks.base import AuditContext
from seoforge.generators import meta, redirects, schema, sitemap
from seoforge.generators.headers import render_security_headers
from seoforge.generators.robots import generate_robots
from seoforge.geo.ai_bots import resolve_policy
from seoforge.urls import path_of


@dataclass(slots=True)
class FixFile:
    path: str  # relative path inside the output directory
    content: str
    description: str
    deploy_path: str | None = None  # where it goes in a site root (None = paste manually)


@dataclass(slots=True)
class FixBundle:
    files: list[FixFile] = field(default_factory=list)

    def add(self, path: str, content: str, description: str, deploy: str | None = None) -> None:
        self.files.append(FixFile(path, content, description, deploy))

    def write(self, out_dir: Path) -> list[Path]:
        written = []
        for f in self.files:
            target = safe_join(out_dir, f.path)
            if target is None:
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(f.content, encoding="utf-8")
            written.append(target)
        index = [
            "# SEOForge fixes",
            "",
            "Generated files. Review every file before deploying.",
            "",
            "| File | What it is | Deploy to |",
            "|---|---|---|",
        ]
        index += [
            f"| `{f.path}` | {f.description} | {f'`/{f.deploy_path}`' if f.deploy_path else 'paste manually'} |"
            for f in self.files
        ]
        (out_dir / "INDEX.md").write_text("\n".join(index) + "\n", encoding="utf-8")
        return written


def safe_join(root: Path, relative: str) -> Path | None:
    """Join a crawl-derived relative path under root; None if it would escape root."""
    base = root.resolve()
    target = (base / relative.lstrip("/")).resolve()
    return target if target == base or base in target.parents else None


def _slug(url: str) -> str:
    path = path_of(url).strip("/") or "home"
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in path)[:120]


def build_bundle(
    ctx: AuditContext,
    *,
    preset: str | None = None,
    redirect_map: Path | None = None,
    extra: Callable[[AuditContext, FixBundle], None] | None = None,
) -> FixBundle:
    crawl, config = ctx.crawl, ctx.config
    bundle = FixBundle()

    maps = sitemap.generate_sitemaps(crawl)
    for name, xml in maps.items():
        bundle.add(
            name, xml, f"XML sitemap of {xml.count('<loc>')} indexable canonical URL(s)", name
        )
    sitemap_url = f"{crawl.site}/sitemap.xml"

    chosen = preset or config.geo.ai_bot_preset
    policy = resolve_policy(chosen, config.geo.ai_bots)
    bundle.add(
        "robots.txt",
        generate_robots(crawl.robots, policy, [sitemap_url], chosen),
        f"robots.txt with your existing rules + AI crawler policy '{chosen}'",
        "robots.txt",
    )

    docs = schema.generate_all(crawl, config.entity)
    todo: dict[str, list[str]] = {
        f"{doc.kind} {doc.url or doc.data.get('name')}": doc.todo for doc in docs if doc.todo
    }
    for graph in schema.build_graphs(crawl, docs):
        if graph.url is None:
            name = "jsonld/site.graph.html"
            what = (
                f"Site-wide JSON-LD ({', '.join(graph.kinds)}) for the shared layout, on every page"
            )
        else:
            name = f"jsonld/{_slug(graph.url)}.graph.html"
            what = f"JSON-LD ({', '.join(graph.kinds)}) for {graph.url}"
        if graph.replaces_existing:
            what += " - replaces the JSON-LD already there (existing nodes are merged in)"
        bundle.add(name, graph.script_tag(), what)
    if todo:
        bundle.add(
            "jsonld/TODO.json",
            json.dumps(todo, indent=2) + "\n",
            "Values SEOForge could not find - fill these in yourself",
        )

    suggestions = meta.generate_meta(crawl, config.entity.name)
    if suggestions:
        body = "\n".join(s.html() for s in suggestions)
        bundle.add("meta-tags.html", body, f"Suggested <head> tags for {len(suggestions)} page(s)")

    rules = redirects.load_map(redirect_map) if redirect_map else []
    plan = redirects.build_plan(crawl, rules)
    for name, content in redirects.render_all(plan).items():
        deploy = None
        if name.endswith("netlify/_redirects"):
            deploy = "_redirects"
        bundle.add(
            name, content, f"{len(plan.rules)} redirect rule(s) - {name.split('/')[1]}", deploy
        )

    home = crawl.pages.get(crawl.start_url) or next(iter(crawl.html_pages), None)
    bundle.add(
        "security-headers.md",
        render_security_headers(home.headers if home else {}),
        "Security headers to add or strengthen (keeps stronger live values)",
    )
    if extra is not None:
        extra(ctx, bundle)
    return bundle


ConfirmFn = Callable[[str, str], bool]


def diff_for(path: Path, new: str) -> str:
    old = path.read_text(encoding="utf-8") if path.exists() else ""
    return "".join(
        difflib.unified_diff(
            old.splitlines(keepends=True),
            new.splitlines(keepends=True),
            fromfile=f"a/{path.name}" if old else "/dev/null",
            tofile=f"b/{path.name}",
        )
    )


def apply_bundle(bundle: FixBundle, site_root: Path, confirm: ConfirmFn) -> list[Path]:
    """Write deployable files into a local site directory, one confirmation per changed file."""
    changed = []
    for f in bundle.files:
        if not f.deploy_path:
            continue
        target = safe_join(site_root, f.deploy_path)
        if target is None:
            continue  # never write outside the site root
        diff = diff_for(target, f.content)
        if not diff:
            continue
        if confirm(str(target), diff):
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(f.content, encoding="utf-8")
            changed.append(target)
    return changed
