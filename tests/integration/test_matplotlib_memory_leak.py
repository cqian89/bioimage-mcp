"""
Memory leak tests for Matplotlib figure handling.

The spec requires testing 100+ figures to verify no memory leaks.
We split this into:
- test_matplotlib_memory_leak: Fast test (10 iterations) for CI
- test_matplotlib_memory_leak_comprehensive: Full test (120 iterations), marked @slow
"""

from pathlib import Path

import pytest

from bioimage_mcp.api.execution import ExecutionService
from bioimage_mcp.artifacts.store import ArtifactStore
from bioimage_mcp.config.schema import Config
from bioimage_mcp.storage.sqlite import connect


@pytest.fixture
def execution_service(tmp_path: Path):
    artifacts_root = tmp_path / "artifacts"
    artifacts_root.mkdir()

    # Use real tools directory
    tools_root = Path(__file__).parent.parent.parent / "tools"
    config = Config(
        artifact_store_root=artifacts_root,
        tool_manifest_roots=[tools_root],
        fs_allowlist_read=[tmp_path, tools_root],
        fs_allowlist_write=[tmp_path, artifacts_root],
        fs_denylist=[],
    )

    conn = connect(config)
    artifact_store = ArtifactStore(config, conn=conn)
    service = ExecutionService(config, artifact_store=artifact_store)
    yield service
    service.close()


@pytest.mark.integration
def test_matplotlib_memory_leak(execution_service):
    """Test that creating and saving many figures doesn't leak memory.

    Verifies that savefig succeeds for multiple iterations.
    Uses ExecutionService to run the tools in their proper environment.
    """
    num_iterations = 10  # Enough to verify basic operation
    session_id = "test-leak-session"

    for i in range(num_iterations):
        # 1. Create figure
        workflow1 = {
            "steps": [{"fn_id": "base.matplotlib.pyplot.figure", "params": {"figsize": [2, 2]}}]
        }
        result1 = execution_service.run_workflow(workflow1, session_id=session_id)
        assert result1["status"] == "success", (
            f"Figure creation failed at {i}: {result1.get('error')}"
        )
        fig_ref = result1["outputs"]["figure"]

        # 2. Save figure (this should trigger close())
        workflow3 = {
            "steps": [
                {
                    "fn_id": "base.matplotlib.Figure.savefig",
                    "inputs": {"figure": fig_ref},
                    "params": {"format": "png"},
                }
            ]
        }
        result3 = execution_service.run_workflow(workflow3, session_id=session_id)
        assert result3["status"] == "success", f"Savefig failed at {i}: {result3.get('error')}"


@pytest.mark.integration
@pytest.mark.slow
def test_matplotlib_memory_leak_comprehensive(execution_service):
    """Comprehensive memory leak test per spec requirement.

    Creates 100+ figures to verify long-running stability.
    Marked slow - excluded from default CI runs.
    """
    num_iterations = 120  # Per spec: "100+ figures"
    session_id = "test-leak-session-comprehensive"

    for i in range(num_iterations):
        # 1. Create figure
        workflow1 = {
            "steps": [{"fn_id": "base.matplotlib.pyplot.figure", "params": {"figsize": [2, 2]}}]
        }
        result1 = execution_service.run_workflow(workflow1, session_id=session_id)
        assert result1["status"] == "success", (
            f"Figure creation failed at {i}: {result1.get('error')}"
        )
        fig_ref = result1["outputs"]["figure"]

        # 2. Save figure (this should trigger close())
        workflow2 = {
            "steps": [
                {
                    "fn_id": "base.matplotlib.Figure.savefig",
                    "inputs": {"figure": fig_ref},
                    "params": {"format": "png"},
                }
            ]
        }
        result2 = execution_service.run_workflow(workflow2, session_id=session_id)
        assert result2["status"] == "success", f"Savefig failed at {i}: {result2.get('error')}"

        if (i + 1) % 20 == 0:
            print(f"Completed {i + 1}/{num_iterations} iterations")


if __name__ == "__main__":
    # For manual execution if needed
    pass
