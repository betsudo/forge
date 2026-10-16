#!/usr/bin/env python3
"""Linux-only regression controls for relocated runtimes and exact source mapping.

Run runtime mode in a Nix-free consumer with an already relocated bundle. Source
mode runs in its Nix builder against the original runtime-origin inventory. It
stops after real Nix metadata evaluation and source validation, before copying
large source archives. Neither mode modifies the supplied bundle.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import platform
import subprocess
import tempfile


def runtime(root):
    commands = [(root / 'bin/midnight-zkir-forge', ['--version']),
                (root / 'bin/midnight-zkir-forge-zkir3-worker', ['profile'])]
    if (root / 'bin/midnight-zkir-forge-zkir31-worker').is_file():
        commands.append((root / 'bin/midnight-zkir-forge-zkir31-worker', ['profile']))
    environment = {name: value for name, value in os.environ.items()
                   if not name.startswith('LD_') and name != 'GLIBC_TUNABLES'}
    controls = []
    variables = ('LD_PRELOAD', 'LD_LIBRARY_PATH', 'LD_AUDIT', 'LD_DEBUG',
                 'LD_BIND_NOW', 'LD_FORGE_REGRESSION_UNKNOWN', 'GLIBC_TUNABLES')
    nonempty = ('/missing-forge-regression-preload.so', '/tmp/not-verified-runtime',
                '/missing-forge-regression-audit.so', 'libs', '1', '1',
                'glibc.malloc.check=1')
    for command, arguments in commands:
        baseline = subprocess.run([str(command), *arguments], env=environment,
                                  capture_output=True, text=True, timeout=30)
        assert baseline.returncode == 0, (command, baseline.stderr)
        for variable, nonempty_value in zip(variables, nonempty):
            for value in ('', nonempty_value):
                result = subprocess.run([str(command), *arguments],
                                        env=dict(environment, **{variable: value}),
                                        capture_output=True, text=True, timeout=30)
                assert result.returncode != 0 and not result.stdout, (variable, result.stdout, result.stderr)
                assert 'refuses loader override variables' in result.stderr, (variable, result.stderr)
        controls.append({'command': command.name, 'ordinary_startup': True,
                         'empty_and_nonempty_loader_override_variables_refused': list(variables)})
    # Consumer Python is a prerequisite/trust boundary. Its own ELF interpreter
    # runs before our Python code and can intercept LD_TRACE_LOADED_OBJECTS.
    traced = subprocess.run([str(commands[0][0]), '--version'],
                            env=dict(environment, LD_TRACE_LOADED_OBJECTS='1'),
                            capture_output=True, text=True, timeout=30)
    assert 'midnight-zkir-forge ' not in traced.stdout and 'zkir-forge ' not in traced.stdout
    return {'mode': 'runtime', 'controls': controls,
            'no_nix_store': not Path('/nix').exists(),
            'no_build_checkout': not Path('/source').exists(),
            'kernel': platform.release(), 'architecture': platform.machine(),
            'pre_python_loader_trace': {'exit_status': traced.returncode,
                                        'forge_version_not_executed': True},
            'boundary': 'trusted consumer Python starts before launcher checks; not adversarial environment isolation'}


def sources(args):
    specification = importlib.util.spec_from_file_location('runtime_sources', args.module)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    origins = json.loads((args.root / 'LICENSES/linux-runtime-origin.json').read_text())
    original_run = module.run
    evaluated = []

    class SourcesValidated(Exception):
        pass

    def intercept(*arguments):
        if list(arguments[:2]) == [args.nix, 'build']:
            raise SourcesValidated()
        value = original_run(*arguments)
        if list(arguments[:3]) == [args.nix, 'eval', '--json']:
            evaluated.append(json.loads(value))
        return value

    module.run = intercept

    def validate(value):
        with tempfile.TemporaryDirectory(prefix='forge-origin-regression-') as directory:
            root = Path(directory)
            (root / 'LICENSES').mkdir()
            (root / 'LICENSES/linux-runtime-origin.json').write_text(json.dumps(value))
            try:
                module.collect(root, root, 'probe', args.nix, args.flake_ref,
                               args.system, args.repository, args.commit)
            except SourcesValidated:
                return None
            except RuntimeError as error:
                return str(error)
            raise AssertionError('source collector did not reach its validation boundary')

    assert validate(origins) is None, 'evaluated exact outputs rejected original runtime'
    metadata = evaluated[-1]
    library = 'libc.so.6'
    outputs = [Path(value) for package in metadata.values() for value in package['outputs']]
    alternatives = [path for path in Path('/nix/store').glob('*-' + metadata['glibc']['name'] + '/lib/' + library)
                    if not any(path.is_relative_to(output) for output in outputs)]
    assert alternatives, 'same-name alternate store output is needed for this regression'
    changed = json.loads(json.dumps(origins))
    path = alternatives[0]
    changed[library]['source_path'] = str(path)
    changed[library]['source_sha256'] = module.digest(path)
    message = validate(changed)
    assert message == 'unmapped runtime library source: ' + library, message
    changed[library]['source_path'] = str(Path(metadata['glibc']['outputs'][0]) / 'lib' / '..' / '..' /
                                          path.parent.parent.name / 'lib' / library)
    message = validate(changed)
    assert message == 'unmapped runtime library source: ' + library, message
    with tempfile.TemporaryDirectory(prefix='forge-source-alias-regression-') as directory:
        alias = Path(directory) / library
        alias.symlink_to(path)
        changed[library]['source_path'] = str(alias)
        message = validate(changed)
        assert message == 'unmapped runtime library source: ' + library, message
        alias.unlink()
        alias.symlink_to(origins[library]['source_path'])
        changed[library]['source_sha256'] = origins[library]['source_sha256']
        assert validate(changed) is None, 'alias to exact original output did not resolve correctly'
    changed = json.loads(json.dumps(origins))
    changed[library]['source_sha256'] = '0' * 64
    message = validate(changed)
    assert message == 'runtime source changed after relocation: ' + library, message
    return {'mode': 'sources', 'flake_reference': args.flake_ref,
            'system': args.system, 'exact_original_outputs_accepted': True,
            'same_package_name_alternate_store_refused': True,
            'matching_alternate_digest_did_not_bypass_output_check': True,
            'dotted_path_to_alternate_store_refused': True,
            'symlink_to_alternate_store_refused': True,
            'symlink_to_exact_original_output_resolved': True,
            'changed_original_source_digest_refused': True,
            'alternate_source_path': str(path),
            'evaluated_outputs': {name: package['outputs'] for name, package in metadata.items()},
            'scope': 'real Nix evaluation and original source reads; stops before source archive generation'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['runtime', 'sources'])
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--module', type=Path, default=Path(__file__).with_name('linux-runtime-sources.py'))
    parser.add_argument('--nix', default='nix')
    parser.add_argument('--flake-ref')
    parser.add_argument('--system', default='aarch64-linux')
    parser.add_argument('--repository', type=Path)
    parser.add_argument('--commit')
    options = parser.parse_args()
    if options.mode == 'sources':
        assert options.flake_ref and options.repository and options.commit
    print(json.dumps({'schema': 1, **(runtime(options.root) if options.mode == 'runtime' else sources(options))}, indent=2))
