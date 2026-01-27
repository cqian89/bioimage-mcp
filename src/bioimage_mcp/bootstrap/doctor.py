from __future__ import annotations

import json

from bioimage_mcp.bootstrap.checks import CheckResult, run_all_checks
from bioimage_mcp.config.loader import load_config
from bioimage_mcp.registry.loader import load_manifests


def run_checks() -> list[CheckResult]:
    return run_all_checks()


def _collect_registry_summary(*, max_invalid: int = 5) -> dict[str, object]:
    try:
        config = load_config()
        manifests, diagnostics = load_manifests(config.tool_manifest_roots)
        tool_count = len(manifests)
        function_count = sum(len(m.functions) for m in manifests)

        invalid_items = []
        # Filter for truly invalid (those that failed to load manifest object)
        invalid_manifests = [d for d in diagnostics if d.errors]
        for diagnostic in invalid_manifests[:max_invalid]:
            invalid_items.append(diagnostic.to_dict())

        all_events = []
        for diagnostic in diagnostics:
            all_events.extend(diagnostic.engine_events)

        # Deterministic ordering
        all_events.sort(key=lambda e: (e.fn_id or "", e.type.value, e.message))

        # Filter based on diagnostic level
        level = config.diagnostic_level
        if level == "minimal":
            # Only show errors/conflicts
            all_events = [
                e for e in all_events if e.type in ("skipped_callable", "overlay_conflict")
            ]
        elif level == "standard":
            # Show everything except maybe missing docs if too many?
            # For now just show all in standard
            pass

        return {
            "tool_count": tool_count,
            "function_count": function_count,
            "invalid_manifest_count": len(invalid_manifests),
            "invalid_manifests": invalid_items,
            "engine_events": [e.to_dict() for e in all_events],
        }
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}


def doctor(*, json_output: bool) -> int:
    """Run local readiness checks and print actionable output."""

    results = run_checks()
    ready = all(r.ok for r in results if r.required)
    registry = _collect_registry_summary()

    if json_output:
        payload = {
            "ready": ready,
            "checks": [r.to_dict() for r in results],
            "registry": registry,
        }
        print(json.dumps(payload))
        return 0 if ready else 1

    if ready:
        print("READY")
    else:
        print("NOT READY")

    if "error" in registry:
        print(f"Registry: unavailable ({registry['error']})")
    else:
        print(
            "Registry: "
            f"{registry['tool_count']} tools, "
            f"{registry['function_count']} functions; "
            f"{registry['invalid_manifest_count']} invalid manifests"
        )
        invalid = registry.get("invalid_manifests")
        if isinstance(invalid, list) and invalid:
            print("Invalid manifests (showing up to 5):")
            for item in invalid:
                if not isinstance(item, dict):
                    continue
                path = item.get("path")
                errors = item.get("errors")
                first_error = errors[0] if isinstance(errors, list) and errors else "unknown error"
                print(f"- {path}: {first_error}")

    if not ready:
        for result in results:
            if result.ok or not result.required:
                continue
            print(f"- {result.name}:")
            for item in result.remediation:
                print(f"  - {item}")
        return 1

    # Print warnings for failing optional checks
    optional_failures = [r for r in results if not r.ok and not r.required]
    if optional_failures:
        print("\nWARNINGS:")
        for result in optional_failures:
            print(f"- {result.name}:")
            for item in result.remediation:
                print(f"  - {item}")

    return 0
