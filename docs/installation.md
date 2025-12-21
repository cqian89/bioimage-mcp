# Installation

## Prerequisites

*   **Operating System**: Linux, macOS, or Windows (WSL2 recommended).
*   **Python**: Version 3.13 or higher.
*   **Package Manager**: `micromamba` (preferred) or `conda` / `mamba`.
*   **Disk Space**: Sufficient space for artifact storage and tool environments.

## Step 1: Install the Package

Clone the repository and install in editable mode:

```bash
git clone https://github.com/your-org/bioimage-mcp.git
cd bioimage-mcp
python -m pip install -e .
```

## Step 2: Configure

Create a starter configuration file:

```bash
bioimage-mcp configure
```

This will create a configuration file (usually in `~/.bioimage-mcp/config.yaml` or `.bioimage-mcp/config.yaml`). You can edit this file to customize:
*   `artifact_store.root`: Where image artifacts and logs are stored.
*   `filesystem.allowed_read`: Paths the server is allowed to read from.
*   `filesystem.allowed_write`: Paths the server is allowed to export to.

## Step 3: Install Tool Environments

Bioimage-MCP uses isolated environments for different tool packs.

**Install the Base Environment (scikit-image, numpy):**
```bash
bioimage-mcp install --profile cpu
```

**Install the Cellpose Environment (optional):**
```bash
bioimage-mcp install --env bioimage-mcp-cellpose
```

## Step 4: Verify Installation

Run the "doctor" command to check system readiness:

```bash
bioimage-mcp doctor
```

This checks for:
*   Python version
*   Environment manager availability
*   Disk space and permissions
*   Network connectivity
*   Environment installation status
