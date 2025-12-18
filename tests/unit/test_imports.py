import subprocess
import sys


def test_imports_smoke() -> None:
    import bioimage_mcp  # noqa: F401


def test_main_module_invocation() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "bioimage_mcp", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "doctor" in result.stdout
    assert "install" in result.stdout
