---
phase: 21-usam-tool-pack-foundation
verified: 2026-02-05T00:00:00Z
status: gaps_found
score: 4/6 must-haves verified
gaps:
  - truth: "Tool execution automatically selects the fastest available device (CUDA > MPS > CPU)."
    status: failed
    reason: "No runtime/device-selection logic is implemented in the microsam tool pack or execution path; only config schema exists."
    artifacts:
      - path: "src/bioimage_mcp/config/schema.py"
        issue: "Defines microsam.device enum but no execution path consumes it."
      - path: "tools/microsam/bioimage_mcp_microsam/entrypoint.py"
        issue: "No inference/device-selection handling; only meta.describe is implemented."
    missing:
      - "Runtime device-selection logic honoring auto preference (CUDA > MPS > CPU)."
      - "Tool execution code that reads microsam.device and selects actual device."
      - "Tests asserting device-selection behavior."
human_verification:
  - test: "Install microsam GPU profile"
    expected: "`bioimage-mcp install microsam --profile gpu` completes successfully on Linux/macOS and prints success summary."
    why_human: "Requires conda/micromamba, GPU stack, network, and OS-specific behavior not available in this environment."
  - test: "Verify model cache presence after install"
    expected: "`.bioimage-mcp/state/microsam_models.json` exists and lists vit_b, vit_b_lm, vit_b_em paths that exist on disk."
    why_human: "Model downloads and cache file creation depend on external network and local filesystem.
      Must be verified on a real installation."
---

# Phase 21: µSAM Tool Pack Foundation Verification Report

**Phase Goal:** The µSAM tool pack is installed and ready for local inference.
**Verified:** 2026-02-05T00:00:00Z
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | Tool registry can load a microsam tool pack manifest without errors | ✓ VERIFIED | `tools/microsam/manifest.yaml` exists with tool_id/env_id/entrypoint and minimal function definition. |
| 2 | A runnable script exists to ensure required microsam models are cached | ✓ VERIFIED | `tools/microsam/bioimage_mcp_microsam/install_models.py` downloads vit_b/vit_b_lm/vit_b_em via micro_sam. |
| 3 | Dedicated isolated conda environment spec exists for microsam | ✓ VERIFIED | `envs/bioimage-mcp-microsam.yaml` includes micro_sam, napari, torch, and cache deps. |
| 4 | Reproducible lockfile exists for supported platforms | ✓ VERIFIED | `envs/bioimage-mcp-microsam.lock.yml` lists linux-64/osx-arm64 and sources `bioimage-mcp-microsam.yaml`. |
| 5 | `bioimage-mcp install microsam` and `--profile gpu` are wired | ✓ VERIFIED | `src/bioimage_mcp/cli.py` allows microsam + profile; `install.py` orchestrates env + GPU + post-install; tests pass. |
| 6 | Tool execution automatically selects fastest device (CUDA > MPS > CPU) | ✗ FAILED | No execution path consumes `microsam.device`; microsam entrypoint only implements meta.describe. |

**Score:** 4/6 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `tools/microsam/manifest.yaml` | Microsam tool pack declaration | ✓ VERIFIED | Contains tool_id/tools.microsam, env_id, entrypoint, platforms. |
| `tools/microsam/bioimage_mcp_microsam/entrypoint.py` | Tool pack entrypoint | ✓ VERIFIED | Implements JSON protocol for meta.describe; no inference yet. |
| `tools/microsam/bioimage_mcp_microsam/install_models.py` | Model cache ensure script | ✓ VERIFIED | Fetches vit_b/vit_b_lm/vit_b_em via micro_sam and outputs JSON. |
| `envs/bioimage-mcp-microsam.yaml` | Conda env spec | ✓ VERIFIED | Includes micro_sam, napari, pytorch, cache deps. |
| `envs/bioimage-mcp-microsam.lock.yml` | Conda lockfile | ✓ VERIFIED | Sources env yaml; platforms include linux-64, osx-arm64. |
| `src/bioimage_mcp/bootstrap/install.py` | Microsam install orchestration | ✓ VERIFIED | Handles microsam profiles, GPU post-install, model bootstrap, state write. |
| `src/bioimage_mcp/bootstrap/checks.py` | Doctor microsam model check | ✓ VERIFIED | Checks `.bioimage-mcp/state/microsam_models.json` and file existence. |
| `src/bioimage_mcp/config/schema.py` | microsam.device config | ⚠️ ORPHANED | Schema exists but unused by execution path. |

### Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- | --- |
| `tools/microsam/manifest.yaml` | `tools/microsam/bioimage_mcp_microsam/entrypoint.py` | entrypoint path | ✓ WIRED | Manifest entrypoint points to file that exists. |
| `src/bioimage_mcp/bootstrap/install.py` | `tools/microsam/.../install_models.py` | `conda/mamba run` | ✓ WIRED | `_microsam_post_install` executes script in env. |
| `src/bioimage_mcp/bootstrap/install.py` | `.bioimage-mcp/state/microsam_models.json` | JSON write | ✓ WIRED | Post-install persists script output to state file. |
| `src/bioimage_mcp/bootstrap/checks.py` | `.bioimage-mcp/state/microsam_models.json` | doctor check | ✓ WIRED | `check_microsam_models` reads and validates required models. |
| `microsam.device` config | execution/device selection | config override | ✗ NOT WIRED | No runtime usage of config or automatic device selection. |

### Requirements Coverage

| Requirement | Status | Blocking Issue |
| --- | --- | --- |
| INFRA-05 | ? NEEDS HUMAN | Requirement text not present; validate against acceptance tests. |
| USAM-01 | ? NEEDS HUMAN | Requirement text not present; validate against acceptance tests. |
| USAM-05 | ? NEEDS HUMAN | Requirement text not present; validate against acceptance tests. |
| USAM-06 | ✗ BLOCKED | Device selection auto logic not implemented. |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| --- | --- | --- | --- | --- |
| `tools/microsam/bioimage_mcp_microsam/entrypoint.py` | 51 | "not implemented in Phase 21" | ℹ️ Info | Acceptable for Phase 21 (no inference functions yet). |

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

Phase 21 establishes the microsam tool pack, environment specs, installation orchestration, and doctor checks. However, the core success criterion that tool execution automatically selects the fastest available device (CUDA > MPS > CPU) is not implemented. The config schema defines `microsam.device`, but no runtime execution path consumes it, and the microsam entrypoint provides only `meta.describe` (no inference/device logic). This blocks the “ready for local inference” goal.

---

_Verified: 2026-02-05T00:00:00Z_
_Verifier: Claude (gsd-verifier)_
