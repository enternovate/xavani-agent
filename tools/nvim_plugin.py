# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""F08: Neovim plugin generator.

Generates the xavani.nvim plugin scaffold: lua module, RPC client to
the Xavani gateway, and README. Deterministic + validated.

Usage::

    from tools.nvim_plugin import generate_nvim_plugin, validate_plugin

    files = generate_nvim_plugin(version="0.7.2")
    problems = validate_plugin(files)
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

_LUA_MODULE = """\
-- xavani.nvim — Neovim client for the Xavani agent gateway.
local M = {}

local defaults = { base_url = "http://localhost:8765" }
M.config = vim.deepcopy(defaults)

function M.setup(opts)
  M.config = vim.tbl_deep_extend("force", defaults, opts or {})
end

--- Send a message and print the reply.
---@param message string
function M.chat(message)
  local body = vim.json.encode({ message = message })
  local cmd = {
    "curl", "-s", "-X", "POST",
    "-H", "Content-Type: application/json",
    "-d", body,
    M.config.base_url .. "/v1/chat",
  }
  local output = vim.fn.systemlist(cmd)
  local ok, decoded = pcall(vim.json.decode, table.concat(output, ""))
  if ok and decoded and decoded.text then
    print(decoded.text)
  else
    print("xavani: no reply")
  end
end

function M.setup_commands()
  vim.api.nvim_create_user_command("Xavani", function(args)
    M.chat(args.args)
  end, { nargs = "*", desc = "Chat with the Xavani agent" })
end

return M
"""

_README = """\
# xavani.nvim

Neovim client for the Xavani agent gateway.

## Install (lazy.nvim)

```lua
{
  "enternovate/xavani.nvim",
  config = function()
    require("xavani").setup({ base_url = "http://localhost:8765" })
  end,
}
```

## Usage

```vim
:Xavani write a test for this module
```
"""


def generate_nvim_plugin(version: str) -> Dict[str, str]:
    """Generate the Neovim plugin files. Returns {path: content}."""
    return {
        "lua/xavani/init.lua": _LUA_MODULE,
        "README.md": _README,
        "plugin/plugin.lua": (
            "--- xavani.nvim entry point\n"
            'local xavani = require("xavani")\n'
            "xavani.setup_commands()\n"
        ),
        "version.json": json.dumps({"version": version}) + "\n",
    }


def validate_plugin(files: Dict[str, str]) -> List[str]:
    """Validate the plugin scaffold. Returns a list of problems."""
    problems: List[str] = []
    for required in ("lua/xavani/init.lua", "plugin/plugin.lua", "README.md", "version.json"):
        if required not in files:
            problems.append(f"missing {required}")
    lua = files.get("lua/xavani/init.lua", "")
    if "function M.chat" not in lua:
        problems.append("lua module missing M.chat")
    if "nvim_create_user_command" not in lua:
        problems.append("lua module missing user command setup")
    if "setup_commands()" not in files.get("plugin/plugin.lua", ""):
        problems.append("entry point missing setup_commands() call")
    try:
        version_data = json.loads(files.get("version.json", "{}"))
        if not version_data.get("version"):
            problems.append("version.json missing version")
    except json.JSONDecodeError as exc:
        problems.append(f"version.json invalid: {exc}")
    return problems
