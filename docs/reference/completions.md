# Shell Completions for xavani

`scripts/gen_completions.py` generates bash, zsh, and fish completion
scripts for the `xavani` binary. The command list is **not** hand-written:
it is derived from the CLI's own slash-command registry
(`xavani_cli.commands.COMMAND_REGISTRY`), the same source that powers
`/help`, gateway dispatch, and in-app autocomplete — so completions track
the running binary automatically. Regenerate whenever the registry changes:

```bash
python3 scripts/gen_completions.py
```

Outputs:

- `scripts/completions/bash/xavani.bash`
- `scripts/completions/zsh/_xavani`
- `scripts/completions/fish/xavani.fish`

## Installation

Source the file for your shell from your rc file.

### bash

```bash
echo 'source /path/to/xavani-agent/scripts/completions/bash/xavani.bash' >> ~/.bashrc
```

### zsh

```bash
echo 'fpath=(/path/to/xavani-agent/scripts/completions/zsh $fpath)' >> ~/.zshrc
echo 'compinit' >> ~/.zshrc
```

(If you prefer, copy `_xavani` into a directory already on your `fpath`,
e.g. `~/.oh-my-zsh/completions/`.)

### fish

```bash
echo 'source /path/to/xavani-agent/scripts/completions/fish/xavani.fish' >> ~/.config/fish/config.fish
```

Or install to fish's own completions directory:

```bash
mkdir -p ~/.config/fish/completions
cp scripts/completions/fish/xavani.fish ~/.config/fish/completions/
```

Start a new shell (or `source ~/.bashrc` / `exec zsh` / `exec fish`) and
type `/` then <kbd>Tab</kbd> to complete slash commands and subcommands.
