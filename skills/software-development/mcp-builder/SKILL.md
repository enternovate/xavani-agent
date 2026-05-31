---
name: mcp-builder
description: Build MCP (Model Context Protocol) servers with proper tool definitions, resource handling, and error management.
categories:
  - software-development
platforms:
  - all
tags:
  - mcp
  - protocol
  - integration
condition: When building an MCP server or adding tools to an existing one.
---

# MCP Builder

> "An MCP server is just an API with a specific contract. Get the contract right."

## When to use

- Building a new MCP server.
- Adding tools to an existing MCP server.
- Integrating external services via MCP.

## Prerequisites

- MCP SDK installed (Python or TypeScript).
- Understanding of the target service's API.

## Steps

### 1. Define the server

```python
from mcp.server import Server
from mcp.types import Tool, TextContent

server = Server("my-server")

@server.list_tools()
async def list_tools():
    return [
        Tool(
            name="my_tool",
            description="Does something useful",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The query"}
                },
                "required": ["query"]
            }
        )
    ]
```

### 2. Implement tool handlers

```python
@server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "my_tool":
        result = await do_something(arguments["query"])
        return [TextContent(type="text", text=result)]
    raise ValueError(f"Unknown tool: {name}")
```

### 3. Error handling

Never expose internal errors to the client:
```python
try:
    result = await external_api_call(args)
except ExternalAPIError as exc:
    return [TextContent(type="text", text=f"Error: {exc.user_message}")]
except Exception:
    return [TextContent(type="text", text="Internal error. Check server logs.")]
```

### 4. Input validation

Validate all inputs before use:
```python
query = arguments.get("query", "")
if not query or len(query) > 1000:
    return [TextContent(type="text", text="Query must be 1-1000 characters.")]
```

### 5. Testing

Test each tool in isolation:
- Valid input → expected output.
- Invalid input → clear error message.
- Missing required field → validation error.
- External service down → graceful degradation.

## Verification

- All tools have descriptions and input schemas.
- All inputs are validated.
- Errors are handled gracefully.
- Each tool is tested.


## Provenance

Xavani-original (written from scratch for Xavani, based on the MCP protocol specification).
No upstream code was copied verbatim. This skill was authored by Enternovate
for the Xavani Agent platform under the MIT license.
