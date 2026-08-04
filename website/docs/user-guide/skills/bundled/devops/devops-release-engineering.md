---
title: "Release Engineering — Manage releases, changelogs, versioning, and deployment pipelines with discipline"
sidebar_label: "Release Engineering"
description: "Manage releases, changelogs, versioning, and deployment pipelines with discipline"
---

{/* This page is auto-generated from the skill's SKILL.md by website/scripts/generate-skill-docs.py. Edit the source SKILL.md, not this page. */}

# Release Engineering

Manage releases, changelogs, versioning, and deployment pipelines with discipline.

## Skill metadata

| | |
|---|---|
| Source | Bundled (installed by default) |
| Path | `skills/devops/release-engineering` |
| Platforms | all |

## Reference: full SKILL.md

:::info
The following is the complete skill definition that Xavani loads when this skill is triggered. This is what the agent sees as instructions when the skill is active.
:::

# Release Engineering

> "A release is not an event — it is a process with gates."

## When to use

- Preparing a new version release.
- Writing or updating a changelog.
- Setting up CI/CD pipelines.
- Managing version numbers.

## Prerequisites

- All tests pass on main.
- Changelog entries collected.

## Steps

### 1. Version bump

Follow semver:
- **Major** (X.0.0): breaking changes.
- **Minor** (0.X.0): new features, backward-compatible.
- **Patch** (0.0.X): bug fixes.

Update version in:
- `pyproject.toml` / `package.json` / `Cargo.toml`
- Banner / CLI version strings
- Any version constants

### 2. Changelog

Format (Keep a Changelog):
```
## [1.2.0] - 2025-06-01

### Added
- New feature X

### Changed
- Improved Y performance by 40%

### Fixed
- Bug Z where...

### Removed
- Deprecated W
```

### 3. Tag and build

```bash
git tag -a v1.2.0 -m "Release 1.2.0"
git push origin v1.2.0
```

CI builds the release artifact.

### 4. Deploy

- Staging first, verify.
- Production with rollback plan.
- Monitor for 30 minutes post-deploy.

### 5. Post-release

- Announce to stakeholders.
- Update documentation.
- Close related issues.

## Verification

- Version bumped in all locations.
- Changelog is complete and accurate.
- Tag exists and points to the right commit.
- Deployment succeeded with monitoring active.
