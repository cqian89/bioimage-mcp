#!/usr/bin/env python3
"""Pipeline validation script (T034).

Runs segmentation pipeline on sample datasets to validate end-to-end functionality.
Used for CI/CD and manual verification.

Usage:
    python scripts/validate_pipeline.py [--dry-run] [--samples-dir DIR]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add src to path for direct script execution
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from bioimage_mcp.api.execution import ExecutionService
from bioimage_mcp.config.schema import Config


def get_default_config() -> Config:
    """Get default configuration for validation."""
    root = Path(__file__).parent.parent
    return Config(
        artifact_store_root=root / "artifacts",
        tool_manifest_roots=[root / "tools" / "cellpose"],
        fs_allowlist_read=[root],
        fs_allowlist_write=[root / "artifacts"],
        fs_denylist=[],
    )


def normalize_samples_dir(samples_dir: str | None) -> Path | None:
    """Normalize samples directory argument."""
    if samples_dir is None:
        return None
    cleaned = samples_dir.strip()
    if not cleaned:
        return None
    return Path(cleaned)


def default_sample_dirs(root: Path) -> list[Path]:
    """Return default dataset directories to search."""
    return [
        root / "datasets" / "samples",
        root / "datasets" / "synthetic",
        root / "datasets" / "FLUTE_FLIM_data_tif",
    ]


def is_image_file(path: Path) -> bool:
    """Check if a path looks like a supported image file."""
    extensions = (".ome.tiff", ".ome.tif", ".tiff", ".tif", ".png")
    return path.is_file() and path.name.lower().endswith(extensions)


def find_sample_images(samples_dir: Path, recursive: bool = True) -> list[Path]:
    """Find sample microscopy images in the given directory."""
    images = []

    if not samples_dir.exists():
        return images

    paths = samples_dir.rglob("*") if recursive else samples_dir.iterdir()
    for path in paths:
        if is_image_file(path):
            images.append(path)

    return sorted(images)


def collect_samples(
    samples_dir: Path | None,
    root: Path,
) -> tuple[Path | None, list[Path]]:
    """Collect sample images from the provided or default datasets."""
    if samples_dir is not None:
        samples = find_sample_images(samples_dir, recursive=True)
        if samples:
            return samples_dir, samples
        return None, []

    for candidate in default_sample_dirs(root):
        samples = find_sample_images(candidate, recursive=True)
        if samples:
            return candidate, samples

    return None, []


def validate_image(svc: ExecutionService, image_path: Path, dry_run: bool = False) -> bool:
    """Run validation on a single image.

    Returns True if validation passed, False otherwise.
    """
    print(f"  Validating: {image_path.name}")

    if dry_run:
        print(f"    [DRY-RUN] Would process: {image_path}")
        return True

    try:
        result = svc.run_workflow(
            {
                "steps": [
                    {
                        "id": "cellpose.segment",
                        "inputs": {
                            "image": {
                                "type": "BioImageRef",
                                "format": "OME-TIFF",
                                "uri": image_path.as_uri(),
                            }
                        },
                        "params": {
                            "model_type": "cyto3",
                            "diameter": 30.0,
                        },
                    }
                ]
            },
            skip_validation=True,
        )

        if result["status"] == "succeeded":
            print("    ✓ Passed")
            return True
        else:
            print(f"    ✗ Failed: {result.get('error', 'Unknown error')}")
            return False

    except Exception as e:
        print(f"    ✗ Error: {e}")
        return False


def main() -> int:
    """Main entry point for validation script."""
    parser = argparse.ArgumentParser(
        description="Validate Cellpose segmentation pipeline on sample datasets"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be done without executing",
    )
    parser.add_argument(
        "--samples-dir",
        type=str,
        default=None,
        help="Directory containing sample images",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("Pipeline Validation Script")
    print("=" * 60)

    root = Path(__file__).parent.parent
    samples_dir = normalize_samples_dir(args.samples_dir)
    selected_dir, samples = collect_samples(samples_dir, root)
    if not samples:
        if samples_dir is not None:
            print(f"\nNo sample images found in: {samples_dir}")
            print("To add samples, place microscopy images in the target directory.")
        else:
            print("\nNo sample images found in default dataset directories:")
            for candidate in default_sample_dirs(root):
                print(f"  - {candidate}")
        if args.dry_run:
            print("\n[DRY-RUN] Validation would pass with no samples")
            return 0
        return 1

    print(f"\nUsing samples from: {selected_dir}")
    print(f"Found {len(samples)} sample image(s)")

    # Run validation
    config = get_default_config()
    passed = 0
    failed = 0

    try:
        with ExecutionService(config) as svc:
            for image_path in samples:
                if validate_image(svc, image_path, dry_run=args.dry_run):
                    passed += 1
                else:
                    failed += 1
    except Exception as e:
        print(f"\nConfiguration error: {e}")
        if args.dry_run:
            print("[DRY-RUN] Validation would have run but config failed")
            return 0
        return 1

    # Report results
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    if failed > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
