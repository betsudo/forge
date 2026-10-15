{
  description = "Pinned private Forge package for a consumer dev shell";
  inputs.forge.url = "git+ssh://git@github.com/input-output-hk/midnight-zkir-forge?rev=5d9c4c62b8c59b4a2939943b762032ff9f390be8";
  inputs.nixpkgs.follows = "forge/nixpkgs";
  outputs = { self, forge, nixpkgs }:
    let
      systems = [ "aarch64-darwin" "x86_64-darwin" "aarch64-linux" "x86_64-linux" ];
    in {
      devShells = nixpkgs.lib.genAttrs systems (system: {
        default = (import nixpkgs { inherit system; }).mkShell {
          packages = [ forge.packages.${system}.default ];
        };
      });
    };
}
