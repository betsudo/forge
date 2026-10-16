# Compile the primary CLI once — #13

Replace the Cargo compatibility binary's inclusion of the entire primary source
with a std-only sibling launcher. The primary still owns parsing and application
behavior. Nix installed symlinks and portable byte-identical aliases remain intact.
Keep the old executable name without a second link of the cryptographic stack.
