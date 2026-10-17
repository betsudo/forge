# Explicit sibling exec

On supported Unix platforms, resolve the launcher's real executable location,
select its sibling zkir-forge, refuse a missing primary or a path/hardlink pointing
back to this launcher, and exec with args_os. Never search PATH. Exec inherits
stdio/environment and preserves process signals and the primary exit status.
No full Forge library dependency is used by this small binary. Installation of
the Cargo legacy bin alone is not supported; install default/all bins or the
primary and alias together. Distribution packaging already supplies both names
and is unchanged. Help/version from either name intentionally uses zkir-forge.
Use copied isolated launchers to test unrelated cwd, symlink invocation, missing
primary, self-recursion/hardlinks, Unicode/space arguments, inherited environment
and nonzero exit status. Existing dual-name/profile/store and worker tests remain.
Measure artifact size and an isolated bin build against the former full source.
