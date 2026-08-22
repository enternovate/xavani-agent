# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.

"""Help-text quality audit: every registry entry ships usable help."""

import pytest

from xavani_cli.commands import COMMAND_REGISTRY


class TestHelpTextAudit:
    def test_every_description_nonempty_capitalized_and_bounded(self):
        for cmd in COMMAND_REGISTRY:
            desc = cmd.description or ""
            assert desc, f"{cmd.name}: empty description"
            assert desc[0].isupper(), f"{cmd.name}: description not capitalized"
            assert len(desc) <= 90, f"{cmd.name}: description over 90 chars"

    def test_subcommands_imply_args_hint(self):
        for cmd in COMMAND_REGISTRY:
            if cmd.subcommands:
                assert cmd.args_hint, f"{cmd.name}: subcommands without args_hint"

    def test_args_hint_mentions_first_subcommand_when_present(self):
        for cmd in COMMAND_REGISTRY:
            if cmd.subcommands and cmd.args_hint:
                first = cmd.subcommands[0]
                hint = cmd.args_hint.lower()
                in_hint = first in hint or "|" in cmd.args_hint
                assert in_hint, (
                    f"{cmd.name}: args_hint ignores subcommands"
                )

    def test_aliases_are_short(self):
        for cmd in COMMAND_REGISTRY:
            for alias in cmd.aliases or ():
                assert len(alias) <= 20, f"{cmd.name}: alias {alias!r} too long"

    def test_descriptions_do_not_leak_internal_terms(self):
        banned = ("todo", "fixme", "wip", "hack", "xxx")
        for cmd in COMMAND_REGISTRY:
            lowered = (cmd.description or "").lower()
            for word in banned:
                assert word not in lowered, f"{cmd.name}: description contains {word!r}"
