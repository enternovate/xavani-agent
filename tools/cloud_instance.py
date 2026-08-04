# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""F10: Cloud-hosted managed instance manifest generator.

Generates the provisioning spec for a hosted Xavani instance: a
deterministic manifest.json (instance type, region, SSH access, API-key
auth, gateway port) plus the provision.sh bootstrap script. Validation
checks the manifest shape (required keys, SSH + API-key auth enabled)
and that the bootstrap script is present and executable.

Usage::

    from tools.cloud_instance import generate_cloud_manifest, validate_manifest

    files = generate_cloud_manifest(version="0.1.0")
    problems = validate_manifest(files)
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

INSTANCE_NAME = "xavani-managed"
MANIFEST_PATH = "cloud/manifest.json"
PROVISION_PATH = "cloud/provision.sh"


def _manifest(version: str) -> Dict[str, Any]:
    """Build the provisioning spec dict for the given version."""
    return {
        "name": INSTANCE_NAME,
        "version": version,
        "description": "Hosted Xavani instance with SSH into managed VMs. Auth via API key.",
        "provider": {
            "vendor": "generic-cloud",
            "region": "us-east-1",
            "instance_type": "t3.medium",
            "image": "ubuntu-24.04",
        },
        "access": {
            "ssh": {
                "enabled": True,
                "port": 22,
                "key_name": "xavani-managed-key",
            },
            "api_key_auth": True,
            "gateway_port": 8765,
        },
        "bootstrap": PROVISION_PATH,
        "features": ["gateway", "ssh", "api-key-auth"],
    }


_PROVISION_SH = """\
#!/bin/sh
# xavani-managed — provision a managed Xavani instance.
# Installs the agent, starts the gateway, and opens the API port.
set -eu

XAVANI_VERSION="${XAVANI_VERSION:-__VERSION__}"
GATEWAY_PORT="${XAVANI_GATEWAY_PORT:-8765}"

# Install the agent from PyPI (managed builds only; no secrets in image).
pip install "xavani-agent==${XAVANI_VERSION}"

# Start the gateway on the API port.
XAVANI_HOME="${XAVANI_HOME:-/var/lib/xavani}" xavani gateway run --port "${GATEWAY_PORT}" &

# Open the API port (firewall rules vary by vendor).
if command -v ufw >/dev/null 2>&1; then
  ufw allow "${GATEWAY_PORT}/tcp"
fi

echo "xavani-managed ready on port ${GATEWAY_PORT}"
"""


def generate_cloud_manifest(version: str) -> Dict[str, str]:
    """Generate the cloud instance files. Returns {path: content}."""
    provision = _PROVISION_SH.replace("__VERSION__", version)
    return {
        MANIFEST_PATH: json.dumps(_manifest(version), indent=2) + "\n",
        PROVISION_PATH: provision,
    }


def validate_manifest(files: Dict[str, str]) -> List[str]:
    """Validate the cloud instance manifest. Returns a list of problems."""
    problems: List[str] = []
    for required in (MANIFEST_PATH, PROVISION_PATH):
        if required not in files:
            problems.append(f"missing {required}")
    try:
        manifest = json.loads(files.get(MANIFEST_PATH, "{}"))
        if manifest.get("name") != INSTANCE_NAME:
            problems.append(f"instance name must be {INSTANCE_NAME}")
        if not manifest.get("version"):
            problems.append("manifest version missing")
        provider = manifest.get("provider", {})
        for key in ("vendor", "region", "instance_type", "image"):
            if not provider.get(key):
                problems.append(f"provider.{key} missing")
        access = manifest.get("access", {})
        ssh = access.get("ssh", {})
        if not ssh.get("enabled"):
            problems.append("ssh access must be enabled")
        if not access.get("api_key_auth"):
            problems.append("api_key_auth must be enabled")
        if not access.get("gateway_port"):
            problems.append("gateway_port missing")
    except json.JSONDecodeError as exc:
        problems.append(f"manifest.json invalid: {exc}")
    provision = files.get(PROVISION_PATH, "")
    if provision and not provision.startswith("#!"):
        problems.append("provision.sh missing shebang")
    return problems
