# Technology Stack

**Project:** Bioimage-MCP
**Researched:** 2026-01-22

## Recommended Stack

### Core Framework
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **Python** | 3.13 | Core Server Language | Latest stable with performance improvements; core server has light deps. |
| **MCP SDK** | Latest | Server Protocol | Standard implementation of Model Context Protocol. |
| **Pydantic** | v2 | Validation | High-performance schema validation for IPC messages. |

### Environment Management
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **Micromamba** | Latest | Package Manager | Significantly faster than Conda; essential for CI/CD and user experience. |
| **Conda Lock** | Latest | Reproducibility | Ensures identical environments across platforms (Linux/macOS/Win). |

### Infrastructure
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **Subprocess** | Stdlib | Process Isolation | Robust, standard way to isolate tool environments. |
| **NDJSON** | N/A | IPC Format | Simple, streamable, language-agnostic message framing. |
| **SQLite** | 3.x | State/Registry | Lightweight, file-based storage for run logs and tool registry. |

### Data & I/O
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **bioio** | Latest | Image I/O | Universal read/write for microscopy formats. |
| **OME-TIFF** | N/A | Interchange Format | Standard, metadata-rich format for file-based handoff. |
| **OME-Zarr** | N/A | Interchange Format | For very large, chunked datasets. |

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| **IPC** | Stdin/Stdout NDJSON | ZeroMQ / gRPC | Stdin/Stdout is simpler, requires no extra ports/deps, and sufficient for control flow. |
| **Env Manager** | Micromamba | venv / pip | Scientific packages (PyTorch, bioformats) often require Conda for non-Python binary deps. |
| **Isolation** | Subprocesses | Docker | Docker requires root/daemon, harder for average user setup; Conda is standard in science. |

## Sources

- Validated against existing `bioimage-mcp` codebase.
- Validated against `MicroscopyLM` architectural patterns.
