from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"

CORE_LFS_PATHS = [
    "datasets/sample_czi/Plate1-Blue-A-02-Scene-1-P2-E1-01.czi",
    "datasets/FLUTE_FLIM_data_tif/Embryo.tif",
    "datasets/FLUTE_FLIM_data_tif/Fluorescein_Embryo.tif",
]
PR_SMOKE_LFS_PATHS = [
    "datasets/synthetic/test.tif",
    "datasets/FLUTE_FLIM_data_tif/hMSC control.tif",
    "datasets/trackpy-examples/bulk_water/frame000_green.ome.tiff",
]
EXTENDED_LFS_PATHS = [
    "datasets/synthetic/test.tif",
    "datasets/FLUTE_FLIM_data_tif/hMSC control.tif",
    "datasets/trackpy-examples/bulk_water/frame000_green.ome.tiff",
    "datasets/sample_data/measurements.csv",
    "datasets/tttr-data/bh/bh_spc132.spc",
    "datasets/tttr-data/imaging/leica/sp5/LSM_1.ptu",
    "datasets/tttr-data/hdf/1a_1b_Mix.hdf5",
]


def _load_workflow(name: str) -> dict:
    path = WORKFLOWS_DIR / name
    assert path.exists(), f"Missing workflow file: {path}"
    data = yaml.safe_load(path.read_text())
    assert isinstance(data, dict), f"Workflow file must parse as a mapping: {path}"
    return data


def _steps_by_name(job: dict) -> dict[str, dict]:
    steps = job.get("steps", [])
    assert isinstance(steps, list)
    result: dict[str, dict] = {}
    for step in steps:
        name = step.get("name")
        if isinstance(name, str):
            result[name] = step
    return result


def _bundle_multiline(paths: list[str]) -> str:
    return "\n".join(paths)


def _define_bundle_run(paths: list[str]) -> str:
    lines = ['echo "LFS_INCLUDE<<EOF" >> "$GITHUB_ENV"']
    lines.extend(f'echo "{path}" >> "$GITHUB_ENV"' for path in paths)
    lines.append('echo "EOF" >> "$GITHUB_ENV"')
    return "\n".join(lines)


def _cache_key_expr(bundle_name: str, paths: list[str]) -> str:
    quoted = "', '".join(paths + [".gitattributes"])
    return "${{ runner.os }}-" + bundle_name + "-${{ hashFiles('" + quoted + "') }}"


def _restore_keys(bundle_name: str) -> list[str]:
    prefix = "${{ runner.os }}-" + bundle_name + "-"
    return [prefix, "${{ runner.os }}-"]


def test_pr_smoke_bundle_covers_curated_dataset_usage() -> None:
    sample_image_source = (REPO_ROOT / "tests" / "smoke" / "conftest.py").read_text(encoding="utf-8")
    scipy_helpers = (
        REPO_ROOT / "tests" / "smoke" / "test_smoke_scipy_submodules.py"
    ).read_text(encoding="utf-8")
    trackpy_equivalence = (
        REPO_ROOT / "tests" / "smoke" / "test_equivalence_trackpy.py"
    ).read_text(encoding="utf-8")
    cellpose_pipeline = (
        REPO_ROOT / "tests" / "smoke" / "test_cellpose_pipeline_live.py"
    ).read_text(encoding="utf-8")

    assert 'path = Path("datasets/FLUTE_FLIM_data_tif/hMSC control.tif")' in sample_image_source
    assert '"params": {"path": "datasets/synthetic/test.tif"}' in scipy_helpers
    assert '"trackpy-examples" / "bulk_water" / "frame000_green.ome.tiff"' in trackpy_equivalence
    assert 'SYNTHETIC_IMAGE = Path("datasets/synthetic/test.tif")' in cellpose_pipeline


def test_smoke_extended_bundle_covers_curated_dataset_usage() -> None:
    pandas_equivalence = (
        REPO_ROOT / "tests" / "smoke" / "test_equivalence_pandas.py"
    ).read_text(encoding="utf-8")

    assert 'path = Path("datasets/sample_data/measurements.csv")' in pandas_equivalence
    assert "datasets/sample_data/measurements.csv" in EXTENDED_LFS_PATHS


def test_ci_pr_workflow_matches_expected_shape() -> None:
    workflow = _load_workflow("ci-pr.yml")

    assert workflow["name"] == "CI PR"
    assert workflow["on"] == {"pull_request": {}, "push": {"branches": ["main"]}}
    assert workflow["concurrency"] == {
        "group": "${{ github.workflow }}-${{ github.ref }}",
        "cancel-in-progress": True,
    }

    jobs = workflow["jobs"]
    assert set(jobs) == {"core-tests", "smoke-pr"}

    core_tests = jobs["core-tests"]
    core_steps = _steps_by_name(core_tests)
    assert core_steps["Checkout repository"]["with"]["lfs"] is False
    assert core_steps["Define LFS bundle"]["run"] == _define_bundle_run(CORE_LFS_PATHS)
    core_cache = core_steps["Restore LFS bundle cache"]
    assert core_cache["uses"] == "actions/cache@v4"
    assert core_cache["with"]["path"] == _bundle_multiline(CORE_LFS_PATHS)
    assert core_cache["with"]["key"] == _cache_key_expr("lfs-core", CORE_LFS_PATHS)
    assert core_cache["with"]["restore-keys"] == _bundle_multiline(_restore_keys("lfs-core"))
    assert core_steps["Fetch LFS datasets on cache miss"]["if"] == (
        "steps.lfs-cache.outputs.cache-hit != 'true'"
    )
    assert core_steps["Fetch LFS datasets on cache miss"]["run"] == (
        'git lfs pull --include="${LFS_INCLUDE//$\'\\n\'/,}" --exclude=""'
    )
    assert core_steps["Install core dev dependencies"]["run"] == 'python -m pip install -e ".[dev]"'
    assert core_steps["Run unit tests"]["run"] == "pytest tests/unit -q"
    assert core_steps["Run contract tests"]["run"] == "pytest tests/contract -q"

    smoke_pr = jobs["smoke-pr"]
    smoke_steps = _steps_by_name(smoke_pr)
    assert smoke_steps["Checkout repository"]["with"]["lfs"] is False
    assert smoke_steps["Define LFS bundle"]["run"] == _define_bundle_run(PR_SMOKE_LFS_PATHS)
    smoke_cache = smoke_steps["Restore LFS bundle cache"]
    assert smoke_cache["uses"] == "actions/cache@v4"
    assert smoke_cache["with"]["path"] == _bundle_multiline(PR_SMOKE_LFS_PATHS)
    assert smoke_cache["with"]["key"] == _cache_key_expr("lfs-pr-smoke", PR_SMOKE_LFS_PATHS)
    assert smoke_cache["with"]["restore-keys"] == _bundle_multiline(
        _restore_keys("lfs-pr-smoke")
    )
    assert smoke_steps["Fetch LFS datasets on cache miss"]["if"] == (
        "steps.lfs-cache.outputs.cache-hit != 'true'"
    )
    assert smoke_steps["Fetch LFS datasets on cache miss"]["run"] == (
        'git lfs pull --include="${LFS_INCLUDE//$\'\\n\'/,}" --exclude=""'
    )
    assert (
        smoke_steps["Install core dev dependencies"]["run"] == 'python -m pip install -e ".[dev]"'
    )
    assert smoke_steps["Write local CI config"]["run"] == "bioimage-mcp configure"
    assert smoke_steps["Prepare local CI config"]["run"] == "python scripts/ci/prepare_ci_config.py"
    assert smoke_steps["Install PR smoke environments"]["run"] == (
        "bioimage-mcp install --profile cpu\nbioimage-mcp install trackpy"
    )
    assert smoke_steps["Capture doctor output"]["run"] == (
        "mkdir -p .tmp/ci\nbioimage-mcp doctor --json > .tmp/ci/doctor-pr.json || true"
    )
    assert (
        smoke_steps["Run PR smoke tests"]["run"]
        == "pytest tests/smoke --smoke-pr -q --smoke-record"
    )

    upload = smoke_steps["Upload smoke diagnostics"]
    assert upload["if"] == "failure()"
    assert upload["uses"] == "actions/upload-artifact@v4"


def test_smoke_extended_workflow_matches_expected_shape() -> None:
    workflow = _load_workflow("smoke-extended.yml")

    assert workflow["name"] == "Smoke Extended"
    assert "workflow_dispatch" in workflow["on"]
    assert "schedule" in workflow["on"]
    assert workflow["concurrency"] == {
        "group": "${{ github.workflow }}-${{ github.ref || github.run_id }}",
        "cancel-in-progress": True,
    }

    jobs = workflow["jobs"]
    assert set(jobs) == {"smoke-extended"}

    smoke_extended = jobs["smoke-extended"]
    steps = _steps_by_name(smoke_extended)

    assert steps["Checkout repository"]["with"]["lfs"] is False
    assert steps["Define LFS bundle"]["run"] == _define_bundle_run(EXTENDED_LFS_PATHS)
    extended_cache = steps["Restore LFS bundle cache"]
    assert extended_cache["uses"] == "actions/cache@v4"
    assert extended_cache["with"]["path"] == _bundle_multiline(EXTENDED_LFS_PATHS)
    assert extended_cache["with"]["key"] == _cache_key_expr("lfs-extended", EXTENDED_LFS_PATHS)
    assert extended_cache["with"]["restore-keys"] == _bundle_multiline(
        _restore_keys("lfs-extended")
    )
    assert steps["Fetch LFS datasets on cache miss"]["if"] == (
        "steps.lfs-cache.outputs.cache-hit != 'true'"
    )
    assert steps["Fetch LFS datasets on cache miss"]["run"] == (
        'git lfs pull --include="${LFS_INCLUDE//$\'\\n\'/,}" --exclude=""'
    )
    assert steps["Write local CI config"]["run"] == "bioimage-mcp configure"
    assert steps["Prepare local CI config"]["run"] == "python scripts/ci/prepare_ci_config.py"
    assert steps["Install extended smoke environments"]["run"] == (
        "bioimage-mcp install --profile cpu\nbioimage-mcp install trackpy stardist tttrlib microsam"
    )
    assert steps["Capture doctor output"]["run"] == (
        "mkdir -p .tmp/ci\nbioimage-mcp doctor --json > .tmp/ci/doctor-extended.json || true"
    )
    assert steps["Run extended smoke tests"]["run"] == (
        "pytest tests/smoke --smoke-extended -q --smoke-record"
    )

    upload = steps["Upload smoke diagnostics"]
    assert upload["if"] == "always()"
    assert upload["uses"] == "actions/upload-artifact@v4"
