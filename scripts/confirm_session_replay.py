#!/usr/bin/env python
"""Confirm/reproduce session_replay transport failures.

This script starts the MCP server over stdio and runs a few session_replay
scenarios (baseline + overrides). It captures:
- tool request/response JSON
- server stderr (including crash tracebacks)

Usage:
  python scripts/confirm_session_replay.py \
    --workflow-json datasets/FLUTE_FLIM_data_tif/outputs/04-outputs/workflow_session.json

Defaults for override replay match the report:
- input: datasets/FLUTE_FLIM_data_tif/Fluorescein_hMSC.tif
- export dir: datasets/FLUTE_FLIM_data_tif/outputs/04-outputs
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import time
from contextlib import AsyncExitStack
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


def _now_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def _safe_json(obj: Any) -> Any:
    """Best-effort JSON serializer for logging."""
    try:
        json.dumps(obj)
        return obj
    except TypeError:
        return {"_repr": repr(obj)}


def _parse_mcp_result(result: Any) -> dict[str, Any]:
    # mcp returns a CallToolResult w/ .content text blocks
    if hasattr(result, "content") and result.content:
        first = result.content[0]
        text = getattr(first, "text", None)
        if text is None:
            return {"_raw": repr(result.content)}
        try:
            return json.loads(text)
        except Exception:
            return {"text": text}
    if isinstance(result, dict):
        return result
    return {"_raw": repr(result)}


async def _call_tool(
    session: ClientSession,
    *,
    tool: str,
    arguments: dict[str, Any],
    timeout_s: float,
) -> dict[str, Any]:
    async with asyncio.timeout(timeout_s):
        raw = await session.call_tool(tool, arguments=arguments)
    return _parse_mcp_result(raw)


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--workflow-json",
        required=True,
        help="Path to exported workflow record JSON file",
    )
    parser.add_argument(
        "--fluorescein-path",
        default="datasets/FLUTE_FLIM_data_tif/Fluorescein_hMSC.tif",
        help="New input image for override replay (repo-relative or absolute)",
    )
    parser.add_argument(
        "--export-dir",
        default="datasets/FLUTE_FLIM_data_tif/outputs/04-outputs",
        help="Directory for overridden export outputs (repo-relative or absolute)",
    )
    parser.add_argument(
        "--out-dir",
        default=None,
        help="Output directory for logs (default: repro_tmp/session_replay_confirm_<ts>)",
    )
    parser.add_argument(
        "--call-timeout-s",
        type=float,
        default=600.0,
        help="Timeout per MCP tool call",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    workflow_path = (repo_root / args.workflow_json).resolve()
    if not workflow_path.exists():
        raise SystemExit(f"workflow_json not found: {workflow_path}")

    fluorescein_path = Path(args.fluorescein_path)
    if not fluorescein_path.is_absolute():
        fluorescein_path = (repo_root / fluorescein_path).resolve()
    if not fluorescein_path.exists():
        raise SystemExit(f"fluorescein_path not found: {fluorescein_path}")

    export_dir = Path(args.export_dir)
    if not export_dir.is_absolute():
        export_dir = (repo_root / export_dir).resolve()
    export_dir.mkdir(parents=True, exist_ok=True)

    out_dir = (
        Path(args.out_dir)
        if args.out_dir
        else repo_root / "repro_tmp" / f"session_replay_confirm_{_now_stamp()}"
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    stderr_path = out_dir / "server.stderr.log"
    interactions_path = out_dir / "interactions.jsonl"
    summary_path = out_dir / "summary.json"

    workflow_ref = {
        # ref_id is required by ArtifactRef, but replay uses uri when present.
        "ref_id": "c786968e574b4909bc7dded50dc95c64",
        "type": "TableRef",
        "uri": workflow_path.as_uri(),
        "format": "workflow-record-json",
    }

    env = dict(os.environ)
    env.setdefault("PYTHONFAULTHANDLER", "1")
    env.setdefault("BIOIMAGE_MCP_LOG_LEVEL", "DEBUG")

    server = StdioServerParameters(
        command="python",
        args=["-m", "bioimage_mcp", "serve", "--stdio"],
        cwd=str(repo_root),
        env=env,
    )

    run_summary: dict[str, Any] = {
        "started_at": datetime.now(UTC).isoformat(),
        "repo_root": str(repo_root),
        "workflow_json": str(workflow_path),
        "workflow_uri": workflow_ref["uri"],
        "fluorescein_path": str(fluorescein_path),
        "export_dir": str(export_dir),
        "results": [],
    }

    exit_stack = AsyncExitStack()
    session: ClientSession | None = None

    def log_event(event: dict[str, Any]) -> None:
        with interactions_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=True) + "\n")

    try:
        with stderr_path.open("w+", encoding="utf-8") as stderr_file:
            read_stream, write_stream = await exit_stack.enter_async_context(
                stdio_client(server, errlog=stderr_file)
            )
            session = ClientSession(read_stream, write_stream)
            await exit_stack.enter_async_context(session)

            t0 = time.perf_counter()
            await session.initialize()
            run_summary["initialize_ms"] = (time.perf_counter() - t0) * 1000

            # 0) sanity: list tools
            req0 = {"include_counts": True}
            log_event({"tool": "list", "arguments": _safe_json(req0)})
            res0 = await _call_tool(
                session, tool="list", arguments=req0, timeout_s=args.call_timeout_s
            )
            log_event({"tool": "list", "result": _safe_json(res0)})
            run_summary["results"].append({"tool": "list", "ok": True})

            # 1) dry-run replay
            req1 = {
                "workflow_ref": workflow_ref,
                "inputs": {},
                "dry_run": True,
            }
            log_event(
                {
                    "tool": "session_replay",
                    "scenario": "baseline_dry_run",
                    "arguments": _safe_json(req1),
                }
            )
            try:
                res1 = await _call_tool(
                    session,
                    tool="session_replay",
                    arguments=req1,
                    timeout_s=args.call_timeout_s,
                )
                log_event(
                    {
                        "tool": "session_replay",
                        "scenario": "baseline_dry_run",
                        "result": _safe_json(res1),
                    }
                )
                run_summary["results"].append(
                    {"tool": "session_replay", "scenario": "baseline_dry_run", "result": res1}
                )
            except Exception as exc:  # noqa: BLE001
                log_event(
                    {
                        "tool": "session_replay",
                        "scenario": "baseline_dry_run",
                        "exception": repr(exc),
                    }
                )
                run_summary["results"].append(
                    {
                        "tool": "session_replay",
                        "scenario": "baseline_dry_run",
                        "exception": repr(exc),
                    }
                )

            # 1b) baseline real replay (same images, same export paths)
            req1b = {
                "workflow_ref": workflow_ref,
                "inputs": {},
            }
            log_event(
                {
                    "tool": "session_replay",
                    "scenario": "baseline_real",
                    "arguments": _safe_json(req1b),
                }
            )
            try:
                res1b = await _call_tool(
                    session,
                    tool="session_replay",
                    arguments=req1b,
                    timeout_s=args.call_timeout_s,
                )
                log_event(
                    {
                        "tool": "session_replay",
                        "scenario": "baseline_real",
                        "result": _safe_json(res1b),
                    }
                )
                run_summary["results"].append(
                    {"tool": "session_replay", "scenario": "baseline_real", "result": res1b}
                )
            except Exception as exc:  # noqa: BLE001
                log_event(
                    {
                        "tool": "session_replay",
                        "scenario": "baseline_real",
                        "exception": repr(exc),
                    }
                )
                run_summary["results"].append(
                    {"tool": "session_replay", "scenario": "baseline_real", "exception": repr(exc)}
                )

            # 2) replay with export path overrides (same input)
            same_export_overrides = {
                "step:4": {
                    "params": {"path": str(export_dir / "hMSC_control_mean_replay.ome.tif")}
                },
                "step:5": {
                    "params": {"path": str(export_dir / "hMSC_control_real_replay.ome.tif")}
                },
                "step:6": {
                    "params": {"path": str(export_dir / "hMSC_control_imag_replay.ome.tif")}
                },
            }
            req2 = {
                "workflow_ref": workflow_ref,
                "inputs": {},
                "step_overrides": same_export_overrides,
            }
            log_event(
                {
                    "tool": "session_replay",
                    "scenario": "same_input_new_exports",
                    "arguments": _safe_json(req2),
                }
            )
            try:
                res2 = await _call_tool(
                    session,
                    tool="session_replay",
                    arguments=req2,
                    timeout_s=args.call_timeout_s,
                )
                log_event(
                    {
                        "tool": "session_replay",
                        "scenario": "same_input_new_exports",
                        "result": _safe_json(res2),
                    }
                )
                run_summary["results"].append(
                    {"tool": "session_replay", "scenario": "same_input_new_exports", "result": res2}
                )
            except Exception as exc:  # noqa: BLE001
                log_event(
                    {
                        "tool": "session_replay",
                        "scenario": "same_input_new_exports",
                        "exception": repr(exc),
                    }
                )
                run_summary["results"].append(
                    {
                        "tool": "session_replay",
                        "scenario": "same_input_new_exports",
                        "exception": repr(exc),
                    }
                )

            # 3) replay with input+export overrides (Fluorescein_hMSC.tif)
            fluorescein_overrides = {
                "step:0": {"params": {"path": str(fluorescein_path)}},
                "step:1": {"params": {"path": str(fluorescein_path)}},
                "step:4": {"params": {"path": str(export_dir / "Fluorescein_hMSC_mean.ome.tif")}},
                "step:5": {"params": {"path": str(export_dir / "Fluorescein_hMSC_real.ome.tif")}},
                "step:6": {"params": {"path": str(export_dir / "Fluorescein_hMSC_imag.ome.tif")}},
            }
            req3 = {
                "workflow_ref": workflow_ref,
                "inputs": {},
                "step_overrides": fluorescein_overrides,
            }
            log_event(
                {"tool": "session_replay", "scenario": "fluorescein", "arguments": _safe_json(req3)}
            )
            try:
                res3 = await _call_tool(
                    session,
                    tool="session_replay",
                    arguments=req3,
                    timeout_s=args.call_timeout_s,
                )
                log_event(
                    {
                        "tool": "session_replay",
                        "scenario": "fluorescein",
                        "result": _safe_json(res3),
                    }
                )
                run_summary["results"].append(
                    {"tool": "session_replay", "scenario": "fluorescein", "result": res3}
                )
            except Exception as exc:  # noqa: BLE001
                log_event(
                    {
                        "tool": "session_replay",
                        "scenario": "fluorescein",
                        "exception": repr(exc),
                    }
                )
                run_summary["results"].append(
                    {"tool": "session_replay", "scenario": "fluorescein", "exception": repr(exc)}
                )

            # 3) capture server stderr
            try:
                stderr_file.flush()
                stderr_file.seek(0)
                run_summary["server_stderr"] = stderr_file.read()
            except Exception as exc:  # noqa: BLE001
                run_summary["server_stderr"] = f"<failed to read stderr: {exc}>"
    finally:
        try:
            await exit_stack.aclose()
        except Exception:
            # If the server crashed, closing can itself fail; best-effort.
            pass

    run_summary["ended_at"] = datetime.now(UTC).isoformat()
    summary_path.write_text(
        json.dumps(run_summary, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
    )

    # Minimal CLI output for humans
    print(str(out_dir))
    if run_summary.get("server_stderr"):
        tail = run_summary["server_stderr"].splitlines()[-50:]
        print("\n".join(tail))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(main()))
    except KeyboardInterrupt:
        raise SystemExit(130)
