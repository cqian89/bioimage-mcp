from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path

import bioio
from bioio import BioImage
from bioio.plugins import get_plugins

DEFAULT_PATH = "datasets/FLUTE_FLIM_data_tif/hMSC control.tif"


def _reader_label(img: BioImage) -> str:
    reader = getattr(img, "reader", None)
    if reader is None:
        return "unknown"
    return f"{type(reader).__module__}.{type(reader).__name__}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check whether BioImage auto-falls back to bioio-tifffile for TIFF files."
    )
    parser.add_argument("path", nargs="?", default=DEFAULT_PATH, help="Path to a TIFF file")
    parser.add_argument(
        "--dump-plugins",
        action="store_true",
        help="Print full plugin list before testing",
    )
    args = parser.parse_args()

    path = Path(args.path)
    print(f"Path: {path}")

    if args.dump_plugins:
        from bioio.plugins import dump_plugins

        dump_plugins()

    plugins = get_plugins(use_cache=True)
    tiff_entries = plugins.get(".tif", []) + plugins.get(".tiff", [])
    tiff_plugin_names = [entry.entrypoint.name for entry in tiff_entries]
    print(f"Registered plugins for .tif/.tiff: {tiff_plugin_names or 'none'}")

    report = bioio.plugin_feasibility_report(str(path))
    print("Feasibility report:")
    for name, support in report.items():
        supported = getattr(support, "supported", None)
        error = getattr(support, "error", None)
        print(f"  {name}: supported={supported} error={error}")

    print("\nAttempting BioImage(path) ...")
    try:
        img = BioImage(str(path))
        reader_label = _reader_label(img)
        print(f"BioImage succeeded with reader: {reader_label}")
        auto_fallback = "bioio_tifffile" in reader_label
        print(f"Auto-fallback to bioio-tifffile: {auto_fallback}")
        return 0
    except Exception as exc:
        print(f"BioImage failed: {exc}")

    tiff_available = importlib.util.find_spec("bioio_tifffile") is not None
    if tiff_available:
        from bioio_tifffile.reader import Reader as TiffReader

        try:
            img = BioImage(str(path), reader=TiffReader)
            print(f"Explicit bioio-tifffile reader succeeded: {_reader_label(img)}")
            print("Auto-fallback to bioio-tifffile: False (manual reader required)")
        except Exception as exc:
            print(f"Explicit bioio-tifffile reader failed: {exc}")
    else:
        print("bioio-tifffile not installed; cannot test tifffile fallback.")

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
