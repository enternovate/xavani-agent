# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for tools/security_scan_tool.py (heuristic security scanner)."""

import json
from pathlib import Path

from tools import security_scan_tool
from tools.security_scan_tool import security_scan

APP_PY = '''\
import hashlib
import pickle
import subprocess

import requests
import yaml

AWS_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPLE"


def load_config(stream):
    config = yaml.load(stream)
    return config


def run_command(command):
    result = subprocess.call(command, shell=True)
    return result


def unsafe_deserialize(blob):
    obj = pickle.loads(blob)
    return obj


def dangerous(user_input):
    return eval(user_input)


def check(url, payload):
    return requests.post(url, data=payload, verify=False)


def weak_password_hash(password):
    return hashlib.md5(password.encode()).hexdigest()


def build_query(name):
    query = f"SELECT * FROM users WHERE name = '{name}'"
    return query


def start_app(app):
    app.run(host="0.0.0.0", debug=True)
'''

CLEAN_PY = '''\
def add(left, right):
    total = left + right
    return total
'''


CREDS_TXT = 'api_key = "abcdef1234567890xyz"\n'


def build_tree(tmp_path: Path) -> Path:
    (tmp_path / "app.py").write_text(APP_PY, encoding="utf-8")
    (tmp_path / "clean.py").write_text(CLEAN_PY, encoding="utf-8")
    (tmp_path / "creds.txt").write_text(CREDS_TXT, encoding="utf-8")
    (tmp_path / "blob.bin").write_bytes(
        b"\x00\x01\x02AKIAIOSFODNN7EXAMPLE\x00\xff"
    )
    return tmp_path


def test_planted_vulns_found_with_expected_rules_and_counts(tmp_path):
    tree = build_tree(tmp_path)
    result = security_scan(str(tree))

    assert result["success"] is True
    assert result["files_scanned"] == 3
    assert result["summary"] == {"HIGH": 6, "MED": 3, "LOW": 1}

    by_rule = {}
    for finding in result["findings"]:
        by_rule.setdefault(finding["rule_id"], []).append(finding)

    assert set(by_rule) == {
        "hardcoded_secret",
        "dangerous_eval_exec",
        "subprocess_shell_true",
        "yaml_load_no_loader",
        "tls_verify_disabled",
        "pickle_load",
        "sql_string_build",
        "flask_debug_true",
        "weak_hash",
    }
    assert all(f["file"].endswith("app.py") for f in by_rule["yaml_load_no_loader"])
    assert len(by_rule["hardcoded_secret"]) == 2

    total = sum(result["summary"][key] for key in ("HIGH", "MED", "LOW"))
    assert total == len(result["findings"])


def test_secrets_are_masked_in_excerpts_and_raw_output(tmp_path):
    tree = build_tree(tmp_path)
    result = security_scan(str(tree))

    aws = next(
        f for f in result["findings"]
        if f["rule_id"] == "hardcoded_secret"
        and f["file"].endswith("app.py")
    )
    assert "AKIA" in aws["excerpt"]
    assert re_aws_masked(aws["excerpt"])
    assert "AKIAIOSFODNN7EXAMPLE" not in json.dumps(result)

    generic = next(
        f for f in result["findings"]
        if f["rule_id"] == "hardcoded_secret"
        and f["file"].endswith("creds.txt")
    )
    assert "***" in generic["excerpt"]
    assert "abcdef1234567890xyz" not in generic["excerpt"]
    assert all(len(f["excerpt"]) <= 80 for f in result["findings"])


def re_aws_masked(excerpt: str) -> bool:
    head = excerpt.split("***", 1)[0]
    return excerpt.count("***") >= 1 and head.endswith("AKIA")


def test_binary_file_is_skipped(tmp_path):
    tree = build_tree(tmp_path)
    result = security_scan(str(tree))

    assert not any(f["file"].endswith("blob.bin") for f in result["findings"])
    assert "AKIAIOSFODNN7EXAMPLE" not in json.dumps(result)


def test_vendor_and_vcs_directories_are_skipped(tmp_path):
    leaked = 'token = "ghp_Abcdefghijklmnopqrstuvwxyz1234"\n'
    git_dir = tmp_path / ".git"
    node_dir = tmp_path / "node_modules" / "pkg"
    git_dir.mkdir(parents=True)
    node_dir.mkdir(parents=True)
    (git_dir / "leak.py").write_text(leaked, encoding="utf-8")
    (node_dir / "index.js").write_text(leaked, encoding="utf-8")
    (tmp_path / "main.py").write_text(CLEAN_PY, encoding="utf-8")

    result = security_scan(str(tmp_path))

    assert result["files_scanned"] == 1
    assert result["findings"] == []
    assert result["summary"] == {"HIGH": 0, "MED": 0, "LOW": 0}


def test_missing_path_reports_failure_without_raising(tmp_path):
    missing = str(tmp_path / "does_not_exist")

    result = security_scan(missing)

    assert result["success"] is False
    assert "error" in result
    assert result["findings"] == []


def test_max_files_limits_scanned_file_count(tmp_path):
    for index in range(6):
        (tmp_path / f"vuln_{index:02d}.py").write_text(
            "import subprocess\n"
            f"subprocess.call('cmd{index}', shell=True)\n",
            encoding="utf-8",
        )

    result = security_scan(str(tmp_path), max_files=3)

    assert result["success"] is True
    assert result["files_scanned"] == 3
    assert len(result["findings"]) == 3
    scanned = {f["file"] for f in result["findings"]}
    expected = {
        str(tmp_path / f"vuln_{index:02d}.py") for index in range(3)
    }
    assert scanned == expected
    assert result["summary"]["HIGH"] == 3


def test_single_file_target_scans_only_that_file(tmp_path):
    target = tmp_path / "single.py"
    target.write_text(
        "import pickle\npickle.loads(b'x')\n", encoding="utf-8"
    )
    other = tmp_path / "other.py"
    other.write_text("import subprocess\nsubprocess.call(c, shell=True)\n", encoding="utf-8")

    result = security_scan(str(target))

    assert result["success"] is True
    assert result["files_scanned"] == 1
    assert {f["rule_id"] for f in result["findings"]} == {"pickle_load"}


def test_handler_returns_json_string(tmp_path):
    tree = build_tree(tmp_path)
    raw = security_scan_tool._handle_security_scan({"path": str(tree)})
    parsed = json.loads(raw)

    assert isinstance(raw, str)
    assert parsed["success"] is True
    assert parsed["summary"]["HIGH"] == 6

    missing_raw = security_scan_tool._handle_security_scan(
        {"path": str(tmp_path / "nope")}
    )
    assert json.loads(missing_raw)["success"] is False


def test_bandit_fallback_returns_empty_when_unavailable(tmp_path):
    py_file = tmp_path / "thing.py"
    py_file.write_text(APP_PY, encoding="utf-8")

    if not security_scan_tool._BANDIT_AVAILABLE:
        assert security_scan_tool._run_bandit_on_file(py_file) == []
