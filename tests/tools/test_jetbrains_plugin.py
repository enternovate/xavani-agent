# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""F09: JetBrains plugin tests."""

import xml.etree.ElementTree as ET

from tools.jetbrains_plugin import (
    CHAT_ACTION_ID,
    PLUGIN_ID,
    TOOL_WINDOW_ID,
    generate_jetbrains_plugin,
    validate_plugin,
)


def test_generation_contains_required_files():
    files = generate_jetbrains_plugin("0.7.2")
    assert set(files.keys()) == {
        "src/main/resources/META-INF/plugin.xml",
        "src/main/kotlin/com/enternovate/xavani/ChatAction.kt",
        "src/main/kotlin/com/enternovate/xavani/XavaniToolWindowFactory.kt",
        "src/main/kotlin/com/enternovate/xavani/XavaniClient.kt",
    }


def test_descriptor_id_and_version():
    files = generate_jetbrains_plugin("0.7.2")
    root = ET.fromstring(files["src/main/resources/META-INF/plugin.xml"])
    assert root.tag == "idea-plugin"
    assert root.findtext("id") == PLUGIN_ID
    assert root.findtext("version") == "0.7.2"


def test_descriptor_has_tool_window():
    files = generate_jetbrains_plugin("0.7.2")
    root = ET.fromstring(files["src/main/resources/META-INF/plugin.xml"])
    extensions = root.find("extensions")
    assert extensions is not None
    tool_windows = [
        ext.get("id")
        for ext in extensions.findall("toolWindow")
        if ext.get("id") == TOOL_WINDOW_ID
    ]
    assert tool_windows == [TOOL_WINDOW_ID]


def test_descriptor_has_chat_action():
    files = generate_jetbrains_plugin("0.7.2")
    root = ET.fromstring(files["src/main/resources/META-INF/plugin.xml"])
    actions = root.find("actions")
    assert actions is not None
    action_ids = [action.get("id") for action in actions.findall("action")]
    assert CHAT_ACTION_ID in action_ids


def test_kt_action_and_client():
    files = generate_jetbrains_plugin("0.7.2")
    assert "class ChatAction : AnAction()" in files[
        "src/main/kotlin/com/enternovate/xavani/ChatAction.kt"
    ]
    assert "/v1/chat" in files[
        "src/main/kotlin/com/enternovate/xavani/XavaniClient.kt"
    ]
    assert "class XavaniToolWindowFactory : ToolWindowFactory" in files[
        "src/main/kotlin/com/enternovate/xavani/XavaniToolWindowFactory.kt"
    ]


def test_validate_ok():
    files = generate_jetbrains_plugin("0.7.2")
    assert validate_plugin(files) == []


def test_validate_missing_action():
    files = generate_jetbrains_plugin("0.7.2")
    files["src/main/resources/META-INF/plugin.xml"] = files[
        "src/main/resources/META-INF/plugin.xml"
    ].replace(CHAT_ACTION_ID, "com.enternovate.xavani.OtherAction")
    problems = validate_plugin(files)
    assert any(CHAT_ACTION_ID in p for p in problems)


def test_validate_bad_xml():
    files = generate_jetbrains_plugin("0.7.2")
    files["src/main/resources/META-INF/plugin.xml"] = "<idea-plugin>"
    problems = validate_plugin(files)
    assert any("invalid" in p for p in problems)


def test_validate_empty():
    problems = validate_plugin({})
    assert problems
    assert any("missing" in p for p in problems)


def test_deterministic():
    assert generate_jetbrains_plugin("0.7.2") == generate_jetbrains_plugin("0.7.2")
