import datetime
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from tests.smoke.utils.interaction_logger import InteractionLog, InteractionLogger
from tests.smoke.utils.mcp_client import TestMCPClient


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
    minimal_mode: bool = True  # True for CI, False for full suite
    session_start_time: float = field(default_factory=time.time)


def _env_available(env_name: str) -> bool:
    """Check if a conda environment is available and functional."""
    try:
        # Use conda run -n env_name python -c "print('ok')" to verify
        result = subprocess.run(
            ["conda", "run", "-n", env_name, "python", "-c", "print('ok')"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0
    except Exception:
        return False


def pytest_addoption(parser):
    """Add smoke test specific options."""
    parser.addoption(
        "--smoke-record",
        action="store_true",
        default=False,
        help="Enable recording mode for smoke tests",
    )
    parser.addoption(
        "--smoke-full",
        action="store_true",
        default=False,
        help="Run full smoke test suite instead of minimal",
    )


@pytest.fixture(scope="session")
def smoke_record(request):
    """Check if recording mode is enabled."""
    return request.config.getoption("--smoke-record")


@pytest.fixture(scope="session")
def smoke_config(request):
    """Global smoke test configuration fixture."""
    config = SmokeConfig()
    if request.config.getoption("--smoke-full", default=False):
        config.minimal_mode = False
    # Store on session for hook access
    request.session._smoke_config = config
    return config


@pytest.fixture(scope="session")
def log_dir(smoke_config, smoke_record):
    """Create log directory if recording is enabled."""
    if smoke_record:
        smoke_config.log_dir.mkdir(parents=True, exist_ok=True)
    return smoke_config.log_dir


@pytest.fixture
def interaction_logger(request, log_dir, smoke_record, live_server):
    """Per-test interaction logger that saves on completion."""
    logger = InteractionLogger()
    yield logger

    if smoke_record:
        test_name = request.node.name
        timestamp = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d_%H%M%S")

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
            status="passed"
            if not getattr(request.node, "rep_call", None) or request.node.rep_call.passed
            else "failed",
            interactions=logger.interactions,
            server_stderr=server_stderr,
        )

        # Error summary population on failure (T023)
        if not (getattr(request.node, "rep_call", None) and request.node.rep_call.passed):
            log.error_summary = (
                str(request.node.rep_call.longrepr)
                if getattr(request.node, "rep_call", None)
                else "Unknown error"
            )

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
    if config and config.minimal_mode:
        elapsed = time.time() - config.session_start_time
        if elapsed > config.minimal_suite_budget_s:
            pytest.exit(
                f"Minimal suite budget exceeded: {elapsed:.1f}s > {config.minimal_suite_budget_s}s"
            )


@pytest.fixture(autouse=True)
def check_required_env(request):
    """Skip test if required environment is not available."""
    marker = request.node.get_closest_marker("requires_env")
    if marker:
        env_name = marker.args[0]
        if not _env_available(env_name):
            pytest.skip(f"Required environment not available: {env_name}")


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
    if smoke_config.minimal_mode:
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
