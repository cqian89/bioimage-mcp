#!/usr/bin/env python3
"""Dynamic registry validation script (T021, T022).

Validates that all dynamically discovered functions have descriptions
and that manifest loading performance meets requirements.

Usage:
    python scripts/validate_dynamic_registry.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

# Add src to path for direct script execution
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from bioimage_mcp.registry.loader import load_manifests


def validate_descriptions(manifests) -> tuple[int, int]:
    """Validate that all functions have non-empty descriptions (T021).

    Args:
        manifests: List of ToolManifest objects

    Returns:
        Tuple of (total_functions, functions_without_descriptions)
    """
    total = 0
    missing_descriptions = 0
    missing_details = []

    for manifest in manifests:
        for func in manifest.functions:
            total += 1
            if not func.description or func.description.strip() == "":
                missing_descriptions += 1
                missing_details.append(f"  - {func.fn_id} (tool: {manifest.tool_id})")

    print("\n" + "=" * 60)
    print("Description Validation (T021)")
    print("=" * 60)
    print(f"Total functions: {total}")
    print(f"Functions without descriptions: {missing_descriptions}")

    if missing_descriptions > 0:
        print("\nFunctions missing descriptions:")
        for detail in missing_details:
            print(detail)

    return total, missing_descriptions


def validate_performance(tools_dir: Path) -> tuple[float, float]:
    """Validate manifest loading performance (T022).

    Args:
        tools_dir: Path to tools directory

    Returns:
        Tuple of (cold_time, warm_time) in seconds
    """
    print("\n" + "=" * 60)
    print("Performance Validation (T022)")
    print("=" * 60)

    # Cold run
    print("Running cold load...")
    start = time.perf_counter()
    manifests_cold, diagnostics_cold = load_manifests([tools_dir])
    cold_time = time.perf_counter() - start
    print(f"  Cold load time: {cold_time:.4f}s")
    print(f"  Manifests loaded: {len(manifests_cold)}")
    print(f"  Diagnostics: {len(diagnostics_cold)}")

    # Warm run
    print("\nRunning warm load...")
    start = time.perf_counter()
    manifests_warm, diagnostics_warm = load_manifests([tools_dir])
    warm_time = time.perf_counter() - start
    print(f"  Warm load time: {warm_time:.4f}s")
    print(f"  Manifests loaded: {len(manifests_warm)}")
    print(f"  Diagnostics: {len(diagnostics_warm)}")

    return cold_time, warm_time


def main() -> int:
    """Main entry point for validation script."""
    print("=" * 60)
    print("Dynamic Registry Validation Script")
    print("=" * 60)

    # Locate tools directory
    root = Path(__file__).parent.parent
    tools_dir = root / "tools"

    if not tools_dir.exists():
        print(f"\nError: Tools directory not found: {tools_dir}")
        return 1

    print(f"\nTools directory: {tools_dir}")

    # Load manifests for description validation
    print("\nLoading manifests for validation...")
    manifests, diagnostics = load_manifests([tools_dir])

    if diagnostics:
        print(f"\nWarning: {len(diagnostics)} manifest(s) had loading errors:")
        for diag in diagnostics:
            print(f"  - {diag.path}: {diag.errors}")

    if not manifests:
        print("\nError: No manifests loaded successfully")
        return 1

    # Validate descriptions (T021)
    total_functions, missing_descriptions = validate_descriptions(manifests)

    # Validate performance (T022)
    cold_time, warm_time = validate_performance(tools_dir)

    # Generate summary report
    print("\n" + "=" * 60)
    print("Summary Report")
    print("=" * 60)

    failures = []

    # Check T021: Description validation
    if missing_descriptions > 0:
        failures.append(f"T021 FAILED: {missing_descriptions} function(s) missing descriptions")
    else:
        print("✓ T021 PASSED: All functions have descriptions")

    # Check T022: Performance validation (warm run < 2.0s)
    if warm_time >= 2.0:
        failures.append(f"T022 FAILED: Warm load time {warm_time:.4f}s >= 2.0s")
    else:
        print(f"✓ T022 PASSED: Warm load time {warm_time:.4f}s < 2.0s")

    # Print overall result
    print("=" * 60)

    if failures:
        print("\n❌ VALIDATION FAILED")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    else:
        print("\n✅ ALL VALIDATIONS PASSED")
        print(f"  - {total_functions} functions validated")
        print(f"  - Cold load: {cold_time:.4f}s")
        print(f"  - Warm load: {warm_time:.4f}s")
        return 0


if __name__ == "__main__":
    sys.exit(main())
