#!/usr/bin/env python3
"""Prepare/restore bounded snapshot envelopes locally; never transfers or publishes."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile

MAX_FILES = 100_001
MAX_BYTES = 64 * 1024**3


class RegularUstar(tarfile.TarInfo):
    def _proc_member(self, archive):
        # tarfile otherwise consumes allocating PAX/GNU extension bodies before
        # the caller sees a member. Our producer only emits plain USTAR files.
        require(self.type in (tarfile.REGTYPE, tarfile.AREGTYPE, tarfile.DIRTYPE), 'archive extension/type refused')
        require(0 <= self.size <= MAX_BYTES, 'member size refused')
        name(self.name)
        return super()._proc_member(archive)


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def regular(path):
    require(path.is_file() and not path.is_symlink(), 'regular file required')


def name(value):
    path = PurePosixPath(value)
    require(value and str(path) == value and not path.is_absolute() and
            all(p not in ('.', '..') for p in path.parts) and '\\' not in value,
            'unsafe archive path')
    return path


def absent(path):
    require(not os.path.lexists(path), 'output already exists')


class Bounded:
    def __init__(self, stream, maximum):
        self.stream, self.maximum, self.count = stream, maximum, 0

    def write(self, data):
        require(self.count + len(data) <= self.maximum, 'compressed byte limit exceeded')
        result = self.stream.write(data)
        self.count += result
        return result

    def read(self, size=-1):
        # A finite request also detects expanded tar padding/header bombs.
        size = min(size if size >= 0 else 1024**2, self.maximum-self.count+1)
        data = self.stream.read(size)
        self.count += len(data)
        require(self.count <= self.maximum, 'expanded stream limit exceeded')
        return data

    def flush(self):
        return self.stream.flush()


def pack(source, target, compressed, expanded):
    require(source.is_dir() and not source.is_symlink(), 'snapshot directory required')
    files, total = [], 0
    for path in source.rglob('*'):
        require(not path.is_symlink(), 'snapshot symlink refused')
        require(path.is_dir() or path.is_file(), 'nonregular snapshot entry')
        relative = path.relative_to(source).as_posix()
        name(relative)
        total += path.stat().st_size if path.is_file() else 0
        require(total <= expanded and len(files) < MAX_FILES, 'snapshot inventory limit exceeded')
        files.append((relative, path))
    require(files, 'empty snapshot')
    with target.open('xb') as output:
        with gzip.GzipFile(filename='', mode='wb', fileobj=Bounded(output, compressed), mtime=0, compresslevel=6) as gz:
            with tarfile.open(fileobj=gz, mode='w|', format=tarfile.USTAR_FORMAT) as archive:
                for relative, path in sorted(files):
                    require(not path.is_symlink(), 'snapshot entry changed to symlink')
                    info = tarfile.TarInfo(relative)
                    if path.is_dir():
                        info.type, info.mode = tarfile.DIRTYPE, 0o700
                        archive.addfile(info)
                    else:
                        regular(path)
                        info.size, info.mode, info.mtime = path.stat().st_size, 0o600, 0
                        with path.open('rb') as stream:
                            archive.addfile(info, stream)
        output.flush()
        os.fsync(output.fileno())
    return total


def unpack(payload, destination, expanded):
    destination.mkdir()
    seen, total = set(), 0
    with payload.open('rb') as raw, gzip.GzipFile(fileobj=raw, mode='rb') as gz:
        bounded = Bounded(gz, expanded + MAX_FILES*1024 + 1024**2)
        with tarfile.open(fileobj=bounded, mode='r|', tarinfo=RegularUstar) as archive:
            for item in archive:
                relative = name(item.name)
                require((item.isreg() or item.isdir()) and not item.pax_headers and item.name not in seen,
                        'nonregular/duplicate archive member')
                seen.add(item.name)
                total += item.size
                require(item.size >= 0 and total <= expanded and len(seen) <= MAX_FILES,
                        'expanded inventory limit exceeded')
                target = destination/relative
                if item.isdir():
                    require(item.size == 0, 'directory payload refused')
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.extractfile(item) as stream, target.open('xb') as output:
                    shutil.copyfileobj(stream, output, length=1024**2)
        # Consume gzip trailer and bound ignored padding/concatenated streams.
        while bounded.read(1024**2):
            pass
    require(seen, 'empty archive')
    return total


def restore(args, snapshot, target):
    command = [str(args.binary), '--profile', args.profile, '--cache-dir', str(target),
               'restore', str(snapshot), '--expected-id', args.snapshot_id,
               '--partition', args.partition, '--max-bytes', str(args.max_expanded_bytes)]
    result = subprocess.run(command, capture_output=True, text=True, timeout=600)
    require(result.returncode == 0, 'Forge snapshot verification refused')
    value = json.loads(result.stdout)
    require(value['snapshot_id'] == args.snapshot_id, 'unexpected restored identity')
    return {'schema': 1, 'restored': True, 'result': value}


def execute(args):
    for field in ('snapshot_id', 'partition'):
        require(re.fullmatch('[0-9a-f]{64}', getattr(args, field)), 'explicit snapshot/partition digest required')
    require(0 < args.max_compressed_bytes <= MAX_BYTES and
            0 < args.max_expanded_bytes <= MAX_BYTES, 'byte budgets must be in 1..64 GiB')
    args.binary = args.binary.resolve(strict=True)
    output = args.output.parent.resolve(strict=True)/args.output.name
    absent(output)
    require(output.parent.is_dir(), 'existing output parent required')
    with tempfile.TemporaryDirectory(prefix='.forge-payload-', dir=output.parent) as temporary:
        work = Path(temporary)
        if args.command == 'pack':
            source = args.snapshot.resolve(strict=True)
            require(not work.is_relative_to(source) and not output.is_relative_to(source),
                    'payload output must be outside snapshot')
            payload = work/'payload.tgz'
            pack(source, payload, args.max_compressed_bytes, args.max_expanded_bytes)
        else:
            require(re.fullmatch('[0-9a-f]{64}', args.payload_sha256), 'payload digest required')
            require(0 < args.payload_bytes <= args.max_compressed_bytes, 'payload size exceeds budget')
            regular(args.payload)
            require(args.payload.stat().st_size == args.payload_bytes, 'compressed size mismatch')
            # Work from a private immutable copy after independent digest checking.
            payload = work/'payload.tgz'
            with args.payload.open('rb') as source, payload.open('xb') as target:
                remaining = args.payload_bytes
                while chunk := source.read(min(1024**2, remaining+1)):
                    require(len(chunk) <= remaining, 'compressed input grew')
                    target.write(chunk)
                    remaining -= len(chunk)
            require(remaining == 0 and digest(payload) == args.payload_sha256, 'compressed digest mismatch')
        expanded = unpack(payload, work/'snapshot', args.max_expanded_bytes)
        verified = restore(args, work/'snapshot', work/'verified')
        value = {'schema': 1, 'kind': 'forge-ci-payload/v1', 'snapshot_sha256': args.snapshot_id,
                 'partition': args.partition, 'payload_sha256': digest(payload),
                 'actual_bytes': payload.stat().st_size, 'expanded_bytes': expanded,
                 'scope': 'local compressed envelope; not network transfer or proof evidence'}
        if args.command == 'pack':
            # Hard-link publication is atomic and cannot overwrite a raced output.
            os.link(payload, output)
        else:
            # CLI performs no-replace publication; never rename a directory over
            # a potentially raced target using Python's platform-dependent rename.
            verified = restore(args, work/'snapshot', output)
            value['restore'] = verified
        return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['pack', 'restore'])
    parser.add_argument('--binary', type=Path, required=True)
    parser.add_argument('--profile', choices=['ledger8-v2', 'zkir3', 'zkir31'], default='zkir31')
    parser.add_argument('--snapshot-id', required=True)
    parser.add_argument('--partition', required=True)
    parser.add_argument('--max-compressed-bytes', type=int, required=True)
    parser.add_argument('--max-expanded-bytes', type=int, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--snapshot', type=Path)
    parser.add_argument('--payload', type=Path)
    parser.add_argument('--payload-sha256')
    parser.add_argument('--payload-bytes', type=int)
    args = parser.parse_args()
    require(args.snapshot is not None if args.command == 'pack' else
            all(v is not None for v in (args.payload, args.payload_sha256, args.payload_bytes)),
            'command-specific snapshot or payload arguments required')
    print(json.dumps(execute(args)))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, KeyError, TypeError, tarfile.TarError, EOFError,
            subprocess.SubprocessError) as error:
        print(json.dumps({'schema': 1, 'error': {'code': 'ci_payload_refused',
                          'message': str(error) if isinstance(error, ValueError) else type(error).__name__}}))
        sys.exit(1)
