from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

import numpy as np
import tifffile

from tests.smoke.utils.mcp_client import TestMCPClient


def _ensure_sample_data() -> tuple[Path, Path, Path]:
    root = Path("datasets/synthetic")
    root.mkdir(parents=True, exist_ok=True)

    img_2d = root / "test_2d.tif"
    if not img_2d.exists():
        tifffile.imwrite(img_2d, np.random.randint(0, 255, (128, 128), dtype=np.uint8))

    img_3d = root / "test_3d.tif"
    if not img_3d.exists():
        tifffile.imwrite(img_3d, np.random.randint(0, 255, (16, 128, 128), dtype=np.uint8))

    img_tracking = root / "test_tracking.tif"
    if not img_tracking.exists():
        tifffile.imwrite(img_tracking, np.random.randint(0, 255, (10, 128, 128), dtype=np.uint8))

    return img_2d, img_3d, img_tracking


def _bioimage_ref(path: Path) -> dict[str, str]:
    return {"type": "BioImageRef", "uri": path.resolve().as_uri()}


async def _run_interactive(
    client: TestMCPClient,
    *,
    label: str,
    tool_id: str,
    image_path: Path,
    check_responsive: bool,
    expect_commit: bool,
) -> dict:
    print(f"\n--- {label} ---")
    print(f"Launching {tool_id} with image: {image_path}")
    run_task = asyncio.create_task(
        client.call_tool(
            "run",
            {
                "id": tool_id,
                "inputs": {"image": _bioimage_ref(image_path)},
            },
        )
    )

    await asyncio.sleep(4)
    if run_task.done():
        result = await run_task
        print("run() returned before GUI interaction:")
        print(json.dumps(result, indent=2))
        return result

    if check_responsive:
        print("Running concurrent MCP checks while viewer is open...")
        listed, described = await asyncio.gather(
            client.call_tool("list", {"path": "micro_sam", "flatten": True, "limit": 200}),
            client.call_tool("describe", {"id": tool_id}),
        )
        listed_ids = [item.get("id") for item in listed.get("items", [])]
        print(f"list() contains {tool_id}: {tool_id in listed_ids}")
        print(f"describe() returned id: {described.get('id')}")

    if expect_commit:
        print("Create a mask and click 'Commit [C]' before closing the viewer.")
    else:
        print("Close the viewer without committing changes.")

    print("Then close the viewer to continue.")
    result = await run_task
    print("run() result:")
    print(json.dumps(result, indent=2))
    return result


async def verify_phase_23() -> None:
    print("=== Phase 23: Interactive Bridge Verification ===")
    print(
        "Display env: "
        f"DISPLAY={os.environ.get('DISPLAY')!r} "
        f"WAYLAND_DISPLAY={os.environ.get('WAYLAND_DISPLAY')!r} "
        f"WSL_DISTRO_NAME={os.environ.get('WSL_DISTRO_NAME')!r}"
    )
    img_2d, img_3d, img_tracking = _ensure_sample_data()

    client = TestMCPClient(call_timeout_s=None)
    await client.start_with_timeout(30)
    try:
        await _run_interactive(
            client,
            label="2D Annotator",
            tool_id="micro_sam.sam_annotator.annotator_2d",
            image_path=img_2d,
            check_responsive=True,
            expect_commit=True,
        )
        await _run_interactive(
            client,
            label="3D Annotator",
            tool_id="micro_sam.sam_annotator.annotator_3d",
            image_path=img_3d,
            check_responsive=False,
            expect_commit=True,
        )
        await _run_interactive(
            client,
            label="Tracking Annotator",
            tool_id="micro_sam.sam_annotator.annotator_tracking",
            image_path=img_tracking,
            check_responsive=False,
            expect_commit=True,
        )

        print("\nNo-edits check: close the next 2D session without committing changes.")
        result = await _run_interactive(
            client,
            label="2D Annotator (No edits)",
            tool_id="micro_sam.sam_annotator.annotator_2d",
            image_path=img_2d,
            check_responsive=False,
            expect_commit=False,
        )
        warnings = result.get("warnings", [])
        print(f"Warnings: {warnings}")

        print("\nVerification session finished.")
    finally:
        await client.stop()


if __name__ == "__main__":
    asyncio.run(verify_phase_23())
