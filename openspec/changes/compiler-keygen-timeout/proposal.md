# Bounded compiler keygen timeout — #14

Replace the adapter's fixed 180-second prepare deadline with an explicit local-only
setting. Larger independently qualified circuits may need more time. Preserve a
finite default, exact qualification and no implicit native fallback. The native
off compiler path remains unchanged; metadata/profile checks retain their limits.
