# Documentation site

A dependency-free static documentation site, with relative local assets and
anchor navigation so GitHub repository Pages base paths work without rewriting.
The site makes no runtime font/CDN/API requests. The font stack uses locally
available Outfit with accessible system fallbacks. Colors follow the official
[Midnight Brand Hub](https://midnight.network/brand-hub): black `#0A0A0A`, white
`#FFFFFF`, accent blue `#0000FE`. The small Forge mark is project artwork rather
than a downloaded corporate logo.

```sh
./bootstrap.sh -- python3 scripts/build-docs.py
./bootstrap.sh -- python3 scripts/check-docs.py
python3 -m http.server 8080 --bind 127.0.0.1 --directory .local/site
```

`docs/http/openapi.json` is copied into the build. Missing API documentation is
a build failure. The checker validates anchors, local links, relative paths,
network-independent assets and required API routes. No dependency installation
or build-time network request is required.

The browser interaction review on 2026-10-15 checked desktop rendering, a
390×844 mobile viewport without horizontal overflow, installation navigation,
mobile menu opening/closing, circuit-test navigation and clipboard contents.
These are interaction checks, not a full automated accessibility audit. The
site includes a skip link, semantic navigation, visible keyboard focus,
ARIA-expanded/current/status, readable code, reduced-motion support and mobile
menu access. If changing navigation or clipboard behavior, repeat that browser
review as well as the static checker.

The prepared Pages workflow is manual. Building the artifact locally does not
publish it or enable GitHub Pages. See [workflow notes](../../container/CI.md).
