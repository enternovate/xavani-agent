from xavani_cli._subprocess_compat import noninteractive_git_env


def test_noninteractive_git_env_imports():
    assert callable(noninteractive_git_env)


def test_noninteractive_git_env_disables_terminal_prompt():
    env = noninteractive_git_env({"PATH": "/usr/bin"})
    assert env["GIT_TERMINAL_PROMPT"] == "0"
