# bioimage-mcp

Bioimage-MCP is a local-first MCP server for bioimage analysis. It exposes a
stable, compact tool surface to AI clients while running analysis tools in
isolated conda environments and exchanging data through file-backed artifacts
instead of large in-memory payloads.

## What You Get

- Stable MCP tool surface for discovery, execution, artifacts, and replay
- Artifact-based I/O using references instead of raw array payloads
- Isolated tool environments for packages such as Cellpose and other tool packs
- Reproducible workflows through session export and replay

## Current Install Status

There is not yet a standalone end-user installer or published packaged setup
flow. The supported setup path today is:

1. Clone this repository.
2. Install the Python package from the checkout with `python -m pip install -e .`.
3. Create and edit the Bioimage-MCP config.
4. Install tool environments with `bioimage-mcp install`.
5. Connect your MCP client to `bioimage-mcp serve --stdio`.

If you are a first-time user, follow the setup guide below exactly.

## First-Time Setup

### Prerequisites

- Python 3.13 or newer
- `micromamba`, `mamba`, or `conda` on `PATH`
- Enough disk space for conda environments and the artifact store
- Linux, macOS, or Windows with WSL2 recommended on Windows

### 1. Clone And Install

```bash
git clone https://github.com/cqian89/bioimage-mcp.git
cd bioimage-mcp
python -m pip install -e .
```

This is the supported installation path today.

### 2. Generate Config From The Repo Root

Run `configure` from the cloned repository root:

```bash
bioimage-mcp configure
```

This creates a repo-local config at:

```text
<repo>/.bioimage-mcp/config.yaml
```

The `configure` command currently writes the config in the current working
directory, not directly to `~/.bioimage-mcp/config.yaml`.

### 3. Edit The Config Before First Use

Open `.bioimage-mcp/config.yaml` and update it for your machine before
connecting a client.

Important first-run rules:

- All configured paths must be absolute paths.
- `fs_allowlist_read` must include the directory that contains your input data.
- `fs_allowlist_write` must include the directory where exports are allowed.
- `artifact_store_root` should point to a writable location with enough space.

Minimal example:

```yaml
artifact_store_root: /home/you/.bioimage-mcp/artifacts
tool_manifest_roots:
  - /home/you/.bioimage-mcp/tools
fs_allowlist_read:
  - /home/you/data
fs_allowlist_write:
  - /home/you/exports
  - /home/you/.bioimage-mcp
fs_denylist:
  - /etc
  - /proc
microsam:
  device: auto
```

Notes:

- Keep the generated `tool_manifest_roots` entry unless you know you need
  something else.
- After you install tool environments from the repo, `bioimage-mcp install`
  will record the bundled repo tool manifests into the config automatically.
- If your data lives somewhere else, add that parent directory to
  `fs_allowlist_read` before trying to import files through the MCP server.

### 4. Install Tool Environments

For a first setup, install the default CPU profile:

```bash
bioimage-mcp install --profile cpu
```

This is the recommended first install. It installs the base environment and the
default CPU tool set, and updates your config with repo tool manifest paths.

Lighter alternatives if you only want the minimum runtime:

```bash
bioimage-mcp install --profile minimal
```

or

```bash
bioimage-mcp install base
```

### 5. Make The Config Visible To MCP Clients

After you finish editing the repo-local config, copy it to the global config
location used by the loader:

```bash
mkdir -p ~/.bioimage-mcp
cp .bioimage-mcp/config.yaml ~/.bioimage-mcp/config.yaml
```

If you are using Windows outside WSL, use the equivalent PowerShell commands to
create `%USERPROFILE%\\.bioimage-mcp` and copy `config.yaml` there.

This is the safest workflow for client-launched servers because clients may
start the process from a working directory other than the repository root. If
you skip this step, the server may load a different config than the one you
just edited.

### 6. Verify The Installation

Run the readiness checks:

```bash
bioimage-mcp doctor
```

Optionally inspect the installed tool status:

```bash
bioimage-mcp list
```

Ready enough for first use means:

- `bioimage-mcp doctor` reports `READY`
- your environment manager is detected
- the base profile or CPU profile installed without failures
- `bioimage-mcp list` shows the expected tool environments

### 7. Connect A Client

The server command is:

```bash
bioimage-mcp serve --stdio
```

#### OpenCode Example

Add this server to your OpenCode config:

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

If `bioimage-mcp` is not on `PATH` inside your client environment, replace it
with the absolute path to the Python interpreter for the environment where you
installed this package.

#### Common Client Notes

| Client | Command | Notes |
| --- | --- | --- |
| OpenCode | `bioimage-mcp serve --stdio` | Inline example above. |
| Claude Desktop | `bioimage-mcp serve --stdio` | Use the same stdio command in `mcpServers`. |
| Codex | `bioimage-mcp serve --stdio` | Use the same stdio command in your MCP server config. |
| VS Code | `bioimage-mcp serve --stdio` | Use the same stdio command in your MCP server definition. |

Use the global config at `~/.bioimage-mcp/config.yaml` for all client setups so
the server does not depend on being launched from the repo root.

For more client-specific examples, see
[docs/tutorials/mcp-client-setup.md](docs/tutorials/mcp-client-setup.md).

## MCP Tool Surface

Bioimage-MCP currently exposes these MCP tools:

- `list`
- `search`
- `describe`
- `run`
- `status`
- `artifact_info`
- `session_export`
- `session_replay`

## Troubleshooting

### No Env Manager On PATH

If `bioimage-mcp install` fails immediately, install `micromamba` first or use
an existing `mamba` or `conda` installation.

### Python Version Mismatch

The core package requires Python 3.13+. If `bioimage-mcp doctor` reports a
Python version problem, create or activate a Python 3.13 environment and
reinstall with:

```bash
python -m pip install -e .
```

### Path Not Allowlisted

If imports or exports fail with a permission or allowlist error, update these
fields in your config:

- `fs_allowlist_read` for input dataset locations
- `fs_allowlist_write` for export destinations

Then copy the updated config back to `~/.bioimage-mcp/config.yaml` before
retrying from your MCP client.

### Client Cannot See Tools Or Loads The Wrong Config

This usually means the server process started outside the repo root and only saw
the global config, or saw no config at all. Verify that:

- `~/.bioimage-mcp/config.yaml` exists
- it contains the paths you expect
- it was copied from the repo-local `.bioimage-mcp/config.yaml` after install

## Project Docs

- [docs/tutorials/mcp-client-setup.md](docs/tutorials/mcp-client-setup.md): client configuration examples
- [specs/027-smoke-test-expansion/quickstart.md](specs/027-smoke-test-expansion/quickstart.md): smoke tiers, markers, and CI smoke setup

## CI Workflows

GitHub Actions is Linux-first and uses two workflows:

- `.github/workflows/ci-pr.yml`: unit tests, contract tests, and PR-tier smoke on `ubuntu-latest`
- `.github/workflows/smoke-extended.yml`: scheduled/manual extended smoke on `ubuntu-latest`

Smoke jobs generate a repo-local config with:

```bash
bioimage-mcp configure
python scripts/ci/prepare_ci_config.py
```

This rewrites `.bioimage-mcp/config.yaml` so CI can read repo datasets and write
artifacts/logs under `.tmp/ci/` without copying config into `~/.bioimage-mcp`.
- [docs/reference/tools.md](docs/reference/tools.md): tool reference
