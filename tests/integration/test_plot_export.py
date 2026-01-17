import os
import shutil
from pathlib import Path
import pytest
from bioimage_mcp_base.ops import io as io_ops


@pytest.mark.integration
def test_export_plotref_to_path(tmp_path):
    """Verify PlotRef can be exported to a user-specified destination."""
    # 1. Create a dummy PNG file to simulate a plot source
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    source_file = source_dir / "plot_123.png"
    source_file.write_bytes(b"dummy_png_content")

    # 2. Create a PlotRef artifact
    plot_ref = {
        "type": "PlotRef",
        "format": "PNG",
        "uri": source_file.as_uri(),
        "path": str(source_file),
        "metadata": {"width_px": 800, "height_px": 600, "dpi": 100, "plot_type": "test_plot"},
    }

    # 3. Define destination
    dest_path = tmp_path / "exported_plot.png"

    # Setup environment for allowed write paths
    os.environ["BIOIMAGE_MCP_FS_ALLOWLIST_WRITE"] = f'["{tmp_path}"]'

    # 4. Call export function (expect it to fail or not support PlotRef yet)
    # We call it via the ops module directly
    result = io_ops.export(
        inputs={"artifact": plot_ref}, params={"path": str(dest_path)}, work_dir=tmp_path
    )

    # 5. Assert file exists at dest_path and content matches
    assert dest_path.exists()
    assert dest_path.read_bytes() == b"dummy_png_content"

    # 6. Verify result artifact
    out_ref = result["outputs"]["output"]
    assert out_ref["type"] == "PlotRef"
    assert out_ref["path"] == str(dest_path)


@pytest.mark.integration
def test_export_plotref_preserves_content(tmp_path):
    """Verify exported file is identical to source."""
    source_file = tmp_path / "src.png"
    content = os.urandom(1024)
    source_file.write_bytes(content)

    plot_ref = {
        "type": "PlotRef",
        "format": "PNG",
        "uri": source_file.as_uri(),
        "path": str(source_file),
        "metadata": {"width_px": 100, "height_px": 100},
    }

    dest_path = tmp_path / "dest.png"
    os.environ["BIOIMAGE_MCP_FS_ALLOWLIST_WRITE"] = f'["{tmp_path}"]'

    io_ops.export(inputs={"artifact": plot_ref}, params={"path": str(dest_path)}, work_dir=tmp_path)

    assert dest_path.read_bytes() == content


@pytest.mark.integration
def test_export_plotref_missing_source_raises(tmp_path):
    """Verify export raises clear error if source file doesn't exist."""
    plot_ref = {
        "type": "PlotRef",
        "format": "PNG",
        "uri": "file:///non/existent/path/plot.png",
        "path": "/non/existent/path/plot.png",
        "metadata": {"width_px": 100, "height_px": 100},
    }

    dest_path = tmp_path / "fail.png"
    os.environ["BIOIMAGE_MCP_FS_ALLOWLIST_WRITE"] = f'["{tmp_path}"]'

    with pytest.raises(Exception) as excinfo:
        io_ops.export(
            inputs={"artifact": plot_ref}, params={"path": str(dest_path)}, work_dir=tmp_path
        )

    # We expect some form of FileNotFoundError or custom error
    assert "not found" in str(excinfo.value).lower()
