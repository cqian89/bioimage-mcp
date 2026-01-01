from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from bioimage_mcp.registry.loader import load_manifests

CONTRACT_PATH = (
    Path(__file__).resolve().parents[2]
    / "specs/007-workflow-test-harness/contracts/axis-tools-schema.yaml"
)

AXIS_TOOL_IDS = {
    "base.xarray.rename",
    "base.xarray.squeeze",
    "base.xarray.expand_dims",
    "base.xarray.transpose",
}

AXIS_TOOL_SCHEMA_KEYS = {
    "base.xarray.rename": "rename",
    "base.xarray.squeeze": "squeeze",
    "base.xarray.expand_dims": "expand_dims",
    "base.xarray.transpose": "transpose",
}


def _load_contract() -> dict[str, Any]:
    return yaml.safe_load(CONTRACT_PATH.read_text())


def _load_base_manifest():
    tools_root = Path(__file__).resolve().parents[2] / "tools"
    manifests, _ = load_manifests([tools_root])
    return next(m for m in manifests if m.tool_id == "tools.base")


def _get_function(manifest, fn_id: str):
    return next(fn for fn in manifest.functions if fn.fn_id == fn_id)


def _expected_params_schema(
    fn_params_schema: dict[str, Any], contract: dict[str, Any], schema_key: str
) -> dict[str, Any]:
    schema = dict(contract["schemas"][schema_key])
    contract_defs = contract.get("$defs", {})
    fn_defs = fn_params_schema.get("$defs", {})

    # Only include defs that are in the function's schema
    needed_defs = {k: v for k, v in contract_defs.items() if k in fn_defs}
    if needed_defs:
        schema = {**schema, "$defs": needed_defs}
    return schema


def _assert_port_matches_contract(port, contract_port: dict[str, Any]) -> None:
    assert port.name == contract_port["name"]
    assert port.artifact_type == contract_port["artifact_type"]
    if "format" in contract_port:
        assert port.format == contract_port["format"]
    if "required" in contract_port:
        assert port.required is contract_port["required"]


def test_axis_tools_registered_in_manifest() -> None:
    base_manifest = _load_base_manifest()
    fn_ids = {fn.fn_id for fn in base_manifest.functions}

    missing = AXIS_TOOL_IDS - fn_ids
    assert not missing, f"Missing axis tools: {sorted(missing)}"

    contract = _load_contract()
    error_codes = contract.get("error_codes", {})
    assert error_codes, "Contract must define axis tool error codes"
    for code, spec in error_codes.items():
        assert code.isupper(), f"Error code {code} must be uppercase"
        assert "message_template" in spec, f"Error code {code} missing message_template"
        assert "http_status" in spec, f"Error code {code} missing http_status"
        assert isinstance(spec["message_template"], str)
        assert spec["http_status"] == 400


def test_rename_schema_matches_contract() -> None:
    contract = _load_contract()
    base_manifest = _load_base_manifest()

    fn = _get_function(base_manifest, "base.xarray.rename")
    expected_schema = _expected_params_schema(fn.params_schema, contract, "rename")

    assert fn.params_schema == expected_schema


def test_squeeze_schema_matches_contract() -> None:
    contract = _load_contract()
    base_manifest = _load_base_manifest()

    fn = _get_function(base_manifest, "base.xarray.squeeze")
    expected_schema = _expected_params_schema(fn.params_schema, contract, "squeeze")

    assert fn.params_schema == expected_schema


def test_expand_dims_schema_matches_contract() -> None:
    contract = _load_contract()
    base_manifest = _load_base_manifest()

    fn = _get_function(base_manifest, "base.xarray.expand_dims")
    expected_schema = _expected_params_schema(fn.params_schema, contract, "expand_dims")

    assert fn.params_schema == expected_schema


def test_transpose_schema_matches_contract() -> None:
    contract = _load_contract()
    base_manifest = _load_base_manifest()

    fn = _get_function(base_manifest, "base.xarray.transpose")
    expected_schema = _expected_params_schema(fn.params_schema, contract, "transpose")

    assert fn.params_schema == expected_schema


def test_axis_tools_common_io_contract() -> None:
    contract = _load_contract()
    base_manifest = _load_base_manifest()
    expected_input = contract["io_contracts"]["common_input"][0]
    expected_output = contract["io_contracts"]["common_output"][0]

    for fn_id in AXIS_TOOL_IDS:
        fn = _get_function(base_manifest, fn_id)
        assert len(fn.inputs) == 1, f"{fn_id} should have exactly one input"
        assert len(fn.outputs) == 1, f"{fn_id} should have exactly one output"
        _assert_port_matches_contract(fn.inputs[0], expected_input)
        _assert_port_matches_contract(fn.outputs[0], expected_output)
