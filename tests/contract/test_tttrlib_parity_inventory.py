"""Contract tests for tttrlib runtime parity inventory coverage."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.smoke_extended

TTTRLIB_COVERAGE_PATH = (
    Path(__file__).parents[2] / "tools" / "tttrlib" / "schema" / "tttrlib_coverage.json"
)
TTTRLIB_SMOKE_PATH = Path(__file__).parents[1] / "smoke" / "test_tttrlib_live.py"

TARGET_CLASSES = ("TTTR", "CLSMImage", "Correlator")
VALID_STATUSES = {"supported", "supported_subset", "deferred", "denied"}


def _load_coverage() -> dict[str, dict[str, str]]:
    with open(TTTRLIB_COVERAGE_PATH) as f:
        raw = json.load(f)
    return raw["coverage"]


def _runtime_callable_ids() -> set[str]:
    script = """
import json
import tttrlib

classes = ['TTTR', 'CLSMImage', 'Correlator']
ids = []
for class_name in classes:
    class_obj = getattr(tttrlib, class_name)
    ids.append(f'tttrlib.{class_name}')
    for method_name in dir(class_obj):
        if method_name.startswith('_'):
            continue
        if callable(getattr(class_obj, method_name)):
            ids.append(f'tttrlib.{class_name}.{method_name}')
print(json.dumps(sorted(set(ids))))
"""

    try:
        result = subprocess.run(
            ["conda", "run", "-n", "bioimage-mcp-tttrlib", "python", "-c", script],
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        pytest.skip(f"tttrlib runtime enumeration unavailable: {exc}")

    return set(json.loads(result.stdout.strip()))


def test_parity_inventory_file_exists() -> None:
    assert TTTRLIB_COVERAGE_PATH.exists(), (
        f"tttrlib coverage inventory not found at {TTTRLIB_COVERAGE_PATH}"
    )


def test_phase25_representative_methods_have_explicit_smoke_coverage() -> None:
    coverage = _load_coverage()
    smoke_content = TTTRLIB_SMOKE_PATH.read_text(encoding="utf-8")

    representative_ids = (
        "tttrlib.Correlator.get_curve",
        "tttrlib.Correlator.get_x_axis",
        "tttrlib.CLSMImage.get_image_info",
        "tttrlib.CLSMImage.get_settings",
    )

    missing_coverage = [method_id for method_id in representative_ids if method_id not in coverage]
    assert not missing_coverage, f"Missing coverage entries: {missing_coverage}"

    missing_smoke = [
        method_id for method_id in representative_ids if method_id not in smoke_content
    ]
    assert not missing_smoke, f"Representative methods missing smoke scenarios: {missing_smoke}"


@pytest.mark.requires_env("bioimage-mcp-tttrlib")
def test_runtime_methods_all_have_coverage_classification() -> None:
    runtime_ids = _runtime_callable_ids()
    coverage = _load_coverage()
    missing = sorted(runtime_ids.difference(coverage.keys()))

    assert not missing, (
        "Runtime callables are missing parity coverage entries: "
        + ", ".join(missing[:20])
        + (" ..." if len(missing) > 20 else "")
    )


@pytest.mark.requires_env("bioimage-mcp-tttrlib")
def test_coverage_status_values_and_required_fields_are_valid() -> None:
    coverage = _load_coverage()

    for fn_id, record in coverage.items():
        assert record.get("status") in VALID_STATUSES, (
            f"{fn_id} has invalid status {record.get('status')}"
        )
        assert isinstance(record.get("owner"), str) and record["owner"].strip(), (
            f"{fn_id} must define non-empty owner"
        )
        assert isinstance(record.get("rationale"), str) and record["rationale"].strip(), (
            f"{fn_id} must define non-empty rationale"
        )
        assert (
            isinstance(record.get("revisit_trigger"), str) and record["revisit_trigger"].strip()
        ), f"{fn_id} must define non-empty revisit_trigger"
