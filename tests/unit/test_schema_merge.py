import json

from seoforge.config import EntityConfig
from seoforge.crawler.crawler import CrawlResult
from seoforge.generators.schema import build_graphs, generate_all
from seoforge.models import PageData

SITE = "https://nk.test"
# The real-world pattern: one @graph in the shared layout, so every page repeats the home
# page's WebPage node.
LAYOUT = {
    "@context": "https://schema.org",
    "@graph": [
        {
            "@type": "Organization",
            "@id": f"{SITE}/#organization",
            "name": "NK",
            "address": {"@type": "PostalAddress", "addressLocality": "Chennai"},
            "employee": [{"@type": "Person", "name": "A", "jobTitle": "CEO"}],
            "sameAs": ["https://www.linkedin.com/company/nk"],
        },
        {"@type": "WebSite", "@id": f"{SITE}/#website", "url": SITE, "name": "NK"},
        {"@type": "WebPage", "@id": f"{SITE}/#webpage", "url": SITE, "name": "Home"},
        {
            "@type": "Service",
            "name": "Web Development",
            "provider": {"@id": f"{SITE}/#organization"},
        },
    ],
}


def _page(path: str, title: str, extra: list[dict] | None = None) -> PageData:
    url = SITE + path
    p = PageData(url=url, final_url=url, status=200, content_type="text/html")
    p.title = title
    p.json_ld = [json.dumps(LAYOUT)] + [json.dumps(e) for e in extra or []]
    return p


def _graphs() -> dict[str | None, list[dict]]:
    home = _page("/", "Home")
    work = _page("/work", "Our Work </script><b>", [{"@type": "Event", "name": "Launch"}])
    crawl = CrawlResult(site=SITE, start_url=f"{SITE}/", pages={home.url: home, work.url: work})
    graphs = build_graphs(crawl, generate_all(crawl, EntityConfig(name="NK")))
    return {g.url: g for g in graphs}  # type: ignore[misc]


def test_layout_graph_is_merged_not_duplicated() -> None:
    graphs = _graphs()
    site = graphs[None].nodes
    org = next(n for n in site if n["@type"] == "Organization")
    assert (
        org["employee"][0]["jobTitle"] == "CEO" and org["address"]["addressLocality"] == "Chennai"
    )
    assert [n["@type"] for n in site].count("Service") == 1  # repeated layout node, kept once
    assert all(n["@type"] != "WebPage" for n in site)


def test_each_page_gets_its_own_webpage_node() -> None:
    graphs = _graphs()
    work = graphs[f"{SITE}/work"]
    pages = [n for n in work.nodes if n["@type"] == "WebPage"]
    assert [p["url"] for p in pages] == [f"{SITE}/work"]  # the home WebPage is not copied
    assert any(n["@type"] == "Event" for n in work.nodes)  # page-only node carried over
    assert work.replaces_existing
    home_page = next(n for n in graphs[f"{SITE}/"].nodes if n["@type"] == "WebPage")
    assert home_page["@id"] == f"{SITE}/#webpage" and home_page["about"]["@id"].endswith(
        "#organization"
    )


def test_script_tag_cannot_be_closed_by_crawled_text() -> None:
    tag = _graphs()[f"{SITE}/work"].script_tag()
    assert tag.count("</script>") == 1 and "<\\/script>" in tag


def test_wrong_webpage_url_is_flagged() -> None:
    from seoforge.checks.base import AuditContext
    from seoforge.checks.structured_data import coverage
    from seoforge.config import Config

    home = _page("/", "Home")
    work = _page("/work", "Work")
    crawl = CrawlResult(site=SITE, start_url=f"{SITE}/", pages={home.url: home, work.url: work})
    ctx = AuditContext(config=Config(), crawl=crawl)
    from seoforge.analysis.structured_data import analyze

    ctx.extras["structured_data"] = analyze(ctx.pages)
    issue = next(i for i in coverage(ctx) if i.check_id == "jsonld-webpage-wrong-url")
    assert issue.urls == [f"{SITE}/work"] and issue.evidence[f"{SITE}/work"] == [SITE]
