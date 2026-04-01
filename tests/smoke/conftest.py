import datetime
import shutil
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

import pytest

from bioimage_mcp.config.loader import load_config
from tests.smoke.utils.interaction_logger import InteractionLog, InteractionLogger
from tests.smoke.utils.mcp_client import TestMCPClient


class SmokeMode(Enum):
    """Smoke suite execution modes."""

    MINIMAL = "minimal"
    PR = "pr"
    EXTENDED = "extended"


@pytest.fixture(scope="session")
def anyio_backend():
    """Use AnyIO's asyncio backend for smoke tests."""

    return "asyncio"


@dataclass
class SmokeConfig:
    """Global configuration for smoke test suite."""

    startup_timeout_s: float = 30.0  # Max seconds for server startup
    minimal_suite_budget_s: float = 120.0  # Max seconds for minimal suite
    scenario_timeout_s: float = 300.0  # Max seconds per scenario
    log_dir: Path = field(default_factory=lambda: Path(".bioimage-mcp/smoke_logs"))
    mode: SmokeMode = SmokeMode.MINIMAL
    session_start_time: float | None = None


def _is_smoke_item(item: pytest.Item) -> bool:
    """Return True if the test item is part of the smoke suite."""
    marker_names = {marker.name for marker in item.iter_markers()}
    if {"smoke_minimal", "smoke_pr", "smoke_extended", "smoke_full"}.intersection(marker_names):
        return True

    item_path = getattr(item, "path", None)
    if item_path is None:
        item_path = Path(str(item.fspath))
    return "tests" in item_path.parts and "smoke" in item_path.parts


def _resolve_log_outcome(
    rep_setup: object | None, rep_call: object | None, rep_teardown: object | None
) -> tuple[str, str | None, str | None]:
    """Map pytest reports to interaction-log status and optional summaries."""
    if rep_teardown is not None and getattr(rep_teardown, "failed", False):
        return "failed", str(rep_teardown.longrepr), None

    if rep_call is not None:
        if getattr(rep_call, "passed", False):
            return "passed", None, None
        if getattr(rep_call, "skipped", False):
            return "skipped", None, str(rep_call.longrepr)
        if getattr(rep_call, "failed", False):
            return "failed", str(rep_call.longrepr), None

    if rep_setup is not None:
        if getattr(rep_setup, "skipped", False):
            return "skipped", None, str(rep_setup.longrepr)
        if getattr(rep_setup, "failed", False):
            return "failed", str(rep_setup.longrepr), None

    return "passed", None, None


def pytest_addoption(parser):
    """Add smoke test specific options."""
    parser.addoption(
        "--smoke-record",
        action="store_true",
        default=False,
        help="Enable recording mode for smoke tests",
    )
    parser.addoption(
        "--smoke-pr",
        action="store_true",
        default=False,
        help="Run PR-gating smoke tests (+ minimal items)",
    )
    parser.addoption(
        "--smoke-extended",
        action="store_true",
        default=False,
        help="Run extended smoke tests (+ PR + minimal items)",
    )
    parser.addoption(
        "--smoke-full",
        action="store_true",
        default=False,
        help="Alias for --smoke-extended (deprecated)",
    )


@pytest.fixture(scope="session")
def smoke_record(request):
    """Check if recording mode is enabled."""
    return request.config.getoption("--smoke-record")


@pytest.fixture(scope="session")
def smoke_config(request):
    """Global smoke test configuration fixture."""
    config = SmokeConfig()
    if request.config.getoption("--smoke-extended", default=False) or request.config.getoption(
        "--smoke-full", default=False
    ):
        config.mode = SmokeMode.EXTENDED
    elif request.config.getoption("--smoke-pr", default=False):
        config.mode = SmokeMode.PR

    # Store on session for hook access
    request.session._smoke_config = config
    return config


@pytest.fixture(scope="session")
def log_dir(smoke_config, smoke_record):
    """Create log directory if recording is enabled."""
    if smoke_record:
        smoke_config.log_dir.mkdir(parents=True, exist_ok=True)
    return smoke_config.log_dir


@pytest.fixture(scope="session")
def smoke_tmp_dir() -> Path:
    """Provide a shared smoke temp root under artifact_store_root/work."""
    config = load_config()
    tmp_dir = config.artifact_store_root / "work" / "smoke_tmp" / uuid.uuid4().hex
    tmp_dir.mkdir(parents=True, exist_ok=True)
    yield tmp_dir
    shutil.rmtree(tmp_dir, ignore_errors=True)


@pytest.fixture(autouse=True)
def interaction_logger(request, log_dir, smoke_record):
    """Per-test interaction logger that saves on completion."""
    logger = InteractionLogger()
    live_server = None
    if smoke_record:
        live_server = request.getfixturevalue("live_server")
        live_server._logger = logger

    yield logger

    if smoke_record:
        live_server._logger = None
        test_name = request.node.name
        timestamp = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d_%H%M%S")
        status, error_summary, skip_reason = _resolve_log_outcome(
            getattr(request.node, "rep_setup", None),
            getattr(request.node, "rep_call", None),
            getattr(request.node, "rep_teardown", None),
        )

        # Get server stderr from live_server
        server_stderr = None
        if hasattr(live_server, "get_stderr"):
            stderr_content = live_server.get_stderr()
            if stderr_content:
                server_stderr = stderr_content

        log = InteractionLog(
            test_run_id=f"smoke_{timestamp}",
            scenario=test_name,
            started_at=datetime.datetime.now(datetime.UTC).isoformat(),
            status=status,
            interactions=logger.interactions,
            server_stderr=server_stderr,
        )

        if error_summary is not None:
            log.error_summary = error_summary
        if skip_reason is not None:
            log.skip_reason = skip_reason

        log_path = log_dir / f"{test_name}_{timestamp}.json"
        logger.save_log(log, log_path)


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Store test result for use in fixtures and enforce scenario timeout."""
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)

    # Enforce scenario timeout (T015)
    if rep.when == "call":
        config = getattr(item.session, "_smoke_config", None)
        if config and rep.duration > config.scenario_timeout_s:
            rep.outcome = "failed"
            timeout_msg = (
                f"Scenario timeout exceeded: {rep.duration:.2f}s > {config.scenario_timeout_s}s"
            )
            if rep.longrepr:
                rep.longrepr = f"{rep.longrepr}\n{timeout_msg}"
            else:
                rep.longrepr = timeout_msg


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item):
    """Enforce suite-level time budget (T012)."""
    config = getattr(item.session, "_smoke_config", None)
    if config and config.mode == SmokeMode.MINIMAL and _is_smoke_item(item):
        if config.session_start_time is None:
            config.session_start_time = time.time()
        elapsed = time.time() - config.session_start_time
        if elapsed > config.minimal_suite_budget_s:
            pytest.exit(
                f"Minimal suite budget exceeded: {elapsed:.1f}s > {config.minimal_suite_budget_s}s"
            )


@pytest.fixture(autouse=True)
def enforce_smoke_tiers(request, smoke_config):
    """Skip smoke tests based on selected tier."""
    if not _is_smoke_item(request.node):
        return

    # EXTENDED mode skips nothing
    if smoke_config.mode == SmokeMode.EXTENDED:
        return

    # PR mode skips EXTENDED
    if smoke_config.mode == SmokeMode.PR:
        if request.node.get_closest_marker("smoke_extended") or request.node.get_closest_marker(
            "smoke_full"
        ):
            pytest.skip("Skipping smoke_extended test in PR mode")
        return

    # MINIMAL mode (default) skips PR and EXTENDED
    if smoke_config.mode == SmokeMode.MINIMAL:
        if (
            request.node.get_closest_marker("smoke_pr")
            or request.node.get_closest_marker("smoke_extended")
            or request.node.get_closest_marker("smoke_full")
        ):
            pytest.skip("Skipping PR/Extended smoke test in minimal mode")


@pytest.fixture(scope="session")
async def live_server(smoke_config):
    """Session-scoped fixture: one server for all smoke tests."""
    client = TestMCPClient(call_timeout_s=smoke_config.scenario_timeout_s)
    await client.start_with_timeout(smoke_config.startup_timeout_s)
    yield client
    await client.stop()


@pytest.fixture
def sample_image(request, smoke_config):
    """Provide sample image path based on test mode."""
    if smoke_config.mode == SmokeMode.MINIMAL:
        path = Path("datasets/synthetic/test.tif")
    else:
        path = Path("datasets/FLUTE_FLIM_data_tif/hMSC control.tif")

    if not path.exists():
        pytest.skip(f"Dataset missing: {path}")
    return path


@pytest.fixture
def helper():
    """Provide DataEquivalenceHelper for smoke tests."""
    from tests.smoke.utils.data_equivalence import DataEquivalenceHelper

    return DataEquivalenceHelper()


@pytest.fixture
def native_executor():
    """Provide NativeExecutor for smoke tests."""
    from tests.smoke.utils.native_executor import NativeExecutor

    return NativeExecutor()


@pytest.fixture
def synthetic_image():
    """Small synthetic image (64x64 float32)."""
    import numpy as np

    return np.random.rand(64, 64).astype(np.float32)


@pytest.fixture
def synthetic_labels():
    """Small synthetic labels (64x64 uint16)."""
    import numpy as np

    labels = np.zeros((64, 64), dtype=np.uint16)
    # Add a few "cells"
    labels[10:20, 10:20] = 1
    labels[30:40, 30:40] = 2
    labels[50:60, 50:60] = 3
    return labels


@pytest.fixture
def synthetic_dataframe():
    """Small synthetic pandas DataFrame."""
    import pandas as pd

    return pd.DataFrame(
        {
            "id": [1, 2, 3],
            "area": [100.5, 200.0, 150.2],
            "label": ["cell1", "cell2", "cell3"],
        }
    )


@pytest.fixture
def synthetic_xarray():
    """Small synthetic xarray DataArray."""
    import numpy as np
    import xarray as xr

    data = np.random.rand(4, 64, 64).astype(np.float32)
    return xr.DataArray(
        data,
        dims=("c", "y", "x"),
        coords={"c": ["ch1", "ch2", "ch3", "ch4"]},
        name="test_data",
        attrs={"units": "counts"},
    )
