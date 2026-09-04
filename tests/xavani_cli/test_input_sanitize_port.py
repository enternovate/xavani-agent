from xavani_cli.input_sanitize import collapse_repeated_input_artifacts
from xavani_cli.input_sanitize import sanitize_user_prompt_text
from xavani_cli.input_sanitize import strip_leaked_bracketed_paste_wrappers


def test_import_succeeds():
    assert strip_leaked_bracketed_paste_wrappers is not None
    assert collapse_repeated_input_artifacts is not None
    assert sanitize_user_prompt_text is not None


def test_strip_canonical_wrapper():
    assert strip_leaked_bracketed_paste_wrappers("\x1b[200~hello\x1b[201~") == "hello"


def test_sanitize_plain_text():
    assert sanitize_user_prompt_text("hello world") == "hello world"
