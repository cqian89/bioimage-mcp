from __future__ import annotations

import json
import sys
from pathlib import Path


def install_models():
    try:
        # Import inside function to avoid immediate failure if micro_sam is missing
        # during initial stages of environment setup (though this script is run
        # in the target environment).
        from micro_sam.util import get_cache_directory, models

        registry = models()
        cache_dir = get_cache_directory()

        required_models = ["vit_b"]
        optional_models = ["vit_b_lm", "vit_b_em_organelles"]

        results = {}
        for model_id in required_models:
            path = registry.fetch(model_id, progressbar=True)
            results[model_id] = str(Path(path).absolute())

        optional_failures = {}
        for model_id in optional_models:
            try:
                path = registry.fetch(model_id, progressbar=True)
                results[model_id] = str(Path(path).absolute())
            except Exception as exc:  # noqa: BLE001
                optional_failures[model_id] = str(exc)

        output = {
            "ok": True,
            "cache_dir": str(cache_dir.absolute()),
            "cache_path": str(cache_dir.absolute()),
            "models": results,
            "optional_failures": optional_failures,
        }
        print(json.dumps(output))
        sys.exit(0)

    except ImportError as e:
        error_output = {
            "ok": False,
            "error": {
                "code": "IMPORT_ERROR",
                "message": f"Required library 'micro_sam' not found: {e}",
            },
        }
        print(json.dumps(error_output))
        sys.exit(1)
    except Exception as e:
        error_output = {"ok": False, "error": {"code": "INSTALL_ERROR", "message": str(e)}}
        print(json.dumps(error_output))
        sys.exit(1)


if __name__ == "__main__":
    install_models()
