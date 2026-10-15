#!/usr/bin/env python3
"""Build a dependency-free Pages artifact, valid under any repository base path."""
import argparse
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', default=str(ROOT / '.local/site'))
args = parser.parse_args()
out = Path(args.output).resolve()
if out == ROOT or ROOT in out.parents and out.parts[len(ROOT.parts)] != '.local':
    parser.error('output must be outside the repository or inside .local')
out.mkdir(parents=True, exist_ok=True)
for path in sorted((ROOT / 'docs/site').iterdir()):
    if path.is_file() and path.suffix in {'.html', '.css', '.js', '.svg'}:
        shutil.copyfile(path, out / path.name)
contract = ROOT / 'docs/http/openapi.json'
if not contract.is_file():
    parser.error('missing docs/http/openapi.json; the API contract must be built with the site')
shutil.copyfile(contract, out / 'openapi.json')
(out / '.nojekyll').write_text('')
print(out)
