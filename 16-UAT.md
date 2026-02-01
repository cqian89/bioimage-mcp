# Phase 16: StarDist Tool Environment UAT

| Test | Expected Behavior | Status | Severity | Notes |
|------|-------------------|--------|----------|-------|
| 1. Install StarDist Environment | `bioimage-mcp install stardist` completes with "Installed: 1" and no errors. | Pass | High | Verifies env definition and lockfile. |
| 2. List StarDist Tool | `bioimage-mcp list --tool stardist` shows `stardist` in the output with status `ready` or similar (not `missing`). | Pass | High | Verifies tool registration and manifest. |
| 3. Verify End-to-End Workflow | `pytest tests/integration/test_stardist_adapter_e2e.py` passes. | Fail | Critical | Failed due to env missing deps (griffe, mcp), python version mismatch (core>=3.13 vs env=3.11), and pythonpath issues. |
