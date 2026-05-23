# nix/packages.nix — Xavani Agent package built with uv2nix
{ inputs, ... }:
{
  perSystem =
    { pkgs, inputs', ... }:
    let
      xavaniAgent = pkgs.callPackage ./xavani-agent.nix {
        inherit (inputs) uv2nix pyproject-nix pyproject-build-systems;
        npm-lockfile-fix = inputs'.npm-lockfile-fix.packages.default;
        # Only embed clean revs — dirtyRev doesn't represent any upstream
        # commit, so comparing it would always claim "update available".
        rev = inputs.self.rev or null;
      };
    in
    {
      packages = {
        default = xavaniAgent;
        tui = xavaniAgent.xavaniTui;
        web = xavaniAgent.xavaniWeb;

        fix-lockfiles = xavaniAgent.xavaniNpmLib.mkFixLockfiles {
          packages = [ xavaniAgent.xavaniTui xavaniAgent.xavaniWeb ];
        };
      };
    };
}
