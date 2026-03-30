# MCP Client Setup Guide

This guide explains how to connect common MCP clients to a local Bioimage-MCP
server.

## Before You Configure A Client

Complete the first-time setup in the repository [README](../../README.md) first.
In particular:

1. Install the package from a repo checkout with `python -m pip install -e .`
2. Run `bioimage-mcp configure` from the repo root
3. Edit `.bioimage-mcp/config.yaml` for your machine
4. Run `bioimage-mcp install --profile cpu`
5. Copy the config to `~/.bioimage-mcp/config.yaml`

That last step matters because `bioimage-mcp configure` writes a repo-local
config in the current working directory, while MCP clients may launch the server
from some other directory.

Before wiring a client, verify the install:

```bash
bioimage-mcp doctor
```

## Shared Server Command

All client configurations should use the same stdio server command:

```bash
bioimage-mcp serve --stdio
```

If `bioimage-mcp` is not on `PATH` inside the client environment, use the
absolute path to the Python interpreter where Bioimage-MCP is installed and run:

```bash
/absolute/path/to/python -m bioimage_mcp serve --stdio
```

## OpenCode

OpenCode uses `~/.config/opencode/opencode.json` for global config or
`opencode.json` in a project directory.

Example:

```json
{
  "mcp": {
    "bioimage-mcp": {
      "type": "local",
      "command": ["bioimage-mcp", "serve", "--stdio"],
      "enabled": true
    }
  }
}
```

After updating the config, reload OpenCode and verify the server is listed:

```bash
opencode mcp list
```

## Claude Desktop

Claude Desktop uses:

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\\Claude\\claude_desktop_config.json`

Example:

```json
{
  "mcpServers": {
    "bioimage-mcp": {
      "command": "bioimage-mcp",
      "args": ["serve", "--stdio"]
    }
  }
}
```

If needed, replace `bioimage-mcp` with the absolute path to the correct Python
interpreter and pass `-m`, `bioimage_mcp`, `serve`, `--stdio` in `args`.

## Cursor

Create or update `.cursor/mcp.json` in your project root:

```json
{
  "mcpServers": {
    "bioimage-mcp": {
      "command": "bioimage-mcp",
      "args": ["serve", "--stdio"]
    }
  }
}
```

## Generic MCP Clients

For Codex, VS Code, and other MCP clients, use the same stdio command:

```text
bioimage-mcp serve --stdio
```

and make sure `~/.bioimage-mcp/config.yaml` exists before launching the client.

## Troubleshooting

### Command Not Found

The client cannot find `bioimage-mcp` or the right Python environment. Use an
absolute interpreter path instead:

```text
/absolute/path/to/python -m bioimage_mcp serve --stdio
```

### Wrong Config Loaded

If the server starts but cannot see your data paths or installed tool manifests,
it is probably loading a different config than the one you edited. Copy your
repo-local config to:

```text
~/.bioimage-mcp/config.yaml
```

then restart the client.

### Connection Refused Or Closed

Run:

```bash
bioimage-mcp doctor
```

and fix any required failures before reconnecting.

### Path Not Allowlisted

If imports or exports fail, update `fs_allowlist_read` or
`fs_allowlist_write` in `~/.bioimage-mcp/config.yaml`, then restart the client.
