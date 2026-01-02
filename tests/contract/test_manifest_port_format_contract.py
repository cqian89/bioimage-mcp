from __future__ import annotations

from pathlib import Path

import pytest

from bioimage_mcp.registry.loader import load_manifests
from bioimage_mcp.registry.manifest_schema import InterchangeFormat


def test_manifest_port_formats_canonical() -> None:
    """T007: Verify all Port.format values in manifests use canonical values only.

    Requirements:
    - Values must be 'OME-TIFF' or 'OME-Zarr'
    - Values are case-sensitive
    - All manifest files in tools/*/manifest.yaml must be checked
    """
    tools_root = Path(__file__).parent.parent.parent / "tools"
    manifests, diagnostics = load_manifests([tools_root])

    canonical_values = {f.value for f in InterchangeFormat}
    errors = []

    # Check diagnostics for manifests that failed to load due to validation errors
    for diag in diagnostics:
        for error in diag.errors:
            # We specifically look for format validation errors
            if "format" in error or "InterchangeFormat" in error:
                errors.append(f"Format validation error in {diag.path}:\n{error}")

    # Check successfully loaded manifests for non-canonical values
    # (Though Pydantic should have caught these, we verify explicitly for the contract)
    for manifest in manifests:
        for fn in manifest.functions:
            # Check inputs
            for port in fn.inputs:
                if (
                    port.artifact_type in ("BioImageRef", "LabelImageRef")
                    and port.format
                    and port.format not in canonical_values
                ):
                    errors.append(
                        f"Manifest '{manifest.tool_id}', function '{fn.fn_id}', "
                        f"input port '{port.name}' has invalid format '{port.format}'. "
                        f"Expected one of: {sorted(canonical_values)}"
                    )

            # Check outputs
            for port in fn.outputs:
                if (
                    port.artifact_type in ("BioImageRef", "LabelImageRef")
                    and port.format
                    and port.format not in canonical_values
                ):
                    errors.append(
                        f"Manifest '{manifest.tool_id}', function '{fn.fn_id}', "
                        f"output port '{port.name}' has invalid format '{port.format}'. "
                        f"Expected one of: {sorted(canonical_values)}"
                    )

    if errors:
        pytest.fail("Non-canonical Port.format values found:\n" + "\n".join(errors))


def test_interchange_format_enum_validation() -> None:
    """T007: Comprehensive test for InterchangeFormat enum validation."""
    # 1. Verify canonical values
    assert InterchangeFormat.OME_TIFF.value == "OME-TIFF"
    assert InterchangeFormat.OME_ZARR.value == "OME-Zarr"

    # 2. Verify successful instantiation from valid strings
    assert InterchangeFormat("OME-TIFF") == InterchangeFormat.OME_TIFF
    assert InterchangeFormat("OME-Zarr") == InterchangeFormat.OME_ZARR

    # 3. Verify case-sensitivity (must fail)
    with pytest.raises(ValueError):
        InterchangeFormat("ome-tiff")
    with pytest.raises(ValueError):
        InterchangeFormat("ome-zarr")
    with pytest.raises(ValueError):
        InterchangeFormat("OME-TIFF".lower())
    with pytest.raises(ValueError):
        InterchangeFormat("OME-ZARR")  # Should be OME-Zarr

    # 4. Verify invalid values (must fail)
    invalid_values = ["TIFF", "Zarr", "JSON", "cellpose-seg-npy", "raw"]
    for val in invalid_values:
        with pytest.raises(ValueError):
            InterchangeFormat(val)


def test_all_tool_manifests_loaded() -> None:
    """Ensure we are actually checking all tool manifests."""
    tools_root = Path(__file__).parent.parent.parent / "tools"
    manifest_files = list(tools_root.glob("*/manifest.yaml"))

    assert len(manifest_files) >= 2, (
        f"Expected at least 2 manifests (base, cellpose), found {len(manifest_files)}"
    )

    manifests, diagnostics = load_manifests([tools_root])
    loaded_paths = {m.manifest_path for m in manifests} | {d.path for d in diagnostics}

    for mf in manifest_files:
        assert mf in loaded_paths, f"Manifest file {mf} was not loaded or diagnosed"
