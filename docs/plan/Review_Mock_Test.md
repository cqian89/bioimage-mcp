# Review of Mock Usage in Tests

## Executive Summary
The project demonstrates a mature and well-structured testing strategy with a clear separation of concerns. Mocks are used appropriately to:
1.  Isolate units in unit tests.
2.  Test infrastructure/orchestration logic without heavy dependencies in "fast" integration tests.
3.  Bypass external system requirements (like Conda environments) where they are not the subject of the test.

Real execution (without mocks) is preserved for specific "live" E2E tests, which correctly skip execution if the necessary environments are missing.

## Findings

### Unit Tests
**Status:** ✅ Appropriate Mock Usage

*   **Isolation:** Unit tests (e.g., `tests/unit/sessions/test_session_manager.py`) correctly use `unittest.mock.Mock` to isolate the class under test from its dependencies (`SessionStore`, `Config`).
*   **System Interactions:** Tests involving system calls (e.g., `tests/unit/bootstrap/test_env_manager.py`, `tests/unit/bootstrap/test_install.py`) use `monkeypatch` to mock `subprocess.run` and `shutil.which`. This is essential for reliability and speed, preventing unit tests from modifying the system or depending on external tools.

### Integration Tests (Infrastructure)
**Status:** ✅ Appropriate Mock Usage (with one note on naming)

*   **Dummy Tools:** Tests like `tests/integration/test_call_tool_dry_run.py` and `tests/integration/test_interactive_call_tool.py` use a "dummy tool" pattern (creating a simple Python script on the fly) and mock the environment manager. This is an excellent pattern for testing the *MCP Server's* logic (execution, session management, artifact handling) without the overhead of real bioimage tools.
*   **Workflow Orchestration:** `tests/integration/test_cellpose_e2e.py` mocks `execute_step` to verify that the workflow engine correctly handles the input/output contract of the Cellpose tool (e.g., creating `LabelImageRef`).
    *   **Note:** The name "E2E" in `test_cellpose_e2e.py` is slightly misleading as it mocks the actual tool execution. It tests the "End-to-End" workflow *logic* for Cellpose, but not the tool itself.

### Integration Tests (Live)
**Status:** ✅ Real Execution (No Mocks)

*   **Real Verification:** `tests/integration/test_live_workflow.py` and `tests/integration/test_flim_phasor_e2e.py` perform true end-to-end testing without mocks.
*   **Safety:** These tests correctly check for environment availability (`_env_available`) and skip if requirements are not met, ensuring the test suite remains robust on dev machines without full setups.

## Recommendations

1.  **Clarify Test Naming:**
    *   Consider renaming `tests/integration/test_cellpose_e2e.py` to `tests/integration/test_cellpose_workflow_logic.py` or `test_cellpose_contract_flow.py`. This would clearly distinguish it from `test_live_workflow.py` which runs the actual tool.

2.  **Mark "Live" Tests:**
    *   Ensure `test_live_workflow.py` and `test_flim_phasor_e2e.py` are distinctively marked (e.g., `@pytest.mark.live` or `@pytest.mark.slow`). Currently, they use `@pytest.mark.integration`, but distinguishing "mocked integration" from "live integration" can help in CI pipelines (e.g., running fast tests on every commit, live tests nightly).

3.  **Maintain Dummy Tool Pattern:**
    *   Continue using the "dummy tool" + "mocked env manager" pattern for new infrastructure features. It provides excellent coverage of the core server logic with minimal overhead.
