from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add tools/base to sys.path so bioimage_mcp_base is importable
repo_root = Path(__file__).parent.parent
tools_base = repo_root / "tools" / "base"
if tools_base.exists() and str(tools_base) not in sys.path:
    sys.path.insert(0, str(tools_base))

from bioimage_mcp_base import utils

DEFAULT_PATH = "datasets/FLUTE_FLIM_data_tif/hMSC control.tif"


def main() -> int:
    parser = argparse.ArgumentParser(description="Check bioimage-mcp base TIFF fallback behavior.")
    parser.add_argument("path", nargs="?", default=DEFAULT_PATH, help="Path to a TIFF file")
    parser.add_argument(
        "--format-hint",
        default=None,
        help="Optional format hint (e.g., OME-TIFF)",
    )
    parser.add_argument(
        "--native",
        action="store_true",
        help="Load using native dimensions (reader.data)",
    )
    args = parser.parse_args()

    path = Path(args.path)
    print(f"Path: {path}")

    try:
        data, warnings, source = utils._load_image_internal(
            path, format_hint=args.format_hint, native=args.native
        )
    except Exception as exc:
        print(f"Load failed: {exc}")
        return 1

    print(f"Source: {source}")
    print(f"Warnings: {warnings}")
    print(f"Shape: {data.shape}")
    print(f"Dtype: {data.dtype}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
