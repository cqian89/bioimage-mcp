from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def install_models():
    try:
        # Import inside function to avoid immediate failure if micro_sam is missing
        # during initial stages of environment setup (though this script is run
        # in the target environment).
        from micro_sam.util import models, get_cache_directory

        registry = models()
        cache_dir = get_cache_directory()

        # We ensure vit_b variants for Generalist, LM, and EM
        required_models = {"generalist": "vit_b", "lm": "vit_b_lm", "em": "vit_b_em"}

        results = {}
        for key, model_id in required_models.items():
            # fetch() downloads the model if it's not in the cache
            path = registry.fetch(model_id, progressbar=True)
            results[model_id] = str(Path(path).absolute())

        output = {"ok": True, "cache_dir": str(cache_dir.absolute()), "models": results}
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
