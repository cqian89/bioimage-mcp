# Export Session Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement `export_session` functionality to export a session's canonical steps as a reproducible workflow artifact.

**Architecture:** 
- `SessionStore`: Update to support `update_session_status`.
- `InteractiveExecutionService`: Add `export_session` logic to filter canonical steps, build workflow spec, and persist as `NativeOutputRef`.
- `FastMCP`: Expose `export_session` as a tool.

**Tech Stack:** Python 3.13, Pydantic, SQLite.

### Task 1: Update SessionStore

**Files:**
- Modify: `src/bioimage_mcp/sessions/store.py`

**Step 1: Write test (already exists or trivial unit test)**
Since `SessionStore` logic is simple SQL, I'll rely on the integration test `tests/integration/test_export_session.py` later, but for TDD I should add a quick unit test or just implement it if it's trivial.
Let's add a unit test for `update_session_status` in `tests/unit/sessions/test_store.py` if it exists, or create it.
I'll check if `tests/unit/sessions/test_store.py` exists.

**Step 2: Check for unit tests**
Check `tests/unit/sessions/test_store.py` existence.

**Step 3: Add unit test for `update_session_status`**
If it exists, add a test case.

**Step 4: Implement `update_session_status` in `store.py`**
```python
    def update_session_status(self, session_id: str, status: str) -> None:
        self.get_session(session_id)
        with self.conn:
            self.conn.execute(
                "UPDATE sessions SET status = ? WHERE session_id = ?",
                (status, session_id),
            )
```

### Task 2: Implement InteractiveExecutionService.export_session

**Files:**
- Modify: `src/bioimage_mcp/api/interactive.py`

**Step 1: Run integration test to see it fail**
Run: `pytest tests/integration/test_export_session.py`
Expected: Skip or Fail (Test skips if method missing, so I'll temporarily comment out the skip logic in the test or just implement the method and see it fail logic validation).
Actually, the test has:
```python
        if not hasattr(interactive, "export_session"):
            pytest.skip("export_session not implemented yet")
```
So I should implement the method skeleton first to enable the test, then watch it fail.

**Step 2: Implement `export_session` skeleton**
```python
    def export_session(self, session_id: str) -> dict[str, Any]:
        pass
```

**Step 3: Run test to confirm failure**
Run: `pytest tests/integration/test_export_session.py`
Expected: Fail (returns None or crashes).

**Step 4: Implement `export_session` logic**
- Get steps.
- Filter canonical.
- Sort.
- Check empty.
- Build content dict.
- Write artifact.
- Update status.
- Return artifact ref dump.

**Step 5: Run test to confirm pass**
Run: `pytest tests/integration/test_export_session.py`
Expected: PASS.

### Task 3: Expose via MCP Tool

**Files:**
- Modify: `src/bioimage_mcp/api/server.py`

**Step 1: Add `export_session` tool**
```python
    @mcp.tool()
    def export_session(session_id: str, ctx: Context | None = None) -> dict[str, Any]:
        # Logic to ensure session_id matches context if needed, or just allow exporting any session?
        # The prompt didn't specify strict ownership checks, just "ctx: Context; interactive.export_session(ctx.session.id)".
        # Wait, if I take session_id as arg, I can export any session.
        # But the prompt said: "Modify src/bioimage_mcp/api/server.py: Add export_session tool. ... ctx: Context. interactive.export_session(ctx.session.id)."
        # This implies exporting the *current* session.
        # However, `export_session(session_id)` is more flexible.
        # Let's see the requirement again.
        # "Add export_session tool. @mcp.tool(). ctx: Context. interactive.export_session(ctx.session.id)."
        # This implies it takes NO arguments (other than ctx) and exports the CURRENT session.
        # But `session_id` is usually a parameter for tools.
        # Let's check `call_tool` implementation in `server.py`. It takes `session_id`.
        # If the user wants `export_session(session_id: str)`, I should implement that.
        # If the user wants `export_session()`, I should implement that.
        # The prompt explicitly said: "Add export_session tool. ... interactive.export_session(ctx.session.id)".
        # This suggests it exports the *current* session found in context.
        # BUT, looking at `call_tool` in `server.py`:
        # def call_tool(fn_id, inputs, params, session_id=None, ...): ... if not session_id and ctx... session_id = ctx.session.id
        # So it's flexible.
        # I will make `export_session` take an optional `session_id`.
        # def export_session(session_id: str | None = None, ctx: Context | None = None):
        #     if not session_id and ctx and ctx.session: session_id = ctx.session.id
        #     if not session_id: raise ...
        #     return interactive.export_session(session_id)
        pass
```

**Step 2: Verify**
I don't have a direct test for `server.py` tool exposure in `test_export_session.py` (it uses `interactive_service` directly).
I should verify `server.py` is valid python at least.
And maybe add a contract test if I can, but `test_export_session.py` is an integration test using the services directly.
I'll stick to implementing it in `server.py` to satisfy the requirement.

