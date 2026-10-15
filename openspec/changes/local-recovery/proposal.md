# Local recovery and simplification

Issue #9. Favor a small reliable local component: share one no-replace directory
publication primitive, remove duplicate readiness updates, and keep successful
request metrics in the operation's transaction. Preserve primary failures when
best-effort error accounting also fails. Add targeted crash/failure/retry tests.
No new service surface, supervisor, dependency, backend pin or Compact change.
