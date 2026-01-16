"""Contract test: artifact metadata schema accepts custom single-char axis names.

Per spec 026-zarr-artifact, the schema must allow single-character custom axis names 
like 'B' (microtime bins) and 'H' (harmonics) in the dims array.
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_schema() -> dict:
    schema_path = (
        _repo_root()
        / "specs"
        / "014-native-artifact-types"
        / "contracts"
        / "artifact-metadata-schema.json"
    )
    if not schema_path.exists():
        pytest.skip("Schema file not found")
    with open(schema_path) as f:
        return json.load(f)


class TestArtifactMetadataSchemaCustomDims:
    """Tests for custom axis name support in artifact metadata schema."""

    def test_schema_accepts_custom_b_axis(self) -> None:
        """Schema must accept dims=['Y','X','B'] for FLIM decay data."""
        schema = _load_schema()

        # Minimal valid artifact with custom B axis for microtime bins
        artifact = {
            "ref_id": "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4",
            "type": "BioImageRef",
            "uri": "file:///path/to/decay.ome.zarr",
            "format": "OME-Zarr",
            "storage_type": "zarr-temp",
            "mime_type": "application/zarr+ome",
            "size_bytes": 1048576,
            "created_at": "2026-01-16T12:00:00Z",
            "metadata": {
                "shape": [32, 32, 64],
                "ndim": 3,
                "dims": ["Y", "X", "B"],  # Custom B axis for microtime bins
                "dtype": "float32",
                "axis_roles": {"B": "microtime_histogram"},
            },
        }

        # This should NOT raise - B must be accepted
        jsonschema.validate(instance=artifact, schema=schema)

    def test_schema_accepts_custom_h_axis(self) -> None:
        """Schema must accept dims=['H','C','Y','X'] for multi-harmonic phasor data."""
        schema = _load_schema()

        artifact = {
            "ref_id": "b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5",
            "type": "BioImageRef",
            "uri": "file:///path/to/phasor.ome.zarr",
            "format": "OME-Zarr",
            "storage_type": "zarr-temp",
            "mime_type": "application/zarr+ome",
            "size_bytes": 524288,
            "created_at": "2026-01-16T12:01:00Z",
            "metadata": {
                "shape": [3, 2, 32, 32],
                "ndim": 4,
                "dims": ["H", "C", "Y", "X"],  # Custom H axis for harmonics
                "dtype": "float32",
                "axis_roles": {"H": "harmonic"},
                "channel_names": ["G", "S"],
            },
        }

        # This should NOT raise - H must be accepted
        jsonschema.validate(instance=artifact, schema=schema)

    def test_schema_still_accepts_standard_tczyx(self) -> None:
        """Schema must still accept standard TCZYX dimensions."""
        schema = _load_schema()

        artifact = {
            "ref_id": "c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6",
            "type": "BioImageRef",
            "uri": "file:///path/to/image.ome.tiff",
            "format": "OME-TIFF",
            "storage_type": "file",
            "mime_type": "image/tiff",
            "size_bytes": 2097152,
            "created_at": "2026-01-16T12:02:00Z",
            "metadata": {
                "shape": [1, 3, 10, 512, 512],
                "ndim": 5,
                "dims": ["T", "C", "Z", "Y", "X"],
                "dtype": "uint16",
            },
        }

        jsonschema.validate(instance=artifact, schema=schema)
