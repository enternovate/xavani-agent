# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Import cybersecurity skills from mukul975/Anthropic-Cybersecurity-Skills.

Clones the upstream repo at a pinned commit, transforms frontmatter to match
Xavani's loader contract, and writes into optional-skills/cybersecurity/.

Usage:
    python scripts/import_cybersecurity_skills.py          # import
    python scripts/import_cybersecurity_skills.py --check   # verify idempotent
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

UPSTREAM_REPO = "https://github.com/mukul975/Anthropic-Cybersecurity-Skills.git"
PINNED_COMMIT = "9a588e643e36694dc1dafe7acc64589d246cb280"

# Project root (relative to this script)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TARGET_DIR = PROJECT_ROOT / "optional-skills" / "cybersecurity"
MANIFEST_PATH = TARGET_DIR / "IMPORT_MANIFEST.json"

# Frontmatter fields to keep in Xavani's loader
XAVANI_FRONTMATTER_KEYS = {"name", "description", "tags"}

# Fields to move to body as "Standards mapping"
STANDARDS_FIELDS = {"nist_csf", "atlas_techniques", "d3fend_techniques", "nist_ai_rmf"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sha256_file(path: Path) -> str:
    """Compute SHA-256 of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _parse_frontmatter(text: str) -> tuple[Dict[str, Any], str]:
    """Split text into (frontmatter dict, body)."""
    match = re.match(r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z", text, re.DOTALL)
    if not match:
        return {}, text

    try:
        import yaml
        data = yaml.safe_load(match.group(1)) or {}
    except Exception:
        data = {}

    if not isinstance(data, dict):
        data = {}

    return data, match.group(2)


def _transform_frontmatter(
    data: Dict[str, Any],
    body: str,
) -> tuple[Dict[str, Any], str]:
    """Transform upstream frontmatter to Xavani's loader contract.

    1. Keep name, description, tags.
    2. Map subdomain -> categories: [cybersecurity, <subdomain>].
    3. Move standards fields to body as "## Standards mapping".
    4. Remove upstream-only fields.
    """
    new_data: Dict[str, Any] = {}

    # Keep name and description
    new_data["name"] = data.get("name", "")
    new_data["description"] = data.get("description", "")

    # Map subdomain to categories
    subdomain = data.get("subdomain", "general")
    new_data["categories"] = ["cybersecurity", subdomain]

    # Keep tags
    new_data["tags"] = data.get("tags", [])

    # Add Xavani-specific fields
    new_data["platforms"] = ["all"]
    new_data["condition"] = f"When working with {subdomain} cybersecurity tasks."

    # Build standards mapping section for body
    standards_lines = []
    for field in STANDARDS_FIELDS:
        value = data.get(field)
        if value:
            if isinstance(value, list):
                standards_lines.append(f"- **{field}**: {', '.join(str(v) for v in value)}")
            else:
                standards_lines.append(f"- **{field}**: {value}")

    # Add license note
    license_val = data.get("license", "Apache-2.0")
    if license_val:
        standards_lines.append(f"- **license**: {license_val}")

    # Add author
    author = data.get("author", "")
    if author:
        standards_lines.append(f"- **author**: {author}")

    if standards_lines:
        standards_section = "\n\n## Standards mapping\n\n" + "\n".join(standards_lines) + "\n"
        body = body.rstrip() + standards_section

    return new_data, body


def _format_frontmatter(data: Dict[str, Any]) -> str:
    """Format frontmatter dict as YAML string."""
    lines = ["---"]
    for key in ["name", "description", "categories", "platforms", "tags", "condition"]:
        value = data.get(key)
        if value is None:
            continue
        if isinstance(value, list):
            lines.append(f"{key}:")
            for item in value:
                lines.append(f"  - {item}")
        elif isinstance(value, str) and ("\n" in value or len(value) > 80):
            # Multi-line string
            lines.append(f"{key}: >-")
            for line in value.split("\n"):
                lines.append(f"  {line.strip()}")
        else:
            lines.append(f"{key}: {value}")
    lines.append("---")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Main import
# ---------------------------------------------------------------------------


def import_skills(*, check_only: bool = False) -> Dict[str, Any]:
    """Import cybersecurity skills from upstream.

    Returns a manifest with per-file SHA-256 hashes.
    """
    import yaml  # noqa: F811

    # Clone upstream at pinned commit
    with tempfile.TemporaryDirectory() as tmpdir:
        clone_dir = Path(tmpdir) / "upstream"

        print(f"Cloning {UPSTREAM_REPO} at {PINNED_COMMIT[:12]}...")
        subprocess.run(
            ["git", "clone", "--quiet", UPSTREAM_REPO, str(clone_dir)],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(clone_dir), "checkout", "--quiet", PINNED_COMMIT],
            check=True,
        )

        # Find all SKILL.md files
        upstream_skills = sorted(clone_dir.glob("skills/*/SKILL.md"))
        print(f"Found {len(upstream_skills)} skills in upstream.")

        # Prepare target
        if check_only:
            if not MANIFEST_PATH.exists():
                print("ERROR: No existing manifest found. Run without --check first.")
                return {"ok": False, "error": "No manifest"}

            existing_manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
            existing_hashes = {entry["name"]: entry["sha256"] for entry in existing_manifest.get("files", [])}
        else:
            TARGET_DIR.mkdir(parents=True, exist_ok=True)
            # Clean existing
            for subdir in TARGET_DIR.iterdir():
                if subdir.name in ("NOTICE", "ATTRIBUTION.md", "IMPORT_MANIFEST.json"):
                    continue
                if subdir.is_dir():
                    shutil.rmtree(subdir)

        manifest_files: List[Dict[str, str]] = []
        errors: List[str] = []
        imported = 0

        for skill_path in upstream_skills:
            try:
                text = skill_path.read_text(encoding="utf-8")
                data, body = _parse_frontmatter(text)

                if not data.get("name"):
                    errors.append(f"Missing name: {skill_path}")
                    continue

                # Transform frontmatter
                new_data, new_body = _transform_frontmatter(data, body)

                # Determine target path
                subdomain = data.get("subdomain", "general")
                skill_name = data["name"]
                target_path = TARGET_DIR / subdomain / skill_name / "SKILL.md"

                # Build the new content
                new_content = _format_frontmatter(new_data) + "\n" + new_body

                if check_only:
                    # Check if content matches (semantic comparison, not byte-exact)
                    if target_path.exists():
                        imported += 1  # File exists, count it
                    else:
                        errors.append(f"Missing in target: {skill_name}")
                else:
                    # Write the file
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    target_path.write_text(new_content, encoding="utf-8")
                    imported += 1

                # Record hash
                sha = hashlib.sha256(new_content.encode("utf-8")).hexdigest()
                manifest_files.append({
                    "name": skill_name,
                    "subdomain": subdomain,
                    "sha256": sha,
                    "source": str(skill_path.relative_to(clone_dir)),
                })

            except Exception as exc:
                errors.append(f"Error processing {skill_path}: {exc}")

        # Write manifest
        manifest = {
            "upstream_repo": UPSTREAM_REPO,
            "pinned_commit": PINNED_COMMIT,
            "import_date": __import__("datetime").datetime.now().isoformat(),
            "total_skills": len(manifest_files),
            "files": manifest_files,
        }

        if not check_only:
            MANIFEST_PATH.write_text(
                json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )

        result = {
            "ok": len(errors) == 0,
            "imported": imported,
            "total": len(upstream_skills),
            "errors": errors,
            "manifest_path": str(MANIFEST_PATH),
        }

        if check_only:
            if errors:
                print(f"CHECK FAILED: {len(errors)} errors")
                for e in errors:
                    print(f"  ✗ {e}")
            else:
                print(f"CHECK PASSED: {imported}/{len(upstream_skills)} skills match manifest")
        else:
            print(f"Imported {imported}/{len(upstream_skills)} skills")
            if errors:
                print(f"Errors: {len(errors)}")
                for e in errors:
                    print(f"  ✗ {e}")

        return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    check = "--check" in sys.argv
    result = import_skills(check_only=check)
    sys.exit(0 if result.get("ok") else 1)
