# Exact Compact 0.35 ZKIR 3.1 worker

This isolated workspace follows the compiler's official dependency tag
`midnight-zkir/zkir-3.1.0-rc.1`, peeled commit
`e82d81d25aabcc5f5092e2bd559083487f577914`. The official split workspace
patches base-crypto, serialize, transient-crypto and storage-core to ledger
`9a8777c4d035fc7f38ae286bcf5f8656668efd9f`.

It accepts JSON 3.1 only. It does not alter the separately qualified JSON3.0
worker or ledger8 dependencies. Actual serialization is
`ir-source[v3-generic]`, `prover-key[v7](ir-source[v3-generic])`, and
`verifier-key[v7]`. A generic tag is not a compatibility promise.

`prove-preimage` is an explicit local benchmark helper. With current JSON source
on stdin, `--preimage PATH`, `--output DIR`, and verified parameter configuration,
it reads `circuit.bzkir`, `circuit.prover`, and `circuit.verifier`, requires binary
IR to equal current source, and generates a new real proof. It verifies the proof
and rejects a changed public statement and corrupted encoding. Neither the
preimage nor proof nor test result enters the Forge store or snapshots.
