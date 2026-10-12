import asyncio
from pathlib import Path

import yaml
from typer.testing import CliRunner

from seoforge import wizard
from seoforge.cli import app
from seoforge.config import load_config


def test_detects_facts_from_home_page(site_url: str) -> None:
    facts = asyncio.run(wizard.detect_site_facts(site_url))
    assert facts["name"] == "Acme Widgets"
    assert "https://github.com/acme-widgets" in facts["same_as"]


def test_answers_become_a_valid_config(tmp_path: Path) -> None:
    facts = {"name": "NodeKraft", "city": "Chennai", "same_as": ["https://www.linkedin.com/x"]}
    answers = {
        "Brand name": "",  # keep the detected default
        "One factual sentence": "NodeKraft is a digital agency in Chennai.",
        "City": "",
        "Official profile URLs": "",
        "AI crawler policy": "allow-all",
    }
    said: list[str] = []

    def ask(question: str, default: str) -> str:
        answer = next((v for k, v in answers.items() if question.startswith(k)), "")
        return answer or default

    data = wizard.build_config("https://nodekraft.tech", facts, ask, said.append)
    path = tmp_path / "seoforge.yaml"
    path.write_text(wizard.render(data))
    cfg = load_config(path)
    assert cfg.site == "https://nodekraft.tech"
    assert cfg.entity.name == "NodeKraft" and cfg.entity.city == "Chennai"
    assert cfg.entity.description == "NodeKraft is a digital agency in Chennai."
    assert cfg.entity.same_as == ["https://www.linkedin.com/x"]
    assert cfg.entity.category is None  # unanswered questions are left out
    assert cfg.geo.ai_bot_preset == "allow-all"
    assert any("search-only" in line for line in said)
    assert "category" not in yaml.safe_load(path.read_text())["entity"]


def test_non_interactive_init_writes_example(tmp_path: Path) -> None:
    path = tmp_path / "seoforge.yaml"
    result = CliRunner().invoke(app, ["init", str(path)])
    assert result.exit_code == 0, result.output
    assert "commented example" in result.output and "entity:" in path.read_text()
    again = CliRunner().invoke(app, ["init", str(path)])
    assert again.exit_code == 1  # never overwrites without --force
