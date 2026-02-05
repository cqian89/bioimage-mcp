---
phase: 21-usam-tool-pack-foundation
verified: 2026-02-05T12:45:00Z
status: passed
score: 6/6 must-haves verified
re_verification:
  previous_status: gaps_found
  previous_score: 4/6
  gaps_closed:
    - "Tool execution automatically selects the fastest available device (CUDA > MPS > CPU)."
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Install microsam GPU profile"
    expected: "`bioimage-mcp install microsam --profile gpu` completes successfully on Linux/macOS and prints success summary."
    result: "PASSED — Installation successful after model name fix (vit_b_em → vit_b_em_organelles)."
  - test: "Verify model cache presence after install"
    expected: "`.bioimage-mcp/state/microsam_models.json` exists and lists vit_b, vit_b_lm, vit_b_em_organelles paths that exist on disk."
    result: "PASSED — State file created, all 3 models present in cache."
---

# Phase 21: µSAM Tool Pack Foundation Verification Report

**Phase Goal:** The µSAM tool pack is installed and ready for local inference.
**Verified:** 2026-02-05T12:45:00Z
**Status:** passed
**Re-verification:** Yes — after gap closure + human testing

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | Tool registry can load a microsam tool pack manifest without errors | ✓ VERIFIED | `tools/microsam/manifest.yaml` exists with tool_id/env_id/entrypoint and minimal function definition. |
| 2 | A runnable script exists to ensure required microsam models are cached | ✓ VERIFIED | `tools/microsam/bioimage_mcp_microsam/install_models.py` downloads vit_b/vit_b_lm/vit_b_em via micro_sam. |
| 3 | Dedicated isolated conda environment spec exists for microsam | ✓ VERIFIED | `envs/bioimage-mcp-microsam.yaml` includes micro_sam, napari, torch, and cache deps. |
| 4 | Reproducible lockfile exists for supported platforms | ✓ VERIFIED | `envs/bioimage-mcp-microsam.lock.yml` lists linux-64/osx-arm64 and sources `bioimage-mcp-microsam.yaml`. |
| 5 | `bioimage-mcp install microsam` and `--profile gpu` are wired | ✓ VERIFIED | `src/bioimage_mcp/bootstrap/install.py` orchestrates env creation, GPU post-install, and model bootstrap. |
| 6 | Tool execution automatically selects fastest device (CUDA > MPS > CPU) | ✓ VERIFIED | `execute_step` injects `tool_config` with microsam.device; `entrypoint.py` calls `select_device`; `device.py` implements CUDA > MPS > CPU order. |

**Score:** 6/6 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `tools/microsam/manifest.yaml` | Microsam tool pack declaration | ✓ VERIFIED | Contains tool_id/tools.microsam, env_id, entrypoint, platforms. |
| `tools/microsam/bioimage_mcp_microsam/install_models.py` | Model cache ensure script | ✓ VERIFIED | Fetches vit_b/vit_b_lm/vit_b_em via micro_sam and outputs JSON. |
| `envs/bioimage-mcp-microsam.yaml` | Conda env spec | ✓ VERIFIED | Includes micro_sam, napari, pytorch, cache deps. |
| `envs/bioimage-mcp-microsam.lock.yml` | Conda lockfile | ✓ VERIFIED | Sources env yaml; platforms include linux-64, osx-arm64. |
| `src/bioimage_mcp/bootstrap/install.py` | Microsam install orchestration | ✓ VERIFIED | Handles microsam profiles, GPU post-install, model bootstrap, state write. |
| `src/bioimage_mcp/api/execution.py` | Tool config wiring | ✓ VERIFIED | Injects `tool_config` for microsam requests using `config.microsam.device`. |
| `tools/microsam/bioimage_mcp_microsam/device.py` | Device selection logic | ✓ VERIFIED | `select_device` prefers CUDA > MPS > CPU and enforces strict mode for forced devices. |
| `tools/microsam/bioimage_mcp_microsam/entrypoint.py` | Tool entrypoint device wiring | ✓ VERIFIED | Reads `tool_config.microsam.device` and calls `select_device`. |
| `tests/unit/api/test_microsam_tool_config.py` | Wiring tests | ✓ VERIFIED | Asserts tool_config injection for microsam only. |
| `tests/unit/tools/test_microsam_device_selection.py` | Device selection tests | ✓ VERIFIED | Covers auto preference, forced device errors, and missing MPS backend. |

### Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- | --- |
| `Config.microsam.device` | `execute_step` request | tool_config injection | ✓ WIRED | `execution.py` adds `request["tool_config"]["microsam"]["device"]`. |
| `tool_config.microsam.device` | `select_device` | entrypoint | ✓ WIRED | `entrypoint.py` reads tool_config and calls `select_device`. |
| `select_device` | device preference order | internal logic | ✓ WIRED | `device.py` checks CUDA → MPS → CPU in auto mode. |
| `install.py` | `install_models.py` | `conda/mamba run` | ✓ WIRED | `_microsam_post_install` executes the model bootstrap script. |
| `install.py` | `.bioimage-mcp/state/microsam_models.json` | JSON write | ✓ WIRED | Post-install persists script output to state file. |
| `checks.py` | `.bioimage-mcp/state/microsam_models.json` | doctor check | ✓ WIRED | `check_microsam_models` reads and validates required models. |

### Requirements Coverage

| Requirement | Status | Blocking Issue |
| --- | --- | --- |
| INFRA-05 | ? NEEDS HUMAN | Requires running microsam inference on real hardware to confirm auto device selection. |
| USAM-01 | ? NEEDS HUMAN | Requires real conda/micromamba install of microsam tool pack. |
| USAM-05 | ? NEEDS HUMAN | Requires verifying specialist model cache after install. |
| USAM-06 | ? NEEDS HUMAN | Requires confirming models are downloaded during install (not first-run). |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| --- | --- | --- | --- | --- |
| `tools/microsam/bioimage_mcp_microsam/entrypoint.py` | 84 | "not implemented in Phase 21" | ℹ️ Info | Acceptable for Phase 21; inference functions are scheduled for later phases. |

### Human Verification Required

#### 1. Install microsam GPU profile

**Test:** Run `bioimage-mcp install microsam --profile gpu` on Linux/macOS.
**Expected:** Installation succeeds, environment created/updated, models downloaded, state file created.
**Why human:** Requires conda/micromamba, GPU drivers, network, and platform-specific steps.

#### 2. Verify model cache presence after install

**Test:** Check `.bioimage-mcp/state/microsam_models.json` and paths for `vit_b`, `vit_b_lm`, `vit_b_em`.
**Expected:** JSON exists with model paths, files exist on disk.
**Why human:** Depends on actual download and local filesystem.

### Gaps Summary

No code gaps detected in this re-verification. Remaining verification requires running the install flow and model downloads on real systems.

---

_Verified: 2026-02-05T12:00:00Z_
_Verifier: Claude (gsd-verifier)_
