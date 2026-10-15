{
  description = "Midnight ZKIR Forge: local ledger8 artifact cache";
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  outputs = { self, nixpkgs }:
    let
      systems = [ "aarch64-darwin" "x86_64-darwin" "aarch64-linux" "x86_64-linux" ];
      eachSystem = nixpkgs.lib.genAttrs systems;
    in {
      devShells = eachSystem (system: let pkgs = import nixpkgs { inherit system; }; in {
        default = pkgs.mkShell {
          packages = with pkgs; [ cargo rustc rustfmt clippy pkg-config openssl sqlite nodejs_24 git gnupg ripgrep pi-coding-agent ];
          shellHook = ''
            export CARGO_BUILD_JOBS="''${CARGO_BUILD_JOBS:-2}"
          '';
        };
      });
      packages = eachSystem (system: let pkgs = import nixpkgs { inherit system; }; in {
        default = pkgs.rustPlatform.buildRustPackage {
          pname = "midnight-zkir-forge";
          version = "0.1.0";
          src = self;
          cargoLock.lockFile = ./Cargo.lock;
          nativeBuildInputs = [ pkgs.pkg-config ];
          buildInputs = [ pkgs.openssl ];
        };
      });
    };
}
