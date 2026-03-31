from __future__ import annotations

import json
import sys
import types
from pathlib import Path

import pytest

from tools.microsam.bioimage_mcp_microsam import install_models as install_models_mod


def test_install_models_tolerates_optional_download_failures(monkeypatch, capsys, tmp_path):
    cache_dir = tmp_path / "models"
    cache_dir.mkdir()

    class FakeRegistry:
        def fetch(self, model_id: str, progressbar: bool = True) -> Path:
            if model_id == "vit_b":
                model_path = cache_dir / model_id
                model_path.write_text("weights")
                return model_path
            raise RuntimeError(f"{model_id} unavailable")

    fake_util = types.ModuleType("micro_sam.util")
    fake_util.get_cache_directory = lambda: cache_dir
    fake_util.models = lambda: FakeRegistry()

    monkeypatch.setitem(sys.modules, "micro_sam", types.ModuleType("micro_sam"))
    monkeypatch.setitem(sys.modules, "micro_sam.util", fake_util)

    with pytest.raises(SystemExit) as excinfo:
        install_models_mod.install_models()

    assert excinfo.value.code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["models"] == {"vit_b": str((cache_dir / "vit_b").absolute())}
    assert payload["optional_failures"] == {
        "vit_b_lm": "vit_b_lm unavailable",
        "vit_b_em_organelles": "vit_b_em_organelles unavailable",
    }
