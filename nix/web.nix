# nix/web.nix — Xavani Web Dashboard (Vite/React) frontend build
{ pkgs, xavaniNpmLib, ... }:
let
  src = ../web;
  npmDeps = pkgs.fetchNpmDeps {
    inherit src;
    hash = "sha256-Tj9n92N3LfVpMA8YhIF0CXuntx2CddR2hx47psfvStk=";
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
