from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"


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
    assert core_steps["Install core dev dependencies"]["run"] == 'python -m pip install -e ".[dev]"'
    assert core_steps["Run unit tests"]["run"] == "pytest tests/unit -q"
    assert core_steps["Run contract tests"]["run"] == "pytest tests/contract -q"

    smoke_pr = jobs["smoke-pr"]
    smoke_steps = _steps_by_name(smoke_pr)
    assert smoke_steps["Fetch LFS datasets"]["run"] == 'git lfs pull --include="datasets/**"'
    assert (
        smoke_steps["Install core dev dependencies"]["run"] == 'python -m pip install -e ".[dev]"'
    )
    assert smoke_steps["Write local CI config"]["run"] == "bioimage-mcp configure"
    assert smoke_steps["Prepare local CI config"]["run"] == "python scripts/ci/prepare_ci_config.py"
    assert smoke_steps["Install PR smoke environments"]["run"] == (
        "bioimage-mcp install --profile cpu\nbioimage-mcp install trackpy"
    )
    assert smoke_steps["Capture doctor output"]["run"] == (
        "mkdir -p .tmp/ci\nbioimage-mcp doctor --json > .tmp/ci/doctor-pr.json"
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

    assert steps["Fetch LFS datasets"]["run"] == 'git lfs pull --include="datasets/**"'
    assert steps["Write local CI config"]["run"] == "bioimage-mcp configure"
    assert steps["Prepare local CI config"]["run"] == "python scripts/ci/prepare_ci_config.py"
    assert steps["Install extended smoke environments"]["run"] == (
        "bioimage-mcp install --profile cpu\nbioimage-mcp install trackpy stardist tttrlib microsam"
    )
    assert steps["Capture doctor output"]["run"] == (
        "mkdir -p .tmp/ci\nbioimage-mcp doctor --json > .tmp/ci/doctor-extended.json"
    )
    assert steps["Run extended smoke tests"]["run"] == (
        "pytest tests/smoke --smoke-extended -q --smoke-record"
    )

    upload = steps["Upload smoke diagnostics"]
    assert upload["if"] == "always()"
    assert upload["uses"] == "actions/upload-artifact@v4"
