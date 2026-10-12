from seoforge.generators.markdown import html_to_markdown

HTML = """<html><body><main><h1>We Kraft</h1>
<p><a href="/c"><span aria-hidden="true"></span><span>Start a Project</span>
<span aria-hidden="true">Start a Project<svg aria-hidden="true"></svg></span></a></p>
<div class="flex flex-col gap-1"><span class="font-bold">Secure</span><span>Development</span></div>
<div style="display: grid"><span>24/7</span><span>Support</span></div>
<p>Node<b>Kraft</b> builds <span>fast</span> sites.</p>
<div style="display:none">secret menu</div><p hidden>also hidden</p></main></body></html>"""


def test_hidden_duplicates_dropped_and_layout_spaced() -> None:
    md = html_to_markdown(HTML, "https://s.test/")
    assert "[Start a Project](https://s.test/c)" in md and md.count("Start a Project") == 1
    assert "Secure Development" in md and "24/7 Support" in md
    assert "Node**Kraft** builds fast sites." in md  # normal inline text is not split
    assert "secret menu" not in md and "also hidden" not in md


def test_live_llms_txt_is_extended_not_replaced() -> None:
    from seoforge.generators.llms import extend_live

    live = "# NK\n\n> Hand-written.\n\n- [Home](https://nk.test/): x\n- [Work](https://nk.test/work.md)\n"
    generated = (
        "# NK\n\n## Main pages\n\n- [Home](https://nk.test/): auto\n"
        "- [Work](https://nk.test/work): auto\n- [About](https://nk.test/about): auto\n"
    )
    text, added = extend_live(live, generated)
    assert added == 1 and text.startswith(live.rstrip())
    assert text.endswith("## More pages\n\n- [About](https://nk.test/about): auto\n")
    assert extend_live(text, generated) == (text, 0)
