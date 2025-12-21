# Proposal: Interactive Tool Calling

## 1. Context & Problem
The current Bioimage-MCP architecture (v0.2) relies on a **"Plan-then-Execute" (Batch)** model:
1. User asks for analysis.
2. LLM plans the *entire* pipeline into a JSON workflow spec.
3. LLM calls `run_workflow(spec)`.

**Issues:**
- **Cognitive Load**: The LLM must "hallucinate" the valid parameter combinations for *all* steps at once.
- **Brittleness**: If step 3 of 5 fails, the entire run fails. The LLM must edit the JSON and retry.
- **Rigidity**: It discourages exploratory analysis ("Let's try filter A, oh that looks bad, let's try filter B").

## 2. Proposed Solution: Interactive Tool Calling
We propose supporting an **Interactive (REPL)** model where the LLM executes tools one by one, observing results immediately.

### 2.1 New MCP Primitive: `call_tool`
Add a direct execution endpoint to the MCP server:

```python
@mcp.tool()
def call_tool(fn_id: str, inputs: dict[str, str], params: dict[str, Any]) -> dict[str, Any]:
    """
    Execute a single tool function immediately.
    Returns: A dict containing output artifact references and status.
    Side Effect: Appends this execution to the active 'Session Log'.
    """
```

### 2.2 The Interactive Loop
1. **Discovery**: LLM calls `list_tools` / `search_functions` to find relevant tools.
2. **Step 1**: LLM calls `call_tool("base.load_image", ...)` -> receives `{"image": "ref://123"}`.
3. **Step 2**: LLM calls `call_tool("base.phasor", {"dataset": "ref://123"}, ...)` -> receives `{"g": "ref://124", "s": "ref://125"}`.
4. **Correction**: If Step 2 errors, LLM sees the error message immediately and retries with different params.

### 2.3 Preserving Reproducibility (Session Logs)
To maintain the project's core value of reproducibility, "Interactive" does not mean "Ephemeral".
- The server maintains a **Session** (implicit or explicit).
- Every successful `call_tool` is appended to the Session's **Linear History**.
- At the end, the Session can be exported as a `Workflow` artifact, identical to the batch JSON format.

## 3. Architecture Changes

### 3.1 API Layer (`src/bioimage_mcp/api/server.py`)
- Expose `call_tool`.

### 3.2 Execution Layer (`src/bioimage_mcp/api/execution.py`)
- Introduce `SessionManager`.
- `run_workflow` becomes a wrapper that iterates through steps and calls the internal `execute_step` logic.
- `call_tool` calls `execute_step` directly and updates the Session.

## 4. Pros vs Cons

| Feature | Batch (Current) | Interactive (Proposed) |
| :--- | :--- | :--- |
| **LLM Reasoning** | Hard (requires planning ahead) | **Natural** (Step-by-step chain of thought) |
| **Error Recovery** | Poor (Macro-retry) | **Excellent** (Micro-retry) |
| **Latency** | Low (Internal loop) | Higher (Round-trip per step) |
| **Safety** | High (Pre-validated graph) | Medium (Runtime validation per step) |

## 5. Recommendation
Adopt **Interactive Tool Calling** as the primary interaction mode for LLM agents, while keeping **Batch** for:
1. Replaying saved workflows.
2. High-throughput processing (where round-trips are too slow).
