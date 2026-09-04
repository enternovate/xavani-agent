from tools.approval import (
    _fold_home_prefixes,
    _rewrite_resolved_user_home,
    _rewrite_resolved_xavani_home,
)


def test_fold_prefers_longest_prefix():
    out = _fold_home_prefixes("cd /home/alice/work", ["/home/alice", "/home/alice/work"], "~")
    assert out == "cd ~/work"


def test_rewrite_user_home_leaves_plain_string():
    assert _rewrite_resolved_user_home("echo hello") == "echo hello"


def test_rewrite_xavani_home_folds_real_home():
    from xavani_constants import get_xavani_home

    home = str(get_xavani_home())
    out = _rewrite_resolved_xavani_home("cat " + home + "/config.yaml")
    assert out == "cat ~/.xavani/config.yaml"
