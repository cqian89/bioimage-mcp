## Specification Analysis Report

**Analysis context**
- `FEATURE_DIR`: `specs/014-native-artifact-types`
- Artifacts loaded: `specs/014-native-artifact-types/spec.md`, `specs/014-native-artifact-types/plan.md`, `specs/014-native-artifact-types/tasks.md`, `.specify/memory/constitution.md`

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| C1 | Constitution Alignment | **CRITICAL** | `specs/014-native-artifact-types/tasks.md:121`, `.specify/memory/constitution.md:72` | Task T038 proposes writing OME-Zarr via `ome_zarr.writer.write_image`, which conflicts with Constitution III: tool implementations **MUST** use `bioio.BioImage` + `bioio.writers.*` (and warns against custom I/O wrappers bypassing plugin detection). | Rewrite export/interchange tasks to use `bioio` writers (e.g., `OMEZarrWriter`) and ensure required `bioio-*` plugins are in tool envs. |
| C2 | Constitution Alignment | **CRITICAL** | `.specify/memory/constitution.md:15`, `specs/014-native-artifact-types/spec.md:85`, `specs/014-native-artifact-types/plan.md:50` | MCP responses expand with new metadata fields, but the plan/spec do not include the Constitution I required **version bump justification** for expanded MCP surface area (even if additive). | Add an explicit “version bump justification” note in plan/spec (or explicitly argue why it doesn’t qualify, if that’s the intended interpretation). |
| C3 | Constitution Alignment | **HIGH** | `.specify/memory/constitution.md:153`, `specs/014-native-artifact-types/spec.md:79`, `specs/014-native-artifact-types/tasks.md:37` | Spec/plan/tasks introduce `ScalarRef`, but the constitution’s “canonical artifact types” list does not include it. This is potentially a governance/architecture mismatch. | Decide whether `ScalarRef` is allowed as a new canonical type (then update the relevant architecture source of truth), or represent scalars using an existing canonical type. |
| G1 | Coverage Gap | **HIGH** | `specs/014-native-artifact-types/spec.md:91`, `specs/014-native-artifact-types/tasks.md:18` | Spec requires provenance recording of dimension metadata (“recorded in workflow provenance”), but tasks do not include any work item to update provenance capture or add tests for it. | Add tasks/tests to ensure provenance includes `shape/dims/ndim/dtype` on artifact creation/transform. |
| G2 | Coverage Gap | **HIGH** | `specs/014-native-artifact-types/spec.md:129`, `specs/014-native-artifact-types/tasks.md:78` | SC-004 requires metadata inspection “in under 100ms without downloading data,” but tasks only assert fields exist; no perf or “no data load” guard exists. | Add a small performance assertion (or at least a “no data materialization” test using a sentinel/mock) for metadata-only inspection. |
| G3 | Coverage Gap | **HIGH** | `specs/014-native-artifact-types/spec.md:87`, `specs/014-native-artifact-types/spec.md:130`, `specs/014-native-artifact-types/tasks.md:101` | Spec/SC enumerate formats including TIFF (non-OME), JPEG, TSV; tasks implement PNG, OME-TIFF, OME-Zarr, CSV, NPY but do not mention TIFF (distinct from OME-TIFF), JPEG, TSV. | Either narrow the spec (if out of scope) or add tasks/tests for the missing formats required by SC-005 / stated export list. |
| I1 | Inconsistency | **MEDIUM** | `specs/014-native-artifact-types/spec.md:105`, `specs/014-native-artifact-types/plan.md:30`, `specs/014-native-artifact-types/tasks.md:146` | Terminology drifts across artifacts: “dimension hints” (spec), `DimensionRequirement` (plan), and `dimension_requirements` (tasks). This can cause schema/tooling mismatches. | Standardize on one term and one manifest field name; add a short glossary in spec or plan to pin definitions. |
| I2 | Inconsistency | **MEDIUM** | `specs/014-native-artifact-types/spec.md:90`, `specs/014-native-artifact-types/tasks.md:22` | Spec says “No new tool-pack dependencies required,” but tasks anticipate adding `ome-zarr-py` to an environment. | Reconcile: confirm dependency already exists, or update spec/plan to acknowledge the required plugin(s) and where they live (tool envs vs core). |
| D1 | Duplication / Drift | **MEDIUM** | `specs/014-native-artifact-types/plan.md:105`, `specs/014-native-artifact-types/tasks.md:36` | Plan’s suggested new test filenames don’t match tasks’ test filenames for similar intent (risk of duplicate tests or missing coverage if both get created). | Align the canonical test file naming list (pick one naming scheme in tasks.md and update plan.md references accordingly). |
| U1 | Underspecification | **MEDIUM** | `specs/014-native-artifact-types/spec.md:99`, `specs/014-native-artifact-types/tasks.md:44` | “Adapters MUST NOT expand to 5D unless explicitly required” is clear, but the mechanism is only partially specified/implemented in tasks (e.g., `should_expand_to_5d` appears later, and only in one adapter). | Specify a single decision function and apply it consistently across adapters/tools, with tests covering: manifest requirement present/absent + format boundary cases. |
| G4 | Coverage Gap | **MEDIUM** | `specs/014-native-artifact-types/spec.md:92`, `specs/014-native-artifact-types/tasks.md:74` | Spec requires “clear error messages” for invalid dimension ops, but no tasks/tests validate error content or error classification. | Add a focused unit test asserting error messaging for at least one invalid op (e.g., squeeze non-singleton). |
| A1 | Ambiguity | **MEDIUM** | `specs/014-native-artifact-types/spec.md:103`, `specs/014-native-artifact-types/tasks.md:109` | “Infer a sensible default” export format is underspecified in the spec; tasks add heuristics, but acceptance criteria don’t pin edge behavior (conflicts likely later). | Promote heuristics into spec as deterministic rules + a small decision table; add acceptance scenarios for ambiguous cases. |
| A2 | Ambiguity / Placeholder-Like | **LOW** | `specs/014-native-artifact-types/plan.md:43` | “NEEDS CLARIFICATION (resolved in research.md)” is hard to audit from spec/plan/tasks alone; it reads like a lingering placeholder. | Replace with a brief resolved decision summary in plan.md, or reference the exact resolved section in research.md (without leaving “needs clarification”). |
| D2 | Duplication Risk | **LOW** | `specs/014-native-artifact-types/tasks.md:36`, `specs/014-native-artifact-types/tasks.md:60` | Some contract coverage appears to overlap (e.g., ArtifactRef metadata contract + later schema compliance in same file). Not necessarily wrong, but could become redundant. | Consolidate related contract checks into one file per contract domain and ensure each test has distinct assertions. |
| I3 | Ambiguous Boundary | **LOW** | `specs/014-native-artifact-types/plan.md:87`, `specs/014-native-artifact-types/tasks.md:117` | Plan describes export support partly in server artifact store, while tasks implement export as a tool op (`tools/base/.../export.py`). Boundary responsibilities are not crisply stated. | Add a single sentence in spec/plan clarifying where export lives (server vs tool env) and why (constitution isolation). |

---

### Coverage Summary Table

| Requirement Key | Has Task? | Task IDs | Notes |
|-----------------|-----------|----------|-------|
| `artifact-refs-include-shape-ndim-dtype` | Yes | T004, T008, T021, T022, T024, T025, T028 | Good coverage of presence; add backward-compat expectations if needed. |
| `artifact-refs-include-dimension-labels` | Yes | T004, T008, T021, T022, T024, T025 | Naming drift: dims vs axes/labels needs consistency. |
| `dimension-reducing-ops-produce-reduced-ndim` | Yes | T013, T014, T016, T017, T018 | Looks aligned to US1 acceptance scenarios. |
| `adapters-no-auto-expand-to-5d` | Yes | T017, T045, T048 | Ensure applies to all adapters, not just xarray. |
| `cross-env-interchange-uses-ome-zarr` | Partial | T019, T046, T047 | Interchange format negotiation/manifest defaults aren’t explicitly covered. |
| `table-artifacts-include-column-metadata` | Yes | T006, T010, T023, T026, T039 | Solid, but confirm contract schema includes it. |
| `export-accepts-format-parameter` | Yes | T032, T035, T040 | Needs constitution-compliant writer choice. |
| `export-infers-default-format` | Yes | T029, T030, T031, T034 | Spec needs deterministic rules to reduce ambiguity. |
| `preserve-physical-pixel-sizes` | Partial | T008, T022, T025 | Presence covered; preservation-through-ops not tested. |
| `manifests-support-dimension-hints` | Yes | T043, T046, T047, T048 | Term alignment needed (`dimension_requirements` vs “hints”). |
| `mcp-responses-additive-backward-compatible` | Partial | T024 | Missing Constitution I “version bump justification.” |
| `provenance-records-dim-metadata` | No | — | Add tasks/tests. |
| `metadata-inspection-without-downloading-data` | Partial | T024 | Add “no materialization” guarantee tests. |
| `metadata-inspection-under-100ms` | No | — | Add perf guardrail test or measurable proxy. |
| `clear-errors-for-invalid-dim-ops` | No | — | Add at least one explicit test. |
| `cross-env-transfer-zero-data-loss` | Yes | T041 | Consider adding an explicit “round-trip” assertion for metadata equality. |

---

### Constitution Alignment Issues (Summary)

- **MUST violation (CRITICAL)**: Avoid direct `ome_zarr.*` writing; use `bioio` readers/writers as required by `.specify/memory/constitution.md:72`.
- **MUST missing (CRITICAL)**: Add a “version bump justification” for MCP surface expansion per `.specify/memory/constitution.md:15`.
- **Potential architecture mismatch (HIGH)**: `ScalarRef` vs canonical artifact types list at `.specify/memory/constitution.md:153`.

---

### Unmapped Tasks (No Clear Spec Requirement/User Story Link)

These may still be valuable, but they aren’t clearly traceable to a spec requirement or user story as written:
- `specs/014-native-artifact-types/tasks.md:22` (T001) environment dependency check
- `specs/014-native-artifact-types/tasks.md:23` (T002) review task
- `specs/014-native-artifact-types/tasks.md:24` (T003) review task
- `specs/014-native-artifact-types/tasks.md:157` (T049-T055) docs, suite run, env update, backward-compat review (could be mapped to NFRs/constitution gates with minor wording changes)

---

### Metrics

- Total Requirements (functional + non-functional derived): **16**
- Total Tasks: **55**
- Coverage % (requirements with ≥1 task): **81%** (13/16)
- Ambiguity Count: **2**
- Duplication/Drift Count: **2**
- Critical Issues Count: **2**

---

## Next Actions

- **Resolve CRITICAL items before `/speckit.implement`** (constitution compliance + version bump justification).
- After that, decide scope for export formats (either narrow `spec.md` export list or add tasks for TIFF/JPEG/TSV).
- Recommended commands:
  - If you want to tighten requirements: rerun `/speckit.specify` to clarify export inference + NFRs (perf, provenance, error messaging).
  - If you want to tighten architecture/implementation boundaries: rerun `/speckit.plan` to reconcile “export in tool env vs server store” and “bioio writer requirement”.
  - If you want to adjust task coverage: manually edit `specs/014-native-artifact-types/tasks.md` to add tasks for provenance/perf/error-message guarantees and constitution-compliant OME-Zarr writing.

---

## Optional Remediation Offer

Would you like me to suggest **concrete remediation edits** (exact wording + where to place them) for the **top N issues** (e.g., N=5), without applying any changes automatically?
