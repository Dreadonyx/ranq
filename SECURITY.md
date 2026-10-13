# Security policy

## Supported versions

Security fixes go into the latest release. Upgrade with `pipx upgrade ranq` (or reinstall
from the latest GitHub release).

## Reporting a vulnerability

Please report vulnerabilities privately through GitHub's
[private vulnerability reporting](https://github.com/H3M4N1H/ranq/security/advisories/new)
rather than a public issue. Include the Ranq version, the command you ran, and the smallest
input (for example a page's HTML) that reproduces the problem. You should get a reply within a
week.

## Threat model

Ranq crawls sites you point it at, so everything it fetches is treated as untrusted input:

- Crawled text is escaped in the HTML report, and only `http(s)` URLs become links.
- Generated JSON-LD escapes `</` so crawled text cannot close a `<script>` tag.
- `ranq fix --apply-to` writes only inside the directory you give it, after showing a diff
  and asking for confirmation for each file.
- `ranq visibility run --cmd` runs only the command you pass, without a shell, with the
  prompt as a single argument.
- API keys are read from environment variables, never from `ranq.yaml` or reports.

The crawler obeys robots.txt and identifies itself as `Ranq/<version>`. It is not designed
to be pointed at internal networks on behalf of untrusted users; if you expose it as a
service, restrict the URLs it may fetch.
