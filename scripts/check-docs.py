#!/usr/bin/env python3
"""Check the built Pages artifact: links, anchors, offline assets and API contract."""
import argparse
from html.parser import HTMLParser
import json
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', default=str(ROOT / '.local/site'))
args = parser.parse_args()
site = Path(args.output).resolve()
class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.refs = []
        self.h1 = 0
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs:
            assert attrs['id'] not in self.ids, f'duplicate id {attrs["id"]}'
            self.ids.add(attrs['id'])
        if tag == 'h1': self.h1 += 1
        for attr in ('src', 'href'):
            if attr in attrs: self.refs.append((tag, attrs[attr]))
page = Page()
page.feed((site / 'index.html').read_text())
assert page.h1 == 1, 'one primary heading required'
for tag, ref in page.refs:
    url = urlsplit(ref)
    if url.scheme or url.netloc:
        assert tag == 'a', f'network-dependent runtime asset: {ref}'
        continue
    assert not url.path.startswith('/'), f'root absolute URL breaks repository Pages: {ref}'
    if url.path:
        assert (site / url.path).is_file(), f'missing local link: {ref}'
    elif url.fragment:
        assert url.fragment in page.ids, f'missing anchor {ref}'
contract = json.loads((site / 'openapi.json').read_text())
assert contract['openapi'].startswith('3.'), 'OpenAPI v3 expected'
for route in ('/v1/bundles', '/v1/profiles', '/v1/stats', '/health/live'):
    assert route in contract['paths'], f'missing documented route {route}'
assert (site / '.nojekyll').exists(), 'Pages must bypass Jekyll'
print(json.dumps({'site': str(site), 'anchors': len(page.ids), 'links': len(page.refs), 'openapi_paths': len(contract['paths']), 'passed': True}))
