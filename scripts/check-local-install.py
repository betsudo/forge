#!/usr/bin/env python3
"""Isolated Nix-launcher installer controls; fake build is not Nix qualification."""
import os
from pathlib import Path
import subprocess
import tempfile
ROOT=Path(__file__).resolve().parent.parent
for collision in [None,'primary-file','primary-link','legacy-file','worker-file']:
    with tempfile.TemporaryDirectory(prefix='forge-local-install-') as directory:
        work=Path(directory).resolve()
        home=work/'home'
        tools=work/'tools'
        tools.mkdir()
        marker=work/'built'
        nix=tools/'nix'
        nix.write_text('#!/bin/sh\ntouch "$INSTALL_TEST_MARKER"\n')
        nix.chmod(0o700)
        commands=home/'.local/bin'
        commands.mkdir(parents=True)
        active=home/'.local/share/midnight-zkir-forge/current/bin'
        active.mkdir(parents=True)
        (active/'zkir-forge').write_text('fixture')
        legacy=commands/'midnight-zkir-forge'
        legacy.symlink_to(active/'midnight-zkir-forge')
        if collision=='primary-file': (commands/'zkir-forge').write_text('keep')
        if collision=='primary-link': (commands/'zkir-forge').symlink_to(work/'unrelated')
        if collision=='legacy-file': legacy.unlink();legacy.write_text('keep')
        if collision=='worker-file': (commands/'midnight-zkir-forge-zkir3-worker').write_text('keep')
        env=dict(os.environ,HOME=str(home),PATH=str(tools)+os.pathsep+os.environ['PATH'],INSTALL_TEST_MARKER=str(marker))
        result=subprocess.run(['bash',str(ROOT/'scripts/install-local.sh')],env=env,capture_output=True,text=True,timeout=30)
        if collision:
            assert result.returncode!=0 and not marker.exists(),(collision,result.stderr)
            if collision.endswith('file'):
                target={'primary-file':'zkir-forge','legacy-file':'midnight-zkir-forge','worker-file':'midnight-zkir-forge-zkir3-worker'}[collision]
                assert (commands/target).read_text()=='keep'
        else:
            assert result.returncode==0 and marker.exists(),result.stderr
            assert (commands/'zkir-forge').resolve()==legacy.resolve()==active/'zkir-forge'
print('Nix local launcher installer: managed upgrade and four pre-build collision refusals passed')
