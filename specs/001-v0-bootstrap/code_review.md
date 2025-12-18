# Code Review: v0.0 Bootstrap Implementation

**Review Date:** 2025-12-18  
**Reviewer:** OpenCode  
**Spec Reference:** `specs/001-v0-bootstrap/tasks.md`

## Executive Summary

The v0.0 Bootstrap implementation is **fully compliant** with the specifications. All 69 tasks from `tasks.md` have been completed and verified. The codebase has a solid architecture, comprehensive test coverage, and the CLI commands function as designed. Two bugs were identified and fixed during review.

**Format note**: The v0.0 built-ins include `builtin.convert_to_ome_zarr` and produce OME-Zarr outputs. The project’s current format strategy is to prefer OME-TIFF as the default intermediate; OME-Zarr support is a future goal.

---

## Architecture Compliance

### Package Structure
All expected modules exist under `src/bioimage_mcp/`:
- `api/` - `server.py`, `discovery.py`, `execution.py`, `artifacts.py`, `pagination.py`
- `artifacts/` - `models.py`, `checksums.py`, `store.py`, `metadata.py`, `export.py`
- `bootstrap/` - `doctor.py`, `install.py`, `configure.py`, `serve.py`, `checks.py`, `env_manager.py`
- `config/` - `schema.py`, `loader.py`, `fs_policy.py`
- `registry/` - `manifest_schema.py`, `loader.py`, `index.py`, `search.py`, `diagnostics.py`
- `runs/` - `models.py`, `store.py`
- `runtimes/` - `executor.py`, `protocol.py`
- `storage/` - `sqlite.py`
- Top-level: `cli.py`, `__main__.py`, `errors.py`, `logging.py`

### Test Structure
Complete test suite matching specifications:
- **Unit tests:** 11 test files (api, artifacts, bootstrap, config, registry, runs, runtimes)
- **Integration tests:** 4 tests (CLI, workflow e2e, discovery perf, fs policy)
- **Contract tests:** 2 tests (discovery, execution/artifacts)

### Tool Pack Structure
Correctly structured `tools/builtin/`:
- `manifest.yaml` with `builtin.gaussian_blur` and `builtin.convert_to_ome_zarr`
- `bioimage_mcp_builtin/` with `entrypoint.py` and `ops/` directory

### Configuration Files
All required files present:
- `pyproject.toml` with correct dependencies
- `ruff.toml` configured for Python 3.13
- `pytest.ini` with correct `pythonpath`
- `envs/bioimage-mcp-base.yaml` with scientific Python stack

---

## Test Results

### Test Execution
```
46 passed, 1 skipped in 5.64s
```

- **Skipped:** `test_discovery_perf.py` (intentionally skipped by default)
- All unit, integration, and contract tests pass

### Test Coverage
Overall coverage: **72%**

| Module | Coverage |
|--------|----------|
| `errors.py` | 100% |
| `artifacts/checksums.py` | 100% |
| `artifacts/models.py` | 100% |
| `registry/diagnostics.py` | 100% |
| `registry/search.py` | 100% |
| `runs/models.py` | 100% |
| `storage/sqlite.py` | 100% |
| `config/fs_policy.py` | 96% |
| `registry/manifest_schema.py` | 95% |
| `bootstrap/checks.py` | 93% |
| `api/pagination.py` | 92% |
| `config/loader.py` | 92% |
| `config/schema.py` | 89% |
| `api/discovery.py` | 85% |
| `api/execution.py` | 86% |
| `registry/loader.py` | 86% |
| `runtimes/executor.py` | 82% |
| `registry/index.py` | 80% |
| `artifacts/store.py` | 74% |

Low coverage modules (0%) are typically bootstrap/CLI code that requires environment setup:
- `__main__.py`, `logging.py`, `api/server.py`, `bootstrap/serve.py`, `bootstrap/configure.py`, `artifacts/export.py`, `runtimes/protocol.py`

---

## Bugs Found and Fixed

### Bug 1: `check_disk` fails when artifact_store_root doesn't exist (FIXED)

**Location:** `src/bioimage_mcp/bootstrap/checks.py:50-56`

**Problem:** The `check_disk` function called `shutil.disk_usage()` on a path that might not exist yet (the `artifact_store_root`), causing a `FileNotFoundError`.

**Symptom:**
```
ERROR[INTERNAL]: FileNotFoundError: [Errno 2] No such file or directory: '/home/user/.bioimage-mcp/artifacts'
```

**Fix:** Modified `check_disk` to traverse up the directory tree to find an existing parent for the disk usage check:
```python
def check_disk(min_free_gb: float = 1.0) -> CheckResult:
    config = load_config()
    root = Path(config.artifact_store_root)
    # Find existing parent for disk_usage check (the path may not exist yet)
    check_path = root
    while not check_path.exists() and check_path.parent != check_path:
        check_path = check_path.parent
    try:
        usage = shutil.disk_usage(check_path)
        ...
```

### Bug 2: Unclosed SQLite database connections (FIXED)

**Location:** Multiple files - `artifacts/store.py`, `runs/store.py`, `registry/index.py`, `api/discovery.py`, `api/execution.py`

**Problem:** SQLite connections created by stores were never closed, causing `ResourceWarning` messages during test runs.

**Fix:** Added `close()` methods and context manager support (`__enter__`/`__exit__`) to all store classes:
- `ArtifactStore` - now tracks `_owns_conn` flag and closes connection in `close()`
- `RunStore` - same pattern
- `ExecutionService` - closes both artifact and run stores
- `DiscoveryService` - optional ownership with `owns_conn` parameter
- `RegistryIndex` - optional ownership with `owns_conn` parameter

Updated tests to use context managers:
```python
with ArtifactStore(config) as store:
    ref = store.import_file(...)
```

---

## CLI Verification

### Commands Tested

| Command | Status | Notes |
|---------|--------|-------|
| `bioimage-mcp --help` | PASS | Shows all subcommands |
| `bioimage-mcp configure` | PASS | Creates `.bioimage-mcp/config.yaml` |
| `bioimage-mcp doctor` | PASS | Shows readiness status and registry info |
| `bioimage-mcp doctor --json` | PASS | Returns valid JSON with all 8 checks |
| `bioimage-mcp install --help` | PASS | Shows `--profile` option |
| `bioimage-mcp serve --help` | PASS | Shows `--stdio` option |
| `python -m bioimage_mcp --help` | PASS | Module invocation works |

### Doctor Output Sample
```
NOT READY
Registry: 0 tools, 0 functions; 0 invalid manifests
- conda_lock:
  - Install conda-lock (used for reproducible env locks)
```

### Doctor JSON Output
All 8 prerequisite checks present and working:
1. `python` - version check
2. `env_manager` - micromamba/conda/mamba detection
3. `disk` - free space check
4. `permissions` - write access check
5. `base_env` - environment validation
6. `gpu` - nvidia-smi detection
7. `conda_lock` - conda-lock installation check
8. `network` - connectivity check

---

## Recommendations

### Immediate (No action required - already fixed)
1. ~~Fix `check_disk` to handle non-existent directories~~ DONE
2. ~~Add proper resource management for SQLite connections~~ DONE

### Future Improvements
1. **Increase test coverage** for CLI and server modules by adding integration tests with mocked environments
2. **Add graceful degradation** for GPU detection on various platforms
3. **Consider connection pooling** for SQLite if performance becomes an issue
4. **Add more comprehensive logging** in the logging.py module

---

## Linting

```bash
$ ruff check .
# 1 import sorting error found and auto-fixed
Found 1 error (1 fixed, 0 remaining).
```

---

## Test Coverage Improvement Plan

### Priority 1: Easy Wins (0% coverage, simple modules)

#### `api/artifacts.py` → Target: 100%
Create `tests/unit/api/test_artifacts.py`:
```python
from bioimage_mcp.api.artifacts import ArtifactsService
from bioimage_mcp.artifacts.store import ArtifactStore
from bioimage_mcp.config.schema import Config

def test_artifacts_service_get_and_export(tmp_path):
    config = Config(
        artifact_store_root=tmp_path / "artifacts",
        tool_manifest_roots=[tmp_path / "tools"],
        fs_allowlist_read=[tmp_path],
        fs_allowlist_write=[tmp_path],
        fs_denylist=[],
    )
    
    with ArtifactStore(config) as store:
        src = tmp_path / "test.txt"
        src.write_text("content")
        ref = store.import_file(src, artifact_type="LogRef", format="text")
        
        svc = ArtifactsService(store)
        
        # Test get_artifact
        payload = svc.get_artifact(ref.ref_id)
        assert "ref" in payload
        
        # Test export_artifact  
        dest = tmp_path / "exported.txt"
        result = svc.export_artifact(ref.ref_id, str(dest))
        assert result["exported_path"] == str(dest)
```

#### `artifacts/export.py` → Target: 100%
This is a thin wrapper around `ArtifactStore.export()`. Either:
- Remove this module (it's redundant), or
- Add a simple test that calls the function directly

#### `logging.py` → Target: 100%
Create `tests/unit/test_logging.py`:
```python
import logging
from bioimage_mcp.logging import configure_logging, get_logger

def test_get_logger_returns_configured_logger():
    logger = get_logger("test.module")
    assert logger.name == "test.module"
    
def test_configure_logging_is_idempotent():
    configure_logging("DEBUG")
    configure_logging("DEBUG")  # Should not add duplicate handlers
    root = logging.getLogger("bioimage_mcp")
    assert len(root.handlers) == 1

def test_configure_logging_respects_level():
    configure_logging("WARNING")
    logger = get_logger()
    assert logger.level == logging.WARNING
```

#### `__main__.py` → Target: 100%
Add to `tests/unit/test_imports.py`:
```python
import subprocess

def test_main_module_invocation():
    result = subprocess.run(
        ["python", "-m", "bioimage_mcp", "--help"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    assert "doctor" in result.stdout
    assert "install" in result.stdout
```

---

### Priority 2: Medium Effort (CLI/Bootstrap modules)

#### `bootstrap/configure.py` → Target: 80%+
Add to `tests/integration/test_cli_doctor_install.py`:
```python
def test_configure_creates_config_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from bioimage_mcp.bootstrap.configure import configure
    configure()
    
    config_path = tmp_path / ".bioimage-mcp" / "config.yaml"
    assert config_path.exists()
    
    import yaml
    with open(config_path) as f:
        data = yaml.safe_load(f)
    assert "artifact_store_root" in data
    assert "tool_manifest_roots" in data
```

#### `bootstrap/install.py` → Target: 80%+
```python
def test_install_calls_env_manager(tmp_path, monkeypatch):
    import subprocess
    called = []
    
    original_run = subprocess.run
    def mock_run(*args, **kwargs):
        called.append(args[0] if args else kwargs.get('args'))
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")
    
    monkeypatch.setattr("subprocess.run", mock_run)
    monkeypatch.setattr(
        "bioimage_mcp.bootstrap.install.detect_env_manager", 
        lambda: ("mamba", "/usr/bin/mamba", "2.0")
    )
    monkeypatch.chdir(tmp_path)
    
    from bioimage_mcp.bootstrap.install import install
    install(profile="cpu")
    
    # Verify env manager was called with correct arguments
    assert any("bioimage-mcp-base" in str(c) for c in called)
```

#### `artifacts/metadata.py` → Target: 90%+
Create `tests/unit/artifacts/test_metadata.py`:
```python
import numpy as np
from pathlib import Path
from bioimage_mcp.artifacts.metadata import extract_image_metadata

def test_extract_metadata_from_tiff(tmp_path):
    import tifffile
    img = np.zeros((10, 20), dtype=np.uint16)
    path = tmp_path / "test.tiff"
    tifffile.imwrite(path, img)
    
    meta = extract_image_metadata(path)
    assert "shape" in meta
    assert "dtype" in meta
    assert meta["dtype"] == "uint16"

def test_extract_metadata_from_invalid_file_returns_empty(tmp_path):
    path = tmp_path / "not_an_image.txt"
    path.write_text("hello world")
    
    meta = extract_image_metadata(path)
    assert meta == {}  # Graceful fallback

def test_extract_metadata_from_nonexistent_file_returns_empty(tmp_path):
    path = tmp_path / "does_not_exist.tiff"
    
    meta = extract_image_metadata(path)
    assert meta == {}
```

#### `bootstrap/env_manager.py` → Target: 90%+
Add to `tests/unit/bootstrap/test_checks.py`:
```python
from bioimage_mcp.bootstrap.env_manager import detect_env_manager, _get_version

def test_get_version_returns_none_on_exception(monkeypatch):
    def raise_error(*args, **kwargs):
        raise OSError("Command failed")
    monkeypatch.setattr("subprocess.run", raise_error)
    
    result = _get_version("/fake/path")
    assert result is None

def test_detect_env_manager_prefers_micromamba(monkeypatch):
    def mock_which(name):
        # All managers available
        return f"/usr/bin/{name}" if name in ("micromamba", "mamba", "conda") else None
    monkeypatch.setattr("shutil.which", mock_which)
    monkeypatch.setattr(
        "bioimage_mcp.bootstrap.env_manager._get_version",
        lambda x: "1.0.0"
    )
    
    result = detect_env_manager()
    assert result is not None
    assert result[0] == "micromamba"  # First in preference order

def test_detect_env_manager_falls_back_to_conda(monkeypatch):
    def mock_which(name):
        return "/usr/bin/conda" if name == "conda" else None
    monkeypatch.setattr("shutil.which", mock_which)
    monkeypatch.setattr(
        "bioimage_mcp.bootstrap.env_manager._get_version",
        lambda x: "4.12.0"
    )
    
    result = detect_env_manager()
    assert result is not None
    assert result[0] == "conda"
```

---

### Priority 3: Higher Effort (Server/Async modules)

#### `bootstrap/serve.py` → Target: 70%+
```python
def test_serve_initializes_registry_and_config(tmp_path, monkeypatch):
    # Mock the MCP server to avoid actual network binding
    mock_server_started = []
    
    def mock_run_server(*args, **kwargs):
        mock_server_started.append(True)
    
    monkeypatch.setattr("bioimage_mcp.bootstrap.serve.run_mcp_server", mock_run_server)
    monkeypatch.chdir(tmp_path)
    
    # Create minimal config
    config_dir = tmp_path / ".bioimage-mcp"
    config_dir.mkdir()
    (config_dir / "config.yaml").write_text("""
artifact_store_root: /tmp/artifacts
tool_manifest_roots: []
fs_allowlist_read: []
fs_allowlist_write: []
fs_denylist: []
""")
    
    from bioimage_mcp.bootstrap.serve import serve
    serve(stdio=True)
    
    assert mock_server_started
```

#### `api/server.py` → Target: 60%+
This requires async testing with the MCP SDK:
```python
import pytest
from bioimage_mcp.api.server import create_mcp_server
from bioimage_mcp.config.schema import Config

@pytest.mark.asyncio
async def test_server_registers_discovery_tools(tmp_path):
    config = Config(
        artifact_store_root=tmp_path / "artifacts",
        tool_manifest_roots=[],
        fs_allowlist_read=[],
        fs_allowlist_write=[],
        fs_denylist=[],
    )
    
    server = create_mcp_server(config)
    
    # Verify tools are registered
    tools = await server.list_tools()
    tool_names = [t.name for t in tools]
    
    assert "list_tools" in tool_names
    assert "describe_tool" in tool_names
    assert "search_functions" in tool_names
    assert "run_workflow" in tool_names
```

---

### Coverage Target Summary

| Module | Current | Target | Effort | Priority |
|--------|---------|--------|--------|----------|
| `api/artifacts.py` | 0% | 100% | Low | P1 |
| `artifacts/export.py` | 0% | 100% | Low | P1 |
| `logging.py` | 0% | 100% | Low | P1 |
| `__main__.py` | 0% | 100% | Low | P1 |
| `bootstrap/configure.py` | 0% | 80%+ | Medium | P2 |
| `bootstrap/install.py` | 25% | 80%+ | Medium | P2 |
| `artifacts/metadata.py` | 47% | 90%+ | Medium | P2 |
| `bootstrap/env_manager.py` | 50% | 90%+ | Medium | P2 |
| `bootstrap/serve.py` | 0% | 70%+ | High | P3 |
| `api/server.py` | 0% | 60%+ | High | P3 |

**Expected overall coverage after improvements: 85-90%**

---

## Conclusion

The v0.0 Bootstrap implementation is **production-ready** for the MVP scope. All user stories (US1, US2, US3) are implemented and independently testable. The two bugs discovered during review have been fixed and all tests pass.

The test coverage improvement plan above provides a clear path to achieving 85-90% coverage with prioritized, actionable test cases.

---

## Test Coverage Improvements Implemented

**Date:** 2025-12-18

Following the recommendations in this code review, the following test coverage improvements were implemented:

### New Test Files Created

1. **`tests/unit/api/test_artifacts.py`** (2 tests)
   - `test_artifacts_service_get_artifact()` - Tests `ArtifactsService.get_artifact()`
   - `test_artifacts_service_export_artifact()` - Tests `ArtifactsService.export_artifact()`

2. **`tests/unit/test_logging.py`** (4 tests)
   - `test_get_logger_returns_configured_logger()`
   - `test_configure_logging_is_idempotent()`
   - `test_configure_logging_respects_level()`
   - `test_get_logger_default_name()`

3. **`tests/unit/artifacts/test_metadata.py`** (3 tests)
   - `test_extract_metadata_from_nonexistent_file_returns_empty()`
   - `test_extract_metadata_from_invalid_file_returns_empty()`
   - `test_extract_metadata_from_empty_file_returns_empty()`

4. **`tests/unit/bootstrap/test_env_manager.py`** (7 tests)
   - `test_get_version_returns_none_on_exception()`
   - `test_get_version_returns_first_line_of_stdout()`
   - `test_get_version_returns_none_for_empty_output()`
   - `test_detect_env_manager_prefers_micromamba()`
   - `test_detect_env_manager_falls_back_to_conda()`
   - `test_detect_env_manager_returns_none_when_nothing_found()`
   - `test_detect_env_manager_uses_mamba_if_micromamba_missing()`

### Updated Test Files

5. **`tests/unit/test_imports.py`**
   - Added `test_main_module_invocation()` for `__main__.py` coverage

6. **`tests/integration/test_cli_doctor_install.py`**
   - Added `test_configure_creates_config_file()`
   - Added `test_configure_returns_early_if_config_exists()`

### Coverage Results

| Module | Before | After | Status |
|--------|--------|-------|--------|
| `api/artifacts.py` | 0% | 100% | DONE |
| `logging.py` | 0% | 100% | DONE |
| `bootstrap/configure.py` | 0% | 100% | DONE |
| `bootstrap/env_manager.py` | 50% | 100% | DONE |
| `artifacts/metadata.py` | 47% | 47% | Partial (fallback paths tested) |
| **Overall** | **72%** | **77%** | +5% |

### Test Execution Summary

```
65 passed, 1 skipped in 6.82s
```

- All 65 tests pass
- 1 test intentionally skipped (`test_discovery_perf.py`)
- All linting checks pass (`ruff check .` reports no errors)

### Remaining Work (P3 Priority)

The following modules still have 0% coverage and require higher effort to test:
- `bootstrap/serve.py` - Requires mocking MCP server
- `api/server.py` - Requires async testing with MCP SDK
- `artifacts/export.py` - Thin wrapper, could be removed or tested
- `runtimes/protocol.py` - Protocol definitions only
