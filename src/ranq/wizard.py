"""`ranq init` wizard: read the home page once, pre-fill what the site already says about
itself, ask the user to confirm or correct it, and write ranq.yaml."""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any
from urllib.parse import urlsplit

import yaml

from ranq.analysis import pagetype as pt
from ranq.config import CrawlConfig, EntityConfig
from ranq.crawler.crawler import Crawler
from ranq.geo import entity
from ranq.storage import Store
from ranq.urls import bare_host

SHARE_PATH = re.compile(r"/(sharer|share|intent|shareArticle)\b", re.I)

AskFn = Callable[[str, str], str]  # (question, default) -> answer
SayFn = Callable[[str], None]

PRESETS = {
    "search-only": "allow AI search and user-initiated fetchers (they cite and link you), "
    "block training crawlers",
    "allow-all": "allow every AI crawler, training included (best for brand awareness)",
    "deny-all": "block every AI crawler",
}


async def detect_site_facts(site: str) -> dict[str, Any]:
    """What the home page says about the brand: name, description, city, founding date and
    official profiles. One robots-aware request; nothing is guessed."""
    store = Store(":memory:")
    try:
        crawl = await Crawler(
            CrawlConfig(max_pages=1, max_depth=0, delay_seconds=0, use_sitemaps=False), store
        ).crawl(site)
    finally:
        store.close()
    home = crawl.pages.get(crawl.start_url) or next(iter(crawl.html_pages), None)
    if home is None or home.status != 200:
        return {}
    report = entity.analyze(crawl, EntityConfig())
    org: dict[str, Any] = next(
        (
            n
            for n in pt.top_nodes(home)
            if pt.node_types(n) & {"Organization", "LocalBusiness", "Corporation"}
        ),
        {},
    )
    profiles = list(report.same_as)
    for link in home.links:
        host = bare_host(link.url)
        path = urlsplit(link.url).path.strip("/")
        if (
            not link.internal
            and path
            and any(host == h or host.endswith("." + h) for h in pt.SOCIAL_HOSTS)
            and host not in ("wa.me", "t.me")  # chat links, not profiles
            and not SHARE_PATH.search(link.url)
        ):
            profiles.append(link.url)
    address = org.get("address")
    city = address.get("addressLocality") if isinstance(address, dict) else None
    description = org.get("description") or home.meta_description
    return {
        "name": report.name,
        "description": description if isinstance(description, str) else None,
        "city": city if isinstance(city, str) else None,
        "founded": str(org["foundingDate"]) if org.get("foundingDate") else None,
        "same_as": list(dict.fromkeys(profiles)),
    }


def build_config(
    site: str, facts: dict[str, Any], ask: AskFn, say: SayFn = lambda _: None
) -> dict[str, Any]:
    """Ask each question with the detected value as default; empty answers are left out."""

    def q(question: str, default: Any = None) -> str:
        return ask(question, "" if default is None else str(default)).strip()

    name = q("Brand name", facts.get("name"))
    description = q(
        "One factual sentence: who you are, what you do, where", facts.get("description")
    )
    category = q("Category (e.g. web development agency, project management software)")
    city = q("City", facts.get("city"))
    founded = q("Founded (year)", facts.get("founded"))
    profiles = q(
        "Official profile URLs, comma-separated (LinkedIn, GitHub, X...)",
        ", ".join(facts.get("same_as") or []),
    )
    say("AI crawler policies:")
    for key, why in PRESETS.items():
        say(f"  {key}: {why}")
    preset = q("AI crawler policy (search-only / allow-all / deny-all)", "search-only")
    if preset not in PRESETS:
        preset = "search-only"

    ent: dict[str, Any] = {"name": name, "description": description, "category": category}
    ent |= {"city": city, "founded": founded}
    ent["same_as"] = [u.strip() for u in profiles.split(",") if u.strip()]
    return {
        "site": site,
        "entity": {k: v for k, v in ent.items() if v},
        "geo": {"ai_bot_preset": preset},
    }


def render(config: dict[str, Any]) -> str:
    header = (
        "# ranq.yaml - written by `ranq init`. Every field is optional; run\n"
        "# `ranq init --example` for a commented file with all settings.\n"
        "# API keys come from environment variables, never from this file.\n"
    )
    return header + yaml.safe_dump(config, sort_keys=False, allow_unicode=True)
