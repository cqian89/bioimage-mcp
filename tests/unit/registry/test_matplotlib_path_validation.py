from __future__ import annotations

from pathlib import Path

import pytest

from bioimage_mcp.registry.dynamic.adapters.matplotlib import (
    MatplotlibAdapter,
    _looks_like_path,
)


def test_reject_write_outside_allowlist():
    """R1.3: imsave to /etc/passwd.png rejected."""
    adapter = MatplotlibAdapter()
    fs_allowlist_write = [Path("/tmp/allowed")]

    with pytest.raises(ValueError) as excinfo:
        adapter.execute(
            fn_id="base.matplotlib.pyplot.imsave",
            inputs=[],
            params={"fname": "/etc/passwd.png", "arr": [[0]]},
            fs_allowlist_write=fs_allowlist_write,
        )
    assert "not allowed for write" in str(excinfo.value).lower()


def test_allow_write_inside_allowlist(tmp_path):
    """R1.3: imsave to temp path allowed."""
    adapter = MatplotlibAdapter()
    allowed_dir = tmp_path / "allowed"
    allowed_dir.mkdir()
    fs_allowlist_write = [allowed_dir]

    dest_path = allowed_dir / "output.png"

    # This should pass validation (it might fail later if matplotlib is not fully mocked,
    # but here we care about the ValueError from path validation)
    try:
        adapter.execute(
            fn_id="base.matplotlib.pyplot.imsave",
            inputs=[],
            params={"fname": str(dest_path), "arr": [[0]]},
            fs_allowlist_write=fs_allowlist_write,
        )
    except Exception as e:
        # We don't care if it fails in matplotlib_ops execution,
        # just that it didn't raise ValueError for path validation
        if isinstance(e, ValueError) and "not allowed for write" in str(e).lower():
            pytest.fail(f"Path validation failed for allowed path: {e}")


def test_reject_read_outside_allowlist():
    """R1.3: imread from /etc/secret.png rejected."""
    adapter = MatplotlibAdapter()
    fs_allowlist_read = [Path("/tmp/allowed")]

    with pytest.raises(ValueError) as excinfo:
        adapter.execute(
            fn_id="base.matplotlib.pyplot.imread",
            inputs=[],
            params={"fname": "/etc/secret.png"},
            fs_allowlist_read=fs_allowlist_read,
        )
    assert "not allowed for read" in str(excinfo.value).lower()


def test_allow_read_inside_allowlist(tmp_path):
    """R1.3: imread from allowed path succeeds validation."""
    adapter = MatplotlibAdapter()
    allowed_dir = tmp_path / "allowed"
    allowed_dir.mkdir()
    fs_allowlist_read = [allowed_dir]

    src_path = allowed_dir / "input.png"
    src_path.touch()

    try:
        adapter.execute(
            fn_id="base.matplotlib.pyplot.imread",
            inputs=[],
            params={"fname": str(src_path)},
            fs_allowlist_read=fs_allowlist_read,
        )
    except Exception as e:
        if isinstance(e, ValueError) and "not allowed for read" in str(e).lower():
            pytest.fail(f"Path validation failed for allowed path: {e}")


def test_ignore_non_path_params():
    """R1.3: plot params like label, color don't trigger validation."""
    adapter = MatplotlibAdapter()
    # No allowlists provided, but should not raise for non-path params

    try:
        adapter.execute(
            fn_id="base.matplotlib.Axes.plot",
            inputs=[],
            params={"label": "my plot", "color": "red"},
        )
    except Exception as e:
        if isinstance(e, ValueError) and "not allowed" in str(e).lower():
            pytest.fail(f"Path validation triggered for non-path params: {e}")


def test_obj_uri_not_treated_as_path():
    """R1.3: obj://session/env/id not flagged as path."""
    adapter = MatplotlibAdapter()

    # Should not raise even without allowlist
    try:
        adapter.execute(
            fn_id="base.matplotlib.Axes.imshow", inputs=[], params={"X": "obj://session/env/id"}
        )
    except Exception as e:
        if isinstance(e, ValueError) and "not allowed" in str(e).lower():
            pytest.fail(f"Path validation triggered for obj:// URI: {e}")


def test_slash_in_label_not_path():
    """Strings with internal slashes should not be treated as paths."""
    assert not _looks_like_path("Mg/Ca ratio")
    assert not _looks_like_path("Sensitivity/Specificity")
    assert not _looks_like_path("A/B testing")
