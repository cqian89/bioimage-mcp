"""Contract tests ensuring tttrlib schema matches manifest.

These tests prevent drift between:
- tools/tttrlib/manifest.yaml (tool surface)
- tools/tttrlib/schema/tttrlib_api.json (curated schema)

If either file changes, update the other to keep them consistent.
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

TTTRLIB_MANIFEST_PATH = Path(__file__).parents[2] / "tools" / "tttrlib" / "manifest.yaml"
TTTRLIB_SCHEMA_PATH = (
    Path(__file__).parents[2] / "tools" / "tttrlib" / "schema" / "tttrlib_api.json"
)


def _load_manifest_raw() -> dict:
    with open(TTTRLIB_MANIFEST_PATH) as f:
        return yaml.safe_load(f)


def _get_manifest_fn(manifest_raw: dict, fn_id: str) -> dict:
    return next(fn for fn in manifest_raw.get("functions", []) if fn.get("fn_id") == fn_id)


def _load_schema_raw() -> dict:
    with open(TTTRLIB_SCHEMA_PATH) as f:
        return json.load(f)


class TestTTTRLibSchemaAlignment:
    def test_tttr_container_type_enum_matches_manifest(self) -> None:
        manifest_raw = _load_manifest_raw()
        schema_raw = _load_schema_raw()

        manifest_fn = _get_manifest_fn(manifest_raw, "tttrlib.TTTR")
        manifest_enum = (
            manifest_fn["params_schema"]["properties"]["container_type"].get("enum") or []
        )

        schema_enum = (
            schema_raw["functions"]["tttrlib.TTTR"]["params"]["container_type"].get("enum") or []
        )

        assert set(schema_enum) == set(manifest_enum)

    def test_clsmimage_params_match_manifest(self) -> None:
        manifest_raw = _load_manifest_raw()
        schema_raw = _load_schema_raw()

        manifest_fn = _get_manifest_fn(manifest_raw, "tttrlib.CLSMImage")
        manifest_props = manifest_fn["params_schema"]["properties"]

        schema_params = schema_raw["functions"]["tttrlib.CLSMImage"]["params"]

        assert set(schema_params.keys()) == set(manifest_props.keys())

    def test_tttr_write_output_key_matches_manifest(self) -> None:
        manifest_raw = _load_manifest_raw()
        schema_raw = _load_schema_raw()

        manifest_fn = _get_manifest_fn(manifest_raw, "tttrlib.TTTR.write")
        manifest_outputs = [o["name"] for o in manifest_fn.get("outputs", [])]

        schema_outputs = list(schema_raw["functions"]["tttrlib.TTTR.write"]["outputs"].keys())

        assert set(schema_outputs) == set(manifest_outputs)
