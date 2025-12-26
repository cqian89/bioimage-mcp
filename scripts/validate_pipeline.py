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


def find_sample_images(samples_dir: Path) -> list[Path]:
    """Find sample microscopy images in the given directory."""
    extensions = {".tiff", ".tif", ".ome.tiff", ".ome.tif", ".png"}
    images = []

    if not samples_dir.exists():
        print(f"Warning: Samples directory does not exist: {samples_dir}")
        return images

    for path in samples_dir.iterdir():
        if path.is_file() and path.suffix.lower() in extensions:
            images.append(path)

    return sorted(images)


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
                        "fn_id": "cellpose.segment",
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
        type=Path,
        default=Path(__file__).parent.parent / "datasets" / "samples",
        help="Directory containing sample images",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("Pipeline Validation Script")
    print("=" * 60)

    # Find sample images
    samples = find_sample_images(args.samples_dir)
    if not samples:
        print(f"\nNo sample images found in: {args.samples_dir}")
        print("To add samples, place microscopy images in datasets/samples/")
        if args.dry_run:
            print("\n[DRY-RUN] Validation would pass with no samples")
            return 0
        return 1

    print(f"\nFound {len(samples)} sample image(s)")

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
