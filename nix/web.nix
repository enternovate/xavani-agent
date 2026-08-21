# nix/web.nix — Xavani Web Dashboard (Vite/React) frontend build
{ pkgs, xavaniNpmLib, ... }:
let
  src = ../web;
  npmDeps = pkgs.fetchNpmDeps {
    inherit src;
    hash = "sha256-2IgXxCRUc5t6U6Q4VO7RzUksekaXNA47ScEXUAnx6qQ=";
  };

  npm = xavaniNpmLib.mkNpmPassthru { folder = "web"; attr = "web"; pname = "xavani-web"; };

  packageJson = builtins.fromJSON (builtins.readFile (src + "/package.json"));
  version = packageJson.version;
in
pkgs.buildNpmPackage (npm // {
  pname = "xavani-web";
  inherit src npmDeps version;

  doCheck = false;

  buildPhase = ''
    npx tsc -b
    npx vite build --outDir dist
  '';

  installPhase = ''
    runHook preInstall
    cp -r dist $out
    runHook postInstall
  '';
})
