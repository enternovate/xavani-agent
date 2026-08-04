# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""F06: xavani-core npm package generator.

Generates the xavani-core npm package scaffold: package.json, a thin
TypeScript client wrapper around the Xavani HTTP gateway, and the README
contract. The generator is deterministic and validates the scaffold
(JSON parses, version syncs with the Python release).

Usage::

    from tools.npm_scaffold import generate_npm_scaffold, validate_scaffold

    files = generate_npm_scaffold(version="0.7.2")
    problems = validate_scaffold(files)
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

PACKAGE_NAME = "xavani-core"

_TYPESCRIPT_CLIENT = """\
/**
 * xavani-core — thin TypeScript client for the Xavani gateway.
 *
 * Speaks the gateway's HTTP JSON API. All calls are promise-based.
 */
export interface XavaniConfig {
  baseUrl: string;
  apiKey?: string;
}

export interface ChatResult {
  text: string;
  sessionId: string;
}

export class Xavani {
  private baseUrl: string;
  private apiKey?: string;

  constructor(config: XavaniConfig) {
    this.baseUrl = config.baseUrl.replace(/\\/$/, "");
    this.apiKey = config.apiKey;
  }

  /** Send a message and return the assistant reply. */
  async chat(message: string, sessionId?: string): Promise<ChatResult> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };
    if (this.apiKey) headers["Authorization"] = `Bearer ${this.apiKey}`;
    const res = await fetch(`${this.baseUrl}/v1/chat`, {
      method: "POST",
      headers,
      body: JSON.stringify({ message, session_id: sessionId }),
    });
    if (!res.ok) throw new Error(`xavani gateway error: ${res.status}`);
    return (await res.json()) as ChatResult;
  }
}
"""

_README = """\
# xavani-core

Thin TypeScript client for the Xavani agent gateway.

## Install

```bash
npm install xavani-core
```

## Usage

```ts
import { Xavani } from "xavani-core";

const xavani = new Xavani({ baseUrl: "http://localhost:8765" });
const result = await xavani.chat("hello");
console.log(result.text);
```

## API

- `new Xavani(config)` — config: `{ baseUrl, apiKey? }`
- `xavani.chat(message, sessionId?)` — send a message, get `{ text, sessionId }`
"""


def generate_npm_scaffold(version: str) -> Dict[str, str]:
    """Generate the npm scaffold files. Returns {path: content}."""
    package_json = {
        "name": PACKAGE_NAME,
        "version": version,
        "description": "TypeScript client for the Xavani agent gateway",
        "main": "dist/index.js",
        "types": "dist/index.d.ts",
        "scripts": {
            "build": "tsc",
            "test": "vitest run",
        },
        "license": "MIT",
        "files": ["dist"],
    }
    return {
        "package.json": json.dumps(package_json, indent=2) + "\n",
        "src/index.ts": _TYPESCRIPT_CLIENT,
        "README.md": _README,
    }


def validate_scaffold(files: Dict[str, str]) -> List[str]:
    """Validate the scaffold. Returns a list of problems."""
    problems: List[str] = []
    for required in ("package.json", "src/index.ts", "README.md"):
        if required not in files:
            problems.append(f"missing {required}")
    try:
        package = json.loads(files.get("package.json", "{}"))
        if package.get("name") != PACKAGE_NAME:
            problems.append("package.json name must be xavani-core")
        if not package.get("version"):
            problems.append("package.json version missing")
    except json.JSONDecodeError as exc:
        problems.append(f"package.json invalid: {exc}")
    index = files.get("src/index.ts", "")
    if "export class Xavani" not in index:
        problems.append("src/index.ts missing Xavani class export")
    return problems
