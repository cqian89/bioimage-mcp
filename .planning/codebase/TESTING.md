# Testing Patterns

**Analysis Date:** 2026-01-22

## Test Framework

**Runner:**
- `pytest` (Version >= 8)
- Config: `pytest.ini`

**Assertion Library:**
- Standard `assert` (built-in to pytest)

**Run Commands:**

### Local PR Gate
Run these to verify changes before pushing:
```bash
pytest tests/unit -q
pytest tests/contract -q
pytest tests/smoke -m smoke_minimal -q
pytest tests/smoke -m smoke_pr -q
```

### Full Suite
```bash
pytest                 # Run all tests (may be slow)
pytest tests/unit/     # Run only unit tests
pytest -m "smoke_extended" # Run all smoke tests
```

## Test File Organization

**Location:**
- Separate `tests/` directory at project root.

**Naming:**
- `test_*.py` for test files.
- `test_*` for test functions.

**Structure & Markers:**
- `tests/unit/`: Logic isolation. Markers: (none required).
- `tests/contract/`: Protocol/Schema compliance. Markers: (none required).
- `tests/integration/`: Multi-service flows. Markers: `integration`.
- `tests/smoke/`: E2E readiness. Markers: `smoke_minimal`, `smoke_pr`, `smoke_extended`.

## Test Structure

**Suite Organization:**
```python
@pytest.mark.integration
def test_discover_describe_run_flow(end_to_end_context, monkeypatch):
    """Docstring explaining the test case."""
    # Setup
    ctx = end_to_end_context
    
    # Execution
    result = ctx["discovery"].list_tools()
    
    # Assertion
    assert "items" in result
```

**Patterns:**
- **Setup:** Use `pytest.fixture` for common dependencies.
- **Teardown:** Managed by fixtures (e.g., `reset_fs_allowlist_env` in `tests/conftest.py`).
- **Assertion:** Direct equality/membership checks.

## Mocking

**Framework:** `monkeypatch` (built-in pytest fixture) and `pytest-mock` (implied by `mocker` usage in some contexts, though `monkeypatch` is more prevalent).

**Patterns:**
```python
def test_error_hints_selected_by_error_code(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "bioimage_mcp.api.execution.execute_step",
        lambda **_kw: ({"ok": False, "error": {"code": "AXIS_SAMPLES_ERROR"}}, "log", 1),
    )
```

**What to Mock:**
- External tool execution (`execute_step`).
- Filesystem environment variables.
- Complex service interactions in unit tests.

**What NOT to Mock:**
- Pydantic models.
- Core internal logic that can be tested with `tmp_path`.

## Fixtures and Factories

**Test Data:**
- Use `tmp_path` for ephemeral file creation.
- Synthetic data generation in tests (e.g., `_write_manifest` in `tests/unit/api/test_execution.py`).

**Location:**
- `tests/conftest.py` for global fixtures.
- `tests/integration/conftest.py` (or similar) for category-specific fixtures.

## Coverage

**Requirements:** Not explicitly enforced in `pyproject.toml`.

**View Coverage:**
- Typically `pytest --cov=src` if `pytest-cov` is installed.

## Test Types

**Unit Tests:**
- Focus on individual services (`DiscoveryService`, `ArtifactsService`).
- Heavy use of mocking for dependencies.

**Integration Tests:**
- End-to-end flows involving multiple services.
- Mocked execution for speed.

**Contract Tests:**
- Verify API schemas and manifest formats.
- Located in `tests/contract/`.

## Common Patterns

**Async Testing:**
- Use `@pytest.mark.anyio`.
- Most server-side and smoke tests are async.

**Error Testing:**
- `with pytest.raises(ErrorCode):`

---

*Testing analysis: 2026-01-22*
