# Phase 3: Data & Artifacts - Context

**Gathered:** 2026-01-22
**Status:** Ready for planning

<domain>
## Phase Boundary

System enables zero-copy data passing and artifact management. Focus on file paths, `mem://` protocol, and `bioio` integration.
(Note: True zero-copy is deferred; implementation focuses on robust `mem://` abstraction backed by files).

</domain>

<decisions>
## Implementation Decisions

### Zero-copy Implementation
- **Defer Shared Memory**: Continue using file-backed simulation for Phase 3. True zero-copy (SHM) is deferred to future optimization.
- **Strict Abstraction**: Maintain strict `mem://` URI facade. External tools must see `mem://session/env/id`, not the backing file paths.
- **Storage Limits**: Bounded by available disk space. No artificial RAM-like size caps.
- **Cleanup Policy**: Session-scoped. `mem://` artifacts (and their backing files) are deleted when the session ends.

### Preview Strategy
- **Generation**: On-demand (lazy). Previews are only generated when requested by the client, not continuously.
- **Formats**: Standardized by server (e.g., JPEG for images, text snippet for data). Client receives server-chosen format.
- **Caching**: Generated previews are cached for the duration of the session to avoid re-computation.

</decisions>

<specifics>
## Specific Ideas

- User emphasized maintaining the `ref_id` and `mem://` abstraction even if file-backed.
- Validated that current `memory.py` is indeed file-simulated (Phase 1 status).

</specifics>

<deferred>
## Deferred Ideas

- True Zero-copy (Shared Memory/Plasma store) implementation.

</deferred>

---

*Phase: 03-data-artifacts*
*Context gathered: 2026-01-22*
