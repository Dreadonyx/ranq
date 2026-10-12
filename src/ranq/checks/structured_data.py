"""Structured data checks (JSON-LD)."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterator

from ranq import sources
from ranq.analysis import pagetype as pt
from ranq.analysis.structured_data import StructuredDataReport, invisible_faq_questions
from ranq.checks.base import AuditContext, check
from ranq.models import Category, Effort, Issue, Severity

SD = Category.STRUCTURED_DATA


def _report(ctx: AuditContext) -> StructuredDataReport | None:
    return ctx.extras.get("structured_data")


@check("structured-data-validity", SD)
def validity(ctx: AuditContext) -> Iterator[Issue]:
    report = _report(ctx)
    if report is None:
        return
    parse = {p.url: p.parse_errors for p in report.pages if p.parse_errors}
    if parse:
        yield Issue(
            "jsonld-invalid-json",
            f"{len(parse)} page(s) contain JSON-LD that does not parse",
            Severity.HIGH,
            SD,
            "Search engines silently ignore JSON-LD blocks with syntax errors.",
            "Fix the JSON (trailing commas, unescaped quotes, comments are common causes) and "
            "re-test with https://validator.schema.org/.",
            urls=sorted(parse),
            evidence=parse,
            source=sources.SD_GENERAL,
        )
    errors: dict[str, list[str]] = defaultdict(list)
    warnings: dict[str, list[str]] = defaultdict(list)
    for page in report.pages:
        for item in page.items:
            for problem in item.problems:
                target = errors if problem.level == "error" else warnings
                target[page.url].append(f"{problem.type}: {problem.message}")
    if errors:
        yield Issue(
            "jsonld-missing-required",
            f"{len(errors)} page(s) have structured data missing required properties",
            Severity.HIGH,
            SD,
            "Required properties are missing, so the page is not eligible for that rich result.",
            "Add the listed properties using real values from the page (`ranq fix` emits "
            "templates; never mark up content that is not visible to users).",
            urls=sorted(errors),
            evidence={k: sorted(set(v)) for k, v in errors.items()},
            source=sources.SD_GALLERY,
        )
    if warnings:
        yield Issue(
            "jsonld-missing-recommended",
            f"{len(warnings)} page(s) lack recommended structured data properties",
            Severity.LOW,
            SD,
            "Recommended properties make entities more complete for search engines and AI systems.",
            "Add the listed properties where you have truthful values.",
            urls=sorted(warnings),
            evidence={k: sorted(set(v)) for k, v in warnings.items()},
            source=sources.SD_GALLERY,
        )


@check("structured-data-coverage", SD)
def coverage(ctx: AuditContext) -> Iterator[Issue]:
    report = _report(ctx)
    if report is None:
        return
    by_url = {p.url: p for p in report.pages}

    def types(url: str) -> set[str]:
        return by_url[url].types if url in by_url else set()

    home = by_url.get(ctx.crawl.start_url)
    site_types = {t for p in report.pages for t in p.types}
    if home is not None and not ({"Organization", "LocalBusiness", "Person"} & site_types):
        yield Issue(
            "no-organization-schema",
            "No Organization / LocalBusiness / Person markup on the site",
            Severity.MEDIUM,
            SD,
            "Entity markup (name, logo, sameAs profiles) helps search engines and AI systems "
            "connect your site to your brand's knowledge graph entity.",
            "Add Organization (or LocalBusiness/Person) JSON-LD to the homepage with name, url, "
            "logo and sameAs links (`ranq fix`).",
            urls=[ctx.crawl.start_url],
            source=f"{sources.G}/appearance/structured-data/organization",
        )
    if home is not None and "WebSite" not in site_types:
        yield Issue(
            "no-website-schema",
            "No WebSite markup",
            Severity.LOW,
            SD,
            "WebSite markup with name (and alternateName) influences the site name shown in "
            "Google results.",
            "Add WebSite JSON-LD with name and url to the homepage.",
            urls=[ctx.crawl.start_url],
            source=f"{sources.G}/appearance/site-names",
        )
    claims_other: dict[str, list[str]] = {}
    for page in ctx.pages:
        own = {u.rstrip("/") for u in (page.url, page.final_url, page.canonical or page.url)}
        for node in pt.top_nodes(page):
            url = node.get("url")
            if (
                pt.node_types(node) & set(pt.WEBPAGE_TYPES)
                and isinstance(url, str)
                and url.rstrip("/") not in own
            ):
                claims_other.setdefault(page.url, []).append(url)
    if claims_other:
        yield Issue(
            "jsonld-webpage-wrong-url",
            f"{len(claims_other)} page(s) carry a WebPage node describing a different URL",
            Severity.MEDIUM,
            SD,
            "The page's JSON-LD includes a WebPage (or AboutPage, CollectionPage...) whose url "
            "is another page, usually because the home page's node sits in a shared layout. "
            "Engines may treat this page as a duplicate of that URL or ignore the markup.",
            "Keep only Organization/WebSite in the shared layout and output the WebPage node "
            "per page with its own url (`ranq fix` writes one @graph per page).",
            effort=Effort.LOW,
            urls=sorted(claims_other),
            evidence=claims_other,
            source=sources.SD_GENERAL,
        )
    articles = sorted(
        p.url
        for p in ctx.pages
        if p.is_indexable and pt.is_article(p) and "Article" not in types(p.url)
    )
    if articles:
        yield Issue(
            "article-no-schema",
            f"{len(articles)} article-like page(s) lack Article markup",
            Severity.MEDIUM,
            SD,
            "Article markup states headline, author and dates explicitly - signals both search "
            "engines and AI answer engines use for attribution and freshness.",
            "Add Article/BlogPosting JSON-LD with headline, author (name + url), datePublished, "
            "dateModified and image.",
            urls=articles,
            source=f"{sources.G}/appearance/structured-data/article",
        )
    products = sorted(
        p.url
        for p in ctx.pages
        if p.is_indexable and pt.is_product(p) and "Product" not in types(p.url)
    )
    if products:
        yield Issue(
            "product-no-schema",
            f"{len(products)} product-like page(s) lack Product markup",
            Severity.MEDIUM,
            SD,
            "Product markup with offers/price enables product rich results and merchant listings.",
            "Add Product JSON-LD with name, image, description, brand and offers (price, "
            "priceCurrency, availability).",
            urls=products,
            source=f"{sources.G}/appearance/structured-data/product",
        )
    deep = sorted(
        p.url
        for p in ctx.pages
        if p.is_indexable
        and p.url.rstrip("/").count("/") >= 4
        and "BreadcrumbList" not in types(p.url)
    )
    if deep:
        yield Issue(
            "breadcrumb-missing",
            f"{len(deep)} nested page(s) lack BreadcrumbList markup",
            Severity.LOW,
            SD,
            "Breadcrumb markup shows the page's position in the site hierarchy in results.",
            "Add BreadcrumbList JSON-LD mirroring visible breadcrumbs (`ranq fix`).",
            urls=deep,
            source=f"{sources.G}/appearance/structured-data/breadcrumb",
        )
    pages = {p.url: p for p in ctx.pages}
    invisible = {
        s.url: qs
        for s in report.pages
        if s.url in pages and (qs := invisible_faq_questions(pages[s.url], s))
    }
    if invisible:
        yield Issue(
            "faq-not-visible",
            f"{len(invisible)} page(s) mark up FAQ questions not visible on the page",
            Severity.HIGH,
            SD,
            "Google's structured data policies require marked-up content to be visible to users. "
            "Hidden markup can trigger a manual action.",
            "Show each question and answer on the page, or remove them from the markup.",
            urls=sorted(invisible),
            evidence=invisible,
            source=sources.SD_GENERAL,
        )
    faq_howto = sorted(p.url for p in report.pages if {"FAQPage", "HowTo"} & p.types)
    if faq_howto:
        yield Issue(
            "faq-howto-limited",
            "FAQ/HowTo markup has limited Google rich result support",
            Severity.INFO,
            SD,
            "Since 2023 Google shows FAQ rich results only for well-known government and health "
            "sites and no longer shows HowTo rich results. The markup stays valid and can still "
            "help other engines and answer extraction - keep it if it is accurate.",
            "No action required; do not expect FAQ/HowTo rich results in Google.",
            effort=Effort.LOW,
            urls=faq_howto,
            source=sources.FAQ_HOWTO_CHANGES,
        )
    microdata_only = sorted(
        p.url for p in report.pages if (p.has_microdata or p.has_rdfa) and not p.items
    )
    if microdata_only:
        yield Issue(
            "microdata-only",
            f"{len(microdata_only)} page(s) use only Microdata/RDFa",
            Severity.INFO,
            SD,
            "Microdata and RDFa are valid, but Ranq validates JSON-LD only, and JSON-LD is "
            "Google's recommended format.",
            "Consider migrating to JSON-LD for easier maintenance.",
            urls=microdata_only,
            source=sources.SD_GENERAL,
        )
