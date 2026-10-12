from seoforge.generators.headers import detect_host, plan_headers, render_security_headers

LIVE_HEADERS = {
    "server": "cloudflare",
    "x-vercel-id": "sin1::abc",
    "content-security-policy": "frame-ancestors 'none'; base-uri 'self'",
    "permissions-policy": "camera=(), microphone=()",
    "referrer-policy": "strict-origin-when-cross-origin",
    "strict-transport-security": "max-age=63072000",
    "x-content-type-options": "nosniff",
    "x-frame-options": "DENY",
}


def test_never_downgrades_stronger_live_values() -> None:
    plans = {p.name: p for p in plan_headers(LIVE_HEADERS)}
    assert all(p.action == "keep" for p in plans.values())
    out = render_security_headers(LIVE_HEADERS)
    assert "Nothing to change" in out and "SAMEORIGIN" not in out


def test_adds_missing_and_strengthens_weak() -> None:
    headers = {"strict-transport-security": "max-age=300", "referrer-policy": "unsafe-url"}
    plans = {p.name: p for p in plan_headers(headers)}
    assert plans["Strict-Transport-Security"].action == "strengthen"
    assert plans["Referrer-Policy"].action == "strengthen"
    assert plans["X-Content-Type-Options"].action == "add"
    assert plans["X-Frame-Options"].action == "add"
    csp_only = plan_headers({"content-security-policy": "frame-ancestors 'self'"})
    assert {p.name: p.action for p in csp_only}["X-Frame-Options"] == "not needed"


def test_detected_host_snippet_first() -> None:
    assert detect_host(LIVE_HEADERS) == "Vercel"
    out = render_security_headers({"server": "Netlify"})
    assert out.index("## Netlify") < out.index("## Vercel")
