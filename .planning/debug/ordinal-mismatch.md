---
status: resolved
trigger: "Investigate why a crash in trackpy.batch causes a persistent Ordinal mismatch (expected 6, got 5) for subsequent calls."
created: 2026-01-23T00:00:00Z
updated: 2026-01-23T00:00:00Z
---

## Current Focus
hypothesis: The worker or manager fails to increment/sync the ordinal counter correctly when an exception occurs.
test: Analyze code in persistent.py and worker_ipc.py for exception handling and ordinal logic.
expecting: To find a path where the ordinal is not updated or a message is lost during a crash.
next_action: gather symptoms

## Symptoms
expected: System handles crash gracefully, subsequent calls work with correct ordinal.
actual: Persistent "Ordinal mismatch" (expected 6, got 5) after a crash.
errors: "Ordinal mismatch"
reproduction: Crash trackpy.batch, then make another call.
started: Unknown

## Eliminated

## Evidence

## Resolution
root_cause:
fix:
verification:
files_changed: []


## Resolution
root_cause: "Worker entrypoint does not capture function stdout, so libraries like trackpy that print to stdout corrupt the NDJSON IPC stream. The client code caught the JSONDecodeError but left the worker alive in READY state, causing the next request to read the previous (buffered) response, resulting in an ordinal mismatch."
fix: "Modified PersistentWorkerManager to catch protocol violations (JSON errors, ordinal mismatches) and immediately kill the worker process, ensuring a fresh worker is spawned for subsequent requests."
verification: "Verified with repro script that polluting stdout now causes the worker to be killed, and subsequent requests successfully spawn a new worker."
files_changed:
  - src/bioimage_mcp/runtimes/persistent.py: "Added strict error handling and worker termination on protocol violations in execute, evict, and materialize."

