# nix/xavani-agent.nix — Overridable Xavani Agent package
#
# callPackage auto-wires nixpkgs args; flake inputs are passed explicitly.
# Users override via:
#   pkgs.xavani-agent.override { extraPythonPackages = [...]; }
#   pkgs.xavani-agent.override { extraDependencyGroups = [ "hindsight" ]; }
{
  lib,
  stdenv,
  makeWrapper,
  callPackage,
  python312,
  nodejs_22,
  ripgrep,
  git,
  openssh,
  ffmpeg,
  tirith,
  # Flake inputs — passed explicitly by packages.nix and overlays.nix
  uv2nix,
  pyproject-nix,
  pyproject-build-systems,
  npm-lockfile-fix,
  # Locked git revision of the flake source — embedded so banner.py can
  # check for updates without needing a local .git directory. Null for
  # impure / dirty builds where flakes can't determine a rev.
  rev ? null,
  # Overridable parameters
  extraPythonPackages ? [ ],
  extraDependencyGroups ? [ ],
}:
let
  nodejs = nodejs_22;
  xavaniVenv = callPackage ./python.nix {
    inherit uv2nix pyproject-nix pyproject-build-systems;
    dependency-groups = [ "all" ] ++ extraDependencyGroups;
  };

  xavaniNpmLib = callPackage ./lib.nix {
    inherit npm-lockfile-fix nodejs;
  };

  xavaniTui = callPackage ./tui.nix {
    inherit xavaniNpmLib;
  };

  xavaniWeb = callPackage ./web.nix {
    inherit xavaniNpmLib;
  };

  bundledSkills = lib.cleanSourceWith {
    src = ../skills;
    filter = path: _type: !(lib.hasInfix "/index-cache/" path);
  };

  # Import bundled plugins (memory, context_engine, platforms/*).  Keeping
  # them out of the Python site-packages keeps import semantics identical
  # to a dev checkout — the loader reads them from XAVANI_BUNDLED_PLUGINS.
  bundledPlugins = lib.cleanSourceWith {
    src = ../plugins;
    filter = path: _type: !(lib.hasInfix "/__pycache__/" path);
  };

  runtimeDeps = [
    nodejs
    ripgrep
    git
    openssh
    ffmpeg
    tirith
  ];

  runtimePath = lib.makeBinPath runtimeDeps;

  sitePackagesPath = python312.sitePackages;

  # Walk propagatedBuildInputs to include transitive Python deps in PYTHONPATH.
  # Without this, a plugin listing e.g. requests as a dep would fail at runtime
  # if requests isn't already in the sealed uv2nix venv.
  allExtraPythonPackages = python312.pkgs.requiredPythonModules extraPythonPackages;

  pythonPath = lib.makeSearchPath sitePackagesPath allExtraPythonPackages;

  pyprojectHash = builtins.hashString "sha256" (builtins.readFile ../pyproject.toml);
  uvLockHash =
    if builtins.pathExists ../uv.lock then
      builtins.hashString "sha256" (builtins.readFile ../uv.lock)
    else
      "none";
  checkPackageCollisions = ''
    import pathlib, sys, re

    def canonical(name):
        return re.sub(r'[-_.]+', '-', name).lower()

    # Collect core venv package names
    core = set()
    venv_sp = pathlib.Path('${xavaniVenv}/${sitePackagesPath}')
    for di in venv_sp.glob('*.dist-info'):
        meta = di / 'METADATA'
        if meta.exists():
            for line in meta.read_text().splitlines():
                if line.startswith('Name:'):
                    core.add(canonical(line.split(':', 1)[1].strip()))
                    break

    # Check each extra package for collisions
    extras_dirs = [${lib.concatMapStringsSep ", " (p: "'${toString p}'") allExtraPythonPackages}]
    for edir in extras_dirs:
        sp = pathlib.Path(edir) / '${sitePackagesPath}'
        if not sp.exists():
            continue
        for di in sp.glob('*.dist-info'):
            meta = di / 'METADATA'
            if not meta.exists():
                continue
            for line in meta.read_text().splitlines():
                if line.startswith('Name:'):
                    pkg = canonical(line.split(':', 1)[1].strip())
                    if pkg in core:
                        print(f'ERROR: plugin package \"{pkg}\" collides with a package in xavani sealed venv', file=sys.stderr)
                        print(f'  from: {di}', file=sys.stderr)
                        print(f'  Remove this dependency from extraPythonPackages.', file=sys.stderr)
                        sys.exit(1)
                    break

    print('No collisions found.')
  '';
in
stdenv.mkDerivation {
  pname = "xavani-agent";
  version = (fromTOML (builtins.readFile ../pyproject.toml)).project.version;

  dontUnpack = true;
  dontBuild = true;
  nativeBuildInputs = [ makeWrapper ];

  installPhase = ''
    runHook preInstall

    mkdir -p $out/share/xavani-agent $out/bin
    cp -r ${bundledSkills} $out/share/xavani-agent/skills
    cp -r ${bundledPlugins} $out/share/xavani-agent/plugins
    cp -r ${xavaniWeb} $out/share/xavani-agent/web_dist

    mkdir -p $out/ui-tui
    cp -r ${xavaniTui}/lib/xavani-tui/* $out/ui-tui/

    ${lib.concatMapStringsSep "\n"
      (name: ''
        makeWrapper ${xavaniVenv}/bin/${name} $out/bin/${name} \
          --suffix PATH : "${runtimePath}" \
          --set XAVANI_BUNDLED_SKILLS $out/share/xavani-agent/skills \
          --set XAVANI_BUNDLED_PLUGINS $out/share/xavani-agent/plugins \
          --set XAVANI_WEB_DIST $out/share/xavani-agent/web_dist \
          --set XAVANI_TUI_DIR $out/ui-tui \
          --set XAVANI_PYTHON ${xavaniVenv}/bin/python3 \
          --set XAVANI_NODE ${lib.getExe nodejs} \
          ${lib.optionalString (rev != null) ''--set XAVANI_REVISION ${rev} \''}
          ${lib.optionalString (extraPythonPackages != [ ]) ''--suffix PYTHONPATH : "${pythonPath}"''}
      '')
      [
        "xavani"
        "xavani-agent"
        "xavani-acp"
      ]
    }

    ${lib.optionalString (extraPythonPackages != [ ]) ''
      echo "=== Checking for plugin/core package collisions ==="
      ${xavaniVenv}/bin/python3 -c "${checkPackageCollisions}"
      echo "=== No collisions ==="
    ''}

    runHook postInstall
  '';

  passthru = {
    inherit
      xavaniTui
      xavaniWeb
      xavaniNpmLib
      xavaniVenv
      ;

    devShellHook = ''
      STAMP=".nix-stamps/xavani-agent"
      STAMP_VALUE="${pyprojectHash}:${uvLockHash}"
      if [ ! -f "$STAMP" ] || [ "$(cat "$STAMP")" != "$STAMP_VALUE" ]; then
        echo "xavani-agent: installing Python dependencies..."
        uv venv .venv --python ${python312}/bin/python3 2>/dev/null || true
        source .venv/bin/activate
        uv pip install -e ".[all]"
        [ -d mini-swe-agent ] && uv pip install -e ./mini-swe-agent 2>/dev/null || true
        mkdir -p .nix-stamps
        echo "$STAMP_VALUE" > "$STAMP"
      else
        source .venv/bin/activate
        export XAVANI_PYTHON=${xavaniVenv}/bin/python3
      fi
    '';
  };

  meta = with lib; {
    description = "AI agent with advanced tool-calling capabilities";
    homepage = "https://github.com/NousResearch/hermes-agent";
    mainProgram = "xavani";
    license = licenses.mit;
    platforms = platforms.unix;
  };
}
