# Phase 17: Update list table formatting and versioning - Research

**Researched:** 2026-02-01
**Domain:** CLI output formatting, Conda environment introspection
**Confidence:** HIGH

## Summary

This phase focuses on improving the `bioimage-mcp list` CLI command to provide a hierarchical view of tools and their constituent packages, including actual library versions extracted from conda lockfiles. The research confirms that the necessary data exists in the `envs/*.lock.yml` files and that the current CLI implementation can be extended to support the requested format without adding heavy dependencies like `rich` (unless desired for future-proofing).

**Primary recommendation:** Use `PyYAML` to parse `envs/*.lock.yml` as the primary source of truth for library versions, falling back to `conda list --json` only when necessary. Group functions by their ID prefix (e.g., `base.scipy.*` -> `scipy`) to generate the hierarchical view.

## Standard Stack

The project already includes the necessary tools for this implementation.

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `PyYAML` | 6.0+ | Parsing lockfiles | Project already uses it for manifests and config. |
| `argparse` | Stdlib | CLI parsing | Project's current CLI framework. |
| `json` | Stdlib | Output/Conda | Used for `--json` output and parsing conda responses. |
| `pathlib` | Stdlib | File I/O | Standard for path manipulation in the project. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `rich` | 13.x | Tree/Table formatting | *Optional:* If advanced visual styling is required. Currently used in some tool envs but not core. |

**Installation:**
No new packages are strictly required for the core server to implement this, as `PyYAML` is already a dependency.

## Architecture Patterns

### Recommended Internal Data Structure
To support both hierarchical text and the new JSON schema, `list_tools` should transform the flat manifest list into a structured model:

```python
class PackageInfo(BaseModel):
    id: str
    library_version: str | None
    function_count: int

class ToolInfo(BaseModel):
    id: str
    tool_version: str
    library_version: str | None
    status: str
    function_count: int
    packages: list[PackageInfo]
```

### Version Resolution Order
1.  **Lockfile**: Search `envs/<env_id>.lock.yml` for the package name.
2.  **Live Query**: Run `conda list -n <env_id> --json` (if manager available and env installed).
3.  **Manifest Fallback**: Use `tool_version` from the manifest.

### Grouping Logic
1.  Take the `tool_id` (e.g., `tools.base`).
2.  For each function in the manifest, strip the tool ID prefix (e.g., `base.`).
3.  The first segment of the remaining ID is the `package_id` (e.g., `scipy`, `skimage`, `io`).
4.  Aggregate function counts by `package_id`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Lockfile Parsing | Custom regex | `yaml.safe_load` | Conda-lock files are valid YAML. |
| Environment Query | Parsing `conda list` text | `conda list --json` | JSON output is stable and easy to parse. |
| Tree Visualization | Manual spacing logic | *Consider* `rich.tree` | Handles complex nesting and characters correctly. |

## Common Pitfalls

### Pitfall 1: Package Naming Divergence
**What goes wrong:** Internal package ID (e.g., `skimage`) differs from Conda package name (e.g., `scikit-image`).
**How to avoid:** Maintain a hardcoded mapping for primary libraries in `src/bioimage_mcp/bootstrap/list.py`.

### Pitfall 2: Conda-Lock Multi-Platform
**What goes wrong:** `conda-lock` can contain packages for multiple platforms in one file.
**How to avoid:** Filter the `package` list in the lockfile by `platform` (e.g., `linux-64`) if specified in the metadata.

### Pitfall 3: Cache Invalidation
**What goes wrong:** CLI cache shows old versions after a tool is updated.
**How to avoid:** Increment `CACHE_VERSION` in `src/bioimage_mcp/bootstrap/list_cache.py` to force a refresh on the first run after implementation.

## Code Examples

### Parsing Conda-Lock (v1 format)
```python
import yaml
from pathlib import Path

def get_version_from_lockfile(env_id: str, conda_package_name: str) -> str | None:
    lock_path = Path("envs") / f"{env_id}.lock.yml"
    if not lock_path.exists():
        return None
    
    with open(lock_path) as f:
        data = yaml.safe_load(f)
    
    # Conda-lock v1 format
    packages = data.get("package", [])
    for pkg in packages:
        if pkg.get("name") == conda_package_name:
            return str(pkg.get("version"))
    return None
```

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| Flat Tool List | Hierarchical Package Tree | Better visibility into tool-pack contents. |
| Manifest Version | Actual Library Version | Transparent environment state for users. |

## Open Questions

1.  **Rich Library Adoption**: Should we add `rich` to core dependencies? It would make the tree rendering much cleaner and support colors, but adds ~5MB of dependencies.
    - *Recommendation*: Start with manual formatting to keep core lightweight, or use a "poor man's tree" implementation.

2.  **Performance**: Parsing 5+ YAML lockfiles on every `list` call.
    - *Recommendation*: The existing `ListToolsCache` should be updated to cache the resolved hierarchical structure, including versions.

## Sources

### Primary (HIGH confidence)
- `envs/*.lock.yml` - Verified format in the codebase.
- `src/bioimage_mcp/bootstrap/list.py` - Analyzed current implementation.
- `PyYAML` documentation - Confirmed YAML 1.2 support.

### Metadata
**Confidence breakdown:**
- Standard stack: HIGH
- Architecture: HIGH
- Pitfalls: MEDIUM (platform filtering needs care)

**Research date:** 2026-02-01
**Valid until:** 2026-03-01
