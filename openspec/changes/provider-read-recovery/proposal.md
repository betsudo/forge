# Bounded provider reads and compiler recovery

Refs #4
Refs #6

Address PR12 review items1/2/8/10: avoid hashing unrelated artifacts on each view request; separate read admission from cache work; resolve explicit cache roots without HOME; stage compiler key copies outside its final bundle. Add meaningful failure/cancellation/retry controls, signed commits and PR12 CI. Compact and official pins remain unchanged; no merge.
