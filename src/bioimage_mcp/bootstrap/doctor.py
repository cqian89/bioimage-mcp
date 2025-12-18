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
        for diagnostic in diagnostics[:max_invalid]:
            invalid_items.append(
                {
                    "path": str(diagnostic.path),
                    "tool_id": diagnostic.tool_id,
                    "errors": diagnostic.errors[:3],
                }
            )

        return {
            "tool_count": tool_count,
            "function_count": function_count,
            "invalid_manifest_count": len(diagnostics),
            "invalid_manifests": invalid_items,
        }
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}


def doctor(*, json_output: bool) -> int:
    """Run local readiness checks and print actionable output."""

    results = run_checks()
    ready = all(r.ok for r in results)
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

    if ready:
        return 0

    for result in results:
        if result.ok:
            continue
        print(f"- {result.name}:")
        for item in result.remediation:
            print(f"  - {item}")

    return 1
