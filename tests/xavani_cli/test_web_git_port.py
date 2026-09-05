from __future__ import annotations


def test_web_git_import_succeeds():
    import xavani_cli.web_git as web_git

    assert web_git is not None


def test_web_git_exposes_main_entry():
    import xavani_cli.web_git as web_git

    assert callable(web_git.repo_status)


def test_harden_git_argv_returns_list():
    from xavani_cli._subprocess_compat import harden_git_argv

    assert isinstance(harden_git_argv(["status"]), list)
