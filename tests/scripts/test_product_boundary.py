# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Task 24a — tests for scripts/check_product_boundary.py.

Code Pack Q names the required cases; the remaining tests pin the rule engine
and the repository scan. The legal-attribution and notices tests are the
"required legal attribution passes" half of the Task 24 acceptance.
"""

from pathlib import Path

import pytest

from scripts import check_product_boundary as boundary

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

pytestmark = pytest.mark.unit


# ── Code Pack Q required cases ──────────────────────────────────────────────


def test_product_button_upstream_portal_host_fails():
    """A product button that opens portal.nousresearch.com fails."""
    text = '{"button": {"label": "Portal", "url": "https://portal.nousresearch.com/signup"}}'
    findings = boundary.scan_text(text, path="fixture.json", kind="runtime")
    assert [f.rule for f in findings] == ["P1"]
    assert "portal.nousresearch.com" in findings[0].detail


def test_product_button_enternovate_release_page_passes():
    """A product button that opens an Enternovate release page passes."""
    text = (
        '{"button": {"label": "Release notes", '
        '"url": "https://github.com/enternovate/xavani-agent/releases/tag/v0.4.0"}}'
    )
    assert boundary.scan_text(text, path="fixture.json", kind="runtime") == []


def test_legal_notice_naming_upstream_holder_passes():
    """A legal notice that names an upstream copyright holder passes."""
    text = (
        "MIT License\n"
        "Copyright (c) 2025 Nous Research\n"
        "Derived from https://github.com/NousResearch/hermes-agent\n"
        "Copyright (c) 2025-2026 Enternovate (Pty) Ltd\n"
    )
    assert boundary.scan_text(text, path="THIRD_PARTY_NOTICES.md", kind="legal") == []


def test_provider_setting_explicit_openai_passes():
    """A provider setting that explicitly selects OpenAI passes."""
    text = '{"provider": "openai", "base_url": "https://api.openai.com/v1", "selected_by": "user"}'
    assert boundary.scan_text(text, path="cli-config.yaml.example", kind="provider_catalog") == []
    assert boundary.classify_host("api.openai.com") == boundary.PROVIDER
    assert not boundary.is_prohibited_host("api.openai.com")


def test_blank_custom_endpoint_stays_blank_after_startup():
    """A blank custom endpoint stays blank: no default endpoint is substituted."""
    assert boundary.scan_text('custom_endpoint: ""\n', path="config.yaml", kind="runtime") == []
    assert boundary.host_of("") == ""
    # No declared default service supplies an endpoint for the remote-inference
    # path while it is off by default.
    remote = [s for s in boundary.DEFAULT_SERVICES if s.category == "remote_inference"]
    assert remote and all(not s.enabled_by_default for s in remote)
    assert all(s.target == "" for s in remote)


def test_default_telemetry_to_owned_host_fails():
    """A default telemetry request fails even if it targets an Enternovate host."""
    service = boundary.DefaultService(
        name="telemetry",
        category="telemetry",
        target="https://enternovate.com/collect",
        enabled_by_default=True,
    )
    findings = boundary.check_default_service(service)
    assert [f.rule for f in findings] == ["P3"]


# ── rule engine ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "host",
    ["nousresearch.com", "portal.nousresearch.com", "api.nousresearch.com", "a.b.nousresearch.com"],
)
def test_every_upstream_subdomain_is_prohibited(host):
    assert boundary.is_prohibited_host(host)


def test_undeclared_host_fails_on_a_runtime_surface():
    findings = boundary.scan_text(
        'URL = "https://tracker.example.net/collect"', path="xavani.py", kind="runtime"
    )
    assert [f.rule for f in findings] == ["P2"]
    assert "tracker.example.net" in findings[0].detail


def test_owned_and_publisher_hosts_pass():
    text = 'A = "https://enternovate.com/x"\nB = "https://enternovate.co.za/docs"\n'
    assert boundary.scan_text(text, path="acp_registry/agent.json", kind="runtime") == []
    assert boundary.classify_host("enternovate.com") == boundary.OWNED
    assert boundary.classify_host("enternovate.co.za") == boundary.PUBLISHER


def test_docs_surface_flags_prohibited_host_but_not_undeclared_host():
    docs = "https://img.shields.io/badge/x https://portal.nousresearch.com/join"
    findings = boundary.scan_text(docs, path="README.md", kind="docs")
    assert [f.rule for f in findings] == ["P1"]


def test_provider_catalog_surface_is_never_host_flagged():
    text = "base_url: https://api.openai.com/v1\nbase_url: https://openrouter.ai/api/v1\n"
    assert boundary.scan_text(text, path="cli-config.yaml.example", kind="provider_catalog") == []


def test_boundary_config_matches_code_pack_q():
    assert boundary.BOUNDARY_CONFIG == {
        "product_names": ["Xavani", "Enternovate"],
        "owned_hosts": ["enternovate.com", "www.enternovate.com"],
        "release_repositories": ["enternovate/xavani-agent", "enternovate/xavani-desktop"],
        "legal_files": ["LICENSE", "THIRD_PARTY_NOTICES.md"],
        "default_remote_inference": False,
        "default_telemetry": False,
        "default_update_checks": False,
    }


def test_file_exceptions_are_file_specific_and_stated():
    for exc in boundary.FILE_EXCEPTIONS:
        assert exc.reason.strip(), f"{exc.path} exception must state a reason"
        assert "/" not in exc.path.rstrip("/") or exc.path.endswith(".md")
        assert exc.rules, f"{exc.path} exception must name the rules it exempts"
        for rule_id in exc.rules:
            assert rule_id in boundary.RULES_BY_ID


def test_every_rule_has_a_category_and_description():
    for rule in boundary.RULES:
        assert rule.category in {"product", "legal"}
        assert rule.description.strip()
    assert boundary.RULES_BY_ID["P1"].category == "product"
    assert boundary.RULES_BY_ID["L2"].category == "legal"


def test_unopted_update_check_to_a_third_party_fails():
    service = boundary.DefaultService(
        name="update-check",
        category="update_check",
        target="https://updates.example.net/latest",
        enabled_by_default=True,
        requires_user_action=False,
    )
    assert [f.rule for f in boundary.check_default_service(service)] == ["P5"]


def test_user_initiated_update_check_passes():
    service = boundary.DefaultService(
        name="update-check",
        category="update_check",
        target="https://updates.example.net/latest",
        enabled_by_default=True,
        requires_user_action=True,
    )
    assert boundary.check_default_service(service) == []


def test_remote_inference_enabled_by_default_fails():
    service = boundary.DefaultService(
        name="remote-inference",
        category="remote_inference",
        target="https://enternovate.com/v1",
        enabled_by_default=True,
    )
    assert [f.rule for f in boundary.check_default_service(service)] == ["P4"]


def test_remote_inference_against_a_provider_endpoint_passes_when_user_selected():
    service = boundary.DefaultService(
        name="remote-inference",
        category="remote_inference",
        target="https://api.openai.com/v1",
        enabled_by_default=True,
        requires_user_action=True,
    )
    assert boundary.check_default_service(service) == []


def test_disabled_services_never_fail():
    for category, target in (
        ("telemetry", "https://enternovate.com/collect"),
        ("remote_inference", "https://enternovate.com/v1"),
        ("update_check", "https://updates.example.net/latest"),
    ):
        service = boundary.DefaultService(
            name="off", category=category, target=target, enabled_by_default=False
        )
        assert boundary.check_default_service(service) == []


# ── legal surfaces ──────────────────────────────────────────────────────────


def test_legal_files_exist_and_are_non_empty():
    for name, text in (
        ("LICENSE", (REPO_ROOT / "LICENSE").read_text(encoding="utf-8")),
        (
            "THIRD_PARTY_NOTICES.md",
            (REPO_ROOT / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8"),
        ),
    ):
        assert text.strip(), f"{name} must not be empty"


def test_license_retains_the_derived_work_mit_notice():
    text = (REPO_ROOT / "LICENSE").read_text(encoding="utf-8")
    assert "MIT License" in text
    assert "Copyright (c) 2025 Nous Research" in text
    assert "Copyright (c) 2025-2026 Enternovate" in text


def test_notices_name_the_derived_work_ancestor_and_its_license():
    text = (REPO_ROOT / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
    assert "Nous Research" in text
    assert "MIT License" in text


def test_notices_name_the_upstream_ported_project_holders():
    text = (REPO_ROOT / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
    for holder in ("Mario Zechner", "Stencil Labs, Inc."):
        assert holder in text, f"missing upstream copyright holder: {holder}"


def test_every_bundled_notice_on_disk_is_declared_in_the_notices_file():
    notices = (REPO_ROOT / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
    discovered = boundary.discover_bundled_notices(REPO_ROOT)
    assert len(discovered) >= 10, discovered
    for rel_path in discovered:
        assert rel_path in notices, f"{rel_path} is not declared in the notices file"


def test_undeclared_notice_file_is_flagged(tmp_path):
    import shutil

    shutil.copy(REPO_ROOT / "LICENSE", tmp_path / "LICENSE")
    shutil.copy(REPO_ROOT / "THIRD_PARTY_NOTICES.md", tmp_path / "THIRD_PARTY_NOTICES.md")
    demo = tmp_path / "skills" / "demo"
    demo.mkdir(parents=True)
    (demo / "LICENSE").write_text("MIT License", encoding="utf-8")
    findings = boundary.scan_legal(tmp_path)
    assert any(
        finding.rule == "L3" and "skills/demo/LICENSE" in finding.path
        for finding in findings
    )


# ── default behaviors as shipped ────────────────────────────────────────────


def test_no_telemetry_service_is_on_by_default():
    assert all(not s.enabled_by_default for s in boundary.DEFAULT_SERVICES if s.category == "telemetry")


def test_no_remote_inference_service_is_on_by_default():
    default_on = [
        s.name
        for s in boundary.DEFAULT_SERVICES
        if s.category == "remote_inference" and s.enabled_by_default
    ]
    assert default_on == []


def test_default_update_checks_target_only_owned_repositories_or_registries():
    for service in boundary.DEFAULT_SERVICES:
        if service.category != "update_check":
            continue
        host = boundary.host_of(service.target)
        assert not boundary.is_prohibited_host(host)
        assert (
            boundary.is_release_repository_target(service.target)
            or boundary.classify_host(host) == boundary.DECLARED
        ), f"{service.name} targets an undeclared host: {service.target}"


def test_every_source_probe_resolves():
    for probe in boundary.SOURCE_PROBES:
        assert (REPO_ROOT / probe.path).is_file(), f"probe {probe.id} path missing"
        assert probe.expect in {"present", "absent"}
        assert probe.rule in boundary.RULES_BY_ID


# ── repository scan ─────────────────────────────────────────────────────────


def test_repo_scan_passes():
    findings = boundary.scan_repo(REPO_ROOT)
    assert findings == [], boundary.render_report(findings, scanned=len(boundary.PRODUCT_SURFACES))


def test_repo_scan_is_deterministic_and_read_only():
    before = {
        path: (REPO_ROOT / path).stat().st_mtime_ns
        for path, _ in boundary.PRODUCT_SURFACES
        if (REPO_ROOT / path).is_file()
    }
    first = boundary.scan_repo(REPO_ROOT)
    second = boundary.scan_repo(REPO_ROOT)
    assert first == second
    after = {
        path: (REPO_ROOT / path).stat().st_mtime_ns
        for path, _ in boundary.PRODUCT_SURFACES
        if (REPO_ROOT / path).is_file()
    }
    assert before == after


def test_main_exits_zero_on_the_repository(capsys):
    assert boundary.main([]) == 0
    assert "PASS" in capsys.readouterr().out


def test_main_json_report_exits_zero(capsys):
    assert boundary.main(["--json"]) == 0
    report = boundary.build_report(boundary.scan_repo(REPO_ROOT), root=REPO_ROOT)
    assert report["ok"] is True
    assert report["scope"] == "agent"
    assert report["counts"]["total"] == 0
    assert report["counts"]["product"] == 0
    assert report["counts"]["legal"] == 0
    assert capsys.readouterr().out.strip().startswith("{")


def _write_legal_stubs(root: Path) -> None:
    (root / "LICENSE").write_text("MIT License\nCopyright (c) 2025 Nous Research\n", encoding="utf-8")
    (root / "THIRD_PARTY_NOTICES.md").write_text("Nous Research\n", encoding="utf-8")


def test_injected_upstream_link_fails_the_scan(tmp_path, monkeypatch):
    """RED capability: an injected upstream default link must be detected."""
    (tmp_path / "banner.py").write_text(
        'PORTAL = "https://portal.nousresearch.com/checkout"\n', encoding="utf-8"
    )
    _write_legal_stubs(tmp_path)
    monkeypatch.setattr(boundary, "PRODUCT_SURFACES", (("banner.py", "runtime"),))
    monkeypatch.setattr(boundary, "DEFAULT_SERVICES", ())
    monkeypatch.setattr(boundary, "SOURCE_PROBES", ())
    monkeypatch.setattr(boundary, "REQUIRED_BUNDLED_NOTICES", ())
    monkeypatch.setattr(boundary, "REQUIRED_ATTRIBUTION", ())

    findings = boundary.scan_repo(tmp_path)
    assert [f.rule for f in findings] == ["P1"]
    assert boundary.main(["--root", str(tmp_path)]) == 1


def test_injected_missing_notices_fail_the_scan(tmp_path, monkeypatch):
    """A removed notices file is a legal-boundary failure, not a pass."""
    (tmp_path / "banner.py").write_text("URL = 'https://github.com/enternovate/xavani-agent'\n", encoding="utf-8")
    (tmp_path / "LICENSE").write_text("MIT License\n", encoding="utf-8")
    monkeypatch.setattr(boundary, "PRODUCT_SURFACES", (("banner.py", "runtime"),))
    monkeypatch.setattr(boundary, "DEFAULT_SERVICES", ())
    monkeypatch.setattr(boundary, "SOURCE_PROBES", ())

    findings = boundary.scan_repo(tmp_path)
    rules = {f.rule for f in findings}
    assert "L1" in rules
    assert "L3" in rules


def test_scan_text_accepts_memory_input_without_a_file():
    assert boundary.scan_text("no links here", path="<memory>", kind="runtime") == []
    assert boundary.extract_urls("see https://enternovate.com/x.") == [
        (1, "https://enternovate.com/x")
    ]


def test_render_report_names_every_finding():
    findings = boundary.scan_text("https://portal.nousresearch.com/x", path="x.py", kind="runtime")
    text = boundary.render_report(findings, scanned=1)
    assert "FAIL" in text
    assert "[P1/product]" in text
    assert "x.py:1" in text
