# Lightweight binary installation entry point

Refs #43. Compact developers and CI need a short exact-version install command
without compiling Forge or modifying a shared Nix installation. Reuse the existing
verified release installer, rather than creating another downloader/extractor.

Add `install.sh` and explicit `--github-path` support. Release publication and
consumer compatibility qualification remain separate. No binary releases currently
exist; this increment must not imply that an example version is downloadable.
