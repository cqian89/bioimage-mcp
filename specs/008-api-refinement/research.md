# Research & Design Decisions: API Refinement & Permission System

**Date**: 2025-12-28  
**Spec**: [spec.md](./spec.md)

## Research Questions & Findings

### 1. Hierarchical Discovery Semantics

**Question**: How to implement navigable discovery without bloating the MCP surface or breaking existing agents?

**Decision**: Introduce an optional `path` parameter to `list_tools` that filters children by dot-notated prefix.

**Rationale**:
- Mimics filesystem and Python package navigation, which is intuitive.
- Single-level retrieval (the default for a given path) keeps context window usage low.
- Batch support via `paths: list[str]` allows agents to "peek" into multiple sub-trees (e.g., `skimage.filters` and `skimage.morphology`) in one round-trip.

**Implementation Pattern**:
```python
# list_tools(path="") -> Root (Environments)
# [ {name: "base", type: "env", has_children: true}, ... ]

# list_tools(path="base") -> Base environment packages
# [ {name: "skimage", type: "package", has_children: true}, ... ]

# list_tools(path="base.skimage.filters") -> Filter functions
# [ {name: "gaussian", type: "function", fn_id: "base.skimage.filters.gaussian"}, ... ]
```

**Alternatives Considered**:
- Separate `list_environments`, `list_packages` tools: Rejected as it bloats the tool catalog.
- Flat listing with client-side filtering: Rejected for >100 functions (context bloat).

---

### 2. Multi-Keyword Search Ranking

**Question**: How to rank search results when multiple keywords are provided?

**Decision**: Two-stage ranking: (1) Primary sort by number of keywords matched, (2) Secondary sort by weighted score.

**Rationale**:
- Matches for "gaussian blur" should prioritize functions containing *both* words.
- Weighting fields ensures that name matches (intentionality) outrank tag matches (contextual).

**Weights**:
- `Name`: 3.0
- `Description`: 2.0
- `Tags`: 1.0

**Implementation Pattern**:
```python
def rank_functions(functions, keywords):
    scored = []
    for fn in functions:
        match_count = sum(1 for k in keywords if k in fn.full_text)
        weight_score = sum(field_weight * (1 if k in fn.field else 0))
        scored.append((fn, match_count, weight_score))
    
    return sorted(scored, key=lambda x: (-x[1], -x[2]))
```

---

### 3. Canonical Naming & Alias Migration

**Question**: How to transition from flat names to hierarchical names without breaking legacy scripts?

**Decision**: Use canonical `env.package.module.function` naming only. No aliases or backward compatibility shims.

**Rationale**:
- Standardizing on `env.package.module.function` provides long-term scalability.
- `builtin` functions are moved to `base` (e.g., `builtin.gaussian` -> `base.skimage.filters.gaussian`).
- Legacy names must be updated by callers; the registry will expose only canonical IDs.

**Migration Path for Builtins**:
| Old Function | New Canonical ID |
|--------------|------------------|
| `builtin.gaussian_blur` | `base.skimage.filters.gaussian` |
| `builtin.convert_to_ome_zarr` | `base.convert_to_ome_zarr` |
| `builtin.threshold_otsu` | `base.skimage.filters.threshold_otsu` |

---

### 4. Permission Inheritance via MCP Roots

**Question**: How to implement `inherit` mode safely and transparently?

**Decision**: Call `list_roots()` at session start and whenever a path check is needed (with short-term caching).

**Rationale**:
- Provides a "zero-config" experience for users working in standard IDEs (VS Code, Cursor).
- `hybrid` mode allows adding network drives or data lakes that might not be in the IDE workspace.
- Logging inherited roots at session start ensures auditability.

**Safety Fallbacks**:
- If client lacks `Roots` capability: Fall back to `explicit` mode (only use config allowlist).
- If client returns empty roots: Deny all operations unless in `hybrid` mode.

---

### 5. Overwrite Protection via MCP Elicitation

**Question**: How to handle "ask on overwrite" without custom UI?

**Decision**: Use `ServerSession.elicit_form` (or `elicit` for simple strings) to prompt the user.

**Rationale**:
- Standard MCP mechanism for gathering user input.
- `ServerSession.elicit*` returns an `ElicitResult` containing `action` (`accept`, `decline`, or `cancel`) and optional `content`.
- Decouples server logic from specific client UI implementations.
- If client lacks `Elicitation` capability, fall back to `permissions.on_overwrite` default (`deny`).

---

### 6. Search Ranking Algorithm Selection

**Question**: Which algorithm should be used for ranking search_functions results?

**Decision**: BM25 with character n-gram tokenization, with optional semantic re-ranking.

**Rationale**:
- BM25 is the industry standard for probabilistic information retrieval
- Character n-grams (e.g., 3-grams) provide inherent typo tolerance without fuzzy matching libraries
- Semantic re-ranking can be added as an optional enhancement for synonym handling

**Implementation Pattern**:
```python
from rank_bm25 import BM25Okapi

def ngram_tokenizer(text, n=3):
    text = text.lower()
    return [text[i:i+n] for i in range(len(text)-n+1)]

# Index: Tokenize by 3-character chunks
tokenized_corpus = [ngram_tokenizer(doc) for doc in corpus]
bm25 = BM25Okapi(tokenized_corpus)

# Search: Handles typos like "gausian" matching "gaussian"
scores = bm25.get_scores(ngram_tokenizer(query))
```

**Combined Ranking**: Two-stage approach:
1. Primary sort by number of keywords matched (existing spec)
2. Secondary sort by BM25 weighted score

**Match Weights** (unchanged from spec):
- Name: 3.0
- Description: 2.0
- Tags: 1.0

**Dependencies**:
- Required: `rank_bm25` (pure Python, ~50 lines implementation)
- Optional: `sentence-transformers` for semantic re-ranking (adds ~500MB, requires torch)

**Performance**:
- BM25 alone: <1ms for 500 functions
- With semantic re-ranking: ~30ms

**Alternatives Considered**:
- **TF-IDF**: Simpler but lacks document length normalization and term saturation
- **Full semantic search**: Too heavy for core dependencies; relegated to optional enhancement
- **Elasticsearch/OpenSearch**: Overkill for local server with <1000 functions

---

### 7. Smart Hierarchy with Shortcuts

**Question**: How to handle environments with single packages (e.g., cellpose.cellpose.models.eval is redundant)?

**Decision**: Implement "Smart Hierarchy with Shortcuts" - full hierarchy exists but navigation auto-expands single-child paths.

**Rationale**:
- Canonical names remain consistent (`env.package.module.function`) for reproducibility
- Agents can navigate efficiently without redundant roundtrips
- Small environments (like cellpose with 2 functions) don't require 4 navigation calls

**Implementation Patterns**:

```python
# Full path always works (canonical)
list_tools(path="cellpose.cellpose.models")  # → [eval, train]

# Smart shortcut - auto-expands single-child paths
list_tools(path="cellpose")  # → [eval, train] directly (skips intermediate levels)

# Explicit flatten for any path
list_tools(path="base", flatten=True)  # → all 47 functions in base, flattened

# Root with flatten
list_tools(flatten=True)  # → all functions across all envs
```

**Auto-Expand Rules**:
1. If a path has exactly one child at a level, auto-descend to next level
2. Continue until reaching functions OR multiple children at a level
3. Response includes `expanded_from` field to show what was auto-expanded

**Response Example**:
```python
list_tools(path="cellpose")
# Returns:
{
  "tools": [
    {"name": "eval", "type": "function", "fn_id": "cellpose.cellpose.models.eval"},
    {"name": "train", "type": "function", "fn_id": "cellpose.cellpose.models.train"}
  ],
  "expanded_from": "cellpose → cellpose.cellpose → cellpose.cellpose.models",
  "next_cursor": null
}
```

**Alternatives Considered**:
- **Flatten single-tool envs**: Rejected - creates inconsistent naming schemes
- **Two-level only**: Rejected - loses hierarchical discoverability for large envs
- **Capability-based grouping**: Rejected - doesn't map to env isolation model

---

### 8. Summary of Decisions

| Feature | Decision | Implementation |
|---------|----------|----------------|
| Hierarchy | Dot-prefix navigation | `list_tools(path="base.skimage")` |
| Hierarchy Shortcuts | Auto-expand single-child paths | Reduces roundtrips, keeps canonical names |
| Search | Multi-keyword weighted | Count matches, then sum weights |
| Search Ranking | BM25 + n-gram tokenization | Typo-tolerant, fast, pure Python |
| Naming | 4-part canonical | `base.skimage.filters.gaussian` |
| Aliases | Not supported (early dev) | Use canonical names only |
| Permissions | Root inheritance | `inherit` mode via `list_roots()` |
| Overwrites | MCP Elicitation | `elicit_form` returns `ElicitResult` |

All research items are resolved. No open blockers for implementation.
