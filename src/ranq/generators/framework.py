"""Framework-specific placement: a guide saying where each generated file goes in the detected
stack, plus native files where the framework has them (Next.js App Router robots.ts,
sitemap.ts and a JSON-LD component)."""

from __future__ import annotations

import json
from collections.abc import Iterable

from ranq.analysis.framework import Framework

# key -> rows of (what, where / how). Keys missing here fall back to GENERIC.
GENERIC = {
    "robots": "Site root: `/robots.txt`",
    "sitemap": "Site root: `/sitemap.xml`",
    "llms": "Site root: `/llms.txt`, `/llms-full.txt` (and the IndexNow key file)",
    "site_graph": "Inside `<head>` of the shared layout/template, on every page",
    "page_graph": "Inside `<head>` (or `<body>`) of that page only",
    "meta": "Each page's `<head>`",
    "headers": "Your host or server config (see security-headers.md)",
    "redirects": "Your host or server config (see redirects/)",
}
GUIDES: dict[str, dict[str, str]] = {
    "nextjs-app": {
        "robots": "`app/robots.ts` (generated in `nextjs/app/robots.ts`); delete "
        "`public/robots.txt` if both exist",
        "sitemap": "`app/sitemap.ts` (generated in `nextjs/app/sitemap.ts`)",
        "llms": "`public/llms.txt`, `public/llms-full.txt`, `public/<indexnow-key>.txt`",
        "site_graph": "`app/layout.tsx`: `<JsonLd data={...} />` with the contents of "
        "`jsonld/site.graph.html` (component in `nextjs/components/JsonLd.tsx`)",
        "page_graph": "Each route's `page.tsx`: `<JsonLd data={...} />` with that page's graph",
        "meta": "`export const metadata` / `generateMetadata` per route: title, description, "
        "`alternates.canonical` and a full `openGraph` (child openGraph replaces the parent's, "
        "so always set url, title and description); set `metadataBase` in the root layout",
        "headers": "`headers()` in next.config, or `vercel.json` on Vercel",
        "redirects": "`redirects()` in next.config",
    },
    "nextjs-pages": {
        "robots": "`public/robots.txt` (or the next-sitemap package)",
        "sitemap": "`public/sitemap.xml` (or next-sitemap)",
        "llms": "`public/llms.txt`, `public/llms-full.txt`",
        "site_graph": "`pages/_app.tsx` inside `<Head>` from next/head",
        "page_graph": "Each page component inside `<Head>`",
        "meta": "`<Head>` in each page (title, description, canonical, og:*)",
        "headers": "`headers()` in next.config.js",
        "redirects": "`redirects()` in next.config.js",
    },
    "nuxt": {
        "robots": "`public/robots.txt`, or `@nuxtjs/robots` (Nuxt SEO) config",
        "sitemap": "`@nuxtjs/sitemap`, or `public/sitemap.xml`",
        "llms": "`public/llms.txt`, `public/llms-full.txt`",
        "site_graph": "`app.vue`: `useHead({ script: [{ type: 'application/ld+json', "
        "innerHTML: JSON.stringify(graph) }] })`",
        "page_graph": "Same `useHead` call in each page component",
        "meta": "`useSeoMeta()` per page",
        "headers": "`routeRules` headers in nuxt.config",
        "redirects": "`routeRules` redirect in nuxt.config",
    },
    "astro": {
        "robots": "`public/robots.txt`",
        "sitemap": "`@astrojs/sitemap` integration, or `public/sitemap.xml`",
        "llms": "`public/llms.txt`, `public/llms-full.txt`",
        "site_graph": 'Base layout: `<script type="application/ld+json" '
        "set:html={JSON.stringify(graph)} />`",
        "page_graph": "Pass the page graph to the layout as a prop and render it the same way",
        "meta": "Layout `<head>` driven by per-page props",
        "headers": "Host config (`_headers` on Netlify/Cloudflare, `vercel.json` on Vercel)",
        "redirects": "`redirects` in astro.config",
    },
    "sveltekit": {
        "robots": "`static/robots.txt`",
        "sitemap": "`static/sitemap.xml` or a `src/routes/sitemap.xml/+server.ts` endpoint",
        "llms": "`static/llms.txt`, `static/llms-full.txt`",
        "site_graph": "`src/routes/+layout.svelte`: `<svelte:head>{@html "
        '`<script type="application/ld+json">${json}</script>`}</svelte:head>`',
        "page_graph": "Same pattern in each `+page.svelte`",
        "meta": "`<svelte:head>` per page",
        "headers": "`setHeaders` in `hooks.server.ts` or load functions",
        "redirects": "`redirect()` in hooks or load functions",
    },
    "remix": {
        "robots": "`public/robots.txt` or a `robots[.]txt` resource route",
        "sitemap": "`public/sitemap.xml` or a `sitemap[.]xml` resource route",
        "llms": "`public/llms.txt`, `public/llms-full.txt`",
        "site_graph": "`app/root.tsx` inside `<head>`",
        "page_graph": "Each route component",
        "meta": "`meta` export per route",
        "headers": "`headers` export or your host",
        "redirects": "`redirect()` in loaders, or your host",
    },
    "gatsby": {
        "robots": "`static/robots.txt` (or gatsby-plugin-robots-txt)",
        "sitemap": "gatsby-plugin-sitemap",
        "llms": "`static/llms.txt`, `static/llms-full.txt`",
        "site_graph": "Shared SEO component used by every page's `Head` export",
        "page_graph": "Each page's `Head` export",
        "meta": "`Head` export per page",
        "headers": "Host config",
        "redirects": "`createRedirect` in gatsby-node or host config",
    },
    "docusaurus": {
        "robots": "`static/robots.txt`",
        "sitemap": "Built in (preset-classic sitemap plugin)",
        "llms": "`static/llms.txt`, `static/llms-full.txt`",
        "site_graph": "`headTags` in docusaurus.config",
        "page_graph": "`<Head>` from @docusaurus/Head in the page",
        "meta": "Front matter (title, description) per doc",
        "headers": "Host config",
        "redirects": "@docusaurus/plugin-client-redirects or host config",
    },
    "wordpress": {
        "robots": "Your SEO plugin's robots.txt editor (Yoast: Tools -> File editor; "
        "Rank Math: General Settings -> Edit robots.txt)",
        "sitemap": "Your SEO plugin generates it; do not upload a static one",
        "llms": "Upload to the web root over SFTP/file manager, or use an llms.txt plugin",
        "site_graph": "Your SEO plugin already outputs Organization/WebSite: fill its settings "
        "instead of pasting a duplicate",
        "page_graph": "Plugin per-page schema settings; paste only nodes the plugin lacks",
        "meta": "SEO plugin per post/page",
        "headers": ".htaccess or a security-headers plugin",
        "redirects": "Redirection plugin or .htaccess",
    },
    "shopify": {
        "robots": "`robots.txt.liquid` theme template",
        "sitemap": "Automatic (/sitemap.xml)",
        "llms": "Shopify cannot serve arbitrary root files; use an app or skip llms.txt",
        "site_graph": "`theme.liquid` inside `<head>`",
        "page_graph": "The matching template or section",
        "meta": "Online Store -> Preferences and each product/page's SEO fields",
        "headers": "Not configurable on Shopify",
        "redirects": "Online Store -> Navigation -> URL Redirects",
    },
}
for _builder in ("wix", "squarespace", "webflow", "framer", "ghost"):
    GUIDES[_builder] = {
        "robots": "The builder's SEO settings (robots.txt editor, if your plan has one)",
        "sitemap": "Automatic",
        "llms": "Only if the builder lets you host root files; otherwise skip llms.txt",
        "site_graph": "Site-wide custom code -> head",
        "page_graph": "Page settings -> custom code / structured data",
        "meta": "Each page's SEO settings",
        "headers": "Usually not configurable",
        "redirects": "The builder's redirect settings",
    }
for _ssg, _dir in (("hugo", "static/"), ("jekyll", "the site root"), ("eleventy", "a passthrough")):
    GUIDES[_ssg] = {
        **GENERIC,
        "robots": f"`robots.txt` in {_dir}",
        "llms": f"`llms.txt`, `llms-full.txt` in {_dir}",
        "site_graph": "The head partial/include used by every page",
        "page_graph": "Front matter + the head partial, per page",
    }

ROWS = [
    ("robots", "robots.txt"),
    ("sitemap", "sitemap.xml"),
    ("llms", "llms.txt / llms-full.txt"),
    ("site_graph", "jsonld/site.graph.html"),
    ("page_graph", "jsonld/<page>.graph.html"),
    ("meta", "meta-tags.html"),
    ("headers", "security-headers.md"),
    ("redirects", "redirects/"),
]


def guide(fw: Framework) -> str:
    rows = GUIDES.get(fw.key, GENERIC)
    lines = [
        f"# Where these files go in {fw.name}",
        "",
        f"Detected from {fw.evidence}. If that is wrong, use the generic paths in INDEX.md.",
        "",
        "| Generated file | Where it goes |",
        "|---|---|",
    ]
    lines += [f"| `{name}` | {rows.get(key, GENERIC[key])} |" for key, name in ROWS]
    return "\n".join(lines) + "\n"


def _ts(value: object) -> str:
    return json.dumps(value, ensure_ascii=False)


def robots_ts(robots_txt: str) -> str:
    """Translate a robots.txt into a Next.js `app/robots.ts` (MetadataRoute.Robots)."""
    groups: list[dict[str, list[str]]] = []
    sitemaps: list[str] = []
    current: dict[str, list[str]] | None = None
    last_agent = False
    for raw in robots_txt.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        key, _, value = line.partition(":")
        key, value = key.strip().lower(), value.strip()
        if key == "user-agent":
            if current is None or not last_agent:
                current = {"agents": [], "allow": [], "disallow": []}
                groups.append(current)
            current["agents"].append(value)
            last_agent = True
            continue
        last_agent = False
        if key == "sitemap":
            sitemaps.append(value)
        elif current is not None and key in ("allow", "disallow") and value:
            current[key].append(value)
    merged: dict[tuple[tuple[str, ...], tuple[str, ...], bool], list[str]] = {}
    for g in groups:
        allow, disallow = tuple(g["allow"]), tuple(g["disallow"])
        if not allow and not disallow:
            allow = ("/",)  # an empty group (or a bare "Disallow:") allows everything
        # Keep "*" on its own so per-bot policies stay visible as a separate rule.
        star = "*" in g["agents"]
        merged.setdefault((allow, disallow, star), []).extend(g["agents"])

    def one_or_many(items: Iterable[str]) -> str:
        items = list(items)
        return _ts(items[0]) if len(items) == 1 else _ts(items)

    rule_lines = []
    for (allow, disallow, _star), agents in merged.items():
        parts = [f"userAgent: {one_or_many(agents)}"]
        if allow:
            parts.append(f"allow: {one_or_many(allow)}")
        if disallow:
            parts.append(f"disallow: {one_or_many(disallow)}")
        rule_lines.append("      { " + ", ".join(parts) + " },")
    out = [
        "// app/robots.ts - generated by Ranq from robots.txt. Review before deploying.",
        'import type { MetadataRoute } from "next";',
        "",
        "export default function robots(): MetadataRoute.Robots {",
        "  return {",
        "    rules: [",
        *rule_lines,
        "    ],",
    ]
    if sitemaps:
        out.append(f"    sitemap: {one_or_many(sitemaps)},")
    out += ["  };", "}", ""]
    return "\n".join(out)


def sitemap_ts(entries: list[tuple[str, str | None]]) -> str:
    """Next.js `app/sitemap.ts` from (url, lastmod) pairs. Dates are the real last-change
    dates found during the crawl; `new Date()` would mark every page changed on every build."""
    rows = "\n".join(f"  [{_ts(url)}, {_ts(lastmod)}]," for url, lastmod in entries)
    return (
        "// app/sitemap.ts - generated by Ranq. Add new pages here, and update a page's\n"
        "// date only when its content really changes.\n"
        'import type { MetadataRoute } from "next";\n'
        "\n"
        "const PAGES: [string, string | null][] = [\n"
        f"{rows}\n"
        "];\n"
        "\n"
        "export default function sitemap(): MetadataRoute.Sitemap {\n"
        "  return PAGES.map(([url, lastModified]) =>\n"
        "    lastModified ? { url, lastModified: new Date(lastModified) } : { url },\n"
        "  );\n"
        "}\n"
    )


JSONLD_COMPONENT = """// components/JsonLd.tsx - generated by Ranq.
// Usage: <JsonLd data={{ "@context": "https://schema.org", "@graph": [...] }} />
export function JsonLd({ data }: { data: object }) {
  return (
    <script
      type="application/ld+json"
      // Escaping "<" keeps any string value from closing the script tag early.
      dangerouslySetInnerHTML={{ __html: JSON.stringify(data).replace(/</g, "\\\\u003c") }}
    />
  );
}
"""
