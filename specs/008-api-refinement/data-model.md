# Data Model: API Refinement & Permissions

**Note**: Per Constitution v0.6.0, backward compatibility is not required during early development. This data model may change without deprecation periods.

## Entity Models

### Server Configuration
Top-level keys in `.bioimage-mcp/config.yaml`.

**permissions**:
- `mode`: `PermissionMode`
- `on_overwrite`: `OverwritePolicy`

**fs_allowlist_read**: list[str] (Top-level)
**fs_allowlist_write**: list[str] (Top-level)
**fs_denylist**: list[str] (Top-level)

**agent_guidance**:
- `warn_unactivated`: bool (Default: true)

---

### Permission Settings

**PermissionMode (Enum)**:
- `explicit`: Use only paths in `fs_allowlist_read/write`.
- `inherit`: (Default) Use paths provided by MCP `list_roots()`.
- `hybrid`: Combine `explicit` and `inherit` paths.

**OverwritePolicy (Enum)**:
- `allow`: Overwrite without asking.
- `deny`: Fail operation if file exists.
- `ask`: Prompt user via MCP Elicitation.

**PermissionDecision (Model)**:
- `operation`: "read" | "write"
- `path`: Absolute path checked.
- `mode`: `PermissionMode` used.
- `decision`: "ALLOWED" | "DENIED" | "ASK"
- `reason`: e.g., "Under inherited root /home/user/workspace"
- `timestamp`: UTC ISO string.

---

### Tool Hierarchy
Models for the refined discovery API.

**ToolHierarchyNode (Model)**:
- `name`: Node name (e.g., "filters").
- `full_path`: Full dot-notated path (e.g., "base.skimage.filters").
- `type`: "environment" | "package" | "module" | "function".
- `has_children`: Boolean.
- `fn_id`: Optional[str] - only present if `type == "function"`.
- `summary`: Optional[str] - short description.

**ScoredFunction (Model)**:
- `fn_id`: Canonical function ID.
- `name`: Human name.
- `description`: Summary text.
- `score`: Total weighted match score.
- `match_count`: Number of keywords matched.
- `tags`: List of strings.

---

### Search Ranking

**SearchIndexEntry (Model)**:
- `fn_id`: Canonical function ID
- `name`: Human name
- `description`: Summary text
- `tags`: List of strings
- `tokenized_name`: list[str] - n-gram tokens for name
- `tokenized_description`: list[str] - n-gram tokens for description
- `tokenized_tags`: list[str] - n-gram tokens for all tags

**RankingConfig (Model)**:
- `name_weight`: float (default: 3.0)
- `description_weight`: float (default: 2.0)
- `tags_weight`: float (default: 1.0)
- `ngram_size`: int (default: 3)
- `algorithm`: "bm25" | "hybrid" (default: "bm25")

---

### Request/Response Schemas

**ListToolsRequest**:
- `path`: Optional[str] - dot-notated prefix.
- `paths`: Optional[list[str]] - batch navigation.
- `limit`: int (default 20).
- `cursor`: str.
- `flatten`: Optional[bool] - If true, return all functions under path flattened.

**ListToolsResponse**:
- `tools`: list[ToolHierarchyNode]
- `next_cursor`: str
- `expanded_from`: Optional[str] - Shows auto-expansion path if single-child traversal occurred.

**SearchFunctionsRequest**:
- `keywords`: list[str] | str (Required).
- `query`: Optional[str] - Legacy alias for `keywords`.
- `tags`: Optional[list[str]].
- `limit`: int (default 20).

**SearchFunctionsResponse**:
- `functions`: list[ScoredFunction]
- `next_cursor`: str

**DescribeFunctionRequest**:
- `fn_id`: Optional[str] - backward compatible single ID.
- `fn_ids`: Optional[list[str]] - batch retrieval.

**DescribeFunctionResponse**:
- `schemas`: dict[str, dict] - Mapping of fn_id to JSON schema.
- `errors`: dict[str, str] - Mapping of fn_id to error message.

**RunFunctionRequest**:
- `fn_id`: Function ID (canonical or alias).
- `inputs`: dict[str, ArtifactRef].
- `params`: dict[str, Any].
- `metadata`: includes `warn_unactivated`.

**RunFunctionResponse**:
- `result`: Execution output.
- `warnings`: list[str] (execution warnings only).
- `workflow_hint`: Guidance for the next step.

---

### Hierarchy Auto-Expansion

When navigating the tool hierarchy, single-child paths are automatically expanded to reduce roundtrips.

**AutoExpandResult (Model)**:
- `original_path`: str - The path requested by the client
- `expanded_path`: str - The final path after auto-expansion
- `levels_skipped`: int - Number of intermediate levels skipped

**Auto-Expand Rules**:
1. If a node has exactly one child, descend automatically
2. Continue until reaching functions OR a node with multiple children
3. The `expanded_from` field in the response shows the traversal path

**Example**:
```
Request: list_tools(path="cellpose")
Traversal: cellpose (1 child) → cellpose.cellpose (1 child) → cellpose.cellpose.models (2 children: eval, train)
Response: expanded_from = "cellpose → cellpose.cellpose → cellpose.cellpose.models"
```
