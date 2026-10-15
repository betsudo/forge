# Local OCI packaging

The Nix `dockerImage` output packages the locked CLI and isolated ZKIR3 worker,
including their Linux runtime closures. It does not copy a macOS binary or fetch
an unpinned Docker base image. No registry publishing is configured.

On **native x86_64 Linux or aarch64 Linux**, with Nix flakes and Docker:

```sh
nix build .#dockerImage --out-link result-image
docker load --input result-image
```

A Darwin Nix installation needs an explicitly configured Linux builder to build
this output; Docker Desktop alone is not a Nix remote builder. On Darwin, build
from a Linux checkout/VM or configure that builder first. Select the matching
Linux platform rather than claiming cross compilation. Both Linux outputs are
defined; build and runtime qualification on each platform remain required.

Prepare verified parameters using the CLI before serving offline, and use an
absolute parameter directory and a dedicated bearer token file. The token file
must be readable by container UID 65532 (for example a dedicated readable
secret bind mount); never commit it. The HTTP server refuses a public bind
without a token. Do not put credentials in URLs or image layers.

```sh
export FORGE_PARAMS_DIR=/absolute/path/to/verified-parameters
export FORGE_TOKEN_FILE=/absolute/path/to/forge-token
docker compose config --quiet
docker compose up -d
```

Compose publishes only `127.0.0.1:8787` on the host. The process runs as
65532:65532, drops capabilities, uses a read-only root filesystem and a temporary
`/tmp`. A named volume retains `/data`; `/params` and the token are read-only.
The image entrypoint sets `--cache-dir /data --params-dir /params`; default
arguments start authenticated HTTP on `0.0.0.0:8787` inside the container.
Parameter downloading is disabled by default. Populate every parameter size
needed by your circuits; missing or corrupt parameters must fail rather than
silently use another identity. This cache serves artifacts and does not cache
proof or test outcomes.

Stop the service with `docker compose down`. This retains the named volume;
`docker compose down --volumes` deletes it and is intentionally not part of
routine shutdown.

For an isolated local container smoke test after loading the image, run:

```sh
./bootstrap.sh -- python3 scripts/check-container.py
```

The smoke test owns its temporary container and volume, checks non-root image
configuration, refuses a public bind without a token and runs authenticated HTTP source
roundtrip/error checks against its own ephemeral localhost port. It does not claim real key generation without verified parameters.
Use the HTTP proof e2e test on the native build for both exact backend profiles.
