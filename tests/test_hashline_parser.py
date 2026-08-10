"""Tests for the hashline patch grammar parser (Task 11, omp port).

Covers every op form from the canonical grammar (grammar.lark) and every
rejection rule from the task spec: missing tag, reversed ranges, overlapping
ranges, unified-diff contamination, empty bodies, bodies under bodyless ops,
and unknown ops.
"""

import pytest

from tools.hashline import (
    AppendTail,
    CutBlock,
    CutRange,
    InsertAfter,
    InsertBefore,
    MoveFile,
    ParseError,
    Paste,
    PutBlock,
    PutRange,
    RemoveFile,
    Section,
    parse,
)


def patch(*lines):
    """Join patch lines into a canonical payload (with trailing LF)."""
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Op forms
# ---------------------------------------------------------------------------


def test_put_range_replaces_inclusive_lines():
    text = patch(
        "[greet.py#A1B2]",
        "PUT 2.=4:",
        "+def greet(name):",
        "+    print(f\"Hi, {name}\")",
    )
    assert parse(text) == [
        Section(
            "greet.py",
            "A1B2",
            (PutRange(2, 4, ("def greet(name):", '    print(f"Hi, {name}")')),),
        )
    ]


def test_put_range_single_line():
    text = patch("[greet.py#A1B2]", "PUT 5.=5:", "+greet(\"team\")")
    assert parse(text) == [
        Section("greet.py", "A1B2", (PutRange(5, 5, ('greet("team")',)),))
    ]


def test_put_block():
    text = patch(
        "[greet.py#A1B2]",
        "PUT 1*:",
        "+@cache",
        "+def greet(name):",
        '+    print(f"Hi, {name}")',
    )
    assert parse(text) == [
        Section(
            "greet.py",
            "A1B2",
            (PutBlock(1, ("@cache", "def greet(name):", '    print(f"Hi, {name}")')),),
        )
    ]


def test_put_block_decorated_function_prompt_example():
    """The omp prompt.md decorated-function example."""
    text = patch(
        "[greet.py#A1B2]",
        "PUT 1*:",
        "+@cache",
        "+def greet(name):",
        '+    print(f"Hi, {name}")',
    )
    (section,) = parse(text)
    assert section.path == "greet.py"
    assert section.tag == "A1B2"
    assert section.ops == (PutBlock(1, ("@cache", "def greet(name):", '    print(f"Hi, {name}")')),)


def test_put_insert_before():
    text = patch("[greet.py#A1B2]", "PUT <3:", "+    msg = \"Hello, \" + name")
    assert parse(text) == [
        Section("greet.py", "A1B2", (InsertBefore(3, ('    msg = "Hello, " + name',)),))
    ]


def test_put_insert_before_file_head():
    text = patch("[greet.py#A1B2]", "PUT <1:", "+#!/usr/bin/env python3")
    assert parse(text) == [
        Section("greet.py", "A1B2", (InsertBefore(1, ("#!/usr/bin/env python3",)),))
    ]


def test_put_insert_after():
    text = patch("[greet.py#A1B2]", "PUT >2:", "+    extra = compute(name)")
    assert parse(text) == [
        Section("greet.py", "A1B2", (InsertAfter(2, ("    extra = compute(name)",), block=False),))
    ]


def test_put_insert_after_block():
    text = patch("[greet.py#A1B2]", "PUT >1*:", "+after()")
    assert parse(text) == [
        Section("greet.py", "A1B2", (InsertAfter(1, ("after()",), block=True),))
    ]


def test_put_append_tail():
    text = patch("[greet.py#A1B2]", "PUT >$:", "+    return result")
    assert parse(text) == [
        Section("greet.py", "A1B2", (AppendTail(("    return result",)),))
    ]


def test_body_blank_line_and_verbatim_content():
    text = patch("[PLAN.md#A1B2]", "PUT >2:", "+- task", "+", "+  - nested")
    assert parse(text) == [
        Section("PLAN.md", "A1B2", (InsertAfter(2, ("- task", "", "  - nested")),))
    ]


def test_body_escaped_prefixes():
    """`+- item` and `++ item` yield literal `- item` / `+ item` rows."""
    text = patch("[PLAN.md#A1B2]", "PUT >2:", "+- task", "++ item")
    assert parse(text) == [
        Section("PLAN.md", "A1B2", (InsertAfter(2, ("- task", "+ item")),))
    ]


def test_body_leading_whitespace_kept():
    text = patch("[greet.py#A1B2]", "PUT 1.=1:", "+    indent = 4")
    (section,) = parse(text)
    assert section.ops[0].body == ("    indent = 4",)


def test_cut_range_anonymous():
    text = patch("[greet.py#A1B2]", "CUT 5.=9")
    assert parse(text) == [Section("greet.py", "A1B2", (CutRange(5, 9),))]


def test_cut_range_named():
    text = patch("[greet.py#A1B2]", "CUT 5.=9 @fn")
    assert parse(text) == [Section("greet.py", "A1B2", (CutRange(5, 9, "fn"),))]


def test_cut_block_named():
    text = patch("[greet.py#A1B2]", "CUT 1* @fn")
    assert parse(text) == [Section("greet.py", "A1B2", (CutBlock(1, "fn"),))]


def test_paste_before_gap_anonymous():
    text = patch("[other.py#3C4D]", "PUT <1")
    assert parse(text) == [Section("other.py", "3C4D", (Paste(1, after=False),))]


def test_paste_after_gap_named():
    text = patch("[other.py#3C4D]", "PUT >40 @fn")
    assert parse(text) == [Section("other.py", "3C4D", (Paste(40, "fn", after=True),))]


def test_paste_tail_anonymous():
    text = patch("[other.py#3C4D]", "PUT >$")
    assert parse(text) == [Section("other.py", "3C4D", (Paste("$", after=True),))]


def test_paste_tail_named():
    text = patch("[other.py#3C4D]", "PUT >$ @fn")
    assert parse(text) == [Section("other.py", "3C4D", (Paste("$", "fn", after=True),))]


def test_paste_span_named():
    text = patch("[greet.py#A1B2]", "PUT 5.=9 @fn")
    assert parse(text) == [
        Section("greet.py", "A1B2", (PutRange(5, 9, body=None, register="fn"),))
    ]


def test_paste_block_named():
    text = patch("[greet.py#A1B2]", "PUT 1* @fn")
    assert parse(text) == [
        Section("greet.py", "A1B2", (PutBlock(1, body=None, register="fn"),))
    ]


def test_rem():
    text = patch("[stale.py#A1B2]", "REM")
    assert parse(text) == [Section("stale.py", "A1B2", (RemoveFile(),))]


def test_mv():
    text = patch("[greet.py#A1B2]", "MV lib/greet.py")
    assert parse(text) == [Section("greet.py", "A1B2", (MoveFile("lib/greet.py"),))]


def test_mv_quoted_destination():
    text = patch("[greet.py#A1B2]", 'MV "my file.py"')
    assert parse(text) == [Section("greet.py", "A1B2", (MoveFile("my file.py"),))]


def test_mv_single_quoted_destination():
    text = patch("[greet.py#A1B2]", "MV 'lib/greet.py'")
    assert parse(text) == [Section("greet.py", "A1B2", (MoveFile("lib/greet.py"),))]


# ---------------------------------------------------------------------------
# Multi-section and registers (prompt.md examples)
# ---------------------------------------------------------------------------


def test_multi_section_named_register_flow():
    """CUT 1* @fn in one section feeds PUT <1 @fn in another (prompt.md)."""
    text = patch(
        "[greet.py#A1B2]",
        "CUT 1* @fn",
        "[lib/greet.py#3C4D]",
        "PUT <1 @fn",
    )
    assert parse(text) == [
        Section("greet.py", "A1B2", (CutBlock(1, "fn"),)),
        Section("lib/greet.py", "3C4D", (Paste(1, "fn", after=False),)),
    ]


def test_edit_then_move_section():
    text = patch(
        "[greet.py#A1B2]",
        "PUT 5.=5:",
        '+greet("team")',
        "MV lib/welcome.py",
    )
    assert parse(text) == [
        Section(
            "greet.py",
            "A1B2",
            (PutRange(5, 5, ('greet("team")',)), MoveFile("lib/welcome.py"),),
        )
    ]


def test_ops_preserve_order():
    text = patch(
        "[a.py#A1B2]",
        "PUT 1.=2:",
        "+x",
        "CUT 4.=4",
        "PUT >5:",
        "+y",
        "REM",
    )
    (section,) = parse(text)
    assert [type(op).__name__ for op in section.ops] == [
        "PutRange",
        "CutRange",
        "InsertAfter",
        "RemoveFile",
    ]


def test_multiple_sections_same_path_kept_separate():
    text = patch("[a.py#A1B2]", "PUT 1.=1:", "+x", "[a.py#A1B2]", "PUT 2.=2:", "+y")
    sections = parse(text)
    assert len(sections) == 2
    assert sections[0].ops == (PutRange(1, 1, ("x",)),)
    assert sections[1].ops == (PutRange(2, 2, ("y",)),)


def test_unwrapped_and_wrapped_payloads_equivalent():
    unwrapped = patch("[greet.py#A1B2]", "PUT 1.=1:", "+x")
    wrapped = patch(
        "*** Begin Patch",
        "[greet.py#A1B2]",
        "PUT 1.=1:",
        "+x",
        "*** End Patch",
    )
    assert parse(unwrapped) == parse(wrapped)


def test_crlf_line_endings_accepted():
    text = "[greet.py#A1B2]\r\nPUT 1.=1:\r\n+x\r\n"
    assert parse(text) == [Section("greet.py", "A1B2", (PutRange(1, 1, ("x",)),))]


def test_blank_lines_between_hunks_ignored():
    text = patch("[a.py#A1B2]", "PUT 1.=1:", "+x", "", "PUT 2.=2:", "+y")
    (section,) = parse(text)
    assert section.ops == (PutRange(1, 1, ("x",)), PutRange(2, 2, ("y",)),)


def test_header_paths_may_contain_slashes_dots_dashes():
    text = patch("[src/lib/util-module.py#1A2B]", "REM")
    assert parse(text) == [Section("src/lib/util-module.py", "1A2B", (RemoveFile(),))]


# ---------------------------------------------------------------------------
# Rejections
# ---------------------------------------------------------------------------


def test_reject_missing_tag():
    with pytest.raises(ParseError, match="tag"):
        parse(patch("[greet.py]", "PUT 1.=1:", "+x"))


def test_reject_lowercase_tag():
    with pytest.raises(ParseError, match="tag"):
        parse(patch("[greet.py#a1b2]", "PUT 1.=1:", "+x"))


def test_reject_bad_tag_length():
    with pytest.raises(ParseError, match="tag"):
        parse(patch("[greet.py#A1B2C]", "PUT 1.=1:", "+x"))


def test_reject_non_hex_tag():
    with pytest.raises(ParseError, match="tag"):
        parse(patch("[greet.py#ZZZZ]", "PUT 1.=1:", "+x"))


def test_reject_reversed_range():
    with pytest.raises(ParseError, match="reverse|Reversed|reversed"):
        parse(patch("[greet.py#A1B2]", "PUT 5.=2:", "+x"))


def test_reject_reversed_cut_range():
    with pytest.raises(ParseError, match="reverse|Reversed|reversed"):
        parse(patch("[greet.py#A1B2]", "CUT 9.=4"))


def test_reject_overlapping_ranges():
    with pytest.raises(ParseError, match="overlap"):
        parse(patch("[greet.py#A1B2]", "PUT 1.=3:", "+a", "+b", "PUT 2.=4:", "+c"))


def test_reject_cut_and_put_overlap():
    with pytest.raises(ParseError, match="overlap"):
        parse(patch("[greet.py#A1B2]", "CUT 1.=3", "PUT 2.=4:", "+c"))


def test_reject_register_span_paste_overlap():
    with pytest.raises(ParseError, match="overlap"):
        parse(patch("[greet.py#A1B2]", "PUT 5.=9 @fn", "PUT 6.=6:", "+x"))


def test_adjacent_ranges_allowed():
    text = patch("[greet.py#A1B2]", "PUT 1.=2:", "+a", "PUT 3.=4:", "+b")
    (section,) = parse(text)
    assert len(section.ops) == 2


def test_reject_empty_body_put_range():
    with pytest.raises(ParseError, match="body"):
        parse(patch("[greet.py#A1B2]", "PUT 1.=2:"))


def test_reject_empty_body_put_block():
    with pytest.raises(ParseError, match="body"):
        parse(patch("[greet.py#A1B2]", "PUT 1*:"))


def test_reject_empty_body_insert_after():
    with pytest.raises(ParseError, match="body"):
        parse(patch("[greet.py#A1B2]", "PUT >3:"))


def test_reject_empty_body_append_tail():
    with pytest.raises(ParseError, match="body"):
        parse(patch("[greet.py#A1B2]", "PUT >$:"))


def test_reject_body_under_cut():
    with pytest.raises(ParseError, match="body"):
        parse(patch("[greet.py#A1B2]", "CUT 1.=2", "+oops"))


def test_reject_body_under_rem():
    with pytest.raises(ParseError, match="body"):
        parse(patch("[stale.py#A1B2]", "REM", "+oops"))


def test_reject_body_under_mv():
    with pytest.raises(ParseError, match="body"):
        parse(patch("[greet.py#A1B2]", "MV lib/greet.py", "+oops"))


def test_reject_colon_on_register_put():
    with pytest.raises(ParseError):
        parse(patch("[greet.py#A1B2]", "PUT >20 @fn:", "+function f() {}"))


def test_reject_body_under_register_put():
    with pytest.raises(ParseError, match="body"):
        parse(patch("[greet.py#A1B2]", "PUT >20 @fn", "+function f() {}"))


def test_reject_colon_on_cut():
    with pytest.raises(ParseError):
        parse(patch("[greet.py#A1B2]", "CUT 1.=2:"))


def test_reject_unified_diff_hunk_header():
    with pytest.raises(ParseError, match="unified|diff"):
        parse(patch("[greet.py#A1B2]", "@@ -1,2 +1,2 @@"))


def test_reject_unified_diff_old_row():
    with pytest.raises(ParseError, match="unified|diff|body"):
        parse(patch("[greet.py#A1B2]", "PUT 1.=2:", "+new", "-old"))


def test_reject_bare_context_row_in_body():
    with pytest.raises(ParseError):
        parse(patch("[greet.py#A1B2]", "PUT 1.=2:", "+new", "    msg = old"))


def test_reject_unknown_op():
    with pytest.raises(ParseError, match="unknown|not a hashline"):
        parse(patch("[greet.py#A1B2]", "FOO 1.=2:", "+x"))


def test_reject_lowercase_put():
    with pytest.raises(ParseError, match="unknown|not a hashline"):
        parse(patch("[greet.py#A1B2]", "put 1.=2:", "+x"))


def test_reject_anonymous_span_paste():
    with pytest.raises(ParseError, match="register"):
        parse(patch("[greet.py#A1B2]", "PUT 1.=2"))


def test_reject_anonymous_block_paste():
    with pytest.raises(ParseError, match="register"):
        parse(patch("[greet.py#A1B2]", "PUT 1*"))


def test_reject_zero_or_bad_line_numbers():
    with pytest.raises(ParseError):
        parse(patch("[greet.py#A1B2]", "PUT 0.=2:", "+x"))
    with pytest.raises(ParseError):
        parse(patch("[greet.py#A1B2]", "PUT abc.=2:", "+x"))
    with pytest.raises(ParseError):
        parse(patch("[greet.py#A1B2]", "PUT <0:", "+x"))


def test_reject_invalid_register_name():
    with pytest.raises(ParseError):
        parse(patch("[greet.py#A1B2]", "CUT 1.=2 @fn!"))


def test_reject_empty_section():
    with pytest.raises(ParseError, match="operation|hunk"):
        parse(patch("[greet.py#A1B2]", "[other.py#3C4D]", "REM"))


def test_reject_content_before_first_header():
    with pytest.raises(ParseError, match="header"):
        parse(patch("PUT 1.=1:", "+x"))


def test_reject_empty_input():
    with pytest.raises(ParseError):
        parse("")


def test_reject_content_after_end_patch():
    with pytest.raises(ParseError):
        parse(patch("*** Begin Patch", "[a.py#A1B2]", "REM", "*** End Patch", "garbage"))


def test_reject_unmatched_end_patch():
    with pytest.raises(ParseError):
        parse(patch("[a.py#A1B2]", "REM", "*** End Patch", "[b.py#C3D4]", "REM"))


def test_reject_malformed_header():
    with pytest.raises(ParseError, match="header"):
        parse(patch("[greet.py#A1B2", "REM"))


def test_error_reports_patch_line_number():
    with pytest.raises(ParseError) as excinfo:
        parse(patch("[greet.py#A1B2]", "CUT 1.=2", "REM", "PUT 5.=2:", "+x"))
    assert excinfo.value.line == 4


def test_error_message_mentions_offending_op():
    with pytest.raises(ParseError) as excinfo:
        parse(patch("[greet.py#A1B2]", "PUT 5.=2:", "+x"))
    assert "PUT" in str(excinfo.value) and "5" in str(excinfo.value)


def test_register_names_with_digits_underscore_dash():
    text = patch(
        "[a.py#A1B2]",
        "CUT 1* @fn_2-x",
        "[b.py#3C4D]",
        "PUT <1 @fn_2-x",
    )
    sections = parse(text)
    assert sections[0].ops == (CutBlock(1, "fn_2-x"),)
    assert sections[1].ops == (Paste(1, "fn_2-x", after=False),)


# ---------------------------------------------------------------------------
# Immutability: frozen dataclasses must not expose mutable containers
# ---------------------------------------------------------------------------


def test_body_rows_are_immutable_tuples():
    """'PUT 1.=2:' body rows are a tuple — append must fail, not silently mutate."""
    (section,) = parse(patch("[greet.py#A1B2]", "PUT 1.=2:", "+a", "+b"))
    op = section.ops[0]
    assert isinstance(op.body, tuple)
    assert op.body == ("a", "b")
    with pytest.raises(AttributeError):
        op.body.append("c")  # type: ignore[attr-defined]


def test_section_ops_are_immutable_tuple():
    """Section.ops is a tuple — parse(...)[0].ops.append(...) must fail."""
    (section,) = parse(patch("[greet.py#A1B2]", "PUT 1.=1:", "+x"))
    assert isinstance(section.ops, tuple)
    with pytest.raises(AttributeError):
        section.ops.append(object())  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Whitespace-stuffed PUT headers (error-message correctness)
# ---------------------------------------------------------------------------


def test_put_header_extra_space_before_locator():
    """'PUT  1.=2:' is a body-taking PUT — the colon is correct, not a register."""
    text = patch("[greet.py#A1B2]", "PUT  1.=2:", "+x")
    assert parse(text) == [Section("greet.py", "A1B2", (PutRange(1, 2, ("x",)),))]


def test_put_header_trailing_space_after_colon():
    """'PUT 1.=1:  ' is a body-taking PUT — there is no register, no trailing junk."""
    text = patch("[greet.py#A1B2]", "PUT 1.=1:  ", "+x")
    assert parse(text) == [Section("greet.py", "A1B2", (PutRange(1, 1, ("x",)),))]


def test_register_put_colon_error_names_the_register():
    """'PUT 1.=2: @fn' — a REAL register plus ':' — says the register takes no body."""
    with pytest.raises(ParseError, match="register PUT takes no body rows"):
        parse(patch("[greet.py#A1B2]", "PUT 1.=2: @fn", "+x"))


def test_trailing_content_after_register_names_trailing_content():
    """'PUT >5 @fn junk' — register present, junk after — flags the trailing bits."""
    with pytest.raises(ParseError, match="trailing content after register"):
        parse(patch("[greet.py#A1B2]", "PUT >5 @fn junk"))


def test_overlap_error_carries_patch_line_number():
    """Overlap errors name the line of the second overlapping op, not None."""
    with pytest.raises(ParseError) as excinfo:
        parse(patch("[greet.py#A1B2]", "PUT 1.=3:", "+a", "+b", "PUT 2.=4:", "+c"))
    assert excinfo.value.line == 5
