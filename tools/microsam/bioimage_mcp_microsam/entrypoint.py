from __future__ import annotations

import json
import sys


def handle_describe(params: dict) -> dict:
    target_fn = params.get("target_fn")
    if target_fn == "meta.describe":
        return {
            "ok": True,
            "params_schema": {
                "type": "object",
                "properties": {
                    "target_fn": {
                        "type": "string",
                        "description": "The function id to describe",
                    }
                },
                "required": ["target_fn"],
            },
        }

    return {
        "ok": False,
        "error": {
            "code": "NOT_FOUND",
            "message": f"Function {target_fn} not found in tools.microsam",
        },
    }


def main():
    try:
        raw_input = sys.stdin.read()
        if not raw_input:
            print(json.dumps({"ok": False, "error": {"message": "Empty input"}}))
            sys.exit(1)

        request = json.loads(raw_input)
        req_id = request.get("id")
        params = request.get("params", {})
        tool_config = request.get("tool_config", {})

        # Resolve runtime device (Task 2, 21-05)
        from bioimage_mcp_microsam.device import select_device

        device_pref = tool_config.get("microsam", {}).get("device", "auto")
        try:
            # We use strict=False for meta.describe to avoid blocking discovery
            # on machines without accelerators when a specific device is forced.
            selected_device = select_device(device_pref, strict=(req_id != "meta.describe"))
        except RuntimeError as e:
            # Handle selection failure for forced unavailable devices
            print(
                json.dumps(
                    {
                        "ok": False,
                        "error": {
                            "code": "DEVICE_UNAVAILABLE",
                            "message": str(e),
                            "details": [
                                {
                                    "path": "microsam.device",
                                    "hint": (
                                        "Set microsam.device to 'auto' or "
                                        "install a compatible GPU profile."
                                    ),
                                }
                            ],
                        },
                    }
                )
            )
            sys.exit(1)

        if req_id == "meta.describe":
            response = handle_describe(params)
        else:
            response = {
                "ok": False,
                "error": {
                    "code": "NOT_IMPLEMENTED",
                    "message": f"Function {req_id} is not implemented in Phase 21",
                },
            }

        print(json.dumps(response))
        if not response.get("ok"):
            sys.exit(1)

    except Exception as e:
        print(json.dumps({"ok": False, "error": {"message": str(e)}}))
        sys.exit(1)


if __name__ == "__main__":
    main()
