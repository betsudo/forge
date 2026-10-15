# Local factory

Adapted from the factory knowledge base and Oxid, with one local writer.
The Nix lock owns Pi, Node and Rust versions. Use `./bootstrap.sh --pi`.
External extensions/skills/prompts are disabled at launch to avoid startup
mutations and inheriting a hosted delivery loop. No extra Pi packages are
needed for this initial loop. Authentication stays in the existing user store.

Each iteration records scope, commands, actual evidence, gaps and next slice
in docs/PROGRESS.md. The first two iterations are bootstrap/compatibility and
local cache. No GitHub claims, PRs, automated merges or persistent supervisors
are activated. Remote coordination and production factory gates remain future
work. Missing usage counters are unknown, never reconstructed estimates.

`./bootstrap.sh --audit-pi` checks runtime and machine-readable local policy.
`./bootstrap.sh --check` runs the selected local engineering checks.
The broader Oxid factory has not been ported or qualified in full.
