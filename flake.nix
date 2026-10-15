{
  description = "Midnight ZKIR Forge: local ledger8 artifact cache";
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  inputs.rust-overlay.url = "github:oxalica/rust-overlay/ca7f624be3935a5bc46d2c240515491ab8675503";
  inputs.rust-overlay.inputs.nixpkgs.follows = "nixpkgs";
  outputs = { self, nixpkgs, rust-overlay }:
    let
      systems = [ "aarch64-darwin" "x86_64-darwin" "aarch64-linux" "x86_64-linux" ];
      eachSystem = nixpkgs.lib.genAttrs systems;
    in {
      devShells = eachSystem (system: let pkgs = import nixpkgs { inherit system; overlays = [ (import rust-overlay) ]; };
          toolchain = pkgs.rust-bin.stable."1.98.1".minimal.override { extensions = [ "rustfmt" "clippy" ]; };
      in {
        default = pkgs.mkShell {
          packages = with pkgs; [ toolchain pkg-config openssl sqlite python3 nodejs_24 git gnupg ripgrep pi-coding-agent ];
          shellHook = ''
            export CARGO_BUILD_JOBS="''${CARGO_BUILD_JOBS:-2}"
          '';
        };
      });
      packages = eachSystem (system: let pkgs = import nixpkgs { inherit system; overlays = [ (import rust-overlay) ]; };
          toolchain = pkgs.rust-bin.stable."1.98.1".minimal.override { extensions = [ "rustfmt" "clippy" ]; };
          worker = (pkgs.makeRustPlatform { cargo = toolchain; rustc = toolchain; }).buildRustPackage {
            pname = "midnight-zkir-forge-zkir3-worker";
            version = "0.2.0";
            src = pkgs.lib.fileset.toSource { root = ./workers/zkir3; fileset = ./workers/zkir3; };
            cargoLock = {
              lockFile = ./workers/zkir3/Cargo.lock;
              outputHashes."midnight-base-crypto-1.0.0" = "sha256-mYOsQLJ5f8WJfuu13pEQAiQ3N2mPNNjUGQnzIQuJuOA=";
            };
            nativeBuildInputs = [ pkgs.pkg-config ];
            buildInputs = [ pkgs.openssl ];
          };
      in {
        zkir3-worker = worker;
        default = (pkgs.makeRustPlatform { cargo = toolchain; rustc = toolchain; }).buildRustPackage {
          pname = "midnight-zkir-forge";
          version = "0.2.0";
          src = pkgs.lib.fileset.toSource {
            root = ./.;
            fileset = pkgs.lib.fileset.unions [ ./Cargo.toml ./Cargo.lock ./build.rs ./flake.lock ./src ./tests ./fixtures ./workers/zkir3 ];
          };
          cargoLock = {
            lockFile = ./Cargo.lock;
            outputHashes."midnight-base-crypto-1.0.2" = "sha256-iNrhLPBGrWxeospwl8eW4TtYNlk+vY5Y564OTRjwBoM=";
          };
          nativeBuildInputs = [ pkgs.pkg-config ];
          buildInputs = [ pkgs.openssl ];
          MIDNIGHT_ZKIR_FORGE_ZKIR3_WORKER = "${worker}/bin/midnight-zkir-forge-zkir3-worker";
          postInstall = ''
            ln -s ${worker}/bin/midnight-zkir-forge-zkir3-worker $out/bin/midnight-zkir-forge-zkir3-worker
          '';
        };
      });
    };
}
