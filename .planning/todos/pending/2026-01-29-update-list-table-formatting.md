---
created: 2026-01-29T14:30
title: Update bioimage-mcp list table formatting and versioning
area: tooling
files:
  - src/bioimage_mcp/api/handlers.py
  - src/bioimage_mcp/cli.py
---

## Problem

The current output of the `bioimage-mcp list` command (and corresponding API) uses redundant prefixes (e.g., 'tool.*') and does not provide granular package version information for the installed tools in the environment. This makes it harder for users to identify the specific versions of libraries like `phasorpy` or `scipy` being used.

## Solution

Modify the listing logic to:
- Remove 'tool.' prefixes from the Tool column.
- Format packages with adaptors in the base environment as 'base.<package>' (e.g., 'base.phasorpy', 'base.scipy').
- Report function counts per package rather than just per tool-pack.
- Retrieve and display the actual release version number of the installed package from the environment.
