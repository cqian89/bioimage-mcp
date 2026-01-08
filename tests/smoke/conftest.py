import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import pytest
import pytest_asyncio

from tests.smoke.utils.mcp_client import TestMCPClient

pytest_plugins = ["pytest_asyncio"]


@dataclass
class SmokeConfig:
    """Global configuration for smoke test suite."""

    startup_timeout_s: float = 30.0  # Max seconds for server startup
    minimal_suite_budget_s: float = 120.0  # Max seconds for minimal suite
    scenario_timeout_s: float = 300.0  # Max seconds per scenario
    log_dir: Path = field(default_factory=lambda: Path(".bioimage-mcp/smoke_logs"))
    minimal_mode: bool = True  # True for CI, False for full suite


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


@pytest.fixture(scope="session")
def smoke_config():
    """Global smoke test configuration fixture."""
    return SmokeConfig()


@pytest.fixture(autouse=True)
def check_required_env(request):
    """Skip test if required environment is not available."""
    marker = request.node.get_closest_marker("requires_env")
    if marker:
        env_name = marker.args[0]
        if not _env_available(env_name):
            pytest.skip(f"Required environment not available: {env_name}")


@pytest_asyncio.fixture(scope="session")
async def live_server(smoke_config):
    """Session-scoped fixture: one server for all smoke tests."""
    client = TestMCPClient()
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
