# Assert fixture

Minimal genuine ZKIR v2 circuit: assert the single private input. Matches the
minimal circuit in official midnight-ledger ZKIR proof tests. With input 1 and
binding input 42 it proves; verification with binding input 43 must fail.
There are no generated keys or parameters committed in the fixture directory.

`assert-v3.zkir` is the exact pinned v3 minimal assert shape, including its
required empty output signature. Its binary IR tag is ir-source[v3-generic].
V3 tests also generate and verify a proof with warm exported keys, then repeat
after eviction/regeneration. JSON3.1 is intentionally refused by this profile.
