from ranq.analysis.framework import detect
from ranq.generators.framework import guide, robots_ts, sitemap_ts
from ranq.models import PageData


def _page(html: str, headers: dict[str, str] | None = None) -> PageData:
    p = PageData(url="https://s.test/", final_url="https://s.test/", status=200)
    p.html, p.headers = html, headers or {}
    return p


def test_detect_frameworks() -> None:
    app = _page('<script src="/_next/static/a.js"></script><script>self.__next_f.push([])</script>')
    assert detect(app).key == "nextjs-app"  # type: ignore[union-attr]
    pages = _page('<script id="__NEXT_DATA__" type="application/json">{}</script>')
    assert detect(pages).key == "nextjs-pages"  # type: ignore[union-attr]
    wp = _page('<meta name="generator" content="WordPress 6.8"><link href="/wp-content/x.css">')
    assert detect(wp).name == "WordPress"  # type: ignore[union-attr]
    assert detect(_page('<meta name="generator" content="Hugo 0.140">')).key == "hugo"  # type: ignore[union-attr]
    assert detect(_page("<p>plain</p>")) is None


def test_robots_ts_keeps_rules() -> None:
    txt = (
        "# comment\nUser-agent: *\nDisallow: /private/\n\n"
        "User-agent: GPTBot\nUser-agent: ClaudeBot\nAllow: /\n\n"
        "User-agent: CCBot\nDisallow: /\n\nSitemap: https://s.test/sitemap.xml\n"
    )
    ts = robots_ts(txt)
    assert '{ userAgent: "*", disallow: "/private/" },' in ts
    assert '{ userAgent: ["GPTBot", "ClaudeBot"], allow: "/" },' in ts
    assert '{ userAgent: "CCBot", disallow: "/" },' in ts
    assert 'sitemap: "https://s.test/sitemap.xml",' in ts
    assert '{ userAgent: "*", allow: "/" }' in robots_ts("User-agent: *\nDisallow:\n")
    both = robots_ts("User-agent: *\nAllow: /\n\nUser-agent: GPTBot\nAllow: /\n")
    assert (
        '{ userAgent: "*", allow: "/" },' in both and '{ userAgent: "GPTBot", allow: "/" },' in both
    )


def test_sitemap_ts_and_guide() -> None:
    ts = sitemap_ts([("https://s.test/", None), ("https://s.test/work", "2026-06-01")])
    assert '["https://s.test/work", "2026-06-01"],' in ts and "new Date()" not in ts
    nextjs = detect(_page("<script>self.__next_f.push([])</script>"))
    assert nextjs is not None and "app/robots.ts" in guide(nextjs)
