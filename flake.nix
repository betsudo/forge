{
  description = "Midnight ZKIR Forge: local ledger8 artifact cache";
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  # Current unstable no longer supports Intel macOS; keep that target on stable.
  inputs.nixpkgs-intel.url = "github:NixOS/nixpkgs/nixpkgs-26.05-darwin";
  inputs.rust-overlay.url = "github:oxalica/rust-overlay/ca7f624be3935a5bc46d2c240515491ab8675503";
  inputs.rust-overlay.inputs.nixpkgs.follows = "nixpkgs";
  outputs = { self, nixpkgs, nixpkgs-intel, rust-overlay }:
    let
      systems = [ "aarch64-darwin" "x86_64-darwin" "aarch64-linux" "x86_64-linux" ];
      eachSystem = nixpkgs.lib.genAttrs systems;
      platformPkgs = system: if system == "x86_64-darwin" then nixpkgs-intel else nixpkgs;
      version = (builtins.fromTOML (builtins.readFile ./Cargo.toml)).package.version;
    in {
      devShells = eachSystem (system: let pkgs = import (platformPkgs system) { inherit system; overlays = [ (import rust-overlay) ]; };
          toolchain = pkgs.rust-bin.stable."1.98.1".minimal.override { extensions = [ "rustfmt" "clippy" ]; };
      in {
        default = pkgs.mkShell {
          packages = with pkgs; [ toolchain pkg-config openssl sqlite python3 nodejs_24 git gnupg ripgrep actionlint pi-coding-agent ];
          shellHook = ''
            export CARGO_BUILD_JOBS="''${CARGO_BUILD_JOBS:-2}"
          '';
        };
      });
      packages = eachSystem (system: let pkgs = import (platformPkgs system) { inherit system; overlays = [ (import rust-overlay) ]; };
          toolchain = pkgs.rust-bin.stable."1.98.1".minimal.override { extensions = [ "rustfmt" "clippy" ]; };
          worker = (pkgs.makeRustPlatform { cargo = toolchain; rustc = toolchain; }).buildRustPackage {
            pname = "midnight-zkir-forge-zkir3-worker";
            inherit version;
            src = pkgs.lib.fileset.toSource { root = ./.; fileset = pkgs.lib.fileset.unions [ ./workers/zkir3 ./src/error.rs ]; };
            sourceRoot = "source/workers/zkir3";
            cargoLock = {
              lockFile = ./workers/zkir3/Cargo.lock;
              outputHashes."midnight-base-crypto-1.0.0" = "sha256-mYOsQLJ5f8WJfuu13pEQAiQ3N2mPNNjUGQnzIQuJuOA=";
            };
            nativeBuildInputs = [ pkgs.pkg-config ];
            buildInputs = [ pkgs.openssl ];
          };
          worker31 = (pkgs.makeRustPlatform { cargo = toolchain; rustc = toolchain; }).buildRustPackage {
            pname = "midnight-zkir-forge-zkir31-worker";
            inherit version;
            src = pkgs.lib.fileset.toSource { root = ./.; fileset = pkgs.lib.fileset.unions [ ./workers/zkir31 ./src/error.rs ]; };
            sourceRoot = "source/workers/zkir31";
            cargoLock = {
              lockFile = ./workers/zkir31/Cargo.lock;
              outputHashes."midnight-base-crypto-1.1.0" = "sha256-efaVU+wDP87weye/J9jO4HbixQ9KyVmyK1IrSxGn6c4=";
              outputHashes."midnight-zkir-3.1.0-rc.1" = "sha256-zYjKc5jNnUXqHVCzovcSOuh7wvjzQN4unb19IbBwbiQ=";
            };
            nativeBuildInputs = [ pkgs.pkg-config ];
            buildInputs = [ pkgs.openssl ];
          };
          forge = (pkgs.makeRustPlatform { cargo = toolchain; rustc = toolchain; }).buildRustPackage {
          pname = "midnight-zkir-forge";
          inherit version;
          src = pkgs.lib.fileset.toSource {
            root = ./.;
            fileset = pkgs.lib.fileset.unions [ ./Cargo.toml ./Cargo.lock ./build.rs ./flake.lock ./src ./tests ./examples ./fixtures ./docs/http/openapi.json ./workers/zkir3 ./workers/zkir31 ./benchmarks/did/prove.rs ./scripts/forge-ci.py ];
          };
          cargoLock = {
            lockFile = ./Cargo.lock;
            outputHashes."midnight-base-crypto-1.0.2" = "sha256-iNrhLPBGrWxeospwl8eW4TtYNlk+vY5Y564OTRjwBoM=";
          };
          nativeBuildInputs = [ pkgs.pkg-config pkgs.makeWrapper ];
          buildInputs = [ pkgs.openssl ];
          MIDNIGHT_ZKIR_FORGE_ZKIR3_WORKER = "${worker}/bin/midnight-zkir-forge-zkir3-worker";
          MIDNIGHT_ZKIR_FORGE_ZKIR31_WORKER = "${worker31}/bin/midnight-zkir-forge-zkir31-worker";
          postInstall = ''
            ln -s ${worker}/bin/midnight-zkir-forge-zkir3-worker $out/bin/midnight-zkir-forge-zkir3-worker
            ln -s ${worker31}/bin/midnight-zkir-forge-zkir31-worker $out/bin/midnight-zkir-forge-zkir31-worker
            install -Dm644 scripts/forge-ci.py $out/share/midnight-zkir-forge/forge-ci.py
            makeWrapper ${pkgs.python3}/bin/python3 $out/bin/midnight-zkir-forge-ci \
              --add-flags "$out/share/midnight-zkir-forge/forge-ci.py --binary $out/bin/midnight-zkir-forge"
          '';
        };
      in {
        default = forge;
        zkir3-worker = worker;
        zkir31-worker = worker31;
      } // pkgs.lib.optionalAttrs pkgs.stdenv.hostPlatform.isLinux {
        dockerImage = pkgs.dockerTools.buildLayeredImage {
          name = "midnight-zkir-forge";
          tag = version;
          contents = [ forge pkgs.cacert ];
          extraCommands = ''
            mkdir -p data params tmp run/secrets
            chmod 1777 tmp
          '';
          fakeRootCommands = ''
            chown 65532:65532 data params
          '';
          config = {
            User = "65532:65532";
            WorkingDir = "/data";
            Entrypoint = [ "${forge}/bin/midnight-zkir-forge" "--cache-dir" "/data" "--params-dir" "/params" ];
            Cmd = [ "serve" "--listen" "0.0.0.0:8787" "--token-file" "/run/secrets/forge-token" ];
            ExposedPorts."8787/tcp" = { };
            Volumes."/data" = { };
            Env = [ "SSL_CERT_FILE=${pkgs.cacert}/etc/ssl/certs/ca-bundle.crt" ];
            Labels = {
              "org.opencontainers.image.title" = "Midnight ZKIR Forge";
              "org.opencontainers.image.source" = "https://github.com/betsudo/forge";
              "org.opencontainers.image.version" = version;
            };
          };
        };
      });
    };
}
