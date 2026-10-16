{
  description = "Pinned Forge package for a consumer dev shell";
  # Exact migrated baseline; backend and dependency pins are unchanged.
  inputs.forge.url = "github:betsudo/forge/9b1d7bbd6f55d05adb8d0543c16b659ac24e6e80";
  inputs.nixpkgs.follows = "forge/nixpkgs";
  inputs.nixpkgs-intel.follows = "forge/nixpkgs-intel";
  outputs = { self, forge, nixpkgs, nixpkgs-intel }:
    let
      systems = [ "aarch64-darwin" "x86_64-darwin" "aarch64-linux" "x86_64-linux" ];
    in {
      devShells = nixpkgs.lib.genAttrs systems (system: {
        default = (import (if system == "x86_64-darwin" then nixpkgs-intel else nixpkgs) { inherit system; }).mkShell {
          packages = [ forge.packages.${system}.default ];
        };
      });
    };
}
