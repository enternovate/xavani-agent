# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""F10: Cloud instance manifest tests."""

import json

from tools.cloud_instance import (
    INSTANCE_NAME,
    MANIFEST_PATH,
    PROVISION_PATH,
    generate_cloud_manifest,
    validate_manifest,
)


def test_generation_contains_required_files():
    files = generate_cloud_manifest("0.7.2")
    assert set(files.keys()) == {MANIFEST_PATH, PROVISION_PATH}


def test_manifest_name_version_and_auth():
    files = generate_cloud_manifest("0.7.2")
    manifest = json.loads(files[MANIFEST_PATH])
    assert manifest["name"] == INSTANCE_NAME
    assert manifest["version"] == "0.7.2"
    assert manifest["access"]["ssh"]["enabled"] is True
    assert manifest["access"]["api_key_auth"] is True


def test_manifest_provisioning_spec():
    files = generate_cloud_manifest("0.7.2")
    manifest = json.loads(files[MANIFEST_PATH])
    provider = manifest["provider"]
    assert provider["region"] == "us-east-1"
    assert provider["instance_type"] == "t3.medium"
    assert provider["image"] == "ubuntu-24.04"
    assert manifest["access"]["gateway_port"] == 8765


def test_provision_script_shebang_and_version():
    files = generate_cloud_manifest("0.7.2")
    provision = files[PROVISION_PATH]
    assert provision.startswith("#!/bin/sh")
    assert 'XAVANI_VERSION="${XAVANI_VERSION:-0.7.2}"' in provision


def test_validate_ok():
    files = generate_cloud_manifest("0.7.2")
    assert validate_manifest(files) == []


def test_validate_no_ssh():
    files = generate_cloud_manifest("0.7.2")
    manifest = json.loads(files[MANIFEST_PATH])
    manifest["access"]["ssh"]["enabled"] = False
    files[MANIFEST_PATH] = json.dumps(manifest)
    problems = validate_manifest(files)
    assert any("ssh" in p for p in problems)


def test_validate_bad_json():
    files = generate_cloud_manifest("0.7.2")
    files[MANIFEST_PATH] = "{not json"
    problems = validate_manifest(files)
    assert any("invalid" in p for p in problems)


def test_validate_empty():
    problems = validate_manifest({})
    assert problems
    assert any("missing" in p for p in problems)


def test_deterministic():
    assert generate_cloud_manifest("0.7.2") == generate_cloud_manifest("0.7.2")
