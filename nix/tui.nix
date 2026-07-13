# nix/tui.nix — Xavani TUI (Ink/React) compiled with tsc and bundled
{ pkgs, xavaniNpmLib, ... }:
let
  src = ../ui-tui;
  npmDeps = pkgs.fetchNpmDeps {
    inherit src;
    hash = "sha256-mMZBB4Q1+T5uxKJfyX3YFSP6IO5yllLapvlSUWFyF+8=";
  };

  npm = xavaniNpmLib.mkNpmPassthru { folder = "ui-tui"; attr = "tui"; pname = "xavani-tui"; };

  packageJson = builtins.fromJSON (builtins.readFile (src + "/package.json"));
  version = packageJson.version;
in
pkgs.buildNpmPackage (npm // {
  pname = "xavani-tui";
  inherit src npmDeps version;

  doCheck = false;
  npmFlags = [ "--legacy-peer-deps" ];

  installPhase = ''
    runHook preInstall

    mkdir -p $out/lib/xavani-tui

    # Single self-contained bundle built by scripts/build.mjs (esbuild).
    cp -r dist $out/lib/xavani-tui/dist

    # package.json kept for "type": "module" resolution on `node dist/entry.js`.
    cp package.json $out/lib/xavani-tui/

    runHook postInstall
  '';
})
