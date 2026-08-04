# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""F09: JetBrains plugin descriptor generator.

Generates the xavani-intellij plugin scaffold: the plugin.xml descriptor
(tool window + actions for all JetBrains IDEs) plus the Kotlin action and
tool-window factory sources. The generator is deterministic; validation
checks the descriptor shape (XML well-formedness, plugin id, version,
contributed actions and tool window).

Usage::

    from tools.jetbrains_plugin import generate_jetbrains_plugin, validate_plugin

    files = generate_jetbrains_plugin(version="0.7.2")
    problems = validate_plugin(files)
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Dict, List

PLUGIN_ID = "com.enternovate.xavani"
PLUGIN_NAME = "Xavani Agent"
CHAT_ACTION_ID = "com.enternovate.xavani.ChatAction"
TOOL_WINDOW_ID = "Xavani"


def _plugin_xml(version: str) -> str:
    """Build the plugin.xml descriptor for the given version."""
    return f"""\
<idea-plugin>
  <id>{PLUGIN_ID}</id>
  <name>{PLUGIN_NAME}</name>
  <version>{version}</version>
  <vendor email="support@enternovate.com" url="https://enternovate.com">Enternovate</vendor>
  <description><![CDATA[Chat with the Xavani agent from any JetBrains IDE.]]></description>
  <depends>com.intellij.modules.platform</depends>

  <extensions defaultExtensionNs="com.intellij">
    <toolWindow id="{TOOL_WINDOW_ID}" anchor="right" secondary="true"
                icon="AllIcons.General.Balloon" factoryClass="com.enternovate.xavani.XavaniToolWindowFactory"/>
  </extensions>

  <actions>
    <action id="{CHAT_ACTION_ID}" class="com.enternovate.xavani.ChatAction"
            text="Xavani: Chat" description="Chat with the Xavani agent">
      <add-to-group group-id="ToolsMenu" anchor="last"/>
    </action>
  </actions>
</idea-plugin>
"""


_CHAT_ACTION_KT = """\
package com.enternovate.xavani

import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.ui.MessageDialogBuilder
import com.intellij.openapi.ui.Messages

/**
 * xavani-intellij — chat with the Xavani agent from any JetBrains IDE.
 */
class ChatAction : AnAction() {
    override fun actionPerformed(event: AnActionEvent) {
        val message = Messages.showInputDialog(
            event.project,
            "Message Xavani:",
            "Xavani Agent",
            Messages.getQuestionIcon(),
        )
        if (message.isNullOrBlank()) return
        val reply = XavaniClient.chat(message)
        MessageDialogBuilder.yesNo("Xavani reply", reply ?: "no reply").show()
    }
}
"""


_TOOL_WINDOW_FACTORY_KT = """\
package com.enternovate.xavani

import com.intellij.openapi.project.Project
import com.intellij.openapi.wm.ToolWindow
import com.intellij.openapi.wm.ToolWindowFactory
import com.intellij.ui.components.JBScrollPane
import com.intellij.ui.components.JBTextArea
import java.awt.BorderLayout
import javax.swing.JButton
import javax.swing.JPanel

/**
 * xavani-intellij — tool window that chats with the Xavani gateway.
 */
class XavaniToolWindowFactory : ToolWindowFactory {
    override fun createToolWindowContent(project: Project, toolWindow: ToolWindow) {
        val output = JBTextArea(12, 60)
        output.isEditable = false
        val send = JButton("Send")
        send.addActionListener {
            val reply = XavaniClient.chat(output.text.trim())
            output.text = reply ?: "no reply"
        }
        val panel = JPanel(BorderLayout())
        panel.add(JBScrollPane(output), BorderLayout.CENTER)
        panel.add(send, BorderLayout.SOUTH)
        toolWindow.contentManager.addContent(
            toolWindow.contentManager.factory.createContent(panel, "Xavani", false)
        )
    }
}
"""


_XAVANI_CLIENT_KT = """\
package com.enternovate.xavani

import java.net.URI
import java.net.http.HttpClient
import java.net.http.HttpRequest
import java.net.http.HttpResponse

/**
 * xavani-intellij — minimal gateway client for the tool window and actions.
 */
object XavaniClient {
    private val client: HttpClient = HttpClient.newHttpClient()

    fun chat(message: String): String? {
        val request = HttpRequest.newBuilder()
            .uri(URI.create("http://localhost:8765/v1/chat"))
            .header("Content-Type", "application/json")
            .POST(HttpRequest.BodyPublishers.ofString("{\\"message\\":\\"$message\\"}"))
            .build()
        return try {
            val body = client.send(request, HttpResponse.BodyHandlers.ofString()).body()
            body
        } catch (exc: Exception) {
            null
        }
    }
}
"""


def generate_jetbrains_plugin(version: str) -> Dict[str, str]:
    """Generate the JetBrains plugin files. Returns {path: content}."""
    return {
        "src/main/resources/META-INF/plugin.xml": _plugin_xml(version),
        "src/main/kotlin/com/enternovate/xavani/ChatAction.kt": _CHAT_ACTION_KT,
        "src/main/kotlin/com/enternovate/xavani/XavaniToolWindowFactory.kt": _TOOL_WINDOW_FACTORY_KT,
        "src/main/kotlin/com/enternovate/xavani/XavaniClient.kt": _XAVANI_CLIENT_KT,
    }


def validate_plugin(files: Dict[str, str]) -> List[str]:
    """Validate the JetBrains plugin scaffold. Returns a list of problems."""
    problems: List[str] = []
    required = (
        "src/main/resources/META-INF/plugin.xml",
        "src/main/kotlin/com/enternovate/xavani/ChatAction.kt",
        "src/main/kotlin/com/enternovate/xavani/XavaniToolWindowFactory.kt",
    )
    for path in required:
        if path not in files:
            problems.append(f"missing {path}")
    try:
        root = ET.fromstring(files.get("src/main/resources/META-INF/plugin.xml", ""))
    except ET.ParseError as exc:
        problems.append(f"plugin.xml invalid: {exc}")
        return problems
    if root.tag != "idea-plugin":
        problems.append("root element must be idea-plugin")
    if root.findtext("id") != PLUGIN_ID:
        problems.append(f"plugin id must be {PLUGIN_ID}")
    if not root.findtext("version"):
        problems.append("plugin version missing")
    actions = root.find("actions")
    action_ids: List[str] = []
    if actions is not None:
        action_ids = [
            str(action.get("id")) for action in actions.findall("action")
        ]
    if CHAT_ACTION_ID not in action_ids:
        problems.append(f"missing {CHAT_ACTION_ID} action")
    extensions = root.find("extensions")
    tool_windows = []
    if extensions is not None:
        tool_windows = [
            ext.get("id")
            for ext in extensions.findall("toolWindow")
            if ext.get("id") == TOOL_WINDOW_ID
        ]
    if not tool_windows:
        problems.append(f"missing {TOOL_WINDOW_ID} tool window")
    return problems
