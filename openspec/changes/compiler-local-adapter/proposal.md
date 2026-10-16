# Compiler-facing local adapter — betsudo/forge #6

Implement a Forge-owned opt-in wrapper around an explicitly qualified official
native compiler/keygen cohort. Default off preserves original generation. Local
mode replaces only the compiler subprocess keygen boundary, then lets the
original compiler write ordinary runtime/integrity metadata. No Compact checkout
or official binary is edited. Cloudflare/fetch mode and publication remain out
of scope. Unsupported cohorts fail without weakening existing Compact guards.
