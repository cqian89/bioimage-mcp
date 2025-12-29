"""Unit tests for validate_pipeline sample selection."""

from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_validate_pipeline_module() -> object:
    module_path = Path(__file__).resolve().parents[2] / "scripts" / "validate_pipeline.py"
    spec = importlib.util.spec_from_file_location("validate_pipeline", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load validate_pipeline module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_collect_samples_fallback_uses_existing_dataset(tmp_path: Path) -> None:
    validate_pipeline = _load_validate_pipeline_module()
    root = tmp_path
    sample_dir = root / "datasets" / "synthetic" / "nested"
    sample_dir.mkdir(parents=True)
    sample_file = sample_dir / "sample.tif"
    sample_file.write_bytes(b"sample")

    selected_dir, samples = validate_pipeline.collect_samples(None, root)

    assert selected_dir == root / "datasets" / "synthetic"
    assert samples == [sample_file]


def test_collect_samples_explicit_dir_no_images(tmp_path: Path) -> None:
    validate_pipeline = _load_validate_pipeline_module()
    root = tmp_path
    explicit_dir = root / "custom_samples"
    explicit_dir.mkdir()

    selected_dir, samples = validate_pipeline.collect_samples(explicit_dir, root)

    assert selected_dir is None
    assert samples == []
