{
  description = "Pinned private Forge package for a consumer dev shell";
  # Reviewed local commit; remote use requires its later authorized publication.
  inputs.forge.url = "git+ssh://git@github.com/input-output-hk/midnight-zkir-forge?rev=f3801e08f1e3af0f1a2c7b3e0e6a5c7070fa4d3a";
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
