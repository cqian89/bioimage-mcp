import asyncio
import json
import os
import sys

# Add the project root to sys.path to ensure we can import from tests
sys.path.append(os.getcwd())

from tests.smoke.utils.mcp_client import TestMCPClient


async def run_requested_check():
    client = TestMCPClient()
    try:
        print("Starting MCP server...")
        await client.start_with_timeout(30.0)

        fn_id = "base.io.bioimage.export"
        tool_name = "run"

        # EXACTLY as requested by user
        arguments = {
            "id": fn_id,
            "inputs": {"image": "d53d0c66aa074c9787580acba3609f74"},
            "params": {
                "dest_path": "datasets/FLUTE_FLIM_data_tif/outputs/hMSC_control_loaded.ome.tif"
            },
        }

        print(f"Calling tool {tool_name} for function {fn_id}...")
        result = await client.session.call_tool(tool_name, arguments=arguments)

        # Check if the result content is JSON
        content = result.content[0].text
        try:
            parsed = json.loads(content)
            status = parsed.get("status")
            if status in ["success", "completed"]:
                print("SUCCESS: Export completed successfully.")
            else:
                print(f"FAILURE: Export status is {status}.")
                if "error" in parsed:
                    print(f"Error: {parsed['error']['message']}")

                log_ref = parsed.get("log_ref")
                if log_ref and log_ref.get("uri"):
                    log_path = log_ref["uri"].replace("file://", "")
                    if os.path.exists(log_path):
                        print("--- Relevant Log Lines ---")
                        with open(log_path) as f:
                            lines = f.readlines()
                            # Show last 20 lines or error-containing lines
                            for line in lines[-20:]:
                                print(line.strip())
        except Exception as e:
            print(f"Could not parse result content: {e}")
            print(content)

    finally:
        await client.stop()


if __name__ == "__main__":
    asyncio.run(run_requested_check())
