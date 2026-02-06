from __future__ import annotations

import argparse
import json
import sys

from bioimage_mcp.errors import BioimageMcpError


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bioimage-mcp")
    parser.add_argument("--debug", action="store_true", help="Show tracebacks on errors")

    subparsers = parser.add_subparsers(dest="command", required=True)

    install = subparsers.add_parser("install", help="Install tool environments")
    install.add_argument(
        "tools", nargs="*", help="Specific tools to install (e.g., cellpose tttrlib)"
    )
    install.add_argument(
        "--profile", choices=["cpu", "gpu", "minimal"], help="Install a predefined profile"
    )
    install.add_argument("--force", action="store_true", help="Reinstall even if already exists")
    install.set_defaults(_handler=_handle_install)

    doctor = subparsers.add_parser("doctor", help="Check local readiness")
    doctor.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    doctor.set_defaults(_handler=_handle_doctor)

    list_cmd = subparsers.add_parser("list", help="List installed tools and their status")
    list_cmd.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    list_cmd.add_argument("--tool", help="Filter by tool ID or short name (e.g. trackpy)")
    list_cmd.set_defaults(_handler=_handle_list)

    configure = subparsers.add_parser("configure", help="Write starter configuration")
    configure.set_defaults(_handler=_handle_configure)

    status_cmd = subparsers.add_parser("status", help="Show storage usage and cleanup status")
    status_cmd.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    status_cmd.set_defaults(_handler=_handle_status)

    cleanup = subparsers.add_parser("cleanup", help="Trigger manual storage cleanup")
    cleanup.add_argument(
        "--dry-run", action="store_true", help="Preview deletions without modifying disk/DB"
    )
    cleanup.add_argument("--force", action="store_true", help="Override cooldown and lock")
    cleanup.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    cleanup.set_defaults(_handler=_handle_cleanup)

    pin = subparsers.add_parser("pin", help="Pin an artifact to exempt it from cleanup")
    pin.add_argument("ref_id", help="Artifact reference ID")
    pin.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    pin.set_defaults(_handler=_handle_pin)

    unpin = subparsers.add_parser("unpin", help="Unpin an artifact so it can be cleaned up")
    unpin.add_argument("ref_id", help="Artifact reference ID")
    unpin.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    unpin.set_defaults(_handler=_handle_unpin)

    serve = subparsers.add_parser("serve", help="Start the MCP server")
    serve.add_argument("--stdio", action="store_true", help="Use stdio transport")
    serve.set_defaults(_handler=_handle_serve)

    remove = subparsers.add_parser("remove", help="Remove a tool environment")
    remove.add_argument("tool", help="Tool to remove (e.g., cellpose)")
    remove.add_argument("--yes", "-y", action="store_true", help="Skip confirmation")
    remove.set_defaults(_handler=_handle_remove)

    run_parser = subparsers.add_parser("run", help="Run a tool via the ExecutionService")
    run_parser.add_argument("tool_id", help="Tool ID to run")
    run_parser.add_argument("--param", "-p", action="append", help="Parameter in key=value format")
    run_parser.add_argument("--input", "-i", action="append", help="Input in key=path format")
    run_parser.add_argument("--session", help="Session ID (defaults to cli-session)")
    run_parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    run_parser.set_defaults(_handler=_handle_run)

    return parser


def _print_error(code: str, message: str, *, details: object | None, debug: bool) -> None:
    print(f"ERROR[{code}]: {message}", file=sys.stderr)
    if details is not None and debug:
        print(json.dumps(details, indent=2, default=str), file=sys.stderr)


def _handle_install(args: argparse.Namespace) -> int:
    from bioimage_mcp.bootstrap.install import install

    if args.tools and args.profile:
        if args.tools != ["microsam"]:
            print(
                "Error: tools and --profile are mutually exclusive (except for microsam)",
                file=sys.stderr,
            )
            return 1

    return install(
        tools=args.tools if args.tools else None,
        profile=args.profile,
        force=args.force,
    )


def _handle_doctor(args: argparse.Namespace) -> int:
    from bioimage_mcp.bootstrap.doctor import doctor

    return doctor(json_output=args.json)


def _handle_list(args: argparse.Namespace) -> int:
    from bioimage_mcp.bootstrap.list import list_tools

    return list_tools(json_output=args.json, tool=args.tool)


def _handle_configure(args: argparse.Namespace) -> int:
    from bioimage_mcp.bootstrap.configure import configure

    return configure()


def _handle_status(args: argparse.Namespace) -> int:
    from bioimage_mcp.bootstrap.status import status

    return status(json_output=args.json)


def _handle_cleanup(args: argparse.Namespace) -> int:
    from bioimage_mcp.bootstrap.cleanup import cleanup

    return cleanup(dry_run=args.dry_run, json_output=args.json, force=args.force)


def _handle_pin(args: argparse.Namespace) -> int:
    from bioimage_mcp.bootstrap.pin import pin

    return pin(args.ref_id, unpin=False, json_output=args.json)


def _handle_unpin(args: argparse.Namespace) -> int:
    from bioimage_mcp.bootstrap.pin import pin

    return pin(args.ref_id, unpin=True, json_output=args.json)


def _handle_serve(args: argparse.Namespace) -> int:
    from bioimage_mcp.bootstrap.serve import serve

    return serve(stdio=args.stdio)


def _handle_remove(args: argparse.Namespace) -> int:
    from bioimage_mcp.bootstrap.remove import remove_tool

    return remove_tool(args.tool, yes=args.yes)


def _handle_run(args: argparse.Namespace) -> int:
    from bioimage_mcp.bootstrap.run import run

    params = {}
    if args.param:
        for p in args.param:
            if "=" in p:
                k, v = p.split("=", 1)
                params[k] = v
            else:
                print(f"Warning: ignoring malformed param {p}", file=sys.stderr)

    inputs = {}
    if args.input:
        for i in args.input:
            if "=" in i:
                k, v = i.split("=", 1)
                inputs[k] = v
            else:
                print(f"Warning: ignoring malformed input {i}", file=sys.stderr)

    return run(
        tool_id=args.tool_id,
        params=params,
        inputs=inputs,
        session_id=args.session or "cli-session",
        json_output=args.json,
    )


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    handler = getattr(args, "_handler", None)
    if handler is None:
        parser.error("No command provided")

    try:
        return int(handler(args))
    except BioimageMcpError as exc:
        _print_error(exc.code, str(exc), details=exc.details, debug=bool(args.debug))
        return 1
    except PermissionError as exc:
        _print_error("PERMISSION", str(exc), details=None, debug=bool(args.debug))
        return 1
    except Exception as exc:  # noqa: BLE001
        if args.debug:
            raise
        _print_error("INTERNAL", f"{type(exc).__name__}: {exc}", details=None, debug=False)
        print("Re-run with --debug for traceback", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
