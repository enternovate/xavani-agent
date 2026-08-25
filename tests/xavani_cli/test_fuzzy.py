"""Fuzzy slash-command matching tests.

Scores candidate names against an input so unknown commands suggest the
right match: prefix > substring > subsequence, ties broken by length.
"""

from xavani_cli.fuzzy import best_match, score


class TestScore:
    def test_exact_match_max_score(self):
        assert score("cost", "cost") == 100

    def test_prefix_beats_substring(self):
        assert score("co", "cost") > score("os", "cost")

    def test_substring_beats_subsequence(self):
        assert score("ost", "cost") > score("ct", "cost")

    def test_no_match_zero(self):
        assert score("xyz", "cost") == 0

    def test_shorter_target_wins_ties(self):
        # Both are prefixes of the query; the shorter target is tighter.
        assert score("mo", "model") >= score("mo", "models")


class TestBestMatch:
    COMMANDS = ["cost", "model", "fresh", "status", "skills", "stream"]

    def test_typo_suggests_closest(self):
        assert best_match("cst", self.COMMANDS) in ("cost",)

    def test_prefix_returns_exact_extension(self):
        assert best_match("stat", self.COMMANDS) == "status"

    def test_no_candidates_none(self):
        assert best_match("anything", []) is None

    def test_garbage_none(self):
        assert best_match("zzzzzzz", self.COMMANDS) is None
