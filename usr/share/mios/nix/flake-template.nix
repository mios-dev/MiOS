{
  description = "MiOS Declarative User Environment and Dotfiles Flake";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    home-manager = {
      url = "github:nix-community/home-manager";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = { self, nixpkgs, home-manager, ... }:
    let
      system = "__SYSTEM_ARCH__";
      pkgs = import nixpkgs {
        inherit system;
        config = { allowUnfree = true; };
      };

      # Generated from mios.toml [packages]
      declaredPackages = with pkgs; [
__DECLARED_PACKAGES__
      ];

      # Generated from mios.toml [shell]
      declaredAliases = {
__DECLARED_ALIASES__
      };

      # Generated from mios.toml [dotfiles]
      declaredDotfiles = {
__DECLARED_DOTFILES__
      };
    in {
      packages.${system}.default = pkgs.buildEnv {
        name = "mios-user-profile";
        paths = declaredPackages;
      };

      homeConfigurations.__USERNAME__ = home-manager.lib.homeManagerConfiguration {
        inherit pkgs;
        modules = [
          {
            home.username = "__USERNAME__";
            home.homeDirectory = "/home/__USERNAME__";
            home.stateVersion = "__STATE_VERSION__";
            home.packages = declaredPackages;

            programs.bash = {
              enable = true;
              shellAliases = declaredAliases;
            };

            home.file = declaredDotfiles;
          }
        ];
      };
    };
}
