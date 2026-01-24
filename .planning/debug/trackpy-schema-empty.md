---
status: diagnosed
trigger: "Diagnose why `bioimage-mcp describe trackpy.locate` returns an empty `params_schema`."
created: 2026-01-24T00:00:00Z
updated: 2026-01-24T00:09:00Z
---

## Current Focus
<!-- OVERWRITE on each update - reflects NOW -->

hypothesis: confirmed - meta.describe call never succeeds because trackpy entrypoint expects command=execute, while describe_function sends legacy request without command
test: compare discovery meta.describe request with trackpy entrypoint handling of legacy requests
expecting: legacy request falls through to Unknown command in trackpy entrypoint, so params_schema stays empty from manifest
next_action: return diagnosis

## Symptoms
<!-- Written during gathering, then IMMUTABLE -->

expected: params_schema includes diameter and other parameters for trackpy.locate
actual: params_schema properties are empty
errors: none reported; response shows inputs correctly
reproduction: run `bioimage-mcp describe trackpy.locate`
started: during Trackpy integration (Phase 05)

## Eliminated
<!-- APPEND only - prevents re-investigating -->

## Evidence
<!-- APPEND only - facts discovered -->

- timestamp: 2026-01-24T00:01:00Z
  checked: repo search for params_schema and trackpy code
  found: trackpy tool uses tools/trackpy/bioimage_mcp_trackpy/introspect.py to emit params_schema; registry loader also builds schema via _parameters_to_json_schema
  implication: missing params likely originates from trackpy introspection or registry schema conversion

- timestamp: 2026-01-24T00:04:00Z
  checked: trackpy entrypoint + discovery flow
  found: describe_function executes meta.describe via tools/trackpy/bioimage_mcp_trackpy/entrypoint.py, which calls introspect_function in trackpy tool env
  implication: empty params_schema likely originates inside trackpy introspect_function (signature/doc parsing), not core registry conversion

- timestamp: 2026-01-24T00:07:00Z
  checked: discovery meta.describe request + trackpy entrypoint request handling
  found: describe_function sends meta.describe without a "command" field; trackpy entrypoint treats legacy request by calling _handle_request, which requires command=="execute" and otherwise returns Unknown command
  implication: meta.describe fails for trackpy, so describe_function falls back to manifest params_schema (empty properties from meta.list)


## Resolution
<!-- OVERWRITE as understanding evolves -->

root_cause: "Trackpy tool entrypoint rejects legacy meta.describe requests (no command field), returning Unknown command; describe_function then falls back to manifest schema which has empty properties from meta.list."
fix: ""
verification: ""
files_changed: []
