"""Contract test: Core server must not import heavy I/O libraries.

Per Constitution III (Artifact References Only), the core server must delegate
all heavy I/O operations to isolated tool environments. This test ensures
bioio and related libraries are never imported in core server code.

Rationale:
- Heavy I/O libraries (bioio, bioio-ome-tiff, bioio-ome-zarr) should only exist
  in isolated tool environments to keep the core server lightweight
- Artifact references (URIs + metadata) are the only I/O contract at the core level
- Tool packs handle actual file I/O in their isolated environments
- This prevents dependency bloat and maintains clear architectural boundaries

Import Rules:
1. Top-level imports are ALWAYS violations (imported at module load time)
2. Lazy imports (inside functions) may be acceptable in specific execution contexts:
   - Adapter files that only execute in worker processes
   - Functions that are never called during server startup
3. Files in critical server paths (api/, server.py) must NEVER import bioio
"""

import ast
from pathlib import Path

import pytest

# Core server code path (excludes tool packs)
CORE_PATH = Path(__file__).parents[2] / "src" / "bioimage_mcp"

# Forbidden imports in core server code
FORBIDDEN_IMPORTS = ["bioio", "bioio_ome_tiff", "bioio_ome_zarr"]

# Files allowed to have ONLY lazy imports (inside functions, not at module level)
# These are execution adapters that run in worker processes, not during server startup
LAZY_IMPORT_ALLOWLIST = [
    "registry/dynamic/adapters/skimage.py",
    "registry/dynamic/adapters/xarray.py",
    "registry/dynamic/adapters/phasorpy.py",
    "registry/dynamic/adapters/scipy_ndimage.py",
    "registry/dynamic/adapters/microsam.py",
    "artifacts/metadata.py",  # Uses graceful fallback if bioio not available
    "artifacts/store.py",  # Lazy imports for export conversions
    "artifacts/preview.py",  # Lazy imports for BioImageRef previews
]

# Files/directories that must NEVER have bioio imports (top-level or lazy)
# These are critical server startup paths
STRICT_BLOCKLIST = [
    "api/",  # All API handlers run during server startup
    "server.py",
]


def find_python_files(root: Path) -> list[Path]:
    """Find all Python files in the given directory tree."""
    return list(root.rglob("*.py"))


class ImportAnalysis:
    """Analysis result for imports in a file."""

    def __init__(self):
        self.top_level_imports: set[str] = set()
        self.lazy_imports: set[str] = set()


def analyze_imports(file_path: Path) -> ImportAnalysis:
    """Analyze imports in a Python file, distinguishing top-level from lazy.

    Top-level imports: import statements at module level or in class definitions
    Lazy imports: import statements inside function/method bodies

    Returns:
        ImportAnalysis with categorized imports
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=str(file_path))
    except SyntaxError:
        # Skip files with syntax errors (may be templates or broken)
        return ImportAnalysis()

    analysis = ImportAnalysis()

    def is_inside_function(node: ast.AST, parent_map: dict) -> bool:
        """Check if a node is inside a function or method definition."""
        current = node
        while current in parent_map:
            parent = parent_map[current]
            if isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef)):
                return True
            current = parent
        return False

    # Build parent map for traversal
    parent_map: dict[ast.AST, ast.AST] = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parent_map[child] = parent

    # Categorize imports
    for node in ast.walk(tree):
        module_names: list[str] = []

        # Handle: import bioio, import bioio.something
        if isinstance(node, ast.Import):
            for alias in node.names:
                module_names.append(alias.name.split(".")[0])

        # Handle: from bioio import X, from bioio.something import Y
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                module_names.append(node.module.split(".")[0])

        # Categorize based on context
        if module_names:
            if is_inside_function(node, parent_map):
                analysis.lazy_imports.update(module_names)
            else:
                analysis.top_level_imports.update(module_names)

    return analysis


def test_no_bioio_imports_in_core():
    """Verify that core server code does not import bioio or related libraries.

    This test enforces Constitution III by ensuring the core server remains
    lightweight and delegates all heavy I/O operations to tool environments.

    Rules:
    1. Top-level imports are ALWAYS violations
    2. Lazy imports are violations EXCEPT in allowlisted adapter files
    3. Allowlisted files must ONLY have lazy imports (no top-level)
    4. Blocklisted files must NEVER have any bioio imports
    """
    top_level_violations = []
    lazy_violations = []
    allowlist_violations = []  # Allowlisted files with top-level imports
    blocklist_violations = []  # Blocklisted files with any imports

    # Scan all Python files in core server
    for py_file in find_python_files(CORE_PATH):
        # Skip test files if any exist in the core path
        if "test_" in py_file.name or py_file.parent.name == "tests":
            continue

        rel_path = py_file.relative_to(CORE_PATH)
        rel_path_str = str(rel_path).replace("\\", "/")

        # Analyze imports
        analysis = analyze_imports(py_file)

        # Check for forbidden imports
        forbidden_top_level = analysis.top_level_imports & set(FORBIDDEN_IMPORTS)
        forbidden_lazy = analysis.lazy_imports & set(FORBIDDEN_IMPORTS)

        # Check blocklist files - NEVER allowed
        is_blocklisted = False
        for blocked in STRICT_BLOCKLIST:
            if blocked.endswith("/"):
                # Directory blocklist: check if file is in this directory
                if rel_path_str.startswith(blocked):
                    is_blocklisted = True
                    break
            else:
                # File blocklist: exact match
                if rel_path_str.endswith(blocked):
                    is_blocklisted = True
                    break

        if is_blocklisted:
            if forbidden_top_level or forbidden_lazy:
                blocklist_violations.append(
                    f"{rel_path}: imports {forbidden_top_level | forbidden_lazy} "
                    "(STRICT BLOCKLIST - no imports allowed)"
                )
            continue

        # Check allowlist files - only lazy imports allowed
        if any(rel_path_str.endswith(allowed) for allowed in LAZY_IMPORT_ALLOWLIST):
            if forbidden_top_level:
                allowlist_violations.append(
                    f"{rel_path}: has TOP-LEVEL imports {forbidden_top_level} "
                    "(allowlisted files may only use LAZY imports)"
                )
            # Lazy imports are OK for allowlisted files
            continue

        # All other files: top-level is violation, lazy is violation
        if forbidden_top_level:
            top_level_violations.append(f"{rel_path}: has TOP-LEVEL imports {forbidden_top_level}")

        if forbidden_lazy:
            lazy_violations.append(
                f"{rel_path}: has LAZY imports {forbidden_lazy} "
                "(not in allowlist, move to tool pack or add to allowlist)"
            )

    # Report all violations together for better debugging
    all_violations = (
        blocklist_violations + top_level_violations + allowlist_violations + lazy_violations
    )

    if all_violations:
        error_msg = (
            "\n\nConstitution III violation: Core server imports heavy I/O libraries\n\n"
            "The following files violate import rules:\n"
            + "\n".join(f"  - {v}" for v in all_violations)
            + "\n\n"
            "Forbidden imports in core server code:\n"
            + "\n".join(f"  - {m}" for m in FORBIDDEN_IMPORTS)
            + "\n\n"
            "Import Rules:\n"
            "  1. Top-level imports are ALWAYS violations (loaded at server startup)\n"
            "  2. Lazy imports (inside functions) are violations EXCEPT in allowlisted adapters\n"
            "  3. Allowlisted adapter files may ONLY use lazy imports (not top-level)\n"
            "  4. Blocklisted files (api/, server.py) must NEVER import bioio\n" + "\n\n"
            "Solution: Move I/O operations to tool packs (tools/base/, tools/cellpose/, etc.)\n"
            "Core code should only handle artifact references (URIs + metadata).\n"
        )
        pytest.fail(error_msg)
