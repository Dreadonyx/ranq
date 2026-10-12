"""Crawled content is attacker-controlled: rendering it must not produce script execution."""

import json
import re

from seoforge.checks.base import AuditContext
from seoforge.config import Config
from seoforge.crawler.crawler import CrawlResult
from seoforge.geo.entity import analyze
from seoforge.models import Category, Issue, PageData, Severity
from seoforge.report.builder import Report
from seoforge.report.render import render_html, render_markdown

EVIL = '<script>alert("x")</script>'
JS_URL = "javascript://www.linkedin.com/%0aalert(document.domain)"


def _report() -> Report:
    home = PageData(url="https://s.test/", final_url="https://s.test/", status=200)
    home.content_type = "text/html"
    home.json_ld = [
        json.dumps(
            {
                "@context": "https://schema.org",
                "@type": "Organization",
                "name": EVIL,
                "sameAs": [JS_URL],
            }
        )
    ]
    crawl = CrawlResult(site="https://s.test", start_url="https://s.test/", pages={home.url: home})
    ctx = AuditContext(config=Config(), crawl=crawl)
    issue = Issue(
        "x",
        f"Title {EVIL}",
        Severity.HIGH,
        Category.CRAWL,
        EVIL,
        EVIL,
        urls=[f"https://s.test/{EVIL}"],
        evidence={"k": f"</pre>{EVIL}"},
        source=JS_URL,
    )
    from seoforge.geo.analysis import GeoReport

    geo = GeoReport(entity=analyze(ctx.crawl, ctx.config.entity))
    return Report(
        site="https://s.test",
        generated_at="now",
        stats={"html_pages": 1},
        issues=[issue],
        plan={"30": [], "60": [], "90": []},
        score=50,
        pages=[
            {
                "url": f"https://s.test/{EVIL}",
                "score": 1,
                "issues": [{"check_id": "x", "title": EVIL, "severity": "high"}],
            }
        ],
        extras={"geo": geo.to_dict()},
    )


def test_html_report_escapes_crawled_content() -> None:
    html = render_html(_report())
    assert EVIL not in html
    assert not re.search(r"href\s*=\s*[\"']?\s*javascript:", html, re.I)


def test_markdown_report_does_not_link_javascript() -> None:
    assert "javascript:" not in render_markdown(_report()).lower()


def test_meta_suggestion_comments_cannot_be_closed() -> None:
    from seoforge.generators.meta import MetaSuggestion

    s = MetaSuggestion(url="https://s.test/a--><script>x</script>", reasons=["r"], todo=["t-->"])
    out = s.html()
    assert "--><script>" not in out and out.count("-->") == 2  # only our two closers
