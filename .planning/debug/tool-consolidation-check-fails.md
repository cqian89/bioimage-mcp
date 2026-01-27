---
status: investigating
trigger: "Investigate why tool_consolidation check fails with ok: false and invalid_base_manifest. Check src/bioimage_mcp/bootstrap/checks.py and the base tool manifest in tools/base/manifest.yaml. Identify what makes it 'invalid' according to the check."
created: 2026-01-27T00:00:00Z
updated: 2026-01-27T00:04:00Z
---

## Current Focus

hypothesis: "base manifest marked invalid because load_manifest_file returns diagnostics (engine_events) even when schema validates"
test: "run load_manifest_file on tools/base/manifest.yaml to see diag contents"
expecting: "diag non-null with overlay_conflict events, causing invalid_base_manifest"
next_action: "summarize root cause and report to user"

## Symptoms

expected: "tool_consolidation check ok: true"
actual: "tool_consolidation check reports ok: false with invalid_base_manifest"
errors: "invalid_base_manifest"
reproduction: "run bioimage-mcp doctor (tool_consolidation check)"
started: "unknown"

## Eliminated

## Evidence

- timestamp: 2026-01-27T00:04:00Z
  checked: "load_manifest_file(tools/base/manifest.yaml)"
  found: "manifest validates; diagnostics present with engine_events: overlay_conflict for base.skimage.filters.gaussian and base.skimage.morphology.remove_small_objects (targets not found)"
  implication: "check_tool_consolidation treats any diag as invalid, so base manifest becomes invalid_base_manifest"

- timestamp: 2026-01-27T00:04:00Z
  checked: "check_tool_consolidation in checks.py"
  found: "flags invalid_base_manifest when manifest is None OR diag is not None"
  implication: "even warnings/engine_events (not schema errors) make base manifest invalid"

## Resolution

root_cause: "load_manifest_file returns diagnostics for overlay conflicts (missing overlay targets), and check_tool_consolidation treats any diagnostics as invalid_base_manifest"
fix: ""
verification: ""
files_changed: []
