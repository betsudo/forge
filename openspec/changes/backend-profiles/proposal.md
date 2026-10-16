# Explicit official backend profile matrix

Status: proposed; current pins and runtime support unchanged.

## Why

JSON major versions and crate labels do not uniquely identify compatible IR, proof systems or key serialization. Official published crates can improve reproducibility only after exact graph qualification.

## What changes

Document observed registry availability and propose a finite, explicit profile matrix with separately pinned workers, descriptor-based consumer acceptance and real per-platform proof qualification. Retain ledger8 8.1.3 and the current exact ZKIR3 worker.

## Non-goals

Automatic upgrades, arbitrary plugins, ZKIR conversion, a claim of universal ZKIR3 compatibility, ledger9 transaction support or Compact changes.

See [research](../../../docs/research/backend-matrix.md).
