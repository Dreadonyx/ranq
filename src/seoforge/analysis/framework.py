"""Detect the site's framework or platform from its HTML and headers, so fixes can say where
each file goes (app/robots.ts in Next.js, static/ in Hugo, an SEO plugin in WordPress...)."""

from __future__ import annotations

import re
from dataclasses import dataclass

from seoforge.models import PageData

GENERATOR_RE = re.compile(r"<meta[^>]+name=[\"']generator[\"'][^>]+content=[\"']([^\"']+)", re.I)


@dataclass(slots=True)
class Framework:
    key: str  # stable id used by the fix generator, e.g. "nextjs-app"
    name: str  # display name, e.g. "Next.js (App Router)"
    evidence: str


# (key, name, needles in HTML, generator prefix) in priority order: the more specific first.
SIGNATURES: list[tuple[str, str, tuple[str, ...], str | None]] = [
    ("nextjs-app", "Next.js (App Router)", ("self.__next_f",), None),
    ("nextjs-pages", "Next.js (Pages Router)", ("__NEXT_DATA__",), None),
    ("nextjs-app", "Next.js", ("/_next/static/",), None),
    ("nuxt", "Nuxt", ("__NUXT__", "/_nuxt/"), "Nuxt"),
    ("astro", "Astro", ("astro-island", "/_astro/"), "Astro"),
    ("sveltekit", "SvelteKit", ("__sveltekit", "data-sveltekit"), None),
    ("remix", "Remix / React Router", ("__remixContext", "__reactRouterContext"), None),
    ("gatsby", "Gatsby", ("___gatsby",), "Gatsby"),
    ("docusaurus", "Docusaurus", ("__docusaurus",), "Docusaurus"),
    ("wordpress", "WordPress", ("/wp-content/", "/wp-includes/"), "WordPress"),
    ("shopify", "Shopify", ("cdn.shopify.com",), None),
    ("wix", "Wix", ("static.wixstatic.com",), "Wix"),
    ("squarespace", "Squarespace", ("static1.squarespace.com",), None),
    ("webflow", "Webflow", ("data-wf-site",), "Webflow"),
    ("framer", "Framer", ("framerusercontent.com",), "Framer"),
    ("ghost", "Ghost", (), "Ghost"),
    ("hugo", "Hugo", (), "Hugo"),
    ("jekyll", "Jekyll", (), "Jekyll"),
    ("eleventy", "Eleventy", (), "Eleventy"),
]


def detect(page: PageData | None) -> Framework | None:
    if page is None or not page.html:
        return None
    html = page.html
    match = GENERATOR_RE.search(html[:20000])
    generator = match.group(1) if match else ""
    vary = page.headers.get("vary", "").lower()
    for key, name, needles, gen in SIGNATURES:
        if gen and generator.lower().startswith(gen.lower()):
            return Framework(key, name, f'<meta name="generator" content="{generator}">')
        hit = next((n for n in needles if n in html), None)
        if hit:
            if key == "nextjs-app" and name == "Next.js" and "next-router-state-tree" not in vary:
                return Framework("nextjs", "Next.js", f"'{hit}' in the HTML")
            return Framework(key, name, f"'{hit}' in the HTML")
    if "rsc" in vary and "next-router" in vary:
        return Framework("nextjs-app", "Next.js (App Router)", f"Vary: {vary}")
    return None
