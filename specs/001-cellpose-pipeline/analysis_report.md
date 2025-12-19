## Specification Analysis Report

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| C1 | Coverage Gap | CRITICAL | spec.md:91; tasks.md:48 | FR-008 export is required but has no explicit tasks/tests. | Add tasks + tests for artifact export (API/CLI) including allowlist enforcement. |
| C2 | Coverage Gap | HIGH | spec.md:85; tasks.md:58 | FR-002 artifact-reference-only payload rule not explicitly asserted by tests/tasks. | Add a contract/integration test asserting only refs/metadata (no pixel arrays) and add guardrails in protocol serialization. |
| A1 | Ambiguity | HIGH | plan.md:15 | plan.md contains ACTION REQUIRED placeholder text in Technical Context. | Replace with concrete decisions; remove placeholder blocks. |
| U1 | Underspecified | HIGH | plan.md:33; tasks.md:18 | Plan “Needs Clarification” questions are not resolved or represented as tasks. | Add Phase 0 tasks to resolve, or update plan/spec with final answers + code references. |
| K1 | Constitution Alignment | HIGH | constitution.md:91; tasks.md:18 | TDD principle applies beyond US phases; Phase 1/2 infra tasks lack explicit tests-first counterparts. | Add test tasks for infra (discovery, manifests, allowlists, artifact schema validation) or justify exceptions. |
| D1 | Duplication | MEDIUM | spec.md:103; tasks.md:18 | spec.md also includes “Implementation Tasks” which may drift from tasks.md. | Make spec tasks high-level pointers to tasks.md or remove the detailed list. |
| I2 | Inconsistency | MEDIUM | spec.md:87; tasks.md:38 | Workflow record naming differs (“workflow record artifact reference” vs “WorkflowRecordRef”). | Pick a canonical name and use consistently across artifacts. |
| A3 | Underspecified | MEDIUM | plan.md:24 | OME-Zarr decision is flagged NEEDS CLARIFICATION. | Explicitly decide v0.1 scope (OME-TIFF only with error behavior, or add tasks). |
| A2 | Ambiguity | MEDIUM | plan.md:70 | Project structure section includes placeholder tree instruction. | Remove placeholder instructions to keep plan deterministic. |
| I1 | Inconsistency | LOW | tasks.md:10; tasks.md:58 | Story tag format in tasks.md docs differs from actual usage. | Align the format docs with the implemented tags. |
| U2 | Ambiguity | LOW | plan.md:29 | Non-functional performance constraints exist in plan but not tracked as requirements. | Promote key NFRs into spec and map to tasks/tests. |

**Coverage Summary Table:**

| Requirement Key | Has Task? | Task IDs | Notes |
|-----------------|-----------|----------|-------|
| the-system-must-support-executing-an-end-to-end-v0-1-workflo | Yes | T010, T015, T019, T033, T034 |  |
| the-system-must-not-embed-large-image-or-label-payloads-dire | No |  | Covered indirectly; missing explicit “no pixel arrays” assertion. |
| for-each-workflow-run-success-or-failure-the-system-must-pro | Yes | T015, T030 |  |
| for-each-successful-workflow-run-the-system-must-produce-a-w | Yes | T007, T015, T024, T025, T028, T030, T041 |  |
| the-system-must-support-replaying-a-workflow-record-to-start | Yes | T007, T024 |  |
| the-system-must-validate-workflow-step-compatibility-before- | Yes | T009, T010, T022, T030, T040 |  |
| the-system-must-provide-clear-actionable-error-messages-when | Yes | T023, T030 |  |
| the-system-must-allow-users-to-export-any-artifact-reference | No |  | No concrete export implementation/test tasks found. |
| the-system-must-enforce-configured-filesystem-allowlists-suc | Yes | T030 |  |
| the-system-must-include-a-minimal-automated-validation-that- | Yes | T007, T015, T032, T033, T034, T036 |  |

**Constitution Alignment Issues:**

- Constitution conflicts are treated as CRITICAL/HIGH; see K1 regarding TDD tests-first coverage for infra phases.

**Unmapped Tasks:**

- Tasks with no clear mapping to an FR (likely infra/test harness work): T001, T002, T003, T004, T005, T006, T008, T011, T012, T013, T014, T016, T017, T018, T020, T021, T026, T027, T029, T031, T035, T037, T038, T039, T042, T043, T044

**Metrics:**

- Total Requirements: 10
- Total Tasks: 44
- Coverage % (requirements with >=1 task): 80% (8/10)
- Ambiguity Count: 6
- Duplication Count: 1
- Critical Issues Count: 1

**Next Actions:**

- [x] C1: Add tasks + tests for artifact export (API/CLI) including allowlist enforcement.
- [x] C2: Add a contract/integration test asserting only refs/metadata (no pixel arrays) and add guardrails in protocol serialization.
- [x] A1: Replace with concrete decisions; remove placeholder blocks.
- [x] U1: No action. I will resolve the placeholders in the next iteration.
- [x] K1: Add test tasks for infra (discovery, manifests, allowlists, artifact schema validation) or justify exceptions.
- [x] D1: Make spec tasks high-level pointers to tasks.md.
- [x] I2: Use `NativeOutputRef` with `format="workflow-record-json"` as the canonical approach (see research.md Section 10).
- [x] A3: OME-TIFF only with error behavior.
- [x] A2: Remove placeholder instructions.
- [x] I1: Align the format docs with the implemented tags.
- [x] U2: Promote key NFRs into spec and map to tasks/tests.
