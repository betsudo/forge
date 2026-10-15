# Compiler-facing compatibility and typed errors

Status: proposed. Forge issue #12. Consumer context only:
https://github.com/MediaNoxLabs/compact/issues/643. Do not modify Compact.

Expose the premises already used by Forge instead of asking consumers to decode
hash recipes or trust a version string. Add one strict versioned descriptor to CLI
and HTTP responses and persistent exports; replace diagnostic substring matching
with shared typed errors and documented fallback decisions. Preserve existing
source/bundle/derivation/output identities and immutable legacy export bytes.

This is a focused local increment, not universal Compact qualification, a new
registry/framework or an authorization/deployment change. Dependencies and official
backend pins remain fixed. Default parameter retrieval remains offline. The release
installer proposal packages exact descriptors/provenance but cannot qualify itself
for a consumer merely by advertising matching values.
