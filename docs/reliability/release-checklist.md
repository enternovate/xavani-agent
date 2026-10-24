# Release checklist

Source: `planning/reliability-master-plan.md`, Task 26.
Version policy: keep the engine, the desktop, and the ACP manifest on one version.

## Release order

1. Produce local candidate artifacts.

```bash
cd ~/xavani-desktop
XAVANI_ENGINE_SRC=/Users/andilemushwana/xavani-agent bash scripts/build-macos.sh
```

2. Run package smoke tests with temporary user homes.

```bash
XAVANI_HOME="$(mktemp -d)" open build/dmg-stage/Xavani.app
```

3. Verify startup without a development checkout. Move the engine repo out of the search path first.
4. Verify the bundled engine revision.

```bash
python3 scripts/check_release_manifest.py \
  build/dmg-stage/Xavani.app/Contents/Resources/release-manifest.json \
  --engine /Users/andilemushwana/xavani-agent
```

5. Verify macOS signing and notarization.

```bash
codesign --verify --deep --strict build/dmg-stage/Xavani.app
spctl --assess --type execute --verbose=2 build/dmg-stage/Xavani.app
```

6. Verify Windows signing and installation. Use the `windows-build` workflow artifacts.
7. Verify an update from the previous supported release.
8. Verify rollback without state loss.
9. Record checksums and the compatibility matrix.

```bash
shasum -a 256 dist/*.dmg
```

10. Present the release evidence to Andile.
11. Obtain explicit publication approval.
12. Publish only the approved artifacts.
13. Read the exact release page and asset metadata after publication.

```bash
gh release view <tag> --json tagName,assets,url
```

14. Download the published artifact to verify its checksum.

## Rules

- Do not run steps 11 to 14 without explicit publication approval.
- Do not claim a public signature from an ad-hoc signature.
- Missing signing credentials block a public stable release. They do not block local testing.
- A missing or dirty engine source blocks the build. The build script enforces this.
