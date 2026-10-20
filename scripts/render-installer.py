#!/usr/bin/env python3
"""Render a standalone shell asset from the canonical verified Python installer."""
import argparse
import hashlib
from pathlib import Path

DELIMITER = '_ZKIR_FORGE_CANONICAL_INSTALLER_'


def render(source):
    text = source.decode('utf-8')
    if DELIMITER in text.splitlines():
        raise ValueError('installer source conflicts with shell delimiter')
    header = (
        '#!/bin/sh\n'
        '# Generated from scripts/install-release.py; do not edit the embedded code.\n'
        '# Requires Python 3.11+ and authenticated gh; installs binaries without Nix/Cargo.\n'
        '# Canonical installer SHA-256: ' + hashlib.sha256(source).hexdigest() + '\n'
        'set -eu\n'
        'exec "${FORGE_INSTALLER_PYTHON:-python3}" - "$@" <<\'' + DELIMITER + '\'\n'
    )
    return (header + text.rstrip('\n') + '\n' + DELIMITER + '\n').encode('utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path(__file__).with_name('install-release.py'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.write_bytes(render(args.source.read_bytes()))
    args.output.chmod(0o755)
