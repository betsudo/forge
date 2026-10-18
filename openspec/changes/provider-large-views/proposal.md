# Bounded complete provider views — #31

Qualify full Passport HTTP delivery without pruning the compiler manifest.
Retain the 4 GiB default and introduce an explicit aggregate budget bounded at
64 GiB. Per-file, metadata, admission, authentication and byte-integrity limits
remain unchanged. No Compact changes or hosted deployment are included.
