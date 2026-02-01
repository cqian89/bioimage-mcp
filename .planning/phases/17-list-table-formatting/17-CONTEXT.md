# Phase 17 Context: Update list table formatting and versioning

## Phase Goal

Update `bioimage-mcp list` CLI output to show hierarchical tool/package structure with actual library versions instead of flat tool-pack listing with manifest versions.

**Scope:** CLI `bioimage-mcp list` command only. MCP API (`tools/list`) remains unchanged.

---

## Decisions

### 1. Output Hierarchy Depth

| Decision | Choice |
|----------|--------|
| Default view | Tool-pack with nested packages (hierarchical) |
| Expansion flag | No - always show same level of detail |
| MCP API changes | None - CLI only change |
| Function counts | Summary with breakdown (e.g., "865 (scipy:45, phasorpy:60...)") |

**Rationale:** Users need visibility into which packages are available within each tool-pack. The base environment alone has 7 packages with 865 functions - showing just "tools.base: 865" hides important structure.

**Example Output:**
```
base                     | 0.2.0       | installed | 865 (scipy:45, phasorpy:60, skimage:...)
  ├── scipy              | 1.14.1      |           | 45
  ├── phasorpy           | 0.8.0       |           | 60
  ├── skimage            | 0.24.0      |           | ...
  ...
cellpose                 | 3.1.0       | installed | 8
```

### 2. Version Information Source

| Decision | Choice |
|----------|--------|
| Display content | Library version only (not tool-pack manifest version) |
| Data source | Lockfile-first, fallback to live conda query |
| Which libraries | Primary wrapped libraries (scipy, phasorpy, cellpose, trackpy, stardist, tttrlib) |
| Missing versions | Fallback to tool_version from manifest |

**Rationale:** Users care about actual library versions (scipy 1.14.1) not internal manifest versions (0.2.0). Lockfile is fast and already exists for reproducibility.

**Version Resolution Order:**
1. Parse `envs/<env_id>.lock.yml` for package version
2. If no lockfile: `conda list -n <env_id> --json` (cached during install)
3. If no match: use `tool_version` from manifest

**Packages to extract versions for:**
- `base.scipy` → scipy version
- `base.phasorpy` → phasorpy version
- `base.skimage` → scikit-image version
- `base.pandas` → pandas version
- `cellpose` → cellpose version
- `trackpy` → trackpy version
- `stardist` → stardist version
- `tttrlib` → tttrlib version
- `base.io`, `base.matplotlib`, `base.xarray` → tool_version (no primary lib)

### 3. Naming Convention

| Decision | Choice |
|----------|--------|
| Tool-pack prefix | Drop "tools." prefix → just "base", "cellpose" |
| Package names | Short name under parent ("scipy" not "base.scipy") |
| Nesting indicator | Tree characters (├──, └──) |
| Tool-pack separation | Blank lines between tool-packs |

**Visual Format:**
```
Tool                     | Version     | Status    | Functions
─────────────────────────────────────────────────────────────────
base                     | 0.2.0       | installed | 865 (7 packages)
  ├── io                 | 0.2.0       |           | 24
  ├── matplotlib         | 3.9.0       |           | 15
  ├── pandas             | 2.2.0       |           | 12
  ├── phasorpy           | 0.8.0       |           | 60
  ├── scipy              | 1.14.1      |           | 450
  ├── skimage            | 0.24.0      |           | 290
  └── xarray             | 2024.10.0   |           | 14

cellpose                 | 3.1.0       | installed | 8
  └── models             | 3.1.0       |           | 8

stardist                 | 0.9.1       | installed | 5
  └── models             | 0.9.1       |           | 5

trackpy                  | 0.7.0       | installed | 137 (9 packages)
  ├── api                | 0.7.0       |           | ...
  ...

tttrlib                  | 0.0.24      | installed | 11
```

### 4. Backwards Compatibility

| Decision | Choice |
|----------|--------|
| JSON structure | Replace entirely with hierarchical format |
| Version field | Add `library_version` field, keep `tool_version` |
| ID field | Change to short form ("base" not "tools.base") |
| Breaking changes | Acceptable for v0.4.0 |

**New JSON Schema:**
```json
{
  "tools": [
    {
      "id": "base",
      "tool_version": "0.2.0",
      "library_version": null,
      "status": "installed",
      "function_count": 865,
      "packages": [
        {
          "id": "scipy",
          "library_version": "1.14.1",
          "function_count": 450
        },
        {
          "id": "phasorpy",
          "library_version": "0.8.0",
          "function_count": 60
        }
      ]
    },
    {
      "id": "cellpose",
      "tool_version": "0.1.0",
      "library_version": "3.1.0",
      "status": "installed",
      "function_count": 8,
      "packages": []
    }
  ]
}
```

---

## Non-Decisions (Out of Scope)

- MCP API (`tools/list`) structure - remains unchanged
- Function-level listing - use `--tool <id>` for that
- Version pinning/upgrading - that's install concern
- Performance optimization beyond lockfile caching

## Deferred Ideas

None captured during discussion.

---

## Implementation Hints

### Files to Modify
- `src/bioimage_mcp/bootstrap/list.py` - Main list logic
- `src/bioimage_mcp/bootstrap/list_cache.py` - Cache structure
- `tests/unit/bootstrap/test_list_output.py` - Update test expectations

### Version Extraction
```python
# Pseudo-code for lockfile parsing
def get_library_version(env_id: str, package_name: str) -> str | None:
    lockfile = Path(f"envs/{env_id}.lock.yml")
    if lockfile.exists():
        # Parse conda-lock format, find package entry
        ...
    return None  # Fallback to tool_version
```

### Package Mapping
Need a mapping from package ID to conda package name:
- `scipy` → `scipy`
- `skimage` → `scikit-image`
- `phasorpy` → `phasorpy`
- `cellpose` → `cellpose`
- etc.

---

*Context created: 2026-02-01*
*Phase: 17 of 17*
