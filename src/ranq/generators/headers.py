"""Security header snippets built from the site's live headers: add what is missing, strengthen
what is weak, and never replace a stronger existing value (e.g. X-Frame-Options DENY)."""

from __future__ import annotations

import re
from dataclasses import dataclass

HSTS_MIN_AGE = 31536000  # one year

RECOMMENDED = {
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "X-Frame-Options": "SAMEORIGIN",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}
WEAK_REFERRER = {"unsafe-url", "no-referrer-when-downgrade", "origin-when-cross-origin"}


@dataclass(slots=True)
class HeaderPlan:
    name: str
    live: str | None
    action: str  # keep | add | strengthen | not needed
    value: str | None  # value to set (None when keeping the live one)
    why: str


def _plan_one(name: str, live: str | None, headers: dict[str, str]) -> HeaderPlan:
    rec = RECOMMENDED[name]
    if name == "X-Frame-Options":
        csp = headers.get("content-security-policy", "")
        if live is None and "frame-ancestors" in csp:
            return HeaderPlan(
                name, None, "not needed", None, "CSP frame-ancestors already covers it"
            )
        if live and live.strip().upper() in ("DENY", "SAMEORIGIN"):
            return HeaderPlan(name, live, "keep", None, "already set")
        if live:
            return HeaderPlan(
                name, live, "strengthen", rec, "ALLOW-FROM is obsolete; browsers ignore it"
            )
    if name == "Strict-Transport-Security" and live:
        match = re.search(r"max-age=(\d+)", live, re.I)
        if match and int(match.group(1)) >= HSTS_MIN_AGE:
            return HeaderPlan(name, live, "keep", None, "max-age is at least one year")
        return HeaderPlan(name, live, "strengthen", rec, "max-age below one year")
    if name == "X-Content-Type-Options" and live:
        if live.strip().lower() == "nosniff":
            return HeaderPlan(name, live, "keep", None, "already set")
        return HeaderPlan(name, live, "strengthen", rec, "only 'nosniff' is valid")
    if name == "Referrer-Policy" and live:
        last = live.split(",")[-1].strip().lower()  # browsers use the last valid token
        if last in WEAK_REFERRER:
            return HeaderPlan(name, live, "strengthen", rec, "leaks full URLs to other sites")
        return HeaderPlan(name, live, "keep", None, "already set")
    if live:
        return HeaderPlan(name, live, "keep", None, "already set")
    return HeaderPlan(name, None, "add", rec, "missing")


def plan_headers(headers: dict[str, str]) -> list[HeaderPlan]:
    """`headers` are the home page's response headers (lower-case keys)."""
    return [_plan_one(name, headers.get(name.lower()), headers) for name in RECOMMENDED]


def detect_host(headers: dict[str, str]) -> str | None:
    server = headers.get("server", "").lower()
    if "x-vercel-id" in headers or server == "vercel":
        return "Vercel"
    if "x-nf-request-id" in headers or server == "netlify":
        return "Netlify"
    if "cf-ray" in headers or server == "cloudflare":
        return "Cloudflare"
    if "nginx" in server:
        return "nginx"
    if "apache" in server:
        return "Apache"
    return None


def _snippets(changes: list[HeaderPlan]) -> dict[str, str]:
    pairs = [(c.name, c.value or "") for c in changes]
    return {
        "Vercel": "vercel.json (merge into an existing `headers` array):\n\n```json\n"
        '{"headers": [{"source": "/(.*)", "headers": [\n'
        + ",\n".join(f'  {{"key": "{k}", "value": "{v}"}}' for k, v in pairs)
        + "\n]}]}\n```\n\nNext.js alternative: return the same list from `headers()` in "
        "next.config.js.",
        "Netlify": "`_headers` file in the publish directory:\n\n```\n/*\n"
        + "\n".join(f"  {k}: {v}" for k, v in pairs)
        + "\n```",
        "Cloudflare": "Cloudflare Pages `_headers` file (same format as Netlify), or a "
        "Transform Rule (Rules -> Transform Rules -> Modify Response Header):\n\n```\n/*\n"
        + "\n".join(f"  {k}: {v}" for k, v in pairs)
        + "\n```",
        "nginx": "nginx server block:\n\n```nginx\n"
        + "\n".join(f'add_header {k} "{v}" always;' for k, v in pairs)
        + "\n```",
        "Apache": "Apache (.htaccess, mod_headers):\n\n```apache\n"
        + "\n".join(f'Header always set {k} "{v}"' for k, v in pairs)
        + "\n```",
    }


def render_security_headers(headers: dict[str, str]) -> str:
    plans = plan_headers(headers)
    host = detect_host(headers)
    lines = [
        "# Security headers",
        "",
        "Based on the live response headers of your home page. Existing values that are already "
        "as strong as the recommendation are kept, never replaced.",
        "",
        "| Header | Live value | Action | Why |",
        "|---|---|---|---|",
    ]
    lines += [
        f"| {p.name} | {f'`{p.live}`' if p.live else '-'} | **{p.action}** | {p.why} |"
        for p in plans
    ]
    changes = [p for p in plans if p.action in ("add", "strengthen")]
    if not changes:
        lines += ["", "Nothing to change: all recommended headers are present."]
        return "\n".join(lines) + "\n"
    snippets = _snippets(changes)
    order = [host] if host in snippets else []
    order += [h for h in snippets if h not in order]
    lines += ["", "Only the headers to add or change are below."]
    if host:
        lines += ["", f"Detected host: **{host}** (shown first)."]
    for name in order:
        lines += ["", f"## {name}", "", snippets[name]]
    lines += [
        "",
        "Content-Security-Policy is not generated: a wrong policy breaks pages. Build one with "
        "https://csp-evaluator.withgoogle.com/ and roll it out as Report-Only first.",
    ]
    return "\n".join(lines) + "\n"
