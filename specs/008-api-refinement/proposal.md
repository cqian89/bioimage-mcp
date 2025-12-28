# Proposal: API Refinement & Permission System

**Date:** December 28, 2025  
**Based on:** 007-workflow-test-harness completion, validation workflow findings, and user requirements  
**Status:** Draft  

## Executive Summary

This proposal addresses four major improvements to bioimage-mcp for the next development phase:

1. **Dynamic Permissions System** - Inherit from MCP client + ask pattern for existing files
2. **Tool Consolidation & Naming** - Remove `builtin`, use `env.package.module.function` scheme
3. **Hierarchical Discovery API** - List tools at any level, batch operations
4. **Enhanced Search & Agent Guidance** - Multi-keyword ranking, prefer `activate_function` workflow

---

## 1. File Permission System Redesign

### 1.1 Problem Statement

Current system requires manual configuration of `fs_allowlist_read` and `fs_allowlist_write` in `config.yaml`. This is:
- Inconvenient for typical workflows
- Inconsistent with how LLM agents naturally operate (they already have file access)
- Missing an "ask" pattern for potentially destructive operations

### 1.2 MCP SDK Research Findings

The MCP SDK provides:

| Feature | Description | Usage |
|---------|-------------|-------|
| **Roots Capability** | Client declares allowed directories | Server calls `session.list_roots()` to get client's workspace |
| **Elicitation** | Interactive prompts during tool execution | `ctx.elicit()` for forms, confirmation dialogs |

**Key insight**: Permissions are handled at **application level**, not protocol level. The standard pattern is for the **client** to declare roots via the Roots capability, and the server validates against them.

### 1.3 Proposed Design

#### Permission Mode Configuration

```yaml
# config.yaml
permissions:
  mode: "inherit"  # Options: "explicit" | "inherit" | "hybrid"
  on_overwrite: "ask"  # Options: "ask" | "allow" | "deny"

# For "explicit" mode (current behavior)
fs_allowlist_read: ["/data/images"]
fs_allowlist_write: ["/home/user/.bioimage-mcp"]
fs_denylist: []

# For "inherit" mode (new default)
# inherit_from_roots is implicit when mode is "inherit"
```

#### Default Behavior Changes

| Operation | Current Default | New Default |
|-----------|-----------------|-------------|
| Read from agent workspace | Denied (unless in allowlist) | **Allowed** (via Roots) |
| Write new file in workspace | Denied (unless in allowlist) | **Allowed** (via Roots) |
| Overwrite existing file | Allowed (if in allowlist) | **Ask** (elicitation) |
| Write outside workspace | Denied | Denied (unchanged) |

#### Implementation Approach

```python
class PermissionManager:
    async def get_allowed_roots(self) -> list[Path]:
        """Get allowed roots from client via MCP Roots capability."""
        if self.config.permissions.mode == "explicit":
            return self.config.fs_allowlist_read
        
        # Inherit from MCP client
        roots_result = await self.server.list_roots()
        return [Path(r.uri) for r in roots_result.roots]
    
    async def check_write(self, path: Path) -> WritePermission:
        """Check write permission, potentially prompting user."""
        if path.exists() and self.config.permissions.on_overwrite == "ask":
            return WritePermission.ASK  # Trigger elicitation
        return WritePermission.ALLOWED
```

### 1.4 Constitution Alignment

**Constitution Principle V (Safety)** currently states:
> "File and network access policies MUST be explicit (allowlisted roots; network off by default if configured)."

**Proposed Amendment**: The "inherit" mode satisfies "explicit" because the roots ARE explicitly declared by the MCP client. Add clarification that inherited roots must be logged at session start.

---

## 2. Tool Consolidation & Naming Scheme

### 2.1 Problem Statement

From validation report:
- `builtin.gaussian_blur` and `base.gaussian` have overlapping functionality
- `builtin` tools use different I/O dependencies than `base`, causing cross-environment failures
- Wrapper functions like `phasor_from_flim` obscure the underlying library functions

### 2.2 Analysis

| Tool | `builtin` | `base` | Overlap |
|------|-----------|--------|---------|
| Gaussian filter | `builtin.gaussian_blur` (scipy) | `base.gaussian` (skimage) | **Yes** |
| OME-Zarr convert | `builtin.convert_to_ome_zarr` | `base.convert_to_ome_zarr` | **Yes** |

**`phasor_from_flim` wraps:**
- `phasorpy.phasor.phasor_from_signal` - core computation
- Internal loading via `bioio` / `tifffile`
- Internal axis resolution and metadata inference

### 2.3 Proposed Solution

#### A. Remove `builtin` Tool Pack

**Rationale**:
- `builtin` was intended for minimal dependencies, but `base` already provides these
- Causes confusion about which tools to use
- Different I/O stacks cause cross-environment failures

**Actions**:
1. Remove `tools/builtin/` directory
2. Update `tool_manifest_roots` in default config
3. Add migration note for users

#### B. New Naming Scheme

**Current**: `base.gaussian`, `base.phasor_from_flim`

**Proposed**: `env_name.package_name.module_name.function_name`

Examples:
```
base.skimage.filters.gaussian
base.phasorpy.phasor.phasor_from_signal
base.scipy.ndimage.gaussian_filter
cellpose.cellpose.models.eval
```

#### C. Migration Path

Per Constitution v0.6.0, no migration path is required. `builtin` is removed immediately.

---

## 3. Hierarchical Discovery API

### 3.1 `list_tools` Redesign

**Current behavior**: Returns flat list of tool packs with pagination

**Proposed behavior**: Hierarchical navigation at any level

```python
# No args: list all installed environments/tool packs
list_tools() 
# -> ["base", "cellpose"]

# With path: list one level below
list_tools(path="base")
# -> ["skimage", "phasorpy", "scipy", "io", "transforms"]

list_tools(path="base.skimage")
# -> ["filters", "morphology", "transform", "measure"]

list_tools(path="base.skimage.filters")
# -> ["gaussian", "median", "sobel", "threshold_otsu", ...]

# List multiple paths in one call
list_tools(paths=["base.skimage.filters", "base.phasorpy.phasor"])
# -> combined results
```

### 3.2 Smart Hierarchy Shortcuts

**Problem**: For single-tool environments like cellpose, the full path `cellpose.cellpose.models.eval` requires 4 navigation calls.

**Solution**: Auto-expand single-child paths.

```python
# Without shortcuts (4 calls)
list_tools()  # → ["base", "cellpose"]
list_tools(path="cellpose")  # → ["cellpose"]  (the package)
list_tools(path="cellpose.cellpose")  # → ["models"]
list_tools(path="cellpose.cellpose.models")  # → ["eval", "train"]

# With shortcuts (2 calls)
list_tools()  # → ["base", "cellpose"]
list_tools(path="cellpose")  # → ["eval", "train"] directly!
```

**Flatten Parameter**:
```python
# Get all functions at once
list_tools(path="base", flatten=True)  # → all 47 functions
list_tools(flatten=True)  # → all functions across all envs
```

### 3.3 `search_functions` Enhancement

**Current**: Single query string, simple text match

**Proposed**: Multi-keyword with ranking

```python
async def search_functions(
    keywords: list[str] | str,  # Multiple keywords
    tags: list[str] | None = None,
    io_in: str | None = None,
    io_out: str | None = None,
    limit: int = 20,  # Default cap
) -> dict:
```

#### Ranking Algorithm

1. Functions matching more keywords rank higher
2. Within same keyword count, more total matches ranks higher
3. Match weights: name (3) > description (2) > tags (1)

### 3.4 Batch Operations

| Operation | Current | Proposed |
|-----------|---------|----------|
| `describe_function` | Single fn_id | `fn_ids: list[str]` |
| `activate_functions` | Already supports list | No change |
| `deactivate_functions` | Single reason | `fn_ids: list[str] \| None` (None = all) |

---

## 4. Rename `call_tool` → `run_function`

### 4.1 Rationale

- `call_tool` implies low-level tool invocation
- `run_function` better describes executing a registered function
- Aligns with naming: "function" is the unit of work

### 4.2 Status

`call_tool` is removed; `run_function` is the only execution API.

---

## 5. Guide Agent to `activate_function` Workflow

### 5.1 Problem

From observations, LLMs often call `run_function` directly without first activating functions, which:
- Bypasses the designed discovery flow
- May miss input/output validation hints
- Doesn't leverage the filtered context

### 5.2 Solutions

#### A. Response-Level Guidance

Add `workflow_hint` to every response:

```json
{
  "status": "succeeded",
  "outputs": {...},
  "workflow_hint": "TIP: Use activate_functions before run_function to get contextual hints."
}
```

#### B. Soft Warning Mode

```yaml
# config.yaml
agent_guidance:
  warn_unactivated: true  # Emit warning in response
```

---

## 6. Additional Fixes from Validation Report

### 6.1 Transformation Tool Bugs

From report:
> `base.moveaxis` and `base.swap_axes` fail with: "Dimension order string has 0 dims but data shape has 3 dims"

**Root cause**: Artifacts from `phasor_calibrate` lack dimension order metadata.

**Fix**: Ensure all output artifacts include `dims` metadata.

### 6.2 Cross-Environment I/O

**Fix** (addressed by removing `builtin`): All tools in `base` use same dependencies.

---

## Constitution Amendment (Applied)

**Version**: v0.6.0 (already amended)

The amendment has been applied.

### Proposed Changes to Constitution

#### Principle V Amendment

**Current**:
> "File and network access policies MUST be explicit (allowlisted roots; network off by default if configured)."

**Proposed**:
> "File and network access policies MUST be explicit and verifiable. Policies MAY be configured via:
> a) Explicit allowlists in configuration
> b) MCP Roots capability with session-start logging of inherited roots  
> c) Hybrid mode combining both
> Write operations to existing files SHOULD prompt for user confirmation via MCP Elicitation."

#### Architecture Constraints Addition

Add:
> - **Tool naming**: Functions SHOULD use `env.package.module.function` naming scheme for clarity
> - **API naming**: `run_function` is the canonical name for function execution (deprecates `call_tool`)

---

## Implementation Priority

| Priority | Item | Effort | Impact |
|----------|------|--------|--------|
| **P0** | Remove `builtin`, consolidate to `base` | 1 day | Eliminates I/O errors |
| **P0** | Fix dimension metadata in artifacts | 1 day | Unblocks axis tools |
| **P1** | Hierarchical `list_tools` | 2 days | Better discovery UX |
| **P1** | Smart hierarchy shortcuts | 1 day | Reduces agent roundtrips |
| **P1** | Multi-keyword search with ranking | 1 day | Better search results |
| **P1** | Rename `call_tool` → `run_function` | 0.5 day | Cleaner API |
| **P2** | MCP Roots integration for permissions | 2 days | Better defaults |
| **P2** | Elicitation for overwrite confirmation | 1 day | Safer writes |
| **P2** | Batch `describe_function` | 1 day | Reduced round-trips |
| **P3** | `activate_function` guidance in responses | 0.5 day | Better agent behavior |
| **P3** | New naming scheme with aliases | 2 days | Cleaner organization |

---

## Success Criteria

### For P0 items
- [ ] All tools run in `base` environment without cross-env I/O errors
- [ ] `base.moveaxis` and `base.swap_axes` work on phasor outputs
- [ ] Validation workflow completes without the 4 failures in report

### For P1 items
- [ ] `list_tools()` returns environment names
- [ ] `list_tools(path="base.skimage")` returns module names
- [ ] Multi-keyword search ranks `["phasor", "calibrate"]` with `phasor_calibrate` at top

### For P2 items
- [ ] Server inherits read roots from MCP client
- [ ] Overwriting existing files prompts for confirmation
- [ ] `describe_function(fn_ids=["a", "b"])` returns both schemas
