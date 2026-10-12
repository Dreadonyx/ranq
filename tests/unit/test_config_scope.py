from seoforge.cli import _site
from seoforge.config import Config, EntityConfig


def _cfg() -> Config:
    return Config(
        site="https://brightworks.example",
        entity=EntityConfig(name="BrightWorks", same_as=["https://www.linkedin.com/company/nk"]),
        competitors=["https://rival.test/"],
        seed_keywords=["digital agency chennai"],
    )


def test_other_site_does_not_inherit_entity() -> None:
    cfg = _cfg()
    assert _site("https://other.vercel.app", cfg) == "https://other.vercel.app"
    assert cfg.entity.name is None and not cfg.competitors and not cfg.seed_keywords
    assert cfg.crawl.max_pages == Config().crawl.max_pages  # preferences kept


def test_same_site_keeps_entity() -> None:
    for url in (
        None,
        "https://brightworks.example/work",
        "brightworks.example",
        "https://www.brightworks.example",
    ):
        cfg = _cfg()
        _site(url, cfg)
        assert cfg.entity.name == "BrightWorks", url
