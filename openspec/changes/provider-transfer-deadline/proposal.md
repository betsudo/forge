# Bound retained provider streams — #34

Two slow readers must not retain every verified provider spool indefinitely.
Keep the two active spools/2GiB cap and integrity-before-response behavior. Add a
finite configurable total transfer deadline without splitting spool ownership
into a larger pool. Keep Compact and official pins unchanged.
