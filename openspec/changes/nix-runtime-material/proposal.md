# Pinned Nix runtime material (issue #43)

Build the existing public d64 Forge runtime once and attach its original Nix closure to a same-run reusable workflow artifact. This removes repeated provisioning as a separately measurable cost. It does not cache circuit results or qualify a consumer, publish a release or enable cache transport.
