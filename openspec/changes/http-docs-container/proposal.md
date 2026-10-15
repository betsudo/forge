# Document and expose the single-host cache

## Why

Issue #4 makes the existing local artifact cache easier to adopt through a Midnight
styled documentation site, basic CI and a first HTTP/container delivery slice.

## What changes

Add a loopback-first HTTP adapter around the existing application/store, explicit
synchronous materialization, verified immutable object downloads and an OpenAPI
contract. Add bounded local end-to-end tests, a static Pages site and workflow
definitions, and a Linux Nix OCI package with persistent storage guidance.

## Non-goals

No code push, workflow dispatch, site deployment or registry publication. No
durable asynchronous jobs, multi-tenant authorization, archives, HTTP provider
views, ledger9, dependency profile changes or replacement of consumer proofs.
