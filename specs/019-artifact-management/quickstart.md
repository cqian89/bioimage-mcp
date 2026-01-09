# Storage & Artifact Management Quickstart

This guide provides a quick reference for managing disk space and artifact retention in `bioimage-mcp`.

## 1. Overview

`bioimage-mcp` generates significant amounts of data (images, logs, tables) during analysis workflows. Efficient storage management ensures your workstation or CI environment doesn't run out of disk space.

**Default Policy:**
*   **Storage Quota:** 50 GB
*   **Retention Period:** 7 days
*   **Warning Threshold:** 80% (logs a warning)
*   **Critical Threshold:** 95% (blocks new runs until space is cleared)

---

## 2. Checking Storage Status

Monitor your current usage to avoid hitting the critical threshold.

```bash
# See current usage summary
bioimage-mcp storage status

# Get machine-readable output for scripts
bioimage-mcp storage status --json
```

---

## 3. Cleaning Up Old Data

Use the `prune` command to remove data that is no longer needed based on your retention policy.

```bash
# Preview what would be deleted (safe!)
bioimage-mcp storage prune --dry-run

# Actually delete expired sessions
bioimage-mcp storage prune

# Delete without confirmation (useful for CI)
bioimage-mcp storage prune --force

# Override retention period (e.g., delete sessions older than 3 days)
bioimage-mcp storage prune --older-than 3
```

---

## 4. Protecting Important Sessions

If you have a workflow result that should never be automatically deleted, you can "pin" it.

```bash
# Find sessions to pin
bioimage-mcp storage list --state completed

# Pin a session to prevent cleanup
bioimage-mcp storage pin ses_abc123

# Unpin when you no longer need it
bioimage-mcp storage pin ses_abc123 --unpin
```

---

## 5. Browsing Sessions

List and filter sessions to identify large or expired datasets.

```bash
# List all sessions
bioimage-mcp storage list

# Filter by state (active, completed, expired, pinned)
bioimage-mcp storage list --state expired

# Sort by size to find large sessions
bioimage-mcp storage list --sort size

# Get detailed JSON for automation
bioimage-mcp storage list --json
```

---

## 6. Configuration

You can customize storage behavior in your `.bioimage-mcp/config.yaml` file.

```yaml
storage:
  quota_bytes: 107374182400  # 100GB
  warning_threshold: 0.80
  critical_threshold: 0.95
  retention_days: 14
  auto_cleanup_enabled: false
```

### Environment Overrides
For CI/CD pipelines, use environment variables to override settings:

```bash
export BIOIMAGE_MCP_STORAGE_QUOTA_BYTES=10737418240  # 10GB for CI
export BIOIMAGE_MCP_STORAGE_RETENTION_DAYS=1
```

---

## 7. Common Scenarios

### CI Pipeline Cleanup
Prevent stale data from accumulating on CI runners.

```bash
# At the start of a CI job: Clear out any leftovers
bioimage-mcp storage prune --force

# At the end of a CI job: Clear everything just created
bioimage-mcp storage prune --force --older-than 0
```

### Developer Disk Full
Quickly identify and resolve storage issues.

```bash
# Check what's using space
bioimage-mcp storage status
bioimage-mcp storage list --sort size

# Preview and then perform cleanup
bioimage-mcp storage prune --dry-run
bioimage-mcp storage prune
```

### Protecting Publication Data
Ensure critical analysis results are safe from automatic pruning.

```bash
# Find your important session
bioimage-mcp storage list --state completed

# Pin it
bioimage-mcp storage pin ses_important_results

# Verify it's protected
bioimage-mcp storage list --state pinned
```
