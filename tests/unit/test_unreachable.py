from seoforge.checks.base import AuditContext
from seoforge.checks.crawl import site_unreachable
from seoforge.config import Config
from seoforge.crawler.crawler import CrawlResult
from seoforge.models import Issue, PageData, Severity
from seoforge.report.builder import health_score


def _ctx(home: PageData | None) -> AuditContext:
    pages = {home.url: home} if home else {}
    crawl = CrawlResult(site="https://s.test", start_url="https://s.test/", pages=pages)
    return AuditContext(config=Config(), crawl=crawl)


def test_dead_deployment_is_critical() -> None:
    home = PageData(url="https://s.test/", final_url="https://s.test/", status=404)
    home.headers = {"x-vercel-error": "DEPLOYMENT_NOT_FOUND", "server": "Vercel"}
    (issue,) = site_unreachable(_ctx(home))
    assert issue.severity == Severity.CRITICAL
    assert "HTTP 404" in issue.title
    assert issue.evidence["https://s.test/"]["x-vercel-error"] == "DEPLOYMENT_NOT_FOUND"


def test_robots_blocked_and_live_site() -> None:
    ctx = _ctx(None)
    ctx.crawl.blocked.append("https://s.test/")
    assert "robots.txt" in next(iter(site_unreachable(ctx))).title
    live = PageData(
        url="https://s.test/", final_url="https://s.test/", status=200, content_type="text/html"
    )
    assert list(site_unreachable(_ctx(live))) == []


def test_empty_crawl_scores_zero() -> None:
    low = Issue("x", "x", Severity.LOW, "crawl", "", "", urls=["https://s.test/"])
    assert health_score([low], 0) == 0
    assert health_score([low], 1) > 90


def test_site_wide_issues_are_not_diluted_by_page_count() -> None:
    about = Issue(
        "eeat-no-about", "x", Severity.MEDIUM, "e-e-a-t", "", "", urls=["https://s.test/"]
    )
    assert about.site_wide
    assert health_score([about], 2) == health_score([about], 200)
    h1 = Issue("h1-missing", "x", Severity.MEDIUM, "on-page", "", "", urls=["https://s.test/a"])
    assert not h1.site_wide
    assert health_score([h1], 2) < health_score([h1], 200)  # one bad page in 200 matters less
    assert Issue("robots-blocks-googlebot", "x", Severity.CRITICAL, "technical", "", "").site_wide


def test_page_scores() -> None:
    from seoforge.report.builder import page_scores

    pages = ["https://s.test/", "https://s.test/a"]
    issues = [
        Issue("eeat-no-about", "about", Severity.MEDIUM, "e-e-a-t", "", "", urls=[pages[0]]),
        Issue("h1-missing", "h1", Severity.MEDIUM, "on-page", "", "", urls=[pages[1]]),
        Issue("thin-content", "thin", Severity.LOW, "on-page", "", "", urls=pages),
    ]
    worst, best = page_scores(issues, pages)
    assert worst["url"] == "https://s.test/a"
    assert [i["check_id"] for i in worst["issues"]] == ["h1-missing", "thin-content"]
    assert best["url"] == "https://s.test/" and [i["check_id"] for i in best["issues"]] == [
        "thin-content"
    ]  # the site-wide About issue is not charged to the home page
    assert worst["score"] < best["score"] < 100


def test_platform_subdomain_flagged() -> None:
    from seoforge.checks.technical import custom_domain, platform_subdomain

    assert platform_subdomain("https://hi-res-lossless-website.vercel.app") == "vercel.app"
    assert platform_subdomain("https://me.github.io/blog/") == "github.io"
    assert platform_subdomain("https://nodekraft.tech") is None
    assert platform_subdomain("https://notvercel.app") is None  # a real domain, not a subdomain
    ctx = _ctx(None)
    ctx.crawl.site = "https://x.vercel.app"
    (issue,) = custom_domain(ctx)
    assert issue.severity == Severity.HIGH and issue.site_wide
    ctx.crawl.site = "https://nodekraft.tech"
    assert list(custom_domain(ctx)) == []
