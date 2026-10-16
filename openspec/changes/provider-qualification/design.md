# Provider fixture design

Pin official npm packages in a private test project with a committed lockfile;
Node/npm run through the existing Nix bootstrap. Accept an explicit qualified
native compiler, Forge package and verified parameter directory. Compile a small
real Compact fixture normally so the actual compiler writes the integrity
manifest after native keygen; do not fabricate compiler provenance.

For each current circuit, prepare cold and warm keys with Forge's JSON3.1 profile
and require byte equality with the independently generated original compiler
outputs. Copy verified private outputs only when equal, preserving the exact
compiler manifest and contract-info bytes. No consumer or Compact checkout edits.

Use real NodeZkConfigProvider and FetchZkConfigProvider with require integrity
and an independently retained compiler-manifest digest. Verify runtime version
and every retrieved key/binary IR against original bytes. Serve only an explicit
allowlist from the owned test bundle, with bounded local fixture responses and
real HTTP gzip decoding. Keep this HTTP fixture distinct from Forge's current
production management/CAS API; it is not an implemented hosted provider service.

Retrieve artifacts for fresh genuine native proofs and invalid-statement/corrupt-
proof controls. Test missing compiler manifest, wrong trust anchor, tampered key,
HTML fallback and unsafe names as hard refusals. No integrity opt-out. Preserve
raw SDK/runtime/tool/package-lock hashes and honest environment/scope receipts;
Node HTTP tests do not establish browser/HTTPS/CDN/auth qualification.
