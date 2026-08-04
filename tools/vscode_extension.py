# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""F07: VS Code extension generator.

Generates the xavani-vscode extension manifest (package.json) plus the
command palette integration. The generator is deterministic; CI
validates the manifest (JSON shape, required contribution points).

Usage::

    from tools.vscode_extension import generate_vscode_extension, validate_extension

    files = generate_vscode_extension(version="0.7.2")
    problems = validate_extension(files)
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

EXTENSION_NAME = "xavani-vscode"


def generate_vscode_extension(version: str) -> Dict[str, str]:
    """Generate the VS Code extension files. Returns {path: content}."""
    manifest = {
        "name": EXTENSION_NAME,
        "displayName": "Xavani Agent",
        "version": version,
        "description": "Chat with the Xavani agent from VS Code",
        "publisher": "enternovate",
        "engines": {"vscode": "^1.90.0"},
        "categories": ["Other"],
        "main": "./out/extension.js",
        "activationEvents": ["onCommand:xavani.chat"],
        "contributes": {
            "commands": [
                {
                    "command": "xavani.chat",
                    "title": "Xavani: Chat",
                    "category": "Xavani",
                },
                {
                    "command": "xavani.resume",
                    "title": "Xavani: Resume Session",
                    "category": "Xavani",
                },
            ],
            "configuration": {
                "title": "Xavani",
                "properties": {
                    "xavani.baseUrl": {
                        "type": "string",
                        "default": "http://localhost:8765",
                        "description": "Xavani gateway base URL",
                    },
                    "xavani.apiKey": {
                        "type": "string",
                        "default": "",
                        "description": "Optional gateway API key",
                    },
                },
            },
        },
        "scripts": {"vscode:prepublish": "npm run compile"},
        "license": "MIT",
    }
    extension_ts = """\
import * as vscode from "vscode";

/**
 * xavani-vscode — chat with the Xavani agent from the command palette.
 */
export function activate(context: vscode.ExtensionContext) {
  const disposable = vscode.commands.registerCommand("xavani.chat", async () => {
    const config = vscode.workspace.getConfiguration("xavani");
    const baseUrl = config.get<string>("baseUrl", "http://localhost:8765");
    const message = await vscode.window.showInputBox({ prompt: "Message Xavani" });
    if (!message) return;
    const res = await fetch(`${baseUrl}/v1/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });
    const data = await res.json();
    vscode.window.showInformationMessage(String(data.text ?? "no reply"));
  });
  context.subscriptions.push(disposable);
}

export function deactivate() {}
"""
    return {
        "package.json": json.dumps(manifest, indent=2) + "\n",
        "src/extension.ts": extension_ts,
    }


def validate_extension(files: Dict[str, str]) -> List[str]:
    """Validate the extension. Returns a list of problems."""
    problems: List[str] = []
    for required in ("package.json", "src/extension.ts"):
        if required not in files:
            problems.append(f"missing {required}")
    try:
        manifest = json.loads(files.get("package.json", "{}"))
        if manifest.get("name") != EXTENSION_NAME:
            problems.append("extension name must be xavani-vscode")
        contributes = manifest.get("contributes", {})
        commands = contributes.get("commands", [])
        if not commands:
            problems.append("no contributed commands")
        if "xavani.chat" not in [c.get("command") for c in commands]:
            problems.append("missing xavani.chat command")
    except json.JSONDecodeError as exc:
        problems.append(f"package.json invalid: {exc}")
    return problems
